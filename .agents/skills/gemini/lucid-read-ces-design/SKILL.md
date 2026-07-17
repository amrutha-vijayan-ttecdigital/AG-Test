---
name: lucid-read-ces-design
description: Read a compiled CES semantic IR JSON file and render a structured, human-readable Markdown report documenting the agents, tools, handoffs, guardrails, and linter findings.
---

# Read CES Design and Render Markdown Report

Generate a detailed Markdown specification document from the compiled CES semantic IR.

## Purpose

The markdown report summarizes the agent contracts, delegation rules, capabilities, and variables in the design without assuming a single linear path. It highlights MUST, MAY, and MUST_NOT requirements, and displays diagnostics compiled by the linter.

## Usage

```bash
python .agents/skills/gemini/lucid-read-ces-design/scripts/lucid_read_ces_design.py \
  --ir docs/designs/ces/ces_ir.json \
  --output docs/designs/ces/design.md
```

## Options

* `--ir` (Required): Path to the compiled CES IR JSON file.
* `--output`, `-o`: Output path for the Markdown report. If omitted, the Markdown is printed to stdout.
