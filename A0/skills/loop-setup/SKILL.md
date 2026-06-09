Understood. Here is only the modified `set-loop` skill.

````markdown
---
name: set-loop
description: Initializes the directory structure and foundational files required for an autonomous optimization and research loop, optionally using AutoResearchX as a reference scaffold.
---

When the user invokes the `set-loop` skill, your objective is to deeply analyze the current directory and generate the foundational files required for an autonomous optimization or research loop.

Do not start the optimization loop yet. This skill only prepares the environment, defines the premise, and creates the files needed for a later loop run.

## Core Behavior

First, inspect the current directory and understand the project before creating files.

Analyze:
- the project structure,
- README or documentation files,
- source files,
- configuration files,
- test or benchmark commands,
- existing scripts,
- current outputs or logs,
- user instructions,
- likely editable files,
- likely protected files,
- the project’s apparent objective.

Do not assume the project type. The setup must work for software engineering, machine learning, research, data analysis, simulation, optimization, refactoring, debugging, benchmarking, documentation, or any other project.

## Optional Reference Scaffold

If the environment supports shell/network access, you may optionally clone this repository as a reference example:

```bash
git clone https://github.com/YaadR/AutoResearchX
````

Use it only as a reference for a complete autonomous loop structure.

Rules:

* Clone it into a temporary or reference directory.
* Do not clone it over the current project.
* Do not blindly copy files from it.
* Do not overwrite current project files with reference files.
* Study its structure and adapt the ideas to the current project.
* The current project and user instructions are always the source of truth.
* If cloning fails, internet access is unavailable, or the repository cannot be reached, continue anyway.

Even without downloading the reference repository, you must still create a complete loop scaffold and define the code file, editable scope, protected scope, validation method, and loop premise.

## Required Files and Directories

Create or update the following:

1. `program.md`

Create this file to define the general loop logic, rules of engagement, project objective, validation process, debugging policy, installation policy, documentation policy, and progression rules.

It must be general enough to adapt to the current project, but specific enough to guide real execution.

Recommended content:

```markdown
# Autonomous Optimization Program

## Objective
Describe the project-specific goal and the primary success condition.

## Project Understanding
Summarize what the project appears to do, what matters, and what is currently known.

## Editable Scope
List files and directories the loop may modify.

## Protected Scope
List files and directories that must not be modified unless the user explicitly approves.

## Main Code Area
Identify the main code file, module, package, app directory, experiment script, or sandbox that the loop should focus on.

If the main code area is unclear, state that the first loop iteration must establish it.

## Validation
Define how progress should be measured.

Use existing tests, benchmarks, build commands, evaluation scripts, smoke tests, manual inspection, or generated metrics when available.

If no validation method exists yet, state that the first loop iteration should create a minimal safe validation harness before attempting optimization.

## Loop Logic
Each iteration must follow:

1. Analyze the current best state.
2. Form a specific hypothesis.
3. Make one coherent change or a small group of tightly related changes.
4. Run validation.
5. Compare against the baseline.
6. Decide whether the change is kept, discarded, or requires verification.
7. Document the result.
8. Clean temporary artifacts.
9. Repeat from the best kept state.

## Decision Rules
The primary objective is the main decision signal.

Also check secondary quality signals:
- correctness,
- robustness,
- stability,
- maintainability,
- performance,
- complexity,
- security,
- user experience,
- reproducibility.

Do not keep a change that improves one narrow metric while damaging the project more broadly.

## Debugging Rules
Diagnose root causes before applying fixes.

Do not hide errors, suppress failures, or make changes that only mask symptoms.

## Dependency Rules
Use existing project tooling when possible.

Install dependencies only when necessary. Document why they were needed.

Avoid unnecessary global changes to the environment.

## Documentation Rules
Each meaningful iteration must record:
- hypothesis,
- change,
- validation performed,
- result,
- decision,
- next step.

## Stagnation Rules
If several iterations produce marginal, unstable, or no improvement, stop minor tweaking and reassess the premise, architecture, algorithm, workflow, data, or validation method.

## User Alignment
If the objective, constraints, or safe edit scope becomes unclear, switch to Plan Mode and ask the user to confirm the premise before continuing.
```

2. `agent_id.md`

Create this file as the project-specific agent identity and directive document.

It should describe the role the loop agent should take for this project.

Adapt the persona to the project. Examples:

* senior full-stack engineer for a web app,
* ML researcher for a model project,
* computational scientist for a simulation,
* library maintainer for a package,
* data analyst for an analytics project,
* systems engineer for performance or infrastructure work.

Recommended content:

```markdown
# Agent Identity

You are a high-autonomy optimization agent working on this project.

## Role
Describe the project-specific expert role you should adopt.

## Mission
Improve the project according to the objective defined in `program.md`.

## Working Philosophy
- Understand before editing.
- Reason over randomness.
- Use evidence as the source of truth.
- Prefer coherent, testable changes.
- Avoid blind parameter scans.
- Preserve maintainability.
- Keep the workspace clean.
- Document decisions clearly.

## Project-Specific Context
Summarize what is known about this project after setup inspection.

## Constraints
List user constraints, protected files, edit boundaries, and environment limitations.

## Reporting Style
Keep reports concise, technical, and decision-oriented.

