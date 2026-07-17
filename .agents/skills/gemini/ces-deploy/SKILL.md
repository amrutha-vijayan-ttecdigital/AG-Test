---
name: ces-deploy
description: Make a CES Agent Studio draft live the safe way — cut an immutable version from the draft and atomically repoint the deployment(s), with rollback. Also exports the live deployed state to a tracked, diffable tree so git is the receipt of what is actually serving. Use after ces-sync; required before testing real callback/transfer behavior.
---

# Deploy & capture CES versions

A draft edit is not live. This skill is the anti-clobber path from "edited the
draft" to "callers get the new behavior," plus the capture step that records
what is live into git.

## Purpose

- **`deploy.py`** cuts an immutable **version** from the current draft and moves
  each deployment's `appVersion` pointer to it. Deployment ids are
  telephony-bound and never recreated — only the pointer moves. Supports
  rollback and single-deployment targeting.
- **`export.py`** writes the live deployed state (instructions, wiring,
  callbacks, app config) to a diffable tree so `git add … && git commit` becomes
  the receipt of what is actually serving.

> Why this matters: the **draft does not apply callback return values** and may
> not route through your telephony path. Running a session against the draft
> shows raw-model behavior, not what a caller gets. Testing real
> callback/transfer behavior therefore *requires* a deploy.

## Usage

```bash
DEPLOY=.agents/skills/gemini/ces-deploy/scripts/deploy.py
EXPORT=.agents/skills/gemini/ces-deploy/scripts/export.py

# Cut the current draft into a version and repoint EVERY deployment to it
python $DEPLOY --label "billing-fix" --desc "fix dispute routing"

# Iterate on ONE deployment (e.g. a dedicated test ingress) without touching the shared one
python $DEPLOY --label "billing-fix" --deployment test-line

# Roll back (nothing is deleted — the pointer just moves)
python $DEPLOY --rollback <versionId>
python $DEPLOY --rollback <versionId> --deployment phone

# Capture the now-live state and commit it
python $EXPORT && git add env-snapshot && git commit -m "capture: billing-fix live"
```

`deploy.py` prints a per-deployment rollback command after every deploy — keep it.

## Options

**deploy.py**
* `--label NAME` — display name for the new version (required to cut + deploy).
* `--desc TEXT` — version description.
* `--rollback VERSION_ID` — repoint to an existing version instead of cutting a new one.
* `--deployment NAME_OR_ID` — target one deployment by displayName or id (default: all).

**export.py**
* `--out DIR` — output directory (default `env-snapshot/`).
* `--deployment NAME_OR_ID` — which deployment to export (default: most recently updated).

## Anti-clobber rules

1. **Claim a shared deployment before iterating.** Two people repointing the
   same deployment means a different version on every call. Announce it.
2. **Cutting a version snapshots the WHOLE draft** — including anyone else's
   in-flight edits. Announce before cutting on a shared app.
3. **Keep the deployment id stable.** `deploy.py` only moves the `appVersion`
   pointer; it never deletes/recreates the (telephony-bound) deployment.
4. **Always keep the rollback** it prints — don't prune the last-known-good version.
5. **Capture after deploying** — run `export.py` and commit so the snapshot
   reflects what is live. There is a version cap per app; prune old versions in
   the console before cutting if you hit it.

## Note on snapshots

CES version snapshots omit each agent's `toolsets` wiring. `export.py` merges it
back from a live agent GET and flags it per agent as `toolsets_source`, so a
faithful copy of "what's live" still includes toolset wiring.
