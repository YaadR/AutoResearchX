# PINN-SINDy AutoResearch: High-Autonomy Research Program

You are conducting an autonomous research loop to identify the governing equations of a complex nonlinear system. This is a **zero-knowledge start**. Your objective is to achieve the best possible physical identification of the system dynamics through expert-level experimentation and innovation.

## Research Environment

1. `README.md`: System overview and scoring metrics.
2. `agent_id_junior.md` & `agent_id_senior.md`: Your professional identity and methodological principles (choose based on autonomy level).
3. `user_takes.md`: Real-time ledger for specific user directives.
5. `train/`: Your primary laboratory directory. You have full authority to create, modify, refactor, and delete any files within this directory to implement, test, debug, and innovate.
6. `results.csv` & `results_concise.csv`: Your experimental record.
7. `prepare.py`: The fixed evaluation harness (Read-only).

## Core Objective: Physical System Identification

The goal is to discover a parsimonious, physically consistent, and globally accurate model of the double-mass system. Use your expertise in **Control Theory** and **Deep Learning** to bridge the gap between noisy data and sparse governing equations.

**Driving Principles:**
- **Relentless Improvement:** Every cycle should aim for measurable progress. Be creative and bold in your hypotheses; combine ideas fearlessly.
- **Smart Efficiency:** Work in a way that scales. Avoid brute-force parameter sweeps; reason through each decision. Manage your token budget, maintain clean code, and delete what is no longer needed.
- **Order & Clarity:** Keep the `train/` directory, logs, and experimental artifacts well-organized. A clean workspace is a sharp mind.

## Degrees of Freedom & Research Domains

You are not limited to a predefined list of parameters. You are encouraged to innovate across these domains:

### 1. Neural State Approximation (The Smoother)
- **Spectral Bias & Architecture:** Beyond MLPs, consider Fourier features, SIRENs, or custom coordinate transformations that respect the system's physics.
- **Differentiability:** Optimize how derivatives are extracted (Autograd vs. Finite Differences vs. Smoothed Splines).
- **Physics-Informed Losses:** Design loss functions that enforce kinematic constraints ($v = \dot{x}$) or energy conservation principles.

### 2. Sparse Dynamics Discovery (SINDy)
- **Library Design:** Beyond polynomials, derive custom friction terms (Coulomb, viscous, Stribeck) or coupling functions.
- **Optimization Strategy:** Experiment with various sparse optimizers (STLSQ, SR3, SSR, etc.) or implement unique regularization schemes.
- **Constraints:** Enforce known physical symmetries or structural zeros in the discovery process.

### 3. Training Dynamics & Optimization
- **Loss Weighting Strategies:** Implement dynamic weighting (like GradNorm or Self-Scaling) to balance data and physics losses.
- **Advanced Schedulers:** Use your DL intuition to design learning rate schedules that match the complexity of the landscape.

### 4. SOTA Research & External Knowledge
- **Web Research for SOTA:** You are explicitly encouraged to use your web search tools to research the latest papers, documentation for PySINDy, or PINN implementation details. If you encounter a bottleneck, look for how researchers at the frontier are solving similar problems.

## Hard Benchmark Details

`prepare.py` generates a difficult controlled double-mass benchmark with:

- nonlinear friction
- weak cubic spring terms
- multisine forcing
- chirp forcing
- step forcing
- PRBS-like forcing
- pulse forcing

### Scoring Formula

```text
val_score = rollout_nmse
          + 0.25 * derivative_nmse
          + 0.10 * worst_case_force_rollout_nmse
          + 1e-3 * complexity
```

Lower is better.

## Visual Outputs

Each run generates the following visualizations:

- `outputs/dashboard.html` — main interactive dashboard
- `outputs/training_progress.png` — training dynamics visualization
- `outputs/validation_rollout.png` — rollout validation plots
- `outputs/derivative_nmse.png` — derivative accuracy assessment
- `outputs/force_case_metrics.png` — performance by forcing family
- `outputs/coefficients_heatmap.png` — discovered coefficient visualization
- `outputs/equations.txt` — discovered sparse equations in text form
- `outputs/summary.json` — detailed metrics in JSON format
- `outputs/research_progress.html` — interactive optimization history (hoverable, shows kept/discarded/pending/best traces)
- `outputs/research_progress.png` — static version of optimization history

## Workflow: The Iterative Loop

