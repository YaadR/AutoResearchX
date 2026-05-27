"""
Fixed data-generation and evaluation harness for PINN-SINDy AutoResearch.

Usage:
    uv run prepare.py
    uv run prepare.py --force

This file is intentionally treated as read-only by the research agent after the
human accepts the benchmark. It creates a deterministic but deliberately harder
controlled double-mass benchmark:

* nonlinear friction: smooth Coulomb + quadratic drag
* weak cubic spring nonlinearities
* multiple input families: multisine, chirp, step, PRBS-like square waves, pulses
* validation includes held-out trajectories across every input family

The agent should optimize train.py against evaluate_candidate(). Lower
val_score is better. The score includes average rollout error, derivative error,
worst-case force-family rollout error, and sparse-model complexity.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Dict, List

import numpy as np
from scipy.integrate import solve_ivp

# -----------------------------------------------------------------------------
# Fixed constants: do not modify during autoresearch runs
# -----------------------------------------------------------------------------
DATA_VERSION = "hard_forcing_friction_v1"
CACHE_DIR = Path(os.path.expanduser("~")) / ".cache" / f"pinn_sindy_autoresearch_{DATA_VERSION}"
DATA_DIR = CACHE_DIR / "data"
TRAIN_PATH = DATA_DIR / "train.npz"
VAL_PATH = DATA_DIR / "val.npz"
META_PATH = DATA_DIR / "metadata.json"

TIME_BUDGET = 300  # seconds. Fixed wall-clock budget for train.py experiments.
DT = 0.02
T_FINAL = 12.0
T_EVAL = np.arange(0.0, T_FINAL + 0.5 * DT, DT, dtype=np.float64)
STATE_DIM = 4
CONTROL_DIM = 1
FORCE_PARAM_DIM = 10

TRAIN_TRAJECTORIES = 20
VAL_TRAJECTORIES = 10
NOISE_STD = 0.015

CASE_NAMES = {
    0: "multisine",
    1: "chirp",
    2: "step",
    3: "prbs",
    4: "pulse",
}

# System parameters for the synthetic benchmark. The agent sees these only
# indirectly through data and the fixed evaluation harness.
M1 = 1.0
M2 = 1.0
K1 = 1.00
K2 = 1.10
B1 = 0.075
B2 = 0.105
K1_CUBIC = 0.045
K2_CUBIC = 0.030
KCOUPLE_CUBIC = 0.035
COULOMB1 = 0.045
COULOMB2 = 0.035
QUAD_DRAG1 = 0.020
QUAD_DRAG2 = 0.018
FRICTION_VEPS = 0.045

# Score weights. Lower is better.
ROLLOUT_WEIGHT = 1.00
DERIVATIVE_WEIGHT = 0.25
WORST_CASE_WEIGHT = 0.10
SPARSITY_WEIGHT = 1.0e-3
BAD_SCORE = 1.0e9


@dataclass(frozen=True)
class EvaluationResult:
    val_score: float
    val_rollout_nmse: float
    val_deriv_nmse: float
    val_worst_case_rollout_nmse: float
    complexity: int
    rollout_mse: float
    deriv_mse: float
    rollout_scale: float
    deriv_scale: float
    eval_seconds: float
    case_rollout_nmse: Dict[str, float]
    case_deriv_nmse: Dict[str, float]


def force_np(t: np.ndarray | float, force_params: np.ndarray) -> np.ndarray:
    """Known scalar control input u(t) for one trajectory.

    force_params layout:
        [kind, amp, f0, f1, phase, offset, duty, step_time, pulse_width, skew]

    The functions are deterministic and vectorized in t. Step and PRBS are not
    differentiable with respect to time, which is intentional: the smoother and
    sparse model must be robust to input discontinuities and broadband content.
    """
    kind_raw, amp, f0, f1, phase, offset, duty, step_time, pulse_width, skew = np.asarray(
        force_params, dtype=np.float64
    )
    kind = int(round(float(kind_raw)))
    t_arr = np.asarray(t, dtype=np.float64)

    if kind == 0:  # multisine
        u = offset
        u = u + amp * np.sin(2.0 * np.pi * f0 * t_arr + phase)
        u = u + 0.35 * amp * np.sin(2.0 * np.pi * f1 * t_arr - 0.7 * phase)
        u = u + 0.18 * amp * np.sin(2.0 * np.pi * (f0 + f1) * 0.5 * t_arr + skew)
        return u

    if kind == 1:  # chirp
        chirp_rate = (f1 - f0) / max(T_FINAL, 1e-12)
        arg = 2.0 * np.pi * (f0 * t_arr + 0.5 * chirp_rate * t_arr**2) + phase
        return offset + amp * np.sin(arg)

    if kind == 2:  # step with small sinusoidal background
        baseline = np.where(t_arr >= step_time, 1.0, -0.45)
        ripple = 0.12 * np.sin(2.0 * np.pi * f0 * t_arr + phase)
        return offset + amp * (baseline + ripple)

    if kind == 3:  # deterministic PRBS-like broadband square input
        raw = np.sin(2.0 * np.pi * f0 * t_arr + phase) + 0.55 * np.sin(2.0 * np.pi * f1 * t_arr + skew)
        square = np.where(raw >= 0.0, 1.0, -1.0)
        return offset + amp * square

    if kind == 4:  # pulse / impulse-like excitation with ringdown probe
        width = max(float(pulse_width), 0.06)
        pulse1 = np.exp(-0.5 * ((t_arr - step_time) / width) ** 2)
        pulse2 = -0.55 * np.exp(-0.5 * ((t_arr - (step_time + 2.5 * width + 0.35)) / (1.4 * width)) ** 2)
        ring = 0.18 * np.sin(2.0 * np.pi * f0 * t_arr + phase)
        return offset + amp * (pulse1 + pulse2 + ring)

    raise ValueError(f"unknown force kind {kind}")


def true_rhs(t: float, z: np.ndarray, force_params: np.ndarray) -> np.ndarray:
    """Ground-truth controlled nonlinear double mass-spring-friction dynamics."""
    x1, v1, x2, v2 = z
    u = float(force_np(t, force_params))
    rel_x = x2 - x1
    rel_v = v2 - v1

    # Smooth Coulomb friction + quadratic drag. This creates a meaningful reason
    # for the agent to try tanh/sign/abs custom SINDy terms, not just polynomials.
    fric1 = COULOMB1 * np.tanh(v1 / FRICTION_VEPS) + QUAD_DRAG1 * v1 * abs(v1)
    fric2 = COULOMB2 * np.tanh(v2 / FRICTION_VEPS) + QUAD_DRAG2 * v2 * abs(v2)

    dx1 = v1
    dv1 = (
        -B1 * v1
        - K1 * x1
        + K2 * rel_x
        + B2 * rel_v
        - K1_CUBIC * x1**3
        + KCOUPLE_CUBIC * rel_x**3
        - fric1
        + u
    ) / M1

    dx2 = v2
    dv2 = (
        -B2 * rel_v
        - K2 * rel_x
        - K2_CUBIC * x2**3
        - KCOUPLE_CUBIC * rel_x**3
        - fric2
    ) / M2
    return np.array([dx1, dv1, dx2, dv2], dtype=np.float64)


def _sample_initial_state(rng: np.random.Generator) -> np.ndarray:
    return np.array(
        [
            rng.uniform(-1.25, 1.25),
            rng.uniform(-0.65, 0.65),
            rng.uniform(-1.10, 1.10),
            rng.uniform(-0.65, 0.65),
        ],
        dtype=np.float64,
    )


def _sample_force_params(rng: np.random.Generator, kind: int, validation: bool = False) -> np.ndarray:
    # Validation is slightly shifted, not outlandish: the learned vector field
    # should generalize across input families rather than memorize trajectories.
    amp_range = (0.45, 1.45) if not validation else (0.55, 1.65)
    f0_range = (0.10, 0.75) if not validation else (0.08, 0.90)
    f1_range = (0.75, 2.10) if not validation else (0.90, 2.45)
    amp = rng.uniform(*amp_range)
    f0 = rng.uniform(*f0_range)
    f1 = rng.uniform(max(f0 + 0.15, f1_range[0]), f1_range[1])
    phase = rng.uniform(-np.pi, np.pi)
    offset = rng.uniform(-0.20, 0.20)
    duty = rng.uniform(0.25, 0.75)
    step_time = rng.uniform(2.0, 8.5)
    pulse_width = rng.uniform(0.08, 0.45)
    skew = rng.uniform(-np.pi, np.pi)
    return np.array([kind, amp, f0, f1, phase, offset, duty, step_time, pulse_width, skew], dtype=np.float64)


def _simulate_one(z0: np.ndarray, force_params: np.ndarray) -> Dict[str, np.ndarray]:
    sol = solve_ivp(
        lambda t, z: true_rhs(t, z, force_params),
        (float(T_EVAL[0]), float(T_EVAL[-1])),
        z0,
        t_eval=T_EVAL,
        rtol=1e-9,
        atol=1e-9,
        method="LSODA",
        max_step=DT / 2.0,
    )
    if not sol.success:
        raise RuntimeError(f"solve_ivp failed: {sol.message}")
    x_clean = sol.y.T.astype(np.float64)
    u = force_np(T_EVAL, force_params).reshape(-1, 1).astype(np.float64)
    dxdt = np.stack([true_rhs(float(t), x_clean[i], force_params) for i, t in enumerate(T_EVAL)])
    return {"x_clean": x_clean, "u": u, "dxdt": dxdt.astype(np.float64)}


def _make_split(n_trajectories: int, seed: int, validation: bool = False) -> Dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    x_clean: List[np.ndarray] = []
    x_meas: List[np.ndarray] = []
    dxdt_true: List[np.ndarray] = []
    controls: List[np.ndarray] = []
    z0s: List[np.ndarray] = []
    force_params: List[np.ndarray] = []
    force_kind: List[int] = []

    kinds = list(CASE_NAMES.keys())
    for i in range(n_trajectories):
        kind = kinds[i % len(kinds)]
        # Shuffle the order while preserving coverage.
        if i % len(kinds) == 0:
            rng.shuffle(kinds)
        z0 = _sample_initial_state(rng)
        fp = _sample_force_params(rng, kind, validation=validation)
        sim = _simulate_one(z0, fp)
        noise = rng.normal(0.0, NOISE_STD, sim["x_clean"].shape)
        x_clean.append(sim["x_clean"])
        x_meas.append(sim["x_clean"] + noise)
        dxdt_true.append(sim["dxdt"])
        controls.append(sim["u"])
        z0s.append(z0)
        force_params.append(fp)
        force_kind.append(kind)

    return {
        "t": T_EVAL.copy(),
        "x_clean": np.stack(x_clean),
        "x_meas": np.stack(x_meas),
        "dxdt_true": np.stack(dxdt_true),
        "u": np.stack(controls),
        "z0": np.stack(z0s),
        "force_params": np.stack(force_params),
        "force_kind": np.array(force_kind, dtype=np.int64),
        "dt": np.array(DT, dtype=np.float64),
    }


def prepare_data(force: bool = False) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if TRAIN_PATH.exists() and VAL_PATH.exists() and META_PATH.exists() and not force:
        print(f"Data already exists at {DATA_DIR}")
        return

    print(f"Generating deterministic hard benchmark data in {DATA_DIR} ...")
    train = _make_split(TRAIN_TRAJECTORIES, seed=123, validation=False)
    val = _make_split(VAL_TRAJECTORIES, seed=456, validation=True)
    np.savez_compressed(TRAIN_PATH, **train)
    np.savez_compressed(VAL_PATH, **val)
    metadata = {
        "version": DATA_VERSION,
        "system": "controlled nonlinear double mass-spring-friction benchmark",
        "state": ["x1", "v1", "x2", "v2"],
        "control": ["u"],
        "force_cases": CASE_NAMES,
        "dt": DT,
        "t_final": T_FINAL,
        "noise_std": NOISE_STD,
        "train_trajectories": TRAIN_TRAJECTORIES,
        "val_trajectories": VAL_TRAJECTORIES,
        "time_budget_seconds": TIME_BUDGET,
        "metric": (
            "val_score = rollout_nmse + 0.25 * deriv_nmse + "
            "0.10 * worst_case_force_rollout_nmse + 1e-03 * complexity"
        ),
    }
    with META_PATH.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print("Done! Ready to train.")


def verify_data_exists() -> None:
    if not (TRAIN_PATH.exists() and VAL_PATH.exists() and META_PATH.exists()):
        raise FileNotFoundError(
            f"Benchmark data not found at {DATA_DIR}. Run `uv run prepare.py` first."
        )


def load_split(split: str) -> Dict[str, np.ndarray]:
    verify_data_exists()
    path = TRAIN_PATH if split == "train" else VAL_PATH
    with np.load(path, allow_pickle=False) as data:
        return {k: data[k] for k in data.files}


def flatten_split(data: Dict[str, np.ndarray], measured: bool = True) -> Dict[str, np.ndarray]:
    """Flatten trajectory arrays into sample arrays for training code."""
    x_key = "x_meas" if measured else "x_clean"
    n_traj, n_time, _ = data[x_key].shape
    t = np.tile(data["t"].reshape(1, n_time, 1), (n_traj, 1, 1))
    z0 = np.repeat(data["z0"][:, None, :], n_time, axis=1)
    fp = np.repeat(data["force_params"][:, None, :], n_time, axis=1)
    force_kind = np.repeat(data["force_kind"][:, None], n_time, axis=1)
    traj_id = np.repeat(np.arange(n_traj)[:, None], n_time, axis=1)
    return {
        "t": t.reshape(-1, 1),
        "x": data[x_key].reshape(-1, STATE_DIM),
        "x_clean": data["x_clean"].reshape(-1, STATE_DIM),
        "dxdt_true": data["dxdt_true"].reshape(-1, STATE_DIM),
        "u": data["u"].reshape(-1, CONTROL_DIM),
        "z0": z0.reshape(-1, STATE_DIM),
        "force_params": fp.reshape(-1, FORCE_PARAM_DIM),
        "force_kind": force_kind.reshape(-1),
        "traj_id": traj_id.reshape(-1),
    }


def _rk4_rollout(
    predict_dxdt: Callable[[np.ndarray, np.ndarray], np.ndarray],
    z0: np.ndarray,
    force_params: np.ndarray,
    t_grid: np.ndarray,
) -> np.ndarray:
    """Fixed-step RK4 rollout of the learned vector field."""
    x = np.empty((len(t_grid), STATE_DIM), dtype=np.float64)
    x[0] = z0.astype(np.float64)
    for i in range(len(t_grid) - 1):
        t = float(t_grid[i])
        h = float(t_grid[i + 1] - t_grid[i])

        def f(t_local: float, z_local: np.ndarray) -> np.ndarray:
            u = np.array([[float(force_np(t_local, force_params))]], dtype=np.float64)
            dz = np.asarray(predict_dxdt(z_local.reshape(1, -1), u), dtype=np.float64).reshape(-1)
            if dz.shape[0] != STATE_DIM or not np.all(np.isfinite(dz)):
                raise FloatingPointError("predict_dxdt returned invalid derivative")
            return dz

        k1 = f(t, x[i])
        k2 = f(t + 0.5 * h, x[i] + 0.5 * h * k1)
        k3 = f(t + 0.5 * h, x[i] + 0.5 * h * k2)
        k4 = f(t + h, x[i] + h * k3)
        x[i + 1] = x[i] + (h / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
        if not np.all(np.isfinite(x[i + 1])) or np.linalg.norm(x[i + 1]) > 1e6:
            raise FloatingPointError("learned rollout diverged")
    return x


def evaluate_candidate(
    predict_dxdt: Callable[[np.ndarray, np.ndarray], np.ndarray],
    complexity: int,
) -> EvaluationResult:
    """Evaluate a learned controlled vector field on held-out trajectories."""
    start = time.time()
    val = load_split("val")
    try:
        x_val = val["x_clean"].reshape(-1, STATE_DIM)
        u_val = val["u"].reshape(-1, CONTROL_DIM)
        dx_true = val["dxdt_true"].reshape(-1, STATE_DIM)
        dx_pred = np.asarray(predict_dxdt(x_val, u_val), dtype=np.float64)
        if dx_pred.shape != dx_true.shape:
            raise ValueError(f"Bad derivative shape: expected {dx_true.shape}, got {dx_pred.shape}")
        if not np.all(np.isfinite(dx_pred)):
            raise FloatingPointError("non-finite derivative predictions")

        deriv_mse = float(np.mean((dx_pred - dx_true) ** 2))
        deriv_scale = float(np.mean(dx_true**2) + 1e-12)
        deriv_nmse = deriv_mse / deriv_scale

        rollout_errors: List[np.ndarray] = []
        case_rollout_values: Dict[str, List[float]] = {name: [] for name in CASE_NAMES.values()}
        case_deriv_values: Dict[str, List[float]] = {name: [] for name in CASE_NAMES.values()}

        cursor = 0
        n_time = len(val["t"])
        for i in range(val["x_clean"].shape[0]):
            kind = int(val["force_kind"][i])
            case_name = CASE_NAMES[kind]
            pred = _rk4_rollout(predict_dxdt, val["x_clean"][i, 0], val["force_params"][i], val["t"])
            err = (pred - val["x_clean"][i]) ** 2
            rollout_errors.append(err)
            denom_roll = float(np.mean(val["x_clean"][i] ** 2) + 1e-12)
            case_rollout_values[case_name].append(float(np.mean(err) / denom_roll))

            dx_slice = slice(cursor, cursor + n_time)
            dxe = (dx_pred[dx_slice] - dx_true[dx_slice]) ** 2
            denom_deriv = float(np.mean(dx_true[dx_slice] ** 2) + 1e-12)
            case_deriv_values[case_name].append(float(np.mean(dxe) / denom_deriv))
            cursor += n_time

        rollout_mse = float(np.mean(np.concatenate([e.reshape(-1) for e in rollout_errors])))
        rollout_scale = float(np.mean(val["x_clean"] ** 2) + 1e-12)
        rollout_nmse = rollout_mse / rollout_scale
        case_rollout_nmse = {k: float(np.mean(v)) for k, v in case_rollout_values.items() if v}
        case_deriv_nmse = {k: float(np.mean(v)) for k, v in case_deriv_values.items() if v}
        worst_case_rollout_nmse = max(case_rollout_nmse.values()) if case_rollout_nmse else BAD_SCORE

        score = (
            ROLLOUT_WEIGHT * rollout_nmse
            + DERIVATIVE_WEIGHT * deriv_nmse
            + WORST_CASE_WEIGHT * worst_case_rollout_nmse
            + SPARSITY_WEIGHT * int(complexity)
        )
        if not math.isfinite(score):
            score = BAD_SCORE
    except Exception:
        deriv_mse = rollout_mse = BAD_SCORE
        deriv_scale = rollout_scale = 1.0
        deriv_nmse = rollout_nmse = worst_case_rollout_nmse = BAD_SCORE
        score = BAD_SCORE
        case_rollout_nmse = {}
        case_deriv_nmse = {}

    return EvaluationResult(
        val_score=float(score),
        val_rollout_nmse=float(rollout_nmse),
        val_deriv_nmse=float(deriv_nmse),
        val_worst_case_rollout_nmse=float(worst_case_rollout_nmse),
        complexity=int(complexity),
        rollout_mse=float(rollout_mse),
        deriv_mse=float(deriv_mse),
        rollout_scale=float(rollout_scale),
        deriv_scale=float(deriv_scale),
        eval_seconds=float(time.time() - start),
        case_rollout_nmse=case_rollout_nmse,
        case_deriv_nmse=case_deriv_nmse,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare the fixed PINN-SINDy hard benchmark data.")
    parser.add_argument("--force", action="store_true", help="Regenerate data even if cache files exist.")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    prepare_data(force=args.force)
    with META_PATH.open("r", encoding="utf-8") as f:
        print(json.dumps(json.load(f), indent=2))
