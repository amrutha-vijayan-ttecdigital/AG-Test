---
name: lucid-read-design
description: Read a Lucidchart or Lucidspark document through the shared Lucid graph compiler and produce Markdown derived from canonical physical, logical, and semantic IR.
---

# Read Lucid Design

Use this skill when the user wants to inspect, review, or understand a Lucid design. The script is read-only and uses the shared `lucid-core` parser. Markdown is a derived view, not the source of truth.

## Requirements

- Prefer `LUCID_API_KEY` in `.env` or the environment.
- `LUCID_TOKEN` is accepted as a deprecated compatibility alias.
- Use `--input-json` for offline operation without credentials.

## Commands

```bash
python3 .agents/skills/gemini/lucid-read-design/scripts/lucid_read_design.py <LUCID_URL_OR_ID> --output docs/designs/design.md --save-raw docs/designs/lucid_raw.json --save-ir docs/designs/lucid_compiled.json
python3 .agents/skills/gemini/lucid-read-design/scripts/lucid_read_design.py --input-json docs/designs/lucid_raw.json --output docs/designs/design.md
```

The generated Markdown includes nodes, resolved connections, entrypoints, branches, joins, cycles, and diagnostics. It does not invent a single process-step order for branching or cyclic graphs.

