# V1 AutoResearch — Pure Loop Framework

This is a modular, high-autonomy framework for autonomous technical research and optimization.

## Quick Start
1. **The Goal**: Define your target in [`Goal.md`](Goal.md).
2. **The Loop**: Follow the methodology in [`Loop.md`](Loop.md).
3. **The Agent**: Adopt the persona in [`Agent.md`](Agent.md).

## File Reference
| File | Purpose |
|------|---------|
| `Goal.md` | Abstract mission objectives and scoring rationale. |
| `Loop.md` | Core autonomous research methodology and pivot strategies. |
| `Agent.md` | Professional researcher identity and principles. |
| `exp/` | The Laboratory. Primary workspace for implementation. |
| `results/` | Structured experimental records. |
| `runs/` | Archive of trial configurations. |
| `user_notes.md` | Human-in-the-loop directive ledger. |

## Initiating the Research Program

The autonomous research program is triggered when the user issues an explicit directive in the CLI, such as:
> "Start the loop using the Senior Research Scientist persona."

Upon this trigger, you must:
1.  **Initialize**: Confirm the project details in `Goal.md`.
2.  **Analyze**: Begin Phase 1 of the Macro Optimization Loop as defined in `Loop.md`.
3.  **Persist**: Continue the loop autonomously until a success threshold is met or a "Stop" command is received.

## Execution Interface
*Note: Specific command names may vary based on your implementation.*

```bash
# Setup
pip install -e .

# Run Experiment
python exp/main.py

# Evaluate (Interface defined in your research task)
[EVAL_COMMAND]
```
