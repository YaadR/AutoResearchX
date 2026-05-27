#!/usr/bin/env python
"""AutoResearch-style parameter optimization loop for paper-adherent baselines.

This file performs random/smart bounded search over each baseline's allowed
parameters for each dataset. It keeps only improvements per baseline × dataset,
logs every experiment, and rewrites dashboard.html after each trial.
"""
from __future__ import annotations

import argparse
import csv
import multiprocessing as mp
import json
import math
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["JAX_PLATFORMS"] = "cpu"
os.environ["JAX_PLATFORM_NAME"] = "cpu"
os.environ.setdefault("XLA_PYTHON_CLIENT_PREALLOCATE", "false")

import numpy as np

from train.baselines import BASELINE_REGISTRY
from train.scripts.data_io import LOCAL_SMALL_FILES, data_type_for_name, load_dataset
from train.scripts.dashboard import write_dashboard
from train.scripts.plot_viz import render_best_visual


DATASET_TARGETS = {
    "afhq": 0.5,
    "gp": 0.25,
    "gp2d": 0.25,
}

RETIRE_COST_THRESHOLD = 1.0


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_logs() -> None:
    for path, header in [
        (Path("reasoning.csv"), ["timestamp", "experiment_id", "baseline", "dataset", "decision", "mean_cost", "best_cost", "params", "reasoning"]),
        (Path("reasoning_concise.csv"), ["timestamp", "experiment_id", "baseline", "dataset", "decision", "mean_cost", "best_cost", "short_note"]),
    ]:
        if not path.exists():
            with path.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(header)


def append_reasoning(row: dict[str, Any]) -> None:
    ensure_logs()
    with open("reasoning.csv", "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            row["timestamp"], row["experiment_id"], row["baseline"], row["dataset"], row["decision"],
            f"{row['mean_cost']:.8f}", f"{row['best_cost']:.8f}", json.dumps(row["params"], sort_keys=True), row["reasoning"],
        ])
    with open("reasoning_concise.csv", "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            row["timestamp"], row["experiment_id"], row["baseline"], row["dataset"], row["decision"],
            f"{row['mean_cost']:.8f}", f"{row['best_cost']:.8f}", row["short_note"],
        ])


def load_progress() -> dict[str, Any]:
    path = Path("artifacts/progress.json")
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"updated_at": None, "experiments": [], "best": {}}


def save_progress(progress: dict[str, Any]) -> None:
    Path("artifacts").mkdir(exist_ok=True)
    progress["updated_at"] = now_iso()
    Path("artifacts/progress.json").write_text(json.dumps(progress, indent=2, ensure_ascii=False), encoding="utf-8")
    write_dashboard(progress, "dashboard.html")


def best_entry_needs_calibration(best_entry: dict[str, Any] | None, *, sample_count: int, target: float,
                                 rtio: float, reltar: bool) -> bool:
    if not best_entry:
        return False
    return (
        int(best_entry.get("sample_count", -1)) != int(sample_count)
        or not math.isclose(float(best_entry.get("target", float("nan"))), float(target), rel_tol=0.0, abs_tol=1e-12)
        or not math.isclose(float(best_entry.get("rtio", float("nan"))), float(rtio), rel_tol=0.0, abs_tol=1e-12)
        or bool(best_entry.get("reltar", False)) != bool(reltar)
    )


def evaluate_baseline(cls, params: dict[str, Any], samples: list[np.ndarray], *, data_type: str,
                      target: float, rtio: float, reltar: bool, max_failures: int = 3) -> tuple[float, dict[str, float]]:
    costs = []
    fid = []
    tar = []
    failures = 0
    for x in samples:
        try:
            model = cls(**params, data_type=data_type, target=target)
            model.smooth(x, target=target, record_loss=True, record_snaps=False, rtio=rtio, reltar=reltar)
            if model.final_loss is None or not np.isfinite(model.final_loss):
                raise FloatingPointError("non-finite final loss")
            costs.append(float(model.final_loss))
            fid.append(float(model.fidelity_term[-1]))
            tar.append(float(model.target_term[-1]))
        except Exception as exc:
            failures += 1
            if failures > max_failures:
                return float("inf"), {"fidelity": float("inf"), "target": float("inf"), "failures": failures}
    return float(np.mean(costs)), {
        "fidelity": float(np.mean(fid)) if fid else float("inf"),
        "target": float(np.mean(tar)) if tar else float("inf"),
        "failures": float(failures),
    }


def mutate_around_best(cls, rng: np.random.Generator, best_params: dict[str, Any] | None, explore_prob: float = 0.35) -> dict[str, Any]:
    if best_params is None or rng.random() < explore_prob:
        return cls.sample_params(rng=rng)
    params = dict(best_params)
    for k, bounds in cls.PARAM_BOUNDS.items():
        lo, hi = bounds
        if k not in params:
            continue
        v = params[k]
        if isinstance(v, int) or k == "iterations":
            step = max(1, int(round(0.25 * (hi - lo))))
            nv = int(np.clip(int(v) + rng.integers(-step, step + 1), lo, hi))
        else:
            if lo > 0:
                nv = float(np.exp(np.log(float(v)) + rng.normal(0.0, 0.35)))
            else:
                nv = float(v + rng.normal(0.0, 0.1 * (hi - lo)))
            nv = float(np.clip(nv, lo, hi))
        params[k] = nv
    if "sigma_final" in params and "sigma" in params:
        params["sigma_final"] = min(float(params["sigma_final"]), float(params["sigma"]))
    return params


def mutate_with_stagnation(cls, rng: np.random.Generator, best_params: dict[str, Any] | None, *, stagnant_streak: int) -> dict[str, Any]:
    if best_params is None:
        return cls.sample_params(rng=rng)
    if stagnant_streak >= 10:
        params = cls.sample_params(rng=rng)
    elif stagnant_streak >= 5:
        params = mutate_around_best(cls, rng, best_params, explore_prob=0.9)
    elif stagnant_streak >= 3:
        params = mutate_around_best(cls, rng, best_params, explore_prob=0.6)
    else:
        params = mutate_around_best(cls, rng, best_params, explore_prob=0.35)
    if stagnant_streak >= 5:
        # Push one random parameter toward a bound to force a larger move when a pair has gone flat.
        name = rng.choice(list(cls.PARAM_BOUNDS.keys()))
        lo, hi = cls.PARAM_BOUNDS[name]
        if name in params:
            params[name] = lo if rng.random() < 0.5 else hi
        if "sigma_final" in params and "sigma" in params:
            params["sigma_final"] = min(float(params["sigma_final"]), float(params["sigma"]))
    return params


