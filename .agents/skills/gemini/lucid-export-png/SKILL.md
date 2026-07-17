---
name: lucid-export-png
description: Export Lucidchart or Lucidspark pages as PNG files with a manifest containing page IDs, checksums, and dimensions.
---

# Lucid Export PNG

Use this skill when visual evidence from a Lucid design is needed. PNGs are visual evidence only; they are not the canonical topology source.

## Requirements

- Prefer `LUCID_API_KEY`; `LUCID_TOKEN` is accepted as a deprecated alias.

## Commands

```bash
python3 .agents/skills/gemini/lucid-export-png/export.py <LUCID_URL_OR_ID> --output docs/designs
python3 .agents/skills/gemini/lucid-export-png/export.py <LUCID_URL_OR_ID> --output docs/designs --page 2
python3 .agents/skills/gemini/lucid-export-png/export.py <LUCID_URL_OR_ID> --output docs/designs --page-id abc123
python3 .agents/skills/gemini/lucid-export-png/export.py <LUCID_URL_OR_ID> --list
```

Exports include the page ID in each filename to avoid collisions when page titles repeat. The script also writes a JSON manifest with file paths, page IDs, SHA-256 checksums, byte counts, and PNG dimensions when available.

