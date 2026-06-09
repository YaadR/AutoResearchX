````markdown
---
name: start-loop
description: Starts the autonomous optimization loop from the setup files, iterating on the train/ sandbox with hypothesis-driven changes, validation, documentation, and user-note integration until explicitly stopped.
---

When the user invokes the `start-loop` skill, transition into the autonomous optimization and research loop.

Assume `set-loop` has already prepared the project. Do not re-scaffold the environment unless required loop files are missing. If a required file is missing, create only the minimal safe replacement needed to proceed, document that recovery, and continue.

## Initialization

Before making any optimization change, read and inspect:

1. `program.md`
   - Treat this as the main loop constitution.
   - Follow its objective, editable scope, protected scope, validation method, decision rules, debugging rules, dependency rules, stagnation rules, and user-alignment rules.

2. `agent_id.md`
   - Adopt the project-specific role, mission, constraints, and working philosophy.

3. `prepare.py`
   - Understand how setup, isolation, validation, data generation, or environment preparation works.
   - Run it only if `program.md` says it is required, the workspace is not prepared, or the first loop iteration depends on it.

4. `train/`
   - Inspect everything inside this directory.
   - Treat `train/` as the primary editable sandbox unless `program.md` explicitly permits edits elsewhere.

5. Existing loop artifacts, if present:
   - `user_notes.md`
   - `loop_log.md`
   - `results.tsv`
   - `progress.md`
   - `outputs/`
   - `runs/`
   - prior summaries, metrics, reports, logs, or validation artifacts.

## Required Loop Files

Create and maintain these files if they do not already exist:

### `user_notes.md`

Use this to record user directions received while the loop is running.

```markdown
# User Notes

## Active Instructions
- Add current user instructions here.

## Historical Instructions
- Move resolved or superseded instructions here.
````

### `loop_log.md`

Use this as the rolling technical log.

```markdown
# Loop Log

## Iteration N

### Hypothesis
State the technical hypothesis.

### Change
Describe the implemented change.

### Validation
List commands, tests, benchmarks, scripts, or inspections performed.

### Result
Summarize the observed outcome.

### Decision
kept / discarded / verification

### Next Step
State the next action.
```

### `results.tsv`

Use this as the concise experiment table.

```text
iteration	status	hypothesis	change	validation	result	next_step
```

### `progress.md`

Use this for compact progress tracking. Prefer concise tables, ASCII diagrams, or Mermaid diagrams only when they improve clarity.

```markdown
# Progress