def method_guided_stagnant_params(
    cls,
    rng: np.random.Generator,
    best_params: dict[str, Any],
    *,
    baseline_name: str,
    dataset_name: str,
) -> dict[str, Any]:
    params = dict(best_params)
    if baseline_name == "anisotropic_diffusion":
        if dataset_name == "gp2d":
            draw = rng.random()
            center_k = float(best_params.get("k", 0.019222161822303702))
            if draw < 0.78:
                params["iterations"] = cls.PARAM_BOUNDS["iterations"][1]
                params["delta_t"] = cls.PARAM_BOUNDS["delta_t"][1]
                params["k"] = float(np.clip(rng.normal(center_k, 0.0000000035), 0.019222154, 0.019222170))
            elif draw < 0.94:
                params["iterations"] = cls.PARAM_BOUNDS["iterations"][1]
                params["delta_t"] = cls.PARAM_BOUNDS["delta_t"][1]
                params["k"] = float(np.clip(rng.normal(center_k, 0.000000010), 0.019222140, 0.019222185))
            elif draw < 0.985:
                params["iterations"] = cls.PARAM_BOUNDS["iterations"][1]
                params["delta_t"] = float(rng.uniform(0.2488, cls.PARAM_BOUNDS["delta_t"][1]))
                params["k"] = float(np.clip(rng.normal(center_k, 0.000000020), 0.019222125, 0.019222205))
            else:
                params["iterations"] = int(rng.integers(120, cls.PARAM_BOUNDS["iterations"][1] + 1))
                params["delta_t"] = float(rng.uniform(0.12, cls.PARAM_BOUNDS["delta_t"][1]))
                params["k"] = float(np.exp(rng.uniform(np.log(0.012), np.log(0.060))))
        else:
            params["iterations"] = int(rng.integers(200, cls.PARAM_BOUNDS["iterations"][1] + 1))
            params["delta_t"] = float(rng.uniform(0.205, cls.PARAM_BOUNDS["delta_t"][1]))
            params["k"] = float(np.exp(rng.uniform(np.log(0.018), np.log(0.04))))
    elif baseline_name == "bilateral_filter":
        if dataset_name == "gp2d":
            draw = rng.random()
            if draw < 0.88:
                params["sigma_s"] = float(np.exp(rng.uniform(np.log(15.902520), np.log(15.902526))))
                params["sigma_r"] = float(np.exp(rng.uniform(np.log(0.4130572), np.log(0.4130576))))
                params["iterations"] = 8
            elif draw < 0.97:
                params["sigma_s"] = float(np.exp(rng.uniform(np.log(15.88), np.log(15.94))))
                params["sigma_r"] = float(np.exp(rng.uniform(np.log(0.410), np.log(0.418))))
                params["iterations"] = int(rng.integers(7, 11))
            else:
                params["sigma_s"] = float(np.exp(rng.uniform(np.log(12.0), np.log(24.0))))
                params["sigma_r"] = float(np.exp(rng.uniform(np.log(0.25), np.log(0.70))))
                params["iterations"] = int(rng.integers(4, 13))
        else:
            params["sigma_s"] = float(np.exp(rng.uniform(np.log(12.0), np.log(cls.PARAM_BOUNDS["sigma_s"][1]))))
            params["sigma_r"] = float(np.exp(rng.uniform(np.log(0.002), np.log(0.25))))
            params["iterations"] = int(rng.integers(8, cls.PARAM_BOUNDS["iterations"][1] + 1))
    elif baseline_name == "weighted_least_squares":
        if dataset_name == "gp2d":
            if rng.random() < 0.97:
                params["lamb"] = float(np.exp(rng.uniform(np.log(0.560868), np.log(0.560874))))
                params["alpha"] = float(rng.uniform(2.953663, 2.953670))
            else:
                params["lamb"] = float(np.exp(rng.uniform(np.log(0.56075), np.log(0.56098))))
                params["alpha"] = float(rng.uniform(2.95355, 2.95382))
        elif dataset_name == "afhq":
            if rng.random() < 0.92:
                params["lamb"] = float(np.exp(rng.uniform(np.log(1.269262), np.log(1.269278))))
                params["alpha"] = float(rng.uniform(2.999978, 2.999990))
            else:
                params["lamb"] = float(np.exp(rng.uniform(np.log(1.15), np.log(1.42))))
                params["alpha"] = float(rng.uniform(2.80, cls.PARAM_BOUNDS["alpha"][1]))
        else:
            draw = rng.random()
            if draw < 0.88:
                params["lamb"] = float(np.exp(rng.uniform(np.log(109.91), np.log(109.965))))
                params["alpha"] = float(rng.uniform(1.05327, 1.05338))
            elif draw < 0.97:
                params["lamb"] = float(np.exp(rng.uniform(np.log(109.65), np.log(110.35))))
                params["alpha"] = float(rng.uniform(1.0526, 1.0541))
            else:
                params["lamb"] = float(np.exp(rng.uniform(np.log(104.0), np.log(118.0))))
                params["alpha"] = float(rng.uniform(1.025, 1.085))
    elif baseline_name == "smoothed_l0_regularization":
        if dataset_name == "gp":
            draw = rng.random()
            if draw < 0.94:
                center_weight = float(best_params.get("weight", 0.04213463880669634))
                center_sigma = float(best_params.get("sigma", 0.24442777027974172))
                center_sigma_final = float(best_params.get("sigma_final", 0.006711910596015094))
                center_lr = float(best_params.get("lr", 0.001002482315712418))
                center_fidelity = float(best_params.get("fidelity", 0.5610356488695584))
                params["weight"] = float(np.clip(np.exp(np.log(center_weight) + rng.normal(0.0, 0.00045)), 0.042105, 0.042155))
                params["sigma"] = float(np.clip(np.exp(np.log(center_sigma) + rng.normal(0.0, 0.00045)), 0.24438, 0.24448))
                params["sigma_final"] = min(
                    float(params["sigma"]),
                    float(np.clip(np.exp(np.log(center_sigma_final) + rng.normal(0.0, 0.00055)), 0.006707, 0.006716)),
                )
                params["iterations"] = int(rng.integers(198, cls.PARAM_BOUNDS["iterations"][1] + 1))
                params["lr"] = float(np.clip(np.exp(np.log(center_lr) + rng.normal(0.0, 0.0005)), 0.00100225, 0.00100275))
                params["fidelity"] = float(np.clip(np.exp(np.log(center_fidelity) + rng.normal(0.0, 0.0008)), 0.5602, 0.5619))
            elif draw < 0.985:
                params["weight"] = float(np.exp(rng.uniform(np.log(0.045), np.log(0.085))))
                params["sigma"] = float(np.exp(rng.uniform(np.log(0.225), np.log(0.285))))
                params["sigma_final"] = min(float(params["sigma"]), float(np.exp(rng.uniform(np.log(0.0055), np.log(0.0100)))))
                params["iterations"] = int(rng.integers(185, cls.PARAM_BOUNDS["iterations"][1] + 1))
                params["lr"] = float(np.exp(rng.uniform(np.log(0.0010), np.log(0.0018))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.45), np.log(0.70))))
            else:
                params["weight"] = float(np.exp(rng.uniform(np.log(0.012), np.log(0.095))))
                params["sigma"] = float(np.exp(rng.uniform(np.log(0.115), np.log(0.38))))
                params["sigma_final"] = min(float(params["sigma"]), float(np.exp(rng.uniform(np.log(0.0035), np.log(0.018)))))
                params["iterations"] = int(rng.integers(120, cls.PARAM_BOUNDS["iterations"][1] + 1))
                params["lr"] = float(np.exp(rng.uniform(np.log(0.001), np.log(0.0022))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.05), np.log(1.0))))
        elif dataset_name == "gp2d":
            draw = rng.random()
            if draw < 0.62:
                center_weight = float(best_params.get("weight", 0.027073373625069386))
                center_sigma = float(best_params.get("sigma", 0.011163))
                center_sigma_final = float(best_params.get("sigma_final", 0.010239787324963886))
                center_lr = float(best_params.get("lr", 0.0010771))
                center_fidelity = float(best_params.get("fidelity", 0.23011294770536428))
                params["weight"] = float(np.clip(np.exp(np.log(center_weight) + rng.normal(0.0, 0.0012)), 0.027068, 0.027080))
                params["sigma"] = float(np.clip(np.exp(np.log(center_sigma) + rng.normal(0.0, 0.0012)), 0.011155, 0.011166))
                params["sigma_final"] = min(
                    float(params["sigma"]),
                    float(np.clip(np.exp(np.log(center_sigma_final) + rng.normal(0.0, 0.0012)), 0.010236, 0.010245)),
                )
                params["iterations"] = 198
                params["lr"] = float(np.clip(np.exp(np.log(center_lr) + rng.normal(0.0, 0.0012)), 0.0010765, 0.0010780))
                params["fidelity"] = float(np.clip(np.exp(np.log(center_fidelity) + rng.normal(0.0, 0.0014)), 0.2294, 0.2308))
            elif draw < 0.82:
                params["weight"] = float(np.exp(rng.uniform(np.log(0.020), np.log(0.040))))
                params["sigma"] = float(np.exp(rng.uniform(np.log(0.0102), np.log(0.0145))))
                params["sigma_final"] = min(float(params["sigma"]), float(np.exp(rng.uniform(np.log(0.0075), np.log(0.0125)))))
                params["iterations"] = int(rng.integers(170, cls.PARAM_BOUNDS["iterations"][1] + 1))
                params["lr"] = float(np.exp(rng.uniform(np.log(0.0008), np.log(0.0019))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.16), np.log(0.34))))
            else:
                params["weight"] = float(np.exp(rng.uniform(np.log(0.003), np.log(0.12))))
                params["sigma"] = float(np.exp(rng.uniform(np.log(0.004), np.log(0.060))))
                params["sigma_final"] = min(float(params["sigma"]), float(np.exp(rng.uniform(np.log(0.0015), np.log(0.030)))))
                params["iterations"] = int(rng.integers(45, cls.PARAM_BOUNDS["iterations"][1] + 1))
                params["lr"] = float(np.exp(rng.uniform(np.log(0.00025), np.log(0.0040))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.03), np.log(1.25))))
        else:
            draw = rng.random()
            if draw < 0.88:
                params["weight"] = float(np.exp(rng.uniform(np.log(0.0052052), np.log(0.0052074))))
                params["sigma"] = float(np.exp(rng.uniform(np.log(0.0366858), np.log(0.0366888))))
                params["sigma_final"] = min(float(params["sigma"]), float(np.exp(rng.uniform(np.log(0.0035121), np.log(0.0035128)))))
                params["iterations"] = 199
                params["lr"] = float(np.exp(rng.uniform(np.log(0.00100203), np.log(0.00100216))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.5318), np.log(0.5327))))
            elif draw < 0.975:
                params["weight"] = float(np.exp(rng.uniform(np.log(0.005202), np.log(0.005210))))
                params["sigma"] = float(np.exp(rng.uniform(np.log(0.036684), np.log(0.036701))))
                params["sigma_final"] = min(float(params["sigma"]), float(np.exp(rng.uniform(np.log(0.0035116), np.log(0.0035142)))))
                params["iterations"] = 199
                params["lr"] = float(np.exp(rng.uniform(np.log(0.0010019), np.log(0.0010024))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.5310), np.log(0.5340))))
            elif draw < 0.995:
                params["weight"] = float(np.exp(rng.uniform(np.log(0.0055), np.log(0.012))))
                params["sigma"] = float(np.exp(rng.uniform(np.log(0.034), np.log(0.046))))
                params["sigma_final"] = min(float(params["sigma"]), float(np.exp(rng.uniform(np.log(0.0032), np.log(0.0065)))))
                params["iterations"] = int(rng.integers(185, cls.PARAM_BOUNDS["iterations"][1] + 1))
                params["lr"] = float(np.exp(rng.uniform(np.log(0.0010), np.log(0.0017))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.36), np.log(0.62))))
            else:
                params["weight"] = float(np.exp(rng.uniform(np.log(0.00435), np.log(0.00495))))
                params["sigma"] = float(np.exp(rng.uniform(np.log(0.0470), np.log(0.0496))))
                params["sigma_final"] = min(float(params["sigma"]), float(np.exp(rng.uniform(np.log(0.0030), np.log(0.00325)))))
                params["iterations"] = int(rng.integers(154, 160))
                params["lr"] = float(np.exp(rng.uniform(np.log(0.001), np.log(0.00104))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.18), np.log(0.8))))
    elif baseline_name == "rrslo":
        if dataset_name == "gp":
            params["weight"] = float(np.exp(rng.uniform(np.log(4.40), np.log(cls.PARAM_BOUNDS["weight"][1]))))
            params["sigma"] = float(np.exp(rng.uniform(np.log(0.0202), np.log(0.0222))))
            params["sigma_final"] = min(float(params["sigma"]), float(np.exp(rng.uniform(np.log(0.00605), np.log(0.00650)))))
            params["iterations"] = int(rng.integers(170, 179))
            params["lr"] = float(np.exp(rng.uniform(np.log(0.000355), np.log(0.000392))))
            params["cmax"] = float(np.exp(rng.uniform(np.log(325.0), np.log(370.0))))
            params["fidelity"] = float(np.exp(rng.uniform(np.log(0.325), np.log(0.355))))
            params["reweight_power"] = float(rng.uniform(0.038, 0.054))
        elif dataset_name == "gp2d":
            draw = rng.random()
            if draw < 0.82:
                params["weight"] = float(np.exp(rng.uniform(np.log(1.958255), np.log(1.958295))))
                params["sigma"] = float(np.exp(rng.uniform(np.log(0.01291958), np.log(0.01291972))))
                params["sigma_final"] = params["sigma"]
                params["iterations"] = cls.PARAM_BOUNDS["iterations"][1]
                params["lr"] = float(np.exp(rng.uniform(np.log(0.000400245), np.log(0.000400270))))
                params["cmax"] = float(np.exp(rng.uniform(np.log(383.74), np.log(383.81))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.426400), np.log(0.426425))))
                params["reweight_power"] = float(rng.uniform(0.030180, 0.030198))
            elif draw < 0.96:
                params["weight"] = float(np.exp(rng.uniform(np.log(1.4), np.log(2.7))))
                params["sigma"] = float(np.exp(rng.uniform(np.log(0.0105), np.log(0.0160))))
                params["sigma_final"] = min(float(params["sigma"]), float(np.exp(rng.uniform(np.log(0.0040), np.log(0.0140)))))
                params["iterations"] = int(rng.integers(240, cls.PARAM_BOUNDS["iterations"][1] + 1))
                params["lr"] = float(np.exp(rng.uniform(np.log(0.0002), np.log(0.0009))))
                params["cmax"] = float(np.exp(rng.uniform(np.log(180.0), np.log(700.0))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.20), np.log(0.70))))
                params["reweight_power"] = float(rng.uniform(0.0, 0.12))
            else:
                params["weight"] = float(np.exp(rng.uniform(np.log(1.956), np.log(1.961))))
                params["sigma"] = float(np.exp(rng.uniform(np.log(0.012915), np.log(0.012925))))
                params["sigma_final"] = params["sigma"]
                params["iterations"] = cls.PARAM_BOUNDS["iterations"][1]
                params["lr"] = float(np.exp(rng.uniform(np.log(0.0003998), np.log(0.0004008))))
                params["cmax"] = float(np.exp(rng.uniform(np.log(382.5), np.log(385.0))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.4255), np.log(0.4270))))
                params["reweight_power"] = float(rng.uniform(0.0295, 0.0310))
        else:
            draw = rng.random()
            if draw < 0.34:
                params["weight"] = cls.PARAM_BOUNDS["weight"][0]
                params["sigma"] = float(np.exp(rng.uniform(np.log(0.0675), np.log(0.0686))))
                params["sigma_final"] = min(float(params["sigma"]), float(np.exp(rng.uniform(np.log(0.0022), np.log(0.0025)))))
                params["iterations"] = int(rng.integers(82, 86))
                params["lr"] = cls.PARAM_BOUNDS["lr"][0]
                params["cmax"] = cls.PARAM_BOUNDS["cmax"][0]
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.62), np.log(0.65))))
                params["reweight_power"] = float(rng.uniform(0.008, 0.012))
            elif draw < 0.50:
                params["weight"] = float(np.exp(rng.uniform(np.log(0.000104), np.log(0.000122))))
                params["sigma"] = float(np.exp(rng.uniform(np.log(0.0670), np.log(0.0695))))
                params["sigma_final"] = min(float(params["sigma"]), float(np.exp(rng.uniform(np.log(0.00285), np.log(0.00318)))))
                params["iterations"] = int(rng.integers(74, 80))
                params["lr"] = float(np.exp(rng.uniform(np.log(0.000200), np.log(0.000206))))
                params["cmax"] = float(np.exp(rng.uniform(np.log(1.10), np.log(1.19))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.71), np.log(0.745))))
                params["reweight_power"] = float(rng.uniform(0.0, 0.004))
            elif draw < 0.70:
                params["weight"] = float(np.exp(rng.uniform(np.log(0.0010), np.log(0.055))))
                params["sigma"] = float(np.exp(rng.uniform(np.log(0.020), np.log(0.120))))
                params["sigma_final"] = min(float(params["sigma"]), float(np.exp(rng.uniform(np.log(0.0020), np.log(0.020)))))
                params["iterations"] = int(rng.integers(80, 221))
                params["lr"] = float(np.exp(rng.uniform(np.log(0.0005), np.log(0.0080))))
                params["cmax"] = float(np.exp(rng.uniform(np.log(2.0), np.log(80.0))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.05), np.log(0.45))))
                params["reweight_power"] = float(rng.uniform(0.0, 0.25))
            elif draw < 0.84:
                params["weight"] = float(np.exp(rng.uniform(np.log(0.12), np.log(cls.PARAM_BOUNDS["weight"][1]))))
                params["sigma"] = float(np.exp(rng.uniform(np.log(0.18), np.log(cls.PARAM_BOUNDS["sigma"][1]))))
                params["sigma_final"] = min(float(params["sigma"]), float(np.exp(rng.uniform(np.log(0.04), np.log(cls.PARAM_BOUNDS["sigma_final"][1])))))
                params["iterations"] = int(rng.integers(220, cls.PARAM_BOUNDS["iterations"][1] + 1))
                params["lr"] = float(np.exp(rng.uniform(np.log(0.0002), np.log(0.0018))))
                params["cmax"] = float(np.exp(rng.uniform(np.log(0.15), np.log(6.0))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.02), np.log(0.18))))
                params["reweight_power"] = float(rng.uniform(0.0, 0.8))
            elif draw < 0.94:
                params["weight"] = float(np.exp(rng.uniform(np.log(0.000112), np.log(0.000135))))
                params["sigma"] = float(np.exp(rng.uniform(np.log(0.0660), np.log(0.0735))))
                params["sigma_final"] = min(float(params["sigma"]), float(np.exp(rng.uniform(np.log(0.00255), np.log(0.00305)))))
                params["iterations"] = int(rng.integers(68, 74))
                params["lr"] = float(np.exp(rng.uniform(np.log(0.000202), np.log(0.000220))))
                params["cmax"] = float(np.exp(rng.uniform(np.log(1.03), np.log(1.12))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.66), np.log(0.71))))
                params["reweight_power"] = float(rng.uniform(0.004, 0.015))
            else:
                params["weight"] = float(np.exp(rng.uniform(np.log(0.00016), np.log(0.0060))))
                params["sigma"] = float(np.exp(rng.uniform(np.log(0.050), np.log(0.110))))
                params["sigma_final"] = min(float(params["sigma"]), float(np.exp(rng.uniform(np.log(0.0012), np.log(0.0060)))))
                params["iterations"] = int(rng.integers(40, 140))
                params["lr"] = float(np.exp(rng.uniform(np.log(0.00016), np.log(0.0016))))
                params["cmax"] = float(np.exp(rng.uniform(np.log(0.7), np.log(8.0))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.35), np.log(0.95))))
                params["reweight_power"] = float(rng.uniform(0.0, 0.08))
    elif baseline_name == "total_variation":
        if dataset_name == "afhq":
            draw = rng.random()
            center_weight = float(best_params.get("weight", 0.0003002086158290966))
            center_lr = float(best_params.get("lr", 0.0052))
            center_fidelity = float(best_params.get("fidelity", 0.458))
            if draw < 0.82:
                params["weight"] = float(np.clip(np.exp(np.log(center_weight) + rng.normal(0.0, 0.020)), 0.000245, 0.000305))
                params["iterations"] = 1
                params["lr"] = float(np.clip(np.exp(np.log(center_lr) + rng.normal(0.0, 0.030)), 0.00395, 0.00485))
                params["fidelity"] = float(np.clip(np.exp(np.log(center_fidelity) + rng.normal(0.0, 0.020)), 0.430, 0.480))
            elif draw < 0.96:
                params["weight"] = float(np.exp(rng.uniform(np.log(0.000220), np.log(0.000315))))
                params["iterations"] = 1
                params["lr"] = float(np.exp(rng.uniform(np.log(0.00335), np.log(0.00505))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.405), np.log(0.505))))
            elif draw < 0.985:
                params["weight"] = float(np.exp(rng.uniform(np.log(0.00010), np.log(0.00036))))
                params["iterations"] = 1
                params["lr"] = float(np.exp(rng.uniform(np.log(0.0024), np.log(0.0058))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.28), np.log(0.68))))
            else:
                params["weight"] = float(np.exp(rng.uniform(np.log(0.00025), np.log(0.0018))))
                params["iterations"] = int(rng.integers(1, 18))
                params["lr"] = float(np.exp(rng.uniform(np.log(0.0014), np.log(0.012))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.18), np.log(1.0))))
        elif dataset_name == "gp2d":
            draw = rng.random()
            center_weight = float(best_params.get("weight", 0.0007167))
            center_lr = float(best_params.get("lr", 0.006652213229978408))
            center_fidelity = float(best_params.get("fidelity", 0.3733373848559295))
            if draw < 0.88:
                params["weight"] = float(np.clip(np.exp(np.log(center_weight) + rng.normal(0.0, 0.0007)), 0.0007160, 0.0007174))
                params["iterations"] = 72
                params["lr"] = float(np.clip(np.exp(np.log(center_lr) + rng.normal(0.0, 0.0007)), 0.006646, 0.006657))
                params["fidelity"] = float(np.clip(np.exp(np.log(center_fidelity) + rng.normal(0.0, 0.0007)), 0.3729, 0.3738))
            elif draw < 0.94:
                params["weight"] = float(np.exp(rng.uniform(np.log(0.000715), np.log(0.000720))))
                params["iterations"] = int(rng.integers(71, 74))
                params["lr"] = float(np.exp(rng.uniform(np.log(0.00662), np.log(0.00668))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.371), np.log(0.376))))
            else:
                params["weight"] = float(np.exp(rng.uniform(np.log(0.000700), np.log(0.000730))))
                params["iterations"] = int(rng.integers(70, 76))
                params["lr"] = float(np.exp(rng.uniform(np.log(0.00650), np.log(0.00678))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.360), np.log(0.385))))
        else:
            draw = rng.random()
            if draw < 0.84:
                params["weight"] = float(np.exp(rng.uniform(np.log(0.20036), np.log(0.20045))))
                params["iterations"] = 3
                params["lr"] = float(np.exp(rng.uniform(np.log(0.04034), np.log(0.04038))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.79178), np.log(0.79205))))
            elif draw < 0.96:
                params["weight"] = float(np.exp(rng.uniform(np.log(0.020), np.log(1.0))))
                params["iterations"] = int(rng.integers(4, 100))
                params["lr"] = float(np.exp(rng.uniform(np.log(0.004), np.log(0.060))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.05), np.log(0.80))))
            else:
                params["weight"] = float(np.exp(rng.uniform(np.log(0.198), np.log(0.203))))
                params["iterations"] = 3
                params["lr"] = float(np.exp(rng.uniform(np.log(0.0400), np.log(0.0406))))
                params["fidelity"] = float(np.exp(rng.uniform(np.log(0.789), np.log(0.794))))
    for name, (lo, hi) in cls.PARAM_BOUNDS.items():
        if name not in params:
            continue
        if isinstance(lo, int) and isinstance(hi, int):
            params[name] = int(np.clip(int(round(params[name])), lo, hi))
        else:
            params[name] = float(np.clip(float(params[name]), lo, hi))
    if "sigma_final" in params and "sigma" in params:
        params["sigma_final"] = min(float(params["sigma_final"]), float(params["sigma"]))
    return params


