# AutoResearch Framework

AutoResearch is a structured framework for implementing autonomous technical research and optimization loops. It separates the **Mission** (Goal), the **Process** (Loop), and the **Identity** (Agent) to enable systematic, high-autonomy exploration of complex problem spaces.

## Framework Versions

- **[V1 (Active)](V1/README.md)**: The mature, modular iteration. Recommended for all new projects. Uses a purely loop-focused approach with generalized instructions and professional research personas.
- **[V0 (Legacy)](V0/README.md)**: The original monolithic benchmark (PINN-SINDy). Kept for historical reference and as a concrete implementation example.

---

## Copilot CLI Installation & Setup

To use the AutoResearch framework within your Copilot CLI, you must install the Loop Agent and its associated skills into your local configuration.

### Setup Prompt (Copy-Paste to Agent)

If you are using an agentic CLI that can manage files, you can simply paste the following prompt:

> "Clone the AutoResearch repository from `https://github.com/YaadR/AutoResearch` and install the Loop Agent and its skills. Copy `A0/agents/loop.agent.md` to my local `.copilot/agents/` directory, and copy the contents of `A0/skills/` to my local `.copilot/skills/` directory, maintaining the folder structure."

### Manual Installation (Shell Commands)

#### Linux / macOS
```bash
# Clone the repository
git clone https://github.com/YaadR/AutoResearch.git
cd AutoResearch

# Create directories
mkdir -p ~/.copilot/agents ~/.copilot/skills/loop-run ~/.copilot/skills/loop-setup

# Copy Agent and Skills
cp A0/agents/loop.agent.md ~/.copilot/agents/
cp A0/skills/loop-run/SKILL.md ~/.copilot/skills/loop-run/
cp A0/skills/loop-setup/SKILL.md ~/.copilot/skills/loop-setup/
```

#### Windows (PowerShell)
```powershell
# Clone the repository
git clone https://github.com/YaadR/AutoResearch.git
cd AutoResearch

# Create directories
New-Item -ItemType Directory -Force -Path "$HOME\.copilot\agents", "$HOME\.copilot\skills\loop-run", "$HOME\.copilot\skills\loop-setup"

# Copy Agent and Skills
Copy-Item "A0\agents\loop.agent.md" -Destination "$HOME\.copilot\agents\"
Copy-Item "A0\skills\loop-run\SKILL.md" -Destination "$HOME\.copilot\skills\loop-run\"
Copy-Item "A0\skills\loop-setup\SKILL.md" -Destination "$HOME\.copilot\skills\loop-setup\"
```

---

## Project Structure (A0 Repository)

The `A0` directory contains the reusable "blueprints" for the framework:

- **`A0/agents/loop.agent.md`**: The primary "AutoResearch Loop Master" persona.
- **`A0/skills/loop-setup/`**: Skill for initializing the modular V1 research environment.
- **`A0/skills/loop-run/`**: Skill for executing the 5-phase research loop.

## Core Principles (V1)

1.  **Hypothesis-Driven**: No changes are made without a technical hypothesis.
2.  **Modular Instructions**: Separation of Mission (`Goal.md`), Process (`Loop.md`), and Identity (`Agent.md`).
3.  **Experimental Rigor**: All trials are documented in a structured ledger with reasoning and evidence.
4.  **Stagnation Recovery**: Explicit protocols for breaking plateaus and pivoting strategies.

For more details on how to run a research project, navigate to the **[V1 Directory](V1/README.md)**.
