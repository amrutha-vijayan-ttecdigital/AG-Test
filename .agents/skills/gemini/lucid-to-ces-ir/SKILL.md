---
name: lucid-to-ces-ir
description: Compile a Lucidchart design for Google CX Agent Studio/CES into a semantic agent, policy, tool, handoff, callback, guardrail, variable, and evaluation IR. Use for nondeterministic CES agent designs. Do not use for DFCX page/route implementation.
---

# Compile Lucid designs for Google CX Agent Studio (CES)

Compile a Lucid chart snapshot containing LLM agents, tools, callbacks, and variables into a canonical, semantic IR conforming to the `ces-design-ir/v1` schema.

## Purpose

Google Customer Experience Agent Studio (CX Agent Studio) backed by the CES API runs model-driven, nondeterministic agents. Unlike deterministic Dialogflow CX (DFCX) flowcharts, CES designs must represent multiple possible paths, behavioral claims, modalities (MUST/MAY/MUST_NOT), and dynamic tool-invocations. 

This skill converts physical shapes and lines into the semantic IR.

## Usage

```bash
# Compile from an offline Lucid JSON snapshot
python .agents/skills/gemini/lucid-to-ces-ir/scripts/lucid_to_ces_ir.py \
  --input-json docs/designs/lucid_raw.json \
  --output docs/designs/ces/ces_ir.json

# Compile from a live Lucid document, saving the raw snapshot
python .agents/skills/gemini/lucid-to-ces-ir/scripts/lucid_to_ces_ir.py \
  <LUCID_URL_OR_ID> \
  --output docs/designs/ces/ces_ir.json \
  --save-raw docs/designs/lucid_raw.json
```

## Options

* `url_or_id`: The ID or URL of the Lucid document to fetch live.
* `--input-json`: Read from a saved Lucid document JSON file instead of fetching live.
* `--output`, `-o` (Required): The output path for the compiled CES IR.
* `--save-raw`: Save a copy of the retrieved raw Lucid snapshot.
