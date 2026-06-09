# {{PROJECT_NAME}}: High-Autonomy Research Program

You are conducting an autonomous research loop to solve a complex {{RESEARCH_FIELD}} challenge. This is a **zero-knowledge start**. Your objective is to achieve a parsimonious, accurate, and robust solution through expert-level scientific experimentation and innovation.

## Research Environment

1. `README.md`: System overview and scoring metrics.
2. `agent_id_junior.md` & `agent_id_senior.md`: Your professional identity and methodological principles (choose based on autonomy level).
3. `user_notes.md`: Real-time ledger for specific user directives and mid-loop feedback.
5. `train/`: Your primary laboratory directory. You have full authority to create, modify, refactor, and delete any files within this directory to implement, test, debug, and innovate.
6. `results.csv` & `results_concise.csv`: Your experimental record.
7. `prepare.py`: The fixed evaluation harness (Read-only).

## Core Objective: {{CORE_OBJECTIVE_SUMMARY}}

The goal is to develop a model or solution that balances {{KEY_TRADEOFF_1}} with {{KEY_TRADEOFF_2}}. Use your expertise in {{FIELD_1}} and {{FIELD_2}} to bridge the gap between raw data/requirements and a high-performance, interpretable outcome.

**Driving Principles:**
- **Relentless Improvement:** Every cycle should aim for measurable progress. Be creative and bold in your hypotheses; combine ideas fearlessly.
- **Scientific Parsimony:** Favor solutions that are as simple as possible but no simpler. Avoid over-engineering; look for the fundamental drivers of performance.
- **Smart Efficiency:** Work in a way that scales. Avoid brute-force parameter sweeps; reason through each decision. Manage your token budget, maintain clean code, and delete what is no longer needed.
- **Order & Clarity:** Keep the `train/` directory, logs, and experimental artifacts well-organized. A clean workspace is a sharp mind.

## Degrees of Freedom & Research Domains

You are not limited to a predefined list of parameters. You are encouraged to innovate across these broad domains:

### 1. Representation & Architecture
- **Inductive Biases:** Design architectures or representations that respect the underlying structure of the problem (e.g., {{SYMMETRY_OR_STRUCTURE_EXAMPLE}}).
- **Feature Engineering:** Discover or derive features that simplify the learning task.

### 2. Constraints & Regularization
- **Domain-Specific Losses:** Design loss functions that enforce known constraints or physical/logical principles.
- **Sparsity & Selection:** Implement strategies to identify the most significant components of your model.

### 3. Optimization & Training Dynamics
- **Adaptive Weighting:** Implement strategies to balance competing objectives (e.g., data accuracy vs. constraint satisfaction).
- **Advanced Schedulers:** Design training regimes that handle the specific complexity or multi-scale nature of the task.

### 4. SOTA Research & External Knowledge
- **Web Research for SOTA:** You are explicitly encouraged to use your web search tools to research the latest papers, documentation for relevant libraries, or implementation details. If you encounter a bottleneck, look for how researchers at the frontier are solving similar problems.

## Benchmark Details

`prepare.py` generates the evaluation environment. The performance is measured by:

### Scoring Formula

```text
val_score = {{PRIMARY_ERROR_TERM}} 
          + {{WEIGHT_1}} * {{SECONDARY_TERM}}
          + {{WEIGHT_2}} * {{COMPLEXITY_PENALTY}}
```

Lower is better (unless specified otherwise).

## Key Commands

```bash
# Preparation
uv run prepare.py --force

# Research/Training
uv run train/main.py

# Evaluation
uv run prepare.py --eval
```

## Workflow: The Iterative Loop

1. **Analyze:** Inspect the previous "Best" run and current failure modes (e.g., instability, high complexity, or poor generalization).
2. **Hypothesize:** Formulate a technical reason for a change (e.g., "The current model fails on {{CASE_X}} due to {{REASON}}; introducing {{TECHNIQUE}} may help").
3. **Innovate:** Modify files within the `train/` directory. You are expected to write new code, classes, and logic—not just flip booleans. Use your web search capabilities if you need to look up specific SOTA implementations.
4. **Execute:** Run your experiment.
5. **Document & Maintain:** 
   - Update `results.csv` with your technical conclusion and reasoning.
   - Update `results_concise.csv` with a high-signal summary for visualization.
   - Clean up any temporary test files or debug artifacts created in the `train/` directory.
6. **Sync:** Regenerate progress visualization/reporting.

## Loop Continuation & Waiting Strategy

**Core Directive:**
- You will **continue the macro optimization loop as long as possible** until the user explicitly tells you to stop or pause.
- When the user refers to "the loop," they always mean the **macro optimization loop** (Analyze → Hypothesize → Innovate → Execute → Document → Sync → repeat).
- **User requests do not exit the loop:** If the user asks you to perform a task or make a change, execute it and then continue the macro optimization loop.

**Exponential Backoff for Experiment Monitoring:**
To preserve token quota, implement an **increasing wait mechanism** when monitoring long-running experiments (5, 10, 20, 40... minutes).

## Acceptance Criteria

- **Primary:** Lower `val_score` is the main signal.
- **Secondary:** Models must be "physically" or logically reasonable. Avoid over-fitting with uninterpretable complexity.
- **Robustness:** A good solution must perform across all test cases/scenarios provided in the benchmark.

### Breakthrough Strategy: Stagnation Recovery

If you detect that improvements are stagnating:
1. **Take drastic creative action:** Consider bold architectural shifts or radically different strategies.
2. **Allocate intense reasoning:** Spend your token budget on deep analysis, not more experiments. 

## Constraints

- **Source Integrity:** Do not edit `prepare.py`.
- **Zero-Init:** Start from the provided baseline spirit. Do not port "secret" hyperparameters without empirical testing.
- **Context Efficiency:** Keep your logs and code concise to maintain a high-signal context window.
- **User Alignment:** Always consult `user_notes.md` for specific mid-loop course corrections.
- **Workspace Containment:** All operations must remain within the `V0/` context directory.
