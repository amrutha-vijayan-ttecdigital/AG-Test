---
name: mermaid-to-lucid
description: Create a Lucid Standard Import archive from Mermaid. Uploading is disabled unless --apply is explicitly passed.
---

# Mermaid To Lucid

Use this skill only when a user asks to create a new Lucid document from an existing Mermaid file. This is not part of the Lucid-to-DFCX compiler path.

By default, the script is offline/read-only and writes a `.lucid` archive. It uploads to Lucid only when `--apply` is passed.

## Command

```bash
python3 .agents/skills/gemini/mermaid-to-lucid/scripts/mermaid_to_lucid.py docs/diagrams/example.mmd
python3 .agents/skills/gemini/mermaid-to-lucid/scripts/mermaid_to_lucid.py docs/diagrams/example.mmd --apply
```

The Standard Import archive uses the official media type `x-application/vnd.lucid.standardImport`, shape `text`, and line `text` objects. It does not emit REST-response-style `textAreas`.