## Loop Discipline
Every loop iteration must include:
- hypothesis,
- implementation,
- validation,
- decision,
- next step.
```

3. `prepare.py`

Create a Python script for project preparation, environment inspection, validation setup, or isolation of a smaller working target.

The exact behavior should be adapted to the project.

It may:

* create required loop directories,
* summarize the environment,
* detect project type,
* identify likely test commands,
* copy or isolate files into `train/`,
* generate sample data,
* run a smoke check,
* prepare outputs for later loop runs.

If no clear project-specific setup is known yet, create a safe non-destructive boilerplate:

```python
from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
TRAIN_DIR = ROOT / "train"
OUTPUTS_DIR = ROOT / "outputs"
RUNS_DIR = ROOT / "runs"


def run_command(command: list[str], timeout: int = 60) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
        }
    except Exception as exc:
        return {
            "command": command,
            "error": repr(exc),
        }


def detect_project() -> dict[str, list[str]]:
    markers = {
        "python": ["pyproject.toml", "requirements.txt", "setup.py", "Pipfile"],
        "node": ["package.json", "pnpm-lock.yaml", "yarn.lock", "package-lock.json"],
        "rust": ["Cargo.toml"],
        "go": ["go.mod"],
        "java": ["pom.xml", "build.gradle", "settings.gradle"],
        "dotnet": ["*.csproj", "*.sln"],
        "docs": ["README.md", "docs"],
        "git": [".git"],
    }

    detected: dict[str, list[str]] = {}

    for kind, names in markers.items():
        found: list[str] = []
        for name in names:
            if "*" in name:
                found.extend(str(path.relative_to(ROOT)) for path in ROOT.glob(name))
            elif (ROOT / name).exists():
                found.append(name)
        detected[kind] = found

    return detected


def suggest_validation(project_markers: dict[str, list[str]]) -> list[list[str]]:
    suggestions: list[list[str]] = []

    if project_markers.get("python"):
        suggestions.extend([
            ["python", "-m", "pytest"],
            ["python", "-m", "compileall", "."],
        ])

    if project_markers.get("node"):
        suggestions.extend([
            ["npm", "test"],
            ["npm", "run", "build"],
        ])

    if project_markers.get("rust"):
        suggestions.append(["cargo", "test"])

    if project_markers.get("go"):
        suggestions.append(["go", "test", "./..."])

    return suggestions


def main() -> None:
    TRAIN_DIR.mkdir(exist_ok=True)
    OUTPUTS_DIR.mkdir(exist_ok=True)
    RUNS_DIR.mkdir(exist_ok=True)

    project_markers = detect_project()

    summary = {
        "root": str(ROOT),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "project_markers": project_markers,
        "suggested_validation_commands": suggest_validation(project_markers),
        "top_level_files": sorted(
            str(path.relative_to(ROOT))
            for path in ROOT.iterdir()
            if path.name not in {".git", "__pycache__"}
        ),
    }

    output_path = OUTPUTS_DIR / "setup_summary.json"
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("Loop setup preparation complete.")
    print(f"Wrote: {output_path}")
    print("Review program.md and agent_id.md before starting the loop.")


if __name__ == "__main__":
    main()
```

4. `train/`

Create a `train/` directory.

This is the sandbox where files can be copied, adapted, changed, extended, optimized, or isolated for loop work.

Create `train/README.md`:

```markdown
# train/

This directory is the editable sandbox for the autonomous optimization loop.

The agent may place project-specific working files here when isolation is useful.

Use this directory for:
- experiments,
- refactors,
- prototypes,
- training scripts,
- evaluation adapters,
- copied or narrowed versions of project files,
- reproducible test cases.

Rules:
- Keep this directory organized.
- Start meaningful iterations from the current best known state.
- Remove temporary debug files when they are no longer useful.
- Preserve important results outside temporary scratch files.
- If files are copied from the main project, document their origin and purpose.
```

## Optional Support Files

Create these if useful for the project:

5. `user_takes.md`

Use this as a standing ledger for user directives.

```markdown
# User Takes

This file records explicit user directives, corrections, constraints, and preferences that should guide the loop.

## Active Directives
- Add active user instructions here.

## Historical Notes
- Move resolved or outdated instructions here.
```

6. `results.tsv`

Use this for experiment tracking.

```text
iteration	status	hypothesis	change	validation	result	next_step
```

7. `outputs/`

Create this directory for generated summaries, metrics, reports, logs, charts, or validation artifacts.

8. `runs/`

Create this directory for preserved best runs, snapshots, checkpoints, or discarded experiment records when needed.

## Premise Requirement

Before finishing, write the initial loop premise into `program.md`.

At minimum, define:

* the main code area or sandbox,
* editable scope,
* protected scope,
* validation method or validation-discovery task,
* current baseline or baseline-discovery task,
* first hypothesis or first investigation target.

If there is not enough information to define a specific first hypothesis, use this default premise:

```markdown
Initial premise:
The first loop iteration should establish a true baseline by running the existing tests, build, benchmark, smoke check, or validation script. If no validation command exists, the first loop iteration should create a minimal safe validation harness before attempting optimization.
```

## Completion Rule

Do not start the loop.

Do not run repeated experiments.

Do not begin optimization.

Only scaffold the environment, adapt the foundational files to the current project, and report that the project is ready for `start-loop` or `loop-run`.

## Final Report

After setup, report:

* whether AutoResearchX was inspected or unavailable,
* files and directories created or updated,
* understood project objective,
* main code area or sandbox,
* editable scope,
* protected scope,
* validation method,
* initial loop premise,
* whether user confirmation is needed before starting the loop.

End by stating that the environment is ready for `start-loop` or `loop-run`.

```
```