| Iteration | Status | Main Change | Result | Next Step |
|---:|---|---|---|---|
```

## Continuous Loop Rule

You are now in the autonomous optimization loop.

Do not stop after one iteration.

Do not ask whether to continue.

Continue selecting the next best action, implementing it, validating it, documenting it, and repeating until one of these occurs:

* the user explicitly says `stop`, `pause`, `halt`, or an equivalent stop command;
* the objective in `program.md` is fully achieved and no meaningful next optimization step remains;
* validation is impossible due to missing credentials, unavailable services, broken environment, or permission boundaries;
* continuing would require editing protected files or performing risky operations without user approval;
* the task premise becomes materially unclear and requires Plan Mode confirmation.

If none of these conditions applies, continue the loop.

## Handling User Messages During the Loop

If the user provides side-context, a correction, a preference, or a new instruction while the loop is running:

1. Do not treat it as a stop command unless the user explicitly says to stop, pause, or halt.
2. Record the instruction in `user_notes.md`.
3. Determine whether it changes:

   * the objective,
   * validation method,
   * editable scope,
   * protected scope,
   * current hypothesis,
   * next iteration priority.
4. Integrate the instruction into the current or next iteration.
5. Return to the core loop defined in `program.md`.

If the instruction conflicts with `program.md`, protected scope, or safe execution boundaries, enter Plan Mode and ask the user to clarify before proceeding.

## Iteration Structure

Each iteration must follow this sequence.

### 1. Analyze

Inspect the current best state and the most relevant evidence.

Review:

* `program.md`
* `agent_id.md`
* `user_notes.md`
* `train/`
* recent changes
* prior results
* validation outputs
* logs
* errors
* metrics
* generated artifacts

Identify the highest-leverage bottleneck or failure mode.

### 2. Hypothesize

Before editing, state a specific hypothesis.

The hypothesis must explain:

* what problem is being targeted,
* why the proposed change should help,
* how success will be measured,
* what would count as failure,
* what regression risk exists.

Do not make random edits.

Do not perform blind parameter scanning.

### 3. Plan the Change

Choose one coherent change or a small group of tightly related changes.

Prefer changes that are:

* targeted,
* reversible,
* measurable,
* consistent with the project architecture,
* aligned with `program.md`.

Avoid mixing unrelated edits in one iteration.

### 4. Implement

Modify the relevant files, primarily inside `train/` unless `program.md` permits other locations.

Rules:

* preserve protected files,
* keep changes readable,
* avoid unnecessary abstractions,
* avoid duplicated logic,
* do not hide failures,
* do not suppress errors without understanding them,
* remove temporary debug code when finished,
* keep the workspace organized.

### 5. Execute Validation

Run the validation method defined in `program.md`.

Validation may include:

* tests,
* benchmarks,
* build commands,
* linting,
* type checks,
* smoke tests,
* evaluation scripts,
* generated reports,
* manual inspection of outputs.

If validation commands are missing, the first loop task should be to create or identify a minimal safe validation method.

If validation fails, diagnose the root cause. Decide whether to fix, adjust, revert, or mark the iteration as discarded.

### 6. Evaluate

Compare the result against the previous best state.

Use the primary objective as the main decision signal.

Also check secondary quality signals:

* correctness,
* robustness,
* stability,
* maintainability,
* performance,
* complexity,
* security,
* user experience,
* reproducibility.

Do not keep a change that improves one narrow metric while damaging the project more broadly.

### 7. Decide

Classify the iteration as one of:

`kept`
The change improves the objective without unacceptable regressions.

`discarded`
The change fails, regresses, adds unjustified complexity, or does not support the hypothesis.

`verification`
The result is promising but needs another run, narrower test, stability check, or additional review before being trusted.

When uncertain, use `verification`.

### 8. Document

Update:

* `loop_log.md`
* `results.tsv`
* `progress.md`
* any additional files required by `program.md`

Each iteration note must include:

* iteration number,
* hypothesis,
* files changed,
* validation performed,
* result,
* decision,
* next step.

Keep documentation concise and useful.

### 9. Preserve or Revert

If the iteration is `kept`:

* preserve the new best state according to `program.md`;
* copy important outputs into `runs/` if appropriate;
* update any best-run pointer or summary file if the project uses one.

If the iteration is `discarded`:

* revert or isolate the failed change if needed;
* keep only the concise record of what was tried and why it failed;
* remove unnecessary temporary artifacts.

If the iteration is `verification`:

* keep enough state to rerun or inspect;
* make the next iteration a verification step unless a higher-priority user instruction supersedes it.

### 10. Continue

Start the next iteration from the best kept state.

Do not ask whether to continue.

Select the next highest-leverage hypothesis and repeat the loop.

## Stagnation Handling

If several iterations produce marginal, unstable, or no improvement:

1. Stop making small tweaks.
2. Re-read `program.md`, `agent_id.md`, and `user_notes.md`.
3. Reassess the objective, constraints, validation method, and failure modes.
4. Identify whether the current approach is fundamentally limited.
5. Consider a larger strategic change, such as:

   * different architecture,
   * different algorithm,
   * different data flow,
   * different validation method,
   * better isolation,
   * stronger tests,
   * simpler implementation,
   * improved instrumentation,
   * revised project framing.
6. Document the stagnation diagnosis in `loop_log.md`.
7. Continue with the revised strategy if it is safe and aligned with the objective.

## Debugging Rules

When errors occur:

* read the full error context,
* identify the likely root cause,
* inspect the relevant source,
* make the smallest coherent fix,
* rerun validation,
* document the error and resolution.

Do not hide errors by removing tests, weakening validation, suppressing exceptions, or ignoring failed commands.

## Dependency and Installation Rules

Before installing dependencies:

1. Check existing project files for the intended package manager.
2. Prefer existing lockfiles and project tooling.
3. Install only what is necessary.
4. Avoid global installation unless explicitly required.
5. Document any dependency change in `loop_log.md`.
6. Validate after installation.

If dependency installation requires permission, credentials, payment, external services, or risky environment changes, pause and ask the user.

## Output Per Iteration

Each completed iteration must update the workspace with:

1. A concise technical entry in `loop_log.md`.
2. A concise row in `results.tsv`.
3. Any required validation output in `outputs/`.
4. A compact progress update in `progress.md`.
5. Any new or updated user instruction in `user_notes.md`.

## Completion Report

When the loop stops because the user explicitly stopped it, the objective is complete, or progress is blocked, provide a final summary containing:

* total iterations completed,
* best kept result,
* most important changes,
* validation evidence,
* current unresolved issues,
* reason the loop stopped,
* recommended next action.

```
```
