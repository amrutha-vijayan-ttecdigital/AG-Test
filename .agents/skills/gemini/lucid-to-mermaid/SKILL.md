---
name: lucid-to-mermaid
description: Render Lucidchart or Lucidspark pages to Mermaid from shared Lucid graph IR. Use when the user asks for .mmd files derived from Lucid, not as an implementation source.
---

# Lucid To Mermaid

This skill renders Mermaid files from the shared `lucid-core` physical/logical graph. Mermaid is a derived view and must not be used as the canonical interchange format for DFCX, playbook, or CX Agent Studio implementation logic.

## Requirements

- Prefer `LUCID_API_KEY`; `LUCID_TOKEN` remains a deprecated alias.
- Use `--input-json` for offline operation.

## Commands

```bash
python3 .agents/skills/gemini/lucid-to-mermaid/scripts/lucid_to_mermaid.py <LUCID_URL_OR_ID> --out-dir docs/diagrams --save-ir docs/diagrams/lucid_compiled.json
python3 .agents/skills/gemini/lucid-to-mermaid/scripts/lucid_to_mermaid.py --input-json docs/designs/lucid_raw.json --out-dir docs/diagrams --pages "Main Dialog" "Authentication"
```

The renderer preserves full labels, avoids ID collisions with stable hash suffixes, retains note/data shapes as graph nodes, resolves valid line-to-line chains, and emits diagnostics for unresolved or ambiguous topology.

