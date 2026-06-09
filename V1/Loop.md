# The Autonomous Research Methodology

## Loop Trigger
The research cycle is initiated by a user directive (e.g., **"Start the loop"**). Once triggered, you are expected to operate autonomously, transitioning through the phases below until the mission objective in `Goal.md` is achieved or the user intervenes.

## The Macro Optimization Cycle
You operate in a continuous cycle of discovery. Every experiment must follow this rigorous process:

1. **Analyze (Diagnosis)**:
   - Critically evaluate the results of the previous experiment.
   - Identify the specific scenario or metric where the solution is weakest.
   - Inspect logs and visualizations for patterns or anomalies.

2. **Hypothesize (Rationalization)**:
   - Formulate a technical reason for a proposed change.
   - *Example*: "The current approach struggles with {{SCENARIO_X}}; I suspect {{TECHNIQUE_Y}} will improve performance by {{REASONING_Z}}."

3. **Innovate (Implementation)**:
   - Apply your change to the `train/` directory.
   - You have full authority to refactor code, introduce new libraries, or rewrite core logic.
   - Focus on structural innovation rather than simple parameter tuning.

4. **Execute (Verification)**:
   - Run the experiment and evaluate against the fixed harness.
   - (Standard command: `python exp/main.py`)

5. **Document (Preservation)**:
   - Update the results ledger (`results/results.csv`) with your technical conclusion.
   - Document *why* a run was kept or discarded.

## Stagnation Recovery & Breakthrough Tactics
If improvement stalls for several iterations:
- **Radical Pivot**: Your current strategy has reached its limit. Abandon the current approach and try a fundamentally different architecture or methodology.
- **Reasoning Sabbatical**: Stop running experiments. Spend a full turn analyzing the entire experimental history to find a non-obvious breakthrough.
- **External Research**: Use search tools to identify how researchers at the frontier are solving similar problems in {{DOMAIN}}.

## Operational Strategy
- **Autonomous Continuity**: Continue the loop indefinitely until a specific success threshold is met or the user intervenes.
- **Exponential Backoff**: Implement an increasing wait mechanism for monitoring long-running processes (e.g., 5, 10, 20, 40... minutes).
