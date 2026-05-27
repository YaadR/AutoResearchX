# AutoResearch: A Framework for Autonomous Research Loops

AutoResearch is a **structured framework** for implementing autonomous optimization and research loops. It provides a template-based architecture that separates concerns across configuration, methodology, execution, and tracking—enabling systematic, large-scale exploration of complex problem spaces.

## Core Philosophy

The framework is built on the premise that **research can be automated and structured** through:

1. **Clear role definition** — Different personas (junior, senior) execute with different autonomy levels and strategic approaches.
2. **Separated concerns** — Problem-specific logic lives in `train.py`, while methodology and constraints are isolated in guidance files.
3. **Disciplined iteration** — A repeating macro loop (Analyze → Hypothesize → Innovate → Execute → Document → Sync) ensures methodical progress.
4. **Transparent tracking** — All experiments are logged with reasoning, enabling historical analysis and reproducibility.
5. **Scalability** — The framework anticipates context overflow and project growth, embedding strategies for efficient management.

## Project Structure

Each AutoResearch project (e.g., `V0/`) follows this organization:

```
project_folder/
├── README.md                          # Quick reference guide (file listing & key commands)
├── program.md                         # Complete methodology & constraints for the agent
├── agent_id_junior.md                 # Junior researcher role: directed, structured execution
├── agent_id_senior.md                 # Senior researcher role: strategic, deep innovation
├── user_notes.md                      # User's mid-loop feedback and directives
├── user_takes.md                      # Real-time ledger of user requests during the loop
├── prepare.py                         # Fixed evaluation harness (read-only)
├── train/train.py                     # Agent's laboratory: full authority to innovate
├── train/scripts/                     # Supporting scripts (utilities, analysis tools)
├── data/                              # Benchmark or domain-specific data
├── outputs/                           # Visualizations and metrics from each run
├── results.csv                        # Complete trial history with detailed reasoning
├── results_concise.csv                # Minimal metrics for visualization & quick ref
├── runs/
│   ├── trials/                        # Snapshot of every historical run
│   └── best/                          # Current best-kept configuration & outputs
└── reference/
    └── original_first_train.py        # Zero-init baseline for comparison
```

## File Roles & Responsibilities

### Core Guidance Files

- **`program.md`** — The agent's primary instruction manual. Contains the macro loop workflow, objectives, constraints, acceptance criteria, setup commands, and strategic guidance. Re-read periodically.

- **`agent_id_junior.md`** — Role definition for directed, methodical research. Emphasizes structured exploration, deliberate choices from documented possibilities, and rigorous tracking. Best for well-scoped optimization.

- **`agent_id_senior.md`** — Role definition for autonomous, strategic research. Emphasizes deep expertise, bold innovation, creative pivots, and principled decision-making. Best for exploratory or high-creativity tasks.

- **`user_notes.md`** — User's narrative feedback and strategic observations. Not part of the loop; used for human-readable documentation.

- **`user_takes.md`** — Dynamic ledger of specific user requests and mid-loop course corrections. Consulted frequently by the agent during execution.

### Execution & Benchmarking

- **`prepare.py`** — Fixed evaluation harness. Defines the benchmark, scoring, and data generation. **Read-only**—never edited by the agent. Ensures reproducibility and fairness.

- **`train/`** — The agent's laboratory directory. Full authority to create, modify, and delete any files within this directory for training, debugging, validation, and experimentation.
  - **`train/train.py`** — The main training script. The agent modifies this to implement hypotheses.
  - **`train/scripts/`** — Supporting utilities, analysis helpers, or domain-specific tools.
  - **Other files in `train/`** — Debug scripts, temporary test files, diagnostic utilities, exploratory code, etc. The agent creates and cleans these as needed.

### Tracking & Documentation

- **`results.csv`** — Complete experiment history. Each row documents a run's hyperparameters, outcome, reasoning, and status (kept/discarded/verification). Enables historical analysis.

- **`results_concise.csv`** — Minimal version used for visualization and quick reference. Agent updates this to keep research progress charts current.