def near_threshold_params(
    cls,
    rng: np.random.Generator,
    best_params: dict[str, Any],
    *,
    baseline_name: str,
    dataset_name: str,
) -> dict[str, Any]:
    params = mutate_around_best(cls, rng, best_params, explore_prob=0.0)
    if baseline_name == "anisotropic_diffusion":
        params["iterations"] = int(np.clip(round(rng.normal(float(best_params.get("iterations", 240)), 18)), 200, 260))
        params["delta_t"] = float(np.clip(rng.normal(float(best_params.get("delta_t", 0.24)), 0.010), 0.215, cls.PARAM_BOUNDS["delta_t"][1]))
        if dataset_name in {"gp", "afhq"}:
            params["k"] = float(np.clip(rng.normal(float(best_params.get("k", 0.028)), 0.0045), 0.018, 0.040))
        else:
            params["iterations"] = cls.PARAM_BOUNDS["iterations"][1]
            params["delta_t"] = cls.PARAM_BOUNDS["delta_t"][1]
            center = float(best_params.get("k", 0.019222161822303702))
            if rng.random() < 0.9:
                params["k"] = float(np.clip(rng.normal(center, 0.0000000045), 0.019222152, 0.019222172))
            else:
                params["k"] = float(np.clip(rng.normal(center, 0.000000018), 0.019222125, 0.019222205))
    return params