1. **Analyze:** Inspect the previous "Best" run and current failure modes (e.g., instability in certain forcing cases, high complexity, or poor derivative matching).
2. **Hypothesize:** Formulate a technical reason for a change (e.g., "The current model fails on PRBS forcing due to high-frequency transients; introducing SIREN activation may help").
3. **Innovate:** Modify files within the `train/` directory. You may create debug scripts, add utilities, or write exploratory code as needed. You are expected to write new code, classes, and logic—not just flip booleans. Use your web search capabilities if you need to look up specific SOTA implementations or documentation.
4. **Execute:** Run your experiment.
5. **Document & Maintain:** 
   - Update `results.csv` with your technical conclusion and reasoning.
   - Update `results_concise.csv` with a high-signal summary for visualization.
   - Clean up any temporary test files or debug artifacts created in the `train/` directory during this iteration.
6. **Sync:** Regenerate progress visualization only.

## Loop Continuation & Waiting Strategy

**Core Directive:**
- You will **continue the macro optimization loop as long as possible** until the user explicitly tells you to stop or pause.
- When the user refers to "the loop," they always mean the **macro optimization loop** (Analyze → Hypothesize → Innovate → Execute → Document → Sync → repeat).
- **User requests do not exit the loop:** If the user asks you to perform a task or make a change, execute it and then continue the macro optimization loop. Do not treat mid-loop requests as a pause or redirection; integrate them and proceed.

**Periodic Recall & Alignment:**
- Every few iterations (approximately every 5–10 experiments), pause to re-read `program.md` and your active `agent_id_*.md` (junior or senior).
- Verify that you remain aligned with the macro task, research philosophy, and constraints. Drift is easy in long loops; this is your reset.
- Use this moment to recalibrate if you notice you are deviating from the stated principles.

**Exponential Backoff for Experiment Monitoring:**
To preserve token quota, implement an **increasing wait mechanism** when monitoring long-running experiments:
- **First check:** Wait 5 minutes before polling completion.
- **Second check:** Wait 10 minutes before polling.
- **Third check:** Wait 20 minutes before polling.
- **Subsequent checks:** Double the wait time each cycle (40, 80, 160, minutes, etc.).

**Why:** Frequent polling to check if a run has finished is expensive in tokens. Only check when you have high confidence the experiment is likely complete. If the run is taking longer than expected, it is better to wait passively and use your token budget for analysis and decision-making when you do check.

## Acceptance Criteria

- **Primary:** Lower `val_score` is the main signal.
- **Secondary:** Models must be physically reasonable. Avoid "over-fitting" with unphysical coefficients that happen to lower the score.
- **Generalization:** Monitor `force_case_metrics.png`. A good model must perform across all forcing families (multisine, chirp, pulse, etc.).

### Breakthrough Strategy: Stagnation Recovery

If you detect that improvements are stagnating (flat or marginal gains over several iterations):

1. **Recognize the plateau:** This is often a signal that incremental tweaks are exhausted.
2. **Take drastic creative action:** Consider bold architectural shifts, novel loss formulations, completely different SINDy libraries, or radically different optimization strategies.
3. **Allocate intense reasoning:** Spend your token budget on deep analysis, not more experiments. Ask: *Why is this family failing?* *What fundamental physics am I missing?* *What would a completely different approach look like?*
4. **Do not settle for marginal:** Small improvements are only valuable if they move toward a better equilibrium. If you are stuck, pivot aggressively.

## Constraints

- **Source Integrity:** Do not edit `prepare.py`.
- **Zero-Init:** Start from the provided baseline spirit. Do not port "secret" hyperparameters from other projects without empirical testing in *this* environment.
- **Context Efficiency:** Keep your logs and code concise to maintain a high-signal context window.
- **User Alignment:** Always consult `user_takes.md` for specific mid-loop course corrections.
- **Workspace Containment:** Any changes, modifications, or file operations must remain within the context directory (`/home/yaadreb/GitHub/AutoResearch/V0/`) unless explicitly specified otherwise by the user.
- **Development Hygiene:** You may create temporary files for testing, debugging, validation, or exploratory analysis. Clean up and delete these files when no longer needed. Keep the project directory orderly and free from unnecessary artifacts.
- **Continuous Improvement:** Always strive to improve `val_score` and model quality. Be creative and efficient in your approach—combine multiple insights, innovate with new loss functions, or propose entirely new architectures if the situation warrants.
- **Project Scalability:** As the project grows (more code, more runs, more outputs), work intelligently to avoid context overflow. Summarize findings, delete obsolete runs, consolidate logs, and maintain clear organization. Do not let project size paralyze decision-making; stay focused on the macro loop.
not let project size paralyze decision-making; stay focused on the macro loop.
ntext overflow. Summarize findings, delete obsolete runs, consolidate logs, and maintain clear organization. Do not let project size paralyze decision-making; stay focused on the macro loop.
not let project size paralyze decision-making; stay focused on the macro loop.
