---
name: handoff
description: Compact the current conversation and workspace state into a handoff document for another agent or a human teammate to pick up. Trigger this skill when the user requests a handoff, session transition, or summary for another developer or agent.
disable-model-invocation: true
---

# handoff

This skill generates a comprehensive, structured handoff markdown document summarizing the current conversation and workspace status so a fresh agent or human teammate can seamlessly take over the work.

## Core Rules

1. **OS Temp Directory**: The handoff document **MUST** be written to the temporary directory of the user's OS, not the active project workspace. This keeps the codebase clean.
2. **Suggested Skills**: Include a dedicated "Suggested Skills" section listing the exact Antigravity skills the incoming agent/user should invoke next (e.g. `grab-latest-skills`, `create-ag-skill`, etc.).
3. **Reference, Don't Duplicate**: Reference existing plans, PRDs, ADRs, or commits by path or URL instead of duplicating their contents.
4. **Redact Secrets**: Strip any sensitive data like API keys, credentials, or personal information (PII).
5. **Tailor to Next Session Focus**: If user arguments are provided, use them to describe what the next session will focus on and tailor the handoff document accordingly.

## Usage

Run the handoff generator script from the project root:

```bash
python3 .agents/skills/gemini/handoff/scripts/create_handoff.py [options]
```

### Arguments:
* `--recipient` (default: `human`): The target recipient. Options: `human` or `agent`.
* `--focus` (optional): Description of what the next session or agent will focus on.
* `--out` (optional): Output file path override (defaults to OS temporary directory).