def summarize_param_shift(best_params: dict[str, Any] | None, params: dict[str, Any]) -> str:
    if not best_params:
        return "initial bounded sample"
    shifts = []
    for name in sorted(params):
        old = best_params.get(name)
        new = params.get(name)
        if old is None:
            shifts.append(f"{name} initialized to {new}")
            continue
        try:
            old_f = float(old)
            new_f = float(new)
        except (TypeError, ValueError):
            if old != new:
                shifts.append(f"{name} {old}->{new}")
            continue
        if abs(new_f - old_f) <= 1e-12:
            continue
        direction = "up" if new_f > old_f else "down"
        shifts.append(f"{name} {direction} {old_f:.4g}->{new_f:.4g}")
    return "; ".join(shifts[:4]) if shifts else "same parameters after clipping"


def method_reason(baseline_name: str) -> str:
    if baseline_name == "anisotropic_diffusion":
        return "probe diffusion time, step size, and edge-stopping k because the current best still has high target mismatch"
    if baseline_name == "bilateral_filter":
        return "probe the useful GP2D bilateral band around moderate spatial kernels and range selectivity after broad edge cases degraded"
    if baseline_name == "weighted_least_squares":
        return "probe larger WLS regularization and edge exponent because the best sits at the old global-smoothing limit"
    if baseline_name in {"rrslo", "smoothed_l0_regularization"}:
        return "probe continuation strength, learning rate, smoothing weight, fidelity balance, and RRSLO reweighting because recent keeps came from narrow edge regimes"
    if baseline_name == "total_variation":
        return "probe low-weight stable TV regimes after high-weight/high-step edge cases worsened the objective"
    return "probe paper-constrained parameters for this baseline"


