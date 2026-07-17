#!/usr/bin/env python3
"""Dump the full current state of the target CES app to inventory/.

Writes one JSON file per resource plus a human-readable _summary.md, so you can
diff the live app over time or hand a model a compact map of what exists.

    python .agents/skills/gemini/ces-api/scripts/inventory.py
    python .agents/skills/gemini/ces-api/scripts/inventory.py --out docs/inventory
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


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

V1_COLLECTIONS = ["agents", "tools", "toolsets", "examples", "guardrails",
                  "deployments", "versions", "changelogs"]
V1BETA_COLLECTIONS = ["evaluations", "evaluationDatasets", "scheduledEvaluationRuns"]


def _dump(path: pathlib.Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="inventory", help="output directory (default: inventory/)")
    args = ap.parse_args()
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    c = CES()
    summary = ["# CES App Inventory", "", f"App: `{c.app_path}`", ""]

    try:
        app = c.app_get()
        _dump(out / "app.json", app)
        summary += [f"## App\n", f"- displayName: `{app.get('displayName', '?')}`",
                    f"- rootAgent: `{short(app.get('rootAgent'))}`",
                    f"- model: `{(app.get('modelSettings') or {}).get('model', '?')}`", ""]
    except SystemExit as e:
        summary += [f"## App\n\n**ERROR** {e}\n"]

    for coll in V1_COLLECTIONS:
        try:
            items = c.list(coll)
        except SystemExit as e:
            summary += [f"## {coll}\n\n**ERROR** {e}\n"]
            continue
        summary.append(f"## {coll} ({len(items)})\n")
        for it in items:
            rid = short(it.get("name"))
            _dump(out / coll / f"{rid}.json", it)
            summary.append(f"- `{rid}` — {it.get('displayName') or rid}")
        summary.append("")

    c_beta = CES(beta=True)
    for coll in V1BETA_COLLECTIONS:
        try:
            items = c_beta.list(coll)
        except SystemExit as e:
            summary += [f"## {coll} (v1beta)\n\n**ERROR** {e}\n"]
            continue
        summary.append(f"## {coll} (v1beta, {len(items)})\n")
        for it in items:
            _dump(out / coll / f"{short(it.get('name'))}.json", it)
            summary.append(f"- `{short(it.get('name'))}`")
        summary.append("")

    (out / "_summary.md").write_text("\n".join(summary))
    print(f"Wrote inventory to {out}/ (see _summary.md)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
