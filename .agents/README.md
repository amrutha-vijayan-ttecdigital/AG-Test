# Project Agent Assets

This directory is the canonical project-level home for agent-facing assets shared by Antigravity, Codex-style agents, and supporting automation.

## Skills

Lucid/Gemini skills are consolidated under:

`./.agents/skills/gemini/`

Do not duplicate these skills under `.gemini/skills/` or `skills/gemini/`. If a tool expects one of the legacy paths, update the tool configuration to read from `.agents/skills/gemini/`.

## Rules

- Keep skill source here as read-only project tooling unless intentionally updating the skill.
- Do not store secrets, credentials, API tokens, or generated local caches here.
- Do not add legacy Dialogflow CX implementation tooling here.
