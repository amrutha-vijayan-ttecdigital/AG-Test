---
name: ces-api
description: Call the Google CX Agent Studio / CES REST API (v1 + v1beta) for the app configured in .env. Use to create, list, get, patch, or delete apps, agents, tools, toolsets, examples, guardrails, deployments, versions, conversations, or evaluations — and to smoke-test a live session with one utterance. This is the foundation the other ces-* skills build on.
---

# CES / Agent Studio REST API

A thin, dependency-light wrapper around the Customer Engagement Suite (CES) Agent
Studio REST API. Prefer this skill for any CES state change so the change is
reproducible — do not click through the console for anything you could script.

## Purpose

Everything under `apps/{app}` is reachable here: `agents`, `tools`, `toolsets`,
`examples`, `guardrails`, `deployments`, `versions`, `changelogs`,
`conversations`, and (with `--beta`) `evaluations`. The shared client at
`.agents/scripts/ces_client.py` is imported by `ces-sync`, `ces-deploy`,
`ces-eval`, and `ces-voice-test`, so there is exactly one place that handles
auth, requests, and long-running operations.

## Auth & config

Uses the active gcloud account's token (falling back to Application Default
Credentials). Run `./setup.sh --verify` first; it checks ADC and the active
account. Connection details come from the kit-root `.env`:

| `.env` key | meaning |
|---|---|
| `GCP_PROJECT_ID` | GCP project id (required) |
| `GCP_REGION` | location, e.g. `us` (default `us`) |
| `CES_APP_ID` / `CES_AGENT_ID` | the app id from the console URL (required) |
| `CES_DEPLOYMENT_ID` | a deployment id (optional; used by `--deployed`) |
| `CES_API_HOST` | host override (default `ces.googleapis.com`) |

CES is a global API — the location is in the URL path, not the host.

## Usage

```bash
S=.agents/skills/gemini/ces-api/scripts

# Inspect the app and its resources
python $S/ces.py app get
python $S/ces.py agents list
python $S/ces.py agents get <agent-id>
python $S/ces.py toolsets list
python $S/ces.py --beta evaluations list

# Patch an agent from a local JSON file (update mask inferred from the file's keys)
python $S/ces.py agents patch <agent-id> --body my-agent.json
python $S/ces.py agents patch <agent-id> --body my-agent.json --update-mask instruction

# Create a resource with a server-assigned id
python $S/ces.py tools create --body my-tool.json

# Smoke-test one turn against the live DRAFT (no deployment)
python $S/ces.py sessions run --input "I'd like to book a table for two"

# Smoke-test against a specific entry agent and a deployment
python $S/ces.py sessions run --input "hello" --agent billing --deployment <deployment-id>
python $S/ces.py sessions run --input "hello" --deployed        # uses CES_DEPLOYMENT_ID

# Dump the whole app to inventory/ (per-resource JSON + _summary.md)
python $S/inventory.py
python $S/inventory.py --out docs/inventory
```

`sessions run` prints the route, tools invoked, and spoken text to stderr and
the full JSON response to stdout — pipe stdout to `jq` to drill in.

## Options (ces.py)

* `resource` — `app`, a collection name, or `sessions`.
* `verb` — `get | list | create | patch | delete | run`.
* `id` — resource id (for `get` / `patch` / `delete`).
* `--body` — JSON file for `create` / `patch`.
* `--update-mask` — comma-separated fields for `patch` (inferred from the body if omitted).
* `--beta` — use the v1beta surface (evaluations, etc.).
* `--input` — utterance for `sessions run`.
* `--agent` — entry agent id for `sessions run` (default: the app root).
* `--deployment` / `--deployed` — target a deployment id (or `CES_DEPLOYMENT_ID`) instead of the draft.
* `--tool-fakes` — set `useToolFakes` for `sessions run`.
* `--session` — reuse a session id across calls for `sessions run`.

## Python usage

```python
import sys; sys.path.insert(0, ".agents/scripts")
from ces_client import CES, short

c = CES()
for a in c.list("agents"):
    print(short(a["name"]), a.get("displayName"))

resp = c.run_session("smoke-1", text="hello")        # draft
resp = c.run_session("smoke-2", text="hello", deployment_id=c.deployment_id)
```

## Notes

* **Draft vs deployment.** `sessions run` hits the draft (current settings) by
  default. Callback *return values* are only applied when a deployment is
  targeted — see `ces-deploy`. Use `--deployment`/`--deployed` to test what a
  real caller gets.
* **Reproducibility.** Capture changes through `ces-sync` / `ces-deploy` and
  commit the result; treat the console as read-only verification.
