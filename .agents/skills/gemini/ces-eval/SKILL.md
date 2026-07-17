---
name: ces-eval
description: Text/routing test harness for a CES Agent Studio app. Runs JSON packs of multi-turn cases through runSession and asserts on the agent route, tools invoked, response keywords, accumulated session params, and latency. Fast routing checks against the draft (with optional tool fakes) without real audio; can also target a deployment with real backends.
---

# Text & routing eval harness

Fast, scriptable regression checks for agent **routing and tool behavior** —
without audio. It exercises the LLM's delegation and tool-call decisions through
the same `runSession` API a caller's turns flow through, and asserts on the
diagnostic trace.

## Purpose

Each test case is one CES session played turn by turn. For every turn you can
assert:

| `expect` key | checks |
|---|---|
| `Agent route path` | the agent chain (tolerant: `router -> billing` matches roles `Router`/`Billing`) |
| `expected_tool_invocation` | a tool was invoked (substring match) |
| `contains` / `keywords` | the spoken response text contains these |
| `params` | accumulated session variables match (`~nonempty`, `~iso-date`, exact) |

Latency is always checked. Session variables seeded via `sessionParams` and any
`updatedVariables` written by callbacks thread forward across turns, so a later
`params` assertion sees accumulated state.

## Usage

```bash
RUN=.agents/skills/gemini/ces-eval/scripts/run_eval.py

# Routing smoke against the draft, with tool fakes ON (no real backends hit)
python $RUN --test-file .agents/skills/gemini/ces-eval/examples/routing.json

# Save full results
python $RUN --test-file pack.json --output results.json

# Real backends (tools actually call out), still against the draft
python $RUN --test-file pack.json --no-fakes

# Against a cut version: target CES_DEPLOYMENT_ID (real backends)
python $RUN --test-file pack.json --deployed

# Start sessions at a specific sub-agent rather than the root
python $RUN --test-file pack.json --entry-agent billing
```

## Targeting (which surface runs)

| flags | surface | tool calls |
|---|---|---|
| *(default)* | draft / current settings | **faked** (`useToolFakes`) — routing only |
| `--no-fakes` | draft / current settings | real backends |
| `--deployed` | the deployment in `CES_DEPLOYMENT_ID` | real backends |

This split matters: the **draft** is what `ces-sync` writes and what you iterate
on; a **deployment** is a cut version a caller can hit. Callback *return values*
only apply on a deployment — for those, use `--deployed` (or test by voice via
`ces-voice-test`).

> Tool fakes only stand in for tools that actually have a fake configured;
> others still call the real backend even with fakes ON. For data-gated
> scenarios, seed identifiers via `sessionParams` or run `--no-fakes` against a
> backend with the right test data.

## Test file format

See `examples/routing.json`. A pack is `{ "testCases": [ { "displayName", "turns": [ { "user", "expect" } ] } ] }`,
with an optional top-level or per-case `startUtterance` and per-case
`sessionParams`. Date templates like `{{date:friday+1w}}` in `user` text resolve
to a real upcoming date at run time.

## Options

* `--test-file PATH` — the JSON pack (required).
* `--output PATH` — write full JSON results.
* `--no-fakes` — disable `useToolFakes` (real backends).
* `--deployed` — target `CES_DEPLOYMENT_ID` instead of the draft.
* `--entry-agent ID` — start sessions at this agent (default: app root).

## QA report generation

Generate human-readable test scripts and governance reports from specs,
results, or directly from a CES Design IR. All output is Markdown —
shareable with clients, PMs, and governance teams without developer context.

```bash
RPT=.agents/skills/gemini/ces-eval/scripts/generate_qa_report.py

# From a CES Design IR — generates BOTH a human test script AND a runnable spec
python $RPT --mode from-design --ir ces_ir.json \
  --agent-name "Hotel Booking Agent" --output-dir testcases/reports/

# From an existing JSON spec — human-readable test script only
python $RPT --mode human --spec spec.json \
  --agent-name "Hotel Booking Agent" --output-dir testcases/reports/

# From automated results — full governance report with design affirmation
python $RPT --mode results --results results.json --spec spec.json \
  --ir ces_ir.json --agent-name "Hotel Booking Agent" --output-dir testcases/reports/

# From roleplay results
python $RPT --mode roleplay --results roleplay_results.json \
  --agent-name "Hotel Booking Agent" --output-dir testcases/reports/
```

### Full pipeline (design → test → report)

```bash
# 1. Compile Lucidchart design to IR
python .agents/skills/gemini/lucid-to-ces-ir/scripts/lucid_to_ces_ir.py \
  <LUCID_URL> --output ces_ir.json

# 2. Generate test script + runnable spec from the design
python $RPT --mode from-design --ir ces_ir.json \
  --agent-name "My Agent" --output-dir testcases/reports/

# 3. Run the tests
python $RUN --test-file testcases/reports/my_agent_spec.json --output results.json

# 4. Generate governance report
python $RPT --mode results --ir ces_ir.json \
  --spec testcases/reports/my_agent_spec.json --results results.json \
  --agent-name "My Agent" --output-dir testcases/reports/
```

The same test cases run both ways — human-readable scripts for manual QA
and JSON specs for automated execution share the same test case IDs, steps,
and expected results.

### Report templates

* `docs/qa/human_test_script_template.md` — step-by-step test script format
* `docs/qa/qa_governance_report.md` — governance report with design affirmation, CX scorecard, issues, and sign-off
