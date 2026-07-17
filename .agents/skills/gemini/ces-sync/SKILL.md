---
name: ces-sync
description: Push local, version-controlled agent definitions (instructions, toolsets, standalone tools, childAgents, callbacks, app config) into the CES Agent Studio DRAFT so the app is reproducible from git instead of console clicks. Supports scoped single-agent syncs to avoid clobbering teammates' in-flight console edits. Run ces-deploy afterward to make the draft live.
---

# Sync local source → CES draft

Makes the CES app reproducible from a source tree. Editing a draft in the
console is fine for quick iteration, but it is not durable — `ces-sync` is how
you push the authoritative, git-tracked definition back up.

## Purpose

Reads a source tree of agent instructions, OpenAPI toolsets, standalone tools,
and callbacks, then creates or patches the matching CES resources in the
**draft**. It does the seven things the console does by hand: toolsets → tools →
agents → tool wiring → child hierarchy → callbacks → app config.

> A sync only updates the **draft**. Nothing a caller hits changes until you cut
> a version and repoint a deployment — use `ces-deploy`. Callback *return
> values* in particular are only applied when deployed.

## Source layout (`--src`, default: current directory)

```
app.json                      # optional: model, globalInstruction, variableDeclarations, rootAgent, logging
agents/<slug>/instruction.md  # the agent's instruction (XML-structured prompt)
agents/<slug>/agent.json      # displayName, description, childAgents, toolsets, tools, callbacks
toolsets/<slug>.yaml          # OpenAPI schema for toolset <slug>
toolsets/host-rewrites.json   # optional {"dev-host": "prod-host"} applied to YAMLs at sync time
tools/<name>.json             # standalone CES tool body (dataStoreTool / pythonFunction / agentTool / ...)
callbacks/<file>.py           # callback code referenced from agent.json
```

`agent.json` reference tokens, resolved to live resource names at wire time:

| field | example | resolves to |
|---|---|---|
| `childAgents` | `["billing", "@display:Transfer Bridge"]` | sibling agent slugs / an existing agent by displayName |
| `toolsets` | `["billing-api"]` | `toolsets/billing-api.yaml`, all its operations wired |
| `tools` | `["faq-store", "@builtin:end_session", "@agent:billing"]` | a `tools/*.json` id, a built-in tool, or an agentTool to a sub-agent |
| `callbacks` | `{"beforeModelCallbacks": [{"description": "...", "file": "x.py"}]}` | `callbacks/x.py` as `pythonCode` |

See `examples/sample-app/` in this skill for a complete, minimal tree.

## Usage

```bash
SYNC=.agents/skills/gemini/ces-sync/scripts/sync.py

# Scoped (PREFERRED for edits) — patch one agent, leave everyone else's draft alone
SYNC_ONLY=billing python $SYNC --src ./my-app
python $SYNC --src ./my-app --only billing,router

# Full sync — toolsets, tools, agents, wiring, app config. Bootstrap / wholesale rewire only.
python $SYNC --src ./my-app
```

**Default to scoped.** A bare full sync patches every managed agent, toolset,
tool, and the app config — it will overwrite a teammate's unsaved console draft.
Before any sync, pull live → local for the agent you're about to touch and diff:

```bash
API=.agents/skills/gemini/ces-api/scripts/ces.py
python $API agents get billing > /tmp/billing-live.json
diff <(python -c "import json;print(json.dumps(json.load(open('/tmp/billing-live.json')),indent=2,sort_keys=True))") \
     <(python -c "import json;print(json.dumps(json.load(open('my-app/agents/billing/agent.json')),indent=2,sort_keys=True))")
```

If the live draft is ahead of local, stop and reconcile before syncing.

## Options

* `--src DIR` — source root (default `.`). Must contain `agents/`.
* `--only SLUGS` — comma-separated agent slugs to patch (same as `SYNC_ONLY`). Scoped mode skips toolsets, standalone tools, and app config.

## Toolset authentication

OpenAPI toolsets default to `serviceAgentIdTokenAuthConfig` (the CES service
agent's OIDC token — right for private Cloud Run / IAP backends). To use OAuth2
client-credentials instead, set in the environment:
`CES_TOOLSET_OAUTH_CLIENT_ID`, `CES_TOOLSET_OAUTH_SECRET_VERSION`,
`CES_TOOLSET_OAUTH_TOKEN_URL`, and optionally `CES_TOOLSET_OAUTH_SCOPE`.

## After syncing

1. Smoke-test the draft: `ces-api … sessions run --input "…"`.
2. Make it live: `ces-deploy` (cut a version + repoint the deployment).
3. Test real behavior (callbacks, transfers) against the deployment, not the draft.
