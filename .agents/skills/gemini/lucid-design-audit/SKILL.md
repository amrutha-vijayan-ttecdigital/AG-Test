---
name: lucid-design-audit
description: Read-only audit of Lucid designs against Dialogflow CX, playbooks, local docs, or CX Agent Studio artifacts using the shared Lucid graph compiler as the design source.
---

# Lucid Design Audit

This skill is investigative and read-only by default. It may compare compiled Lucid graph artifacts with local files or live runtime state, but it must not mutate Lucid, Dialogflow CX, playbooks, or CX Agent Studio apps.

## Source Of Truth

Run `lucid-compile-graph` or the core-backed `lucid-read-design` script first. Use these artifacts in this order:

1. Raw Lucid REST snapshot.
2. Physical graph IR.
3. Logical graph IR.
4. CX semantic IR and diagnostics.
5. Derived Markdown, Mermaid, PNGs, and context packets.

Do not use old Lucid examples with top-level `shapes`, `connections`, `containedByPage`, `shapeId`, or `textAreas[].t`. The Lucid contents response has `pages[].items.shapes`, `pages[].items.lines`, `pages[].items.groups`, and `pages[].items.layers`; text comes from `textAreas[].text`.

## Mapping Rules

- A Lucid diamond is decision evidence, not automatically a DFCX page.
- If the design or current implementation shows that the routes belong on the preceding prompt page, preserve that relationship.
- Map DFCX pages, event handlers, route groups, playbooks, and CX Agent Studio agents only from explicit evidence or clearly marked inference.
- Keep ambiguity visible in the report rather than forcing a single interpretation.

## Audit Flow

```bash
python3 .agents/skills/gemini/lucid-compile-graph/scripts/lucid_compile_graph.py <LUCID_URL_OR_ID> --out-dir docs/designs/lucid-compiled --save-raw
```

Then compare the compiled logical/semantic IR against local docs, exported DFCX state, playbook files, or CX Agent Studio app definitions. Any proposed write must be delivered as a separate, explicit apply step and must not be executed during the audit.

