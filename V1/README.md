# AutoResearch Framework V1 — Modular Research Loop

This is the mature, V1 iteration of the AutoResearch framework. It is a modular, high-autonomy environment designed for professional scientific discovery and technical optimization.

## Core Architecture

The framework is split into three foundational modules:

1.  **The Mission ([`Goal.md`](Goal.md))**: Defines the "What". Contains objectives, scoring rationale, and acceptance criteria.
2.  **The Process ([`Loop.md`](Loop.md))**: Defines the "How". Outlines the 5-phase iterative cycle, stagnation recovery, and monitoring strategies.
3.  **The Identity ([`Agent.md`](Agent.md))**: Defines the "Who". Consolidates the researcher persona, professional philosophy, and operational rules.

## File Reference

| File / Folder | Purpose |
| :--- | :--- |
| **`Goal.md`** | Mission objectives, scoring formula, and evaluation rationale. |
| **`Loop.md`** | Macro optimization methodology and breakthrough tactics. |
| **`Agent.md`** | **Primary source of truth** for researcher persona and operational rigor. |
| **`exp/`** | The Laboratory. Primary workspace for all experimental code and logic. |
| **`results/`** | Structured experimental records (`results.csv`) and metrics. |
| **`runs/`** | Historical snapshot archive (best vs. trials). |
| **`user_notes.md`** | Real-time ledger for human-in-the-loop directives and feedback. |

## Initiating the Research Program

The autonomous research program is triggered by an explicit user directive in the CLI:
> **"Start the loop using the [Agent Persona] persona."**

Upon this trigger, the agent will:
1.  **Initialize**: Synchronize with the mission defined in `Goal.md`.
2.  **Analyze**: Enter Phase 1 (Diagnosis) of the research methodology in `Loop.md`.
3.  **Persist**: Operate autonomously through the Analyze → Hypothesize → Innovate → Execute → Document cycle until the mission is complete.

## Operational Standards

- **Hypothesis-Driven**: Every modification to the `exp/` directory must be preceded by a technical hypothesis.
- **Result Integrity**: All experimental outcomes must be documented in `results/results.csv`.
- **Surgical Innovation**: Favor structural code improvements over simple hyperparameter tuning.

## Execution Interface

```bash
# Setup Environment
pip install -e .

# Run Research/Experiment Logic
python exp/main.py

# Evaluate Candidate (Standard interface)
python [PROJECT_EVAL_SCRIPT] --eval
```
