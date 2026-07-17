---
name: lucid-ces-design-audit
description: Audit the compiled CES design IR, reporting structural and semantic ambiguities or failures, and compare the design against a saved CES runtime snapshot.
---

# Audit and Lint CES Design

Lints the compiled CES IR against 38 semantic and structural validation rules, reporting potential design flaws, gaps in test coverage, or unconfigured variables. Can also run a comparison (diff) between the design IR and an offline runtime app export.

## Purpose

Designers and developers use this linter to identify model-driven gaps in instructions, missing confirmations on sensitive tools, variables that lack owner definitions, and undocumented loops. 

## Usage

```bash
# Audit design and fail on errors
python .agents/skills/gemini/lucid-ces-design-audit/scripts/lucid_ces_design_audit.py \
  --ir docs/designs/ces/ces_ir.json \
  --report docs/designs/ces/ces_lint.md \
  --fail-on error

# Compare design against saved runtime export
python .agents/skills/gemini/lucid-ces-design-audit/scripts/lucid_ces_design_audit.py \
  --ir docs/designs/ces/ces_ir.json \
  --ces-export fixtures/ces_app_export.json \
  --runtime-diff docs/designs/ces/runtime_diff.md
```

## Options

* `--ir` (Required): Path to the compiled CES IR JSON file.
* `--report`: Output path for the Markdown linter report.
* `--fail-on`: Either `error`, `warning`, or `never` (defaults to `error`). Exits with code 1 if matching severities are found.
* `--format`: Output format, either `text` or `json`.
* `--ces-export`: Saved CES application export JSON path to compare.
* `--runtime-diff`: Output path for the Markdown difference report.
