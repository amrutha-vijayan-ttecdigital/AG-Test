---
name: visual-design-audit
description: Read-only visual audit of Dialogflow CX, playbook, or CX Agent Studio designs using PNGs together with compiled Lucid graph artifacts.
---

# Visual Design Audit

Use this skill when visual layout matters: swimlanes, nearby labels, prompt boxes, decision diamonds, fallbacks, or page grouping that cannot be proven from REST contents alone.

## Rules

- PNGs are visual evidence, not topology source data.
- Use compiled Lucid graph artifacts first, then inspect PNGs to resolve visual context that REST contents cannot encode.
- Do not generate or execute live DFCX/CX Agent Studio patches from this skill.
- If a write is needed, produce a separate proposed apply command or patch plan with an explicit `--apply` guard.

## Workflow

1. Compile the Lucid design with `lucid-compile-graph` or load existing compiled artifacts.
2. Inspect the relevant PNG or crop for visual context.
3. Compare the visual evidence with logical graph edges, diagnostics, and semantic inferences.
4. Compare read-only DFCX/playbook/CX Agent Studio state if needed.
5. Report source-backed findings, inferred findings, ambiguity, and any proposed apply step separately.

Remember: an "Expected Response?" diamond often represents route/event-handler branching for the preceding prompt page, but this is not a universal rule. Preserve the evidence and explain the mapping decision.

