#!/usr/bin/env python3
"""Faithfully export the app's DEPLOYED state into a tracked, diffable tree.

This is the git CAPTURE step: run it after deploying, commit the diff, and the
commit becomes the receipt of what is actually live.

    python .agents/skills/gemini/ces-deploy/scripts/export.py
    python .agents/skills/gemini/ces-deploy/scripts/export.py --out env-snapshot --deployment phone

Writes <out>/:
    profile.json        key facts + the live version id + resource counts
    app.json            app settings (model, rootAgent, logging, variables)
    agents/<slug>.md    instruction text (the human-diffable surface)
    agents/<slug>.json  that agent's wiring: description, tools, childAgents, toolsets, callbacks
    callbacks/*.py      callback code, one file per hook entry
    tools.json  toolsets.json  examples.json

Source = the deployment's appVersion snapshot (what is actually serving). NOTE:
CES version snapshots DROP each agent's `toolsets` wiring, so it is merged back
from a live agent GET (the draft) and flagged per agent as `toolsets_source`.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time


def _load_shared_client():
    here = pathlib.Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / ".agents" / "scripts"
        if cand.is_dir():
            sys.path.insert(0, str(cand))
            break
    from ces_client import CES, short  # type: ignore
    return CES, short


CES, short = _load_shared_client()

HOOKS = ("beforeModelCallbacks", "afterModelCallbacks", "beforeToolCallbacks", "afterToolCallbacks")
HOOK_SHORT = {"beforeModelCallbacks": "beforeModel", "afterModelCallbacks": "afterModel",
              "beforeToolCallbacks": "beforeTool", "afterToolCallbacks": "afterTool"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Export the live deployed CES state to disk")
    ap.add_argument("--out", default="env-snapshot", help="output dir (default: env-snapshot/)")
    ap.add_argument("--deployment", metavar="NAME_OR_ID",
                    help="which deployment to export (default: most recently updated)")
    args = ap.parse_args()

    c = CES()
    out = pathlib.Path(args.out)
    (out / "agents").mkdir(parents=True, exist_ok=True)
    (out / "callbacks").mkdir(parents=True, exist_ok=True)

    deps = c.list("deployments")
    if not deps:
        sys.exit("no deployments exist for this app")
    if args.deployment:
        deps = [d for d in deps if short(d["name"]) == args.deployment
                or (d.get("displayName") or "").lower() == args.deployment.lower()]
        if not deps:
            sys.exit(f"--deployment {args.deployment!r} matched no deployment")
        dep = deps[0]
    else:
        dep = max(deps, key=lambda d: d.get("updateTime", ""))

    ver_id = short(dep.get("appVersion", ""))
    snap = (c.get("versions", ver_id).get("snapshot", {}) or {})
    app = snap.get("app", {}) or {}

    # Live toolset wiring per agent (the snapshot drops it).
    live_toolsets: dict[str, list | None] = {}
    for a in snap.get("agents", []):
        slug = short(a["name"])
        try:
            live_toolsets[slug] = c.get("agents", slug).get("toolsets", [])
        except SystemExit:
            live_toolsets[slug] = None  # deployed-only agent, absent from the draft

    written = []
    for a in snap.get("agents", []):
        slug = short(a["name"])
        instr = a.get("instruction")
        instr = instr if isinstance(instr, str) else (instr or {}).get("text", "")
        (out / "agents" / f"{slug}.md").write_text(instr or "")

        wiring = {k: a[k] for k in ("displayName", "description", "tools", "childAgents",
                                    "transferRules", "remoteDialogflowAgent") if k in a}
        cb_meta: dict[str, list] = {}
        for h in HOOKS:
            specs = []
            for i, cb in enumerate(a.get(h) or []):
                fn = f"{slug}.{HOOK_SHORT[h]}.{i}.py"
                (out / "callbacks" / fn).write_text(cb.get("pythonCode", ""))
                specs.append({"description": cb.get("description", ""), "code_file": f"callbacks/{fn}"})
            if specs:
                cb_meta[h] = specs
        if cb_meta:
            wiring["callbacks"] = cb_meta
        ts = live_toolsets.get(slug)
        wiring["toolsets"] = ts if ts is not None else []
        wiring["toolsets_source"] = ("live-draft (snapshot drops it)" if ts is not None
                                     else "deployed-only agent; unavailable")
        (out / "agents" / f"{slug}.json").write_text(json.dumps(wiring, indent=2, sort_keys=True))
        written.append(slug)

    for coll in ("tools", "toolsets", "examples"):
        (out / f"{coll}.json").write_text(json.dumps(snap.get(coll, []), indent=2, sort_keys=True))
    (out / "app.json").write_text(json.dumps(app, indent=2, sort_keys=True))

    ver = c.get("versions", ver_id)
    profile = {
        "project": c.project,
        "location": c.location,
        "app_id": c.app,
        "deployment_id": short(dep["name"]),
        "deployment_name": dep.get("displayName"),
        "deployed_version_id": ver_id,
        "deployed_version_label": ver.get("displayName"),
        "model": (app.get("modelSettings") or {}).get("model"),
        "root_agent": short(app.get("rootAgent", "")),
        "counts": {k: len(snap.get(k, [])) for k in ("agents", "tools", "toolsets", "examples")},
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "exported_from": "deployed appVersion snapshot + live toolsets merge",
    }
    (out / "profile.json").write_text(json.dumps(profile, indent=2, sort_keys=True))
    print(f"{len(written)} agents -> {out}/  (version {ver_id[:8]} {ver.get('displayName')!r})")
    print("Commit the diff: git add", out, "&& git commit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