def propose_candidate(
    cls,
    rng: np.random.Generator,
    *,
    baseline_name: str,
    dataset_name: str,
    target: float,
    best_cost: float,
    best_params: dict[str, Any] | None,
    stagnant_streak: int,
) -> tuple[dict[str, Any], str, str]:
    if best_params is None or not np.isfinite(best_cost):
        params = mutate_with_stagnation(cls, rng, best_params, stagnant_streak=stagnant_streak)
        strategy = "global_initialization"
    elif baseline_name == "anisotropic_diffusion" and (
        best_cost < 1.12 or (dataset_name == "gp2d" and best_cost < 1.35)
    ):
        params = near_threshold_params(
            cls,
            rng,
            best_params,
            baseline_name=baseline_name,
            dataset_name=dataset_name,
        )
        strategy = "near_threshold_anisotropic_exploit"
    elif baseline_name in {"weighted_least_squares", "smoothed_l0_regularization", "rrslo", "bilateral_filter", "total_variation"} and rng.random() < 0.985:
        params = method_guided_stagnant_params(
            cls,
            rng,
            best_params,
            baseline_name=baseline_name,
            dataset_name=dataset_name,
        )
        strategy = "method_guided_active_refinement"
    elif stagnant_streak >= 10:
        if baseline_name in {"weighted_least_squares", "smoothed_l0_regularization", "rrslo", "bilateral_filter"}:
            method_prob = 0.99 if baseline_name in {"smoothed_l0_regularization", "rrslo"} else 0.95
        else:
            method_prob = 0.85
        if rng.random() < method_prob:
            params = method_guided_stagnant_params(
                cls,
                rng,
                best_params,
                baseline_name=baseline_name,
                dataset_name=dataset_name,
            )
            strategy = "method_guided_stagnation_probe"
        else:
            params = mutate_around_best(cls, rng, best_params, explore_prob=0.45)
            strategy = "wide_local_refinement_after_stagnation"
    elif stagnant_streak >= 5:
        params = mutate_with_stagnation(cls, rng, best_params, stagnant_streak=stagnant_streak)
        strategy = "wide_exploration_after_stagnation"
    elif stagnant_streak >= 3:
        params = mutate_with_stagnation(cls, rng, best_params, stagnant_streak=stagnant_streak)
        strategy = "mixed_explore_exploit"
    else:
        params = mutate_with_stagnation(cls, rng, best_params, stagnant_streak=stagnant_streak)
        strategy = "local_refinement"
    shift = summarize_param_shift(best_params, params)
    hypothesis = (
        f"Candidate strategy={strategy}. For {baseline_name} × {dataset_name}, "
        f"{method_reason(baseline_name)}. Parameter change: {shift}. "
        f"Judge by mean positive cost J against target={target:.3f}; keep only if J improves current best {best_cost:.6f}."
    )
    return params, strategy, hypothesis


