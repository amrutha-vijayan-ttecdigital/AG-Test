#!/usr/bin/env python3
"""The one safe way to deploy a CES app — cut a version from the draft and
repoint the deployment(s), keeping the (telephony-bound) deployment id stable.

    python .agents/skills/gemini/ces-deploy/scripts/deploy.py --label "<name>" [--desc "..."]
    python .agents/skills/gemini/ces-deploy/scripts/deploy.py --label "<name>" --deployment <name-or-id>
    python .agents/skills/gemini/ces-deploy/scripts/deploy.py --rollback <versionId>
    python .agents/skills/gemini/ces-deploy/scripts/deploy.py --rollback <versionId> --deployment <name-or-id>

A draft edit is NOT live. Cutting a version snapshots the WHOLE draft into an
immutable version, then each targeted deployment's `appVersion` pointer is moved
to it. Deployment ids are telephony-bound and are never deleted/recreated here —
only their pointer moves.

An app can have more than one deployment (e.g. a phone ingress and a web one). By
default this repoints EVERY deployment to the new version; use --deployment to
move just one (the "dedicated test deployment" pattern: iterate on one ingress
without touching the shared one).

Rules that prevent clobbering:
  - Cutting a version snapshots EVERYONE's in-flight draft edits. Announce before
    cutting on a shared app.
  - Claim a shared deployment before iterating; two people repointing the same
    deployment means a different version on every call.
  - Keep the rollback this prints — don't prune the last-known-good version.
  - Capture after deploying: run export.py and commit the diff.

⚠️ You MUST deploy to test real behavior. The DRAFT does not apply callback
return values. To iterate without clobbering a shared live deployment, deploy to
a DEDICATED test deployment with --deployment.
"""
from __future__ import annotations

import argparse
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

DEPLOY = "python .agents/skills/gemini/ces-deploy/scripts/deploy.py"


def select(deps: list[dict], want: str | None) -> list[dict]:
    if want is None:
        return deps
    matches = [d for d in deps
               if short(d["name"]) == want or (d.get("displayName") or "").lower() == want.lower()]
    if not matches:
        names = [f"{d.get('displayName')!r}={short(d['name'])}" for d in deps]
        sys.exit(f"--deployment {want!r} matched none of: {names}")
    if len(matches) > 1:
        sys.exit(f"--deployment {want!r} is ambiguous ({len(matches)} matches)")
    return matches


def main() -> int:
    ap = argparse.ArgumentParser(description="Cut a CES version and repoint deployment(s)")
    ap.add_argument("--label", help="display name for the new version")
    ap.add_argument("--desc", default="", help="version description")
    ap.add_argument("--rollback", metavar="VERSION_ID", help="repoint to an existing version (revert)")
    ap.add_argument("--deployment", metavar="NAME_OR_ID",
                    help="target a single deployment by displayName or id (default: ALL)")
    args = ap.parse_args()

    c = CES()
    all_deps = c.list("deployments")
    if not all_deps:
        sys.exit("no deployments exist for this app — create one in the console first")
    base = c.app_path
    targets = select(all_deps, args.deployment)
    scope = "ALL" if args.deployment is None else f"only {args.deployment!r}"

    print(f"app={base}")
    print(f"deployments={len(all_deps)} targeting {scope}:")
    for d in targets:
        print(f"  {d.get('displayName')!r} ({short(d['name'])}) serving {short(d.get('appVersion',''))}")

    if args.rollback:
        for d in targets:
            did, cur = short(d["name"]), short(d.get("appVersion", ""))
            c.patch("deployments", did, {"appVersion": f"{base}/versions/{args.rollback}"},
                    update_mask="appVersion")
            print(f"ROLLED BACK: {d.get('displayName')!r} ({did}) {cur} -> {args.rollback}")
        return 0

    if not args.label:
        sys.exit("--label required to cut + deploy (or use --rollback <versionId>)")

    print(f"\ncutting version {args.label!r} from the DRAFT ...")
    res = c.wait_op(
        c.create("versions", {"displayName": args.label, "description": args.desc or f"deploy {args.label}"}),
        "create version",
    )
    new = res["name"]
    nid = short(new)

    for d in targets:
        did, cur = short(d["name"]), short(d.get("appVersion", ""))
        c.patch("deployments", did, {"appVersion": new}, update_mask="appVersion")
        print(f"DEPLOYED: {d.get('displayName')!r} ({did}) {cur} -> {nid}")
        rb = f"{DEPLOY} --rollback {cur}"
        if args.deployment is None and len(all_deps) > 1:
            rb += f" --deployment {did}"
        print(f"  ROLLBACK: {rb}")
    print("CAPTURE:  python .agents/skills/gemini/ces-deploy/scripts/export.py && git add env-snapshot && git commit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
