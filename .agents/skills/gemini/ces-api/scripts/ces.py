#!/usr/bin/env python3
"""CES / Agent Studio REST CLI (v1 + v1beta).

Thin command-line wrapper over the shared client in .agents/scripts/ces_client.py.
Reads connection details from the kit-root .env.

    python .agents/skills/gemini/ces-api/scripts/ces.py app get
    python .agents/skills/gemini/ces-api/scripts/ces.py agents list
    python .agents/skills/gemini/ces-api/scripts/ces.py agents get <id>
    python .agents/skills/gemini/ces-api/scripts/ces.py agents patch <id> --body agent.json
    python .agents/skills/gemini/ces-api/scripts/ces.py --beta evaluations list

Smoke-test the live draft (or a deployment) with one turn:
    python .agents/skills/gemini/ces-api/scripts/ces.py sessions run --input "book a table for two"
    python .agents/skills/gemini/ces-api/scripts/ces.py sessions run --input "hi" --agent billing --deployment <id>

Collections under apps/{app}: agents, tools, toolsets, examples, guardrails,
deployments, versions, changelogs, conversations (v1beta adds evaluations*).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import uuid


def _load_shared_client():
    """Put .agents/scripts on the path and import the shared CES client."""
    here = pathlib.Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / ".agents" / "scripts"
        if cand.is_dir():
            sys.path.insert(0, str(cand))
            break
    from ces_client import CES, load_env, short  # type: ignore
    return CES, load_env, short


CES, load_env, short = _load_shared_client()


def _run_smoke(c, args) -> dict:
    """One synchronous turn — the minimum 'does it respond?' check."""
    session_id = args.session or f"smoke-{uuid.uuid4().hex[:12]}"
    deployment = args.deployment or (c.deployment_id if args.deployed else None)
    resp = c.run_session(
        session_id,
        text=args.input,
        deployment_id=deployment,
        use_tool_fakes=args.tool_fakes,
        entry_agent=args.agent,
    )
    # Surface the salient bits up top; full payload follows.
    texts, tools, route = [], [], []
    for out in resp.get("outputs", []):
        if out.get("text"):
            texts.append(out["text"])
        diag = out.get("diagnosticInfo", {})
        for msg in diag.get("messages", []):
            role = msg.get("role", "")
            if role and role not in {"user", "model", "system"} and role not in route:
                route.append(role)
            for chunk in msg.get("chunks", []):
                tc = chunk.get("toolCall", {})
                if tc.get("displayName"):
                    tools.append(tc["displayName"])
    print(f"# session : {session_id}", file=sys.stderr)
    print(f"# target  : {'deployment ' + deployment if deployment else 'draft/current settings'}", file=sys.stderr)
    print(f"# route   : {' -> '.join(route) or '(none)'}", file=sys.stderr)
    print(f"# tools   : {', '.join(tools) or '(none)'}", file=sys.stderr)
    print(f"# response: {' '.join(texts)[:400] or '(no text)'}", file=sys.stderr)
    return resp


def _cli() -> None:
    p = argparse.ArgumentParser(description="CES / Agent Studio REST client")
    p.add_argument("resource", help="'app', a collection (agents, tools, ...), or 'sessions'")
    p.add_argument("verb", help="get | list | create | patch | delete | run")
    p.add_argument("id", nargs="?", help="resource id (get/patch/delete)")
    p.add_argument("--body", help="JSON file with the request body (create/patch)")
    p.add_argument("--update-mask", help="comma-separated fields for patch")
    p.add_argument("--beta", action="store_true", help="use the v1beta API surface")
    # sessions run (smoke test)
    p.add_argument("--input", help="utterance for `sessions run`")
    p.add_argument("--agent", help="entry agent id for `sessions run` (default: root)")
    p.add_argument("--session", help="reuse a session id for `sessions run`")
    p.add_argument("--deployment", help="target a deployment id for `sessions run`")
    p.add_argument("--deployed", action="store_true",
                   help="target CES_DEPLOYMENT_ID from .env for `sessions run`")
    p.add_argument("--tool-fakes", action="store_true",
                   help="set useToolFakes for `sessions run`")
    args = p.parse_args()

    c = CES(beta=args.beta)
    body = json.loads(pathlib.Path(args.body).read_text()) if args.body else None

    if args.resource == "app":
        if args.verb != "get":
            sys.exit("app supports only 'get'")
        out = c.app_get()
    elif args.resource == "sessions" and args.verb == "run":
        if not args.input:
            sys.exit("--input required for `sessions run`")
        out = _run_smoke(c, args)
    elif args.verb == "list":
        out = c.list(args.resource)
    elif args.verb == "get":
        if not args.id:
            sys.exit("id required for get")
        out = c.get(args.resource, args.id)
    elif args.verb == "create":
        if not body:
            sys.exit("--body required for create")
        out = c.create(args.resource, body)
    elif args.verb == "patch":
        if not args.id or not body:
            sys.exit("id and --body required for patch")
        out = c.patch(args.resource, args.id, body, args.update_mask)
    elif args.verb == "delete":
        if not args.id:
            sys.exit("id required for delete")
        out = c.delete(args.resource, args.id)
    else:
        sys.exit(f"unknown verb {args.verb!r}")

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    _cli()
