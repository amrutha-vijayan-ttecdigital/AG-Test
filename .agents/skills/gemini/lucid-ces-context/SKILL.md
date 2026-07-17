---
name: lucid-ces-context
description: Generate a task-specific context packet from the compiled CES IR to avoid overloading LLM model context windows with irrelevant details.
---

# Generate Task-Specific Context Packet

Creates a compact, tailored context packet containing only the relevant application parts, selected agent contracts, MUST/MAY/MUST_NOT claims, and validation findings related to a target agent and task.

## Purpose

Instead of dumping the entire Lucid raw JSON, Mermaid, and Markdown documents into the context of an engineering model, this skill generates a pruned task-specific packet. It filters the agent capability graph by a target agent and search radius, ensuring a high signal-to-noise ratio.

## Usage

```bash
python .agents/skills/gemini/lucid-ces-context/scripts/lucid_ces_context.py \
  --ir docs/designs/ces/ces_ir.json \
  --agent agent.billing \
  --task "Implement confirmation before payment update" \
  --include-evaluations \
  --output docs/designs/ces/context/payment-update.md
```

## Options

* `--ir` (Required): Path to the compiled CES IR JSON file.
* `--agent`: The ID of the target agent.
* `--task`: Description of the task or requested change.
* `--radius`: Neighborhood BFS depth from target agent (default: 1).
* `--include-evaluations`: Flag to include evaluation scenarios in the packet.
* `--include-visual-evidence`: Flag to include visual evidence references.
* `--max-chars`: Max character length; trims non-critical text from the packet if exceeded.
* `--output`, `-o`: Output path for the Markdown context packet. If omitted, prints to stdout.
