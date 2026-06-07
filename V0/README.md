# {{PROJECT_NAME}} — {{PROJECT_SUBTITLE}}

## Quick Start

**Read and follow:** [`program.md`](program.md) — Complete instructions for the research loop, objectives, acceptance criteria, and constraints.

## File Reference

| File | Purpose |
|------|---------|
| `program.md` | **Primary instructions:** Research loop workflow, objectives, constraints, and all operational guidance. Start here. |
| `agent_id_junior.md` | Researcher persona: junior researcher role with directed methodology and structured exploration. |
| `agent_id_senior.md` | Researcher persona: senior researcher role with strategic innovation and deep expertise principles. |
| `user_notes.md` | Real-time ledger for user directives and mid-loop feedback. Consult frequently during experiments. |
| `train/` | Your primary laboratory directory. Full authority to create, modify, and delete any files within for training, debugging, and experimentation. |
| `prepare.py` | Fixed evaluation harness (Read-only). Do not edit. |
| `results.csv` | All trials with detailed reasoning and conclusions. |
| `results_concise.csv` | Minimal metrics for visualization and quick reference. |
| `runs/trials/` | Snapshot of every run for historical reference. |
| `runs/best/` | Current best kept configuration, maintained by you. |

## Key Commands

```bash
# Setup
uv sync

# Prepare benchmark data / environment
uv run prepare.py --force
```

---

**Next:** Open [`program.md`](program.md) and follow its instructions for the full research methodology.