def make_trial_seed(global_seed: int, pair_index: int, completed_trials: int) -> int:
    seed_seq = np.random.SeedSequence([global_seed, pair_index, completed_trials + 1])
    return int(seed_seq.generate_state(1, dtype=np.uint32)[0])


def run_pair_trial(payload: dict[str, Any]) -> dict[str, Any]:
    t0 = time.time()
    try:
        cls = payload["cls"]
        rng = np.random.default_rng(payload["seed"])
        params, strategy, hypothesis = propose_candidate(
            cls,
            rng,
            baseline_name=payload["baseline"],
            dataset_name=payload["dataset"],
            target=payload["target"],
            best_cost=payload["best_cost"],
            best_params=payload["best_params"],
            stagnant_streak=payload["stagnant_streak"],
        )
        mean_cost, comp = evaluate_baseline(
            cls,
            params,
            payload["samples"],
            data_type=payload["data_type"],
            target=payload["target"],
            rtio=payload["rtio"],
            reltar=payload["reltar"],
        )
        return {
            "ok": True,
            "error": None,
            "pair_key": payload["pair_key"],
            "baseline": payload["baseline"],
            "dataset": payload["dataset"],
            "mean_cost": mean_cost,
            "components": comp,
            "params": params,
            "strategy": strategy,
            "hypothesis": hypothesis,
            "elapsed_sec": time.time() - t0,
            "kept": bool(mean_cost < payload["best_cost"]),
            "target": payload["target"],
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": repr(exc),
            "pair_key": payload.get("pair_key"),
            "baseline": payload.get("baseline"),
            "dataset": payload.get("dataset"),
            "mean_cost": float("inf"),
            "components": {"fidelity": float("inf"), "target": float("inf"), "failures": float("inf")},
            "params": payload.get("best_params") or {},
            "strategy": "worker_error",
            "hypothesis": "Worker failed before completing the proposed candidate evaluation.",
            "elapsed_sec": time.time() - t0,
            "kept": False,
            "target": payload.get("target"),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=20, help="Batch experiments per baseline × dataset in one loop iteration.")
    parser.add_argument("--sample-count", type=int, default=10, help="Max local small samples to evaluate.")
    parser.add_argument("--target", type=float, default=None, help="Override target sparsity ratio for all datasets.")
    parser.add_argument("--rtio", type=float, default=0.5, help="Fidelity ratio in reward. target weight is 1-rtio.")
    parser.add_argument("--reltar", action="store_true", help="Use target relative to original gradient density, matching functions.py option.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--baselines", nargs="*", default=list(BASELINE_REGISTRY.keys()))
    parser.add_argument("--datasets", nargs="*", default=list(LOCAL_SMALL_FILES.keys()))
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    random.seed(args.seed)
    progress = load_progress()
    ensure_logs()

    datasets: dict[str, list[np.ndarray]] = {}
    for name in args.datasets:
        path = Path(LOCAL_SMALL_FILES[name])
        if not path.exists():
            raise FileNotFoundError(f"Missing {path}. Run: python prepare.py --sample-count {args.sample_count}")
        samples = load_dataset(path, max_items=args.sample_count)
        if not samples:
            raise ValueError(f"No numeric arrays could be extracted from {path}; inspect train/scripts/data_io.py for schema mapping.")
        datasets[name] = samples

    experiment_id = max([e.get("experiment_id", 0) for e in progress.get("experiments", [])] or [0])
    pair_states: list[dict[str, Any]] = []
    experiment_counts: dict[str, int] = {}
    for exp in progress.get("experiments", []):
        key = f"{exp.get('baseline')} × {exp.get('dataset')}"
        experiment_counts[key] = experiment_counts.get(key, 0) + 1

    calibration_dirty = False
    for dataset_name in args.datasets:
        samples = datasets[dataset_name]
        data_type = data_type_for_name(dataset_name)
        target = float(args.target) if args.target is not None else DATASET_TARGETS.get(dataset_name, 0.25)
        for baseline_name in args.baselines:
            cls = BASELINE_REGISTRY[baseline_name]
            key = f"{baseline_name} × {dataset_name}"
            best_entry = progress.get("best", {}).get(key)
            if best_entry_needs_calibration(
                best_entry,
                sample_count=len(samples),
                target=target,
                rtio=args.rtio,
                reltar=args.reltar,
            ):
                old_cost = float(best_entry["mean_cost"])
                calibrated_cost, calibrated_components = evaluate_baseline(
                    cls,
                    best_entry["params"],
                    samples,
                    data_type=data_type,
                    target=target,
                    rtio=args.rtio,
                    reltar=args.reltar,
                )
                best_entry = {
                    **best_entry,
                    "mean_cost": calibrated_cost,
                    "components": calibrated_components,
                    "target": target,
                    "sample_count": len(samples),
                    "rtio": args.rtio,
                    "reltar": bool(args.reltar),
                    "calibrated_at": now_iso(),
                    "calibrated_from_mean_cost": old_cost,
                }
                progress.setdefault("best", {})[key] = best_entry
                calibration_dirty = True
                print(
                    f"{key}: calibrated best for sample_count={len(samples)} rtio={args.rtio:.3f} "
                    f"{old_cost:.6f}->{calibrated_cost:.6f}",
                    flush=True,
                )
            best_cost = float(best_entry["mean_cost"]) if best_entry else float("inf")
            best_params = best_entry.get("params") if best_entry else None
            history = [e for e in progress.get("experiments", []) if e.get("baseline") == baseline_name and e.get("dataset") == dataset_name]
            stagnant_streak = 0
            if history:
                current_best = float("inf")
                for exp in history:
                    mc = float(exp.get("mean_cost", float("inf")))
                    if mc < current_best:
                        current_best = mc
                        stagnant_streak = 0
                    else:
                        stagnant_streak += 1
            completed_trials = experiment_counts.get(key, 0)
            remaining_trials = args.trials
            retired = best_cost <= RETIRE_COST_THRESHOLD
            pair_states.append({
                "pair_key": key,
                "baseline_name": baseline_name,
                "dataset_name": dataset_name,
                "baseline_index": args.baselines.index(baseline_name),
                "dataset_index": args.datasets.index(dataset_name),
                "pair_index": len(pair_states),
                "cls": cls,
                "samples": samples,
                "data_type": data_type,
                "target": target,
                "best_cost": best_cost,
                "best_params": best_params,
                "stagnant_streak": stagnant_streak,
                "completed_trials": completed_trials,
                "remaining_trials": remaining_trials,
                "retired": retired,
            })
            if retired:
                print(
                    f"#{experiment_id:04d} {key}: retired best={best_cost:.6f} below {RETIRE_COST_THRESHOLD:.1f}",
                    flush=True,
                )

    if calibration_dirty:
        save_progress(progress)

    while True:
        batch_states = [state for state in pair_states if state["remaining_trials"] > 0 and not state["retired"]]
        if not batch_states:
            break
        payloads = []
        for state in batch_states:
            payloads.append({
                "pair_key": state["pair_key"],
                "baseline": state["baseline_name"],
                "dataset": state["dataset_name"],
                "cls": state["cls"],
                "samples": state["samples"],
                "data_type": state["data_type"],
                "target": state["target"],
                "rtio": args.rtio,
                "reltar": args.reltar,
                "best_cost": state["best_cost"],
                "best_params": state["best_params"],
                "stagnant_streak": state["stagnant_streak"],
                "seed": make_trial_seed(args.seed, state["pair_index"], state["completed_trials"]),
            })

        workers = max(1, min(len(payloads), os.cpu_count() or 1))
        ctx = mp.get_context("spawn")
        with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as executor:
            results = list(executor.map(run_pair_trial, payloads))

        for state, result in zip(batch_states, results):
            experiment_id += 1
            mean_cost = float(result["mean_cost"])
            comp = result["components"]
            params = result["params"]
            strategy = result.get("strategy", "unspecified")
            hypothesis = result.get("hypothesis", "")
            kept = bool(result["kept"] and result["ok"])
            decision = "kept" if kept else ("error" if not result["ok"] else "discarded")
            elapsed = float(result["elapsed_sec"])

            if kept:
                state["best_cost"] = mean_cost
                state["best_params"] = dict(params)
                state["stagnant_streak"] = 0
                visual_path = None
                visual_error = None
                try:
                    visual_path = render_best_visual(
                        state["baseline_name"],
                        state["dataset_name"],
                        params,
                        state["samples"][0],
                        target=state["target"],
                        rtio=args.rtio,
                        reltar=args.reltar,
                        mean_cost=mean_cost,
                        experiment_id=experiment_id,
                    )
                except Exception as exc:
                    visual_error = repr(exc)
                progress.setdefault("best", {})[state["pair_key"]] = {
                    "experiment_id": experiment_id,
                    "baseline": state["baseline_name"],
                    "dataset": state["dataset_name"],
                    "mean_cost": mean_cost,
                    "params": params,
                    "components": comp,
                    "target": state["target"],
                    "sample_count": len(state["samples"]),
                    "rtio": args.rtio,
                    "reltar": bool(args.reltar),
                }
                if visual_path:
                    progress["best"][state["pair_key"]]["visual_path"] = visual_path
                if visual_error:
                    progress["best"][state["pair_key"]]["visual_error"] = visual_error
            elif result["ok"]:
                state["stagnant_streak"] += 1
            else:
                state["stagnant_streak"] += 1

            state["completed_trials"] += 1
            state["remaining_trials"] = max(0, state["remaining_trials"] - 1)

            best_cost = state["best_cost"]
            reasoning = (
                f"Hypothesis: {hypothesis} "
                f"Mean cost={mean_cost:.6f}; fidelity={comp.get('fidelity'):.6f}; target={comp.get('target'):.6f}. "
                f"Kept only if this improves the baseline×dataset best cost. Runtime {elapsed:.2f}s."
            )
            if not result["ok"]:
                reasoning = f"Worker error: {result['error']}. " + reasoning
            short_note = f"{decision} via {strategy}: {mean_cost:.5f} vs best {best_cost:.5f}"
            row = {
                "timestamp": now_iso(),
                "experiment_id": experiment_id,
                "baseline": state["baseline_name"],
                "dataset": state["dataset_name"],
                "decision": decision,
                "mean_cost": mean_cost,
                "best_cost": best_cost,
                "params": params,
                "reasoning": reasoning,
                "short_note": short_note,
            }
            append_reasoning(row)
            progress.setdefault("experiments", []).append({
                **row,
                "kept": kept,
                "strategy": strategy,
                "hypothesis": hypothesis,
                "components": comp,
                "elapsed_sec": elapsed,
                "target": state["target"],
            })
            save_progress(progress)
            print(
                f"#{experiment_id:04d} {state['pair_key']}: {decision} target={state['target']:.3f} mean_cost={mean_cost:.6f} params={params}",
                flush=True,
            )
            if state["best_cost"] <= RETIRE_COST_THRESHOLD and not state["retired"]:
                state["retired"] = True
                print(
                    f"#{experiment_id:04d} {state['pair_key']}: retired best={state['best_cost']:.6f} below {RETIRE_COST_THRESHOLD:.1f}",
                    flush=True,
                )


if __name__ == "__main__":
    main()
