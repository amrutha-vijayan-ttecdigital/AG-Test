---
name: lucid-compile-graph
description: Compile a Lucid REST document snapshot into physical, logical, semantic, Markdown, Mermaid, and context-packet artifacts without mutating Lucid or Google Cloud.
---

# Lucid Compile Graph

Use this skill when a Lucid design must be read as a graph before auditing or implementation work.

The compiler is read-only. It fetches or loads a Lucid REST document snapshot, preserves raw shapes, lines, groups, layers, custom data, and linked data, then derives logical topology, conservative CX semantics, Markdown, Mermaid, and model-context packets from that canonical graph.

## Commands

```bash
python3 .agents/skills/gemini/lucid-compile-graph/scripts/lucid_compile_graph.py <lucid-url-or-document-id> --out-dir docs/designs/lucid-compiled
python3 .agents/skills/gemini/lucid-compile-graph/scripts/lucid_compile_graph.py --input-json fixtures/lucid.json --out-dir /tmp/lucid-compiled
```

Use `--save-raw` when fetching live Lucid content and a raw snapshot should be retained. Use `--input-json` for offline tests and reviews.

Do not use Mermaid, PNG, or Markdown as implementation source data. They are derived views.