- **`runs/trials/`** — Snapshot of every run's `train.py`, outputs, and metadata. Enables reproducibility and historical comparison.

- **`runs/best/`** — The currently kept best model configuration. Contains the best `train.py`, outputs, and metrics. Maintained by the agent; used as reference for next iterations.

- **`reference/original_first_train.py`** — The initial baseline `train.py`. Serves as the zero-init reference point for measuring progress.

### Outputs & Visualizations

- **`outputs/`** — Generated after each run. Contains dashboards, plots, loss curves, metrics, and any visualization the benchmark produces. Used to diagnose failure modes and guide next hypotheses.

## The Macro Loop

The agent executes an iterative cycle:

1. **Analyze** — Inspect the best run, identify weaknesses, and examine visualizations.
2. **Hypothesize** — Formulate a technical reason for a change based on analysis.
3. **Innovate** — Modify files in the `train/` directory (including `train.py`, utilities, or debug scripts) and implement the hypothesis.
4. **Execute** — Run the experiment using the evaluation harness.
5. **Document** — Log the run in `results.csv` and `results_concise.csv` with reasoning.
6. **Sync** — Regenerate progress visualizations and charts.

This cycle **repeats continuously** until the user stops the agent, integrating user feedback as it arrives.

## Key Design Principles

### 1. Separation of Concerns
- **Problem-agnostic infrastructure** (`program.md`, `prepare.py`, tracking files) stays stable.
- **Domain-specific innovation** lives entirely in the `train/` directory—including `train.py`, debug scripts, utilities, and any experimental files.
- Swapping to a new problem requires only replacing `prepare.py`, the `train/` directory, and data—not methodology.

### 2. Transparency & Reproducibility
- Every run is logged with full reasoning and status.
- Historical snapshots enable retrospective analysis and rollback.
- Benchmark harness is frozen, ensuring fair comparison.

### 3. Scalability & Context Hygiene
- As projects grow, the agent cleans up obsolete runs, consolidates logs, and summarizes findings.
- Periodic re-reading of `program.md` and role files keeps the agent aligned and prevents drift.
- Context management strategies (exponential backoff for polling, orderly documentation) prevent overwhelm.

### 4. Strategic Flexibility
- Role selection (junior vs. senior) tunes the agent's approach to task scope and creativity level.
- User mid-loop feedback (`user_takes.md`) integrates without halting the loop.
- Stagnation recovery protocols trigger bold, creative pivots when marginal gains plateau.

## Using AutoResearch on a New Problem

1. **Create a new project folder** (e.g., `V1/`, `experiment_name/`).

2. **Copy the template** from `V0/`:
   - Copy `program.md`, `agent_id_junior.md`, `agent_id_senior.md`, `README.md`.
   - Adapt these files minimally—they are largely problem-agnostic.

3. **Replace the problem-specific components:**
   - Write a new `prepare.py` that defines your benchmark, data, and scoring.
   - Write an initial `train.py` in the `train/` directory that implements a baseline for your domain.
   - Create domain-specific data in `data/`.

4. **Initialize tracking:**
   - Create empty `results.csv` and `results_concise.csv` with appropriate headers.
   - Create `runs/trials/` and `runs/best/` directories.

5. **Start the loop:**
   - Choose a role (junior or senior) and begin executing the macro loop.
   - The framework handles the rest: iteration, tracking, visualization, and scaling.

## Conceptual Strengths

- **Disciplined Experimentation:** Forces coherent hypotheses, not random parameter sweeps.
- **Audit Trail:** Complete history enables debugging, reproducibility, and learning from past decisions.
- **Adaptive Autonomy:** Supports both structured (junior) and creative (senior) modes.
- **Extensible:** New files, utilities, and domain-specific tools integrate naturally.
- **Sustainable:** Scales to hundreds of runs without losing clarity or context.

## Getting Started

1. Navigate to `V0/` and read [`V0/README.md`](V0/README.md).
2. Follow the quick-start commands to set up the environment.
3. Review `V0/program.md` for complete methodology.
4. Run your first experiment and observe the loop in action.