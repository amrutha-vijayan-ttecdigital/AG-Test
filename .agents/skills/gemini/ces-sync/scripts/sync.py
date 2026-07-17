#!/usr/bin/env python3
"""Sync a CES draft app from repo-owned source files.

Pushes your local, version-controlled agent definitions into the CES DRAFT so
the app is reproducible from git instead of from console clicks. It:

  1. creates/patches every OpenAPI toolset from its checked-in schema (+ auth)
  2. creates/patches standalone tools (dataStore / pythonFunction / agentTool)
  3. creates/patches each agent's instruction + displayName + description
  4. wires each agent's toolset operations and standalone tools
  5. wires each agent's childAgents (the router hierarchy)
  6. wires each agent's callbacks (pythonCode from callbacks/*.py)
  7. patches app-level config (model, globalInstruction, variables, rootAgent)

Source layout (under --src, default: current directory):

    app.json                      # optional app-level config (see below)
    agents/<slug>/instruction.md  # the agent's instruction text
    agents/<slug>/agent.json      # displayName, description, childAgents, toolsets, tools, callbacks
    toolsets/<slug>.yaml          # OpenAPI schema for toolset <slug>
    toolsets/host-rewrites.json   # optional {"old-host": "new-host"} applied to YAMLs at sync time
    tools/<name>.json             # standalone CES tool body (dataStoreTool / pythonFunction / agentTool)
    callbacks/<file>.py           # callback code referenced by agent.json

agent.json reference tokens (resolved to live resource names at wire time):
    "childAgents": ["other-slug", "@display:Some External Agent"]
    "toolsets":    ["billing-api"]                 # -> toolsets/billing-api.yaml
    "tools":       ["faq-store", "@builtin:end_session", "@agent:billing"]
    "callbacks":   {"beforeModelCallbacks": [{"description": "...", "file": "x.py"}]}

Run:
    python .agents/skills/gemini/ces-sync/scripts/sync.py --src ./my-app
    SYNC_ONLY=billing python .agents/skills/gemini/ces-sync/scripts/sync.py --src ./my-app
    python .agents/skills/gemini/ces-sync/scripts/sync.py --src ./my-app --only billing,router

DEFAULT TO scoped (`--only`/`SYNC_ONLY`) for incremental edits so you never
clobber a teammate's in-flight console draft. A bare full sync touches every
managed resource — only run it for bootstrap or a deliberate wholesale rewire,
and pull live -> local first for any agent someone else may be editing.
"""
from __future__ import annotations

import argparse
import json
import os
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


# --------------------------------------------------------------------------
# Source loading
# --------------------------------------------------------------------------

class Source:
    """Reads the on-disk source tree into memory."""

    def __init__(self, root: pathlib.Path):
        self.root = root
        self.agents_dir = root / "agents"
        self.toolsets_dir = root / "toolsets"
        self.tools_dir = root / "tools"
        self.callbacks_dir = root / "callbacks"

    def agent_slugs(self) -> list[str]:
        if not self.agents_dir.is_dir():
            return []
        return sorted(p.name for p in self.agents_dir.iterdir()
                      if p.is_dir() and (p / "agent.json").exists())

    def agent_def(self, slug: str) -> dict:
        d = json.loads((self.agents_dir / slug / "agent.json").read_text())
        instr_file = d.get("instruction", "instruction.md")
        instr_path = self.agents_dir / slug / instr_file
        d["_instruction_text"] = d.get("instructionText") or (
            instr_path.read_text() if instr_path.exists() else "")
        return d

    def toolset_slugs(self) -> list[str]:
        if not self.toolsets_dir.is_dir():
            return []
        return sorted(p.stem for p in self.toolsets_dir.glob("*.yaml")) + \
               sorted(p.stem for p in self.toolsets_dir.glob("*.yml"))

    def toolset_schema(self, slug: str) -> str:
        for ext in (".yaml", ".yml"):
            p = self.toolsets_dir / f"{slug}{ext}"
            if p.exists():
                return self._rewrite_hosts(p.read_text())
        raise SystemExit(f"toolset schema not found for {slug!r}")

    def _rewrite_hosts(self, schema: str) -> str:
        rewrites_path = self.toolsets_dir / "host-rewrites.json"
        if rewrites_path.exists():
            for src, dst in json.loads(rewrites_path.read_text()).items():
                if src and dst and src != dst:
                    schema = schema.replace(src, dst)
        return schema

    def tool_defs(self) -> dict[str, dict]:
        if not self.tools_dir.is_dir():
            return {}
        return {p.stem: json.loads(p.read_text()) for p in sorted(self.tools_dir.glob("*.json"))}

    def callback_code(self, filename: str) -> str:
        return (self.callbacks_dir / filename).read_text()

    def app_config(self) -> dict:
        p = self.root / "app.json"
        return json.loads(p.read_text()) if p.exists() else {}


# --------------------------------------------------------------------------
# Toolset API auth — service-agent OIDC by default; OAuth2 if configured
# --------------------------------------------------------------------------

def toolset_api_auth() -> dict:
    client_id = os.environ.get("CES_TOOLSET_OAUTH_CLIENT_ID", "").strip()
    if client_id:
        cfg = {
            "clientId": client_id,
            "clientSecretVersion": os.environ["CES_TOOLSET_OAUTH_SECRET_VERSION"],
            "tokenEndpoint": os.environ["CES_TOOLSET_OAUTH_TOKEN_URL"],
            "oauthGrantType": "CLIENT_CREDENTIAL",
        }
        scope = os.environ.get("CES_TOOLSET_OAUTH_SCOPE", "").strip()
        if scope:
            cfg["scopes"] = scope.split()
        return {"oauthConfig": cfg}
    # Cloud Run / private backend reached with the CES service agent's OIDC token.
    return {"serviceAgentIdTokenAuthConfig": {}}


# --------------------------------------------------------------------------
# Sync steps
# --------------------------------------------------------------------------

def in_scope(slug: str, scope: set[str] | None) -> bool:
    return scope is None or slug in scope


def ensure_toolsets(c: CES, src: Source) -> dict[str, str]:
    existing = {short(t["name"]): t for t in c.list("toolsets")}
    mapping: dict[str, str] = {}
    for slug in src.toolset_slugs():
        body = {
            "displayName": slug,
            "description": f"{slug} OpenAPI toolset",
            "openApiToolset": {
                "openApiSchema": src.toolset_schema(slug),
                "apiAuthentication": toolset_api_auth(),
            },
        }
        if slug in existing:
            mapping[slug] = existing[slug]["name"]
            try:
                c.patch("toolsets", slug, body, update_mask="displayName,description,openApiToolset")
                print(f"  toolset {slug}: patched")
            except SystemExit as e:
                print(f"  toolset {slug}: PATCH FAILED ({str(e)[:200]})")
            continue
        try:
            res = c.wait_op(c.post_with_id("toolsets", slug, body), f"create toolset {slug}")
            mapping[slug] = res.get("name", c._app_url(f"toolsets/{slug}"))
            print(f"  toolset {slug}: CREATED")
        except SystemExit as e:
            print(f"  toolset {slug}: CREATE FAILED ({str(e)[:300]})")
    return mapping


def resolve_toolsets_readonly(c: CES, src: Source) -> dict[str, str]:
    existing = {short(t["name"]): t for t in c.list("toolsets")}
    return {slug: existing[slug]["name"] for slug in src.toolset_slugs() if slug in existing}


def ensure_agents(c: CES, src: Source, scope: set[str] | None) -> dict[str, str]:
    existing = {short(a["name"]): a for a in c.list("agents")}
    mapping: dict[str, str] = {}
    for slug in src.agent_slugs():
        if slug in existing:
            mapping[slug] = existing[slug]["name"]
        if not in_scope(slug, scope):
            continue
        d = src.agent_def(slug)
        body = {
            "displayName": d.get("displayName", slug),
            "description": d.get("description", ""),
            "instruction": d["_instruction_text"],
        }
        if slug in existing:
            try:
                c.patch("agents", slug, body, update_mask="displayName,description,instruction")
                print(f"  agent {slug}: patched")
            except SystemExit as e:
                print(f"  agent {slug}: PATCH FAILED ({str(e)[:200]})")
            continue
        try:
            res = c.wait_op(c.post_with_id("agents", slug, body), f"create agent {slug}")
            mapping[slug] = res.get("name", c._app_url(f"agents/{slug}"))
            print(f"  agent {slug}: CREATED")
        except SystemExit as e:
            print(f"  agent {slug}: CREATE FAILED ({str(e)[:300]})")
    return mapping


def ensure_tools(c: CES, src: Source) -> dict[str, str]:
    """Create/patch standalone tools from tools/<name>.json. Returns name->resource."""
    existing = {short(t["name"]): t for t in c.list("tools")}
    mapping: dict[str, str] = {}
    for name, body in src.tool_defs().items():
        # Pick a sensible update mask from the tool kind present in the body.
        kind = next((k for k in ("dataStoreTool", "pythonFunction", "agentTool",
                                  "openApiTool", "clientFunction", "connectorTool")
                     if k in body), None)
        mask = ",".join([k for k in ("displayName", "description") if k in body] + ([kind] if kind else []))
        if name in existing:
            mapping[name] = existing[name]["name"]
            try:
                c.patch("tools", name, body, update_mask=mask or None)
                print(f"  tool {name}: patched")
            except SystemExit as e:
                print(f"  tool {name}: PATCH FAILED ({str(e)[:200]})")
            continue
        try:
            res = c.wait_op(c.post_with_id("tools", name, body), f"create tool {name}")
            mapping[name] = res.get("name", c._app_url(f"tools/{name}"))
            print(f"  tool {name}: CREATED")
        except SystemExit as e:
            print(f"  tool {name}: CREATE FAILED ({str(e)[:300]})")
    return mapping


def _resolve_tool_ref(ref: str, c: CES, agent_map: dict[str, str],
                      tool_map: dict[str, str], existing_tools: dict[str, dict]) -> str | None:
    """Resolve an agent.json tools[] entry to a CES resource name."""
    if ref.startswith("@builtin:"):
        return f"{c.app_path}/tools/{ref.split(':', 1)[1]}"
    if ref.startswith("@agent:"):
        slug = ref.split(":", 1)[1]
        return agent_map.get(slug)
    if ref in tool_map:
        return tool_map[ref]
    if ref in existing_tools:
        return existing_tools[ref]["name"]
    return None


def wire_agents(c: CES, src: Source, toolset_map: dict[str, str], agent_map: dict[str, str],
                tool_map: dict[str, str], scope: set[str] | None) -> None:
    # Cache each toolset's operation ids once.
    toolset_refs: dict[str, dict] = {}
    for slug, name in toolset_map.items():
        try:
            ops = [short(t["name"]) for t in c.retrieve_tools(name)
                   if short(t["name"]).lower() not in {"health", "healthz", "healthcheck"}]
        except SystemExit as e:
            print(f"  toolset {slug}: retrieveTools FAILED ({str(e)[:150]})")
            continue
        if ops:
            toolset_refs[slug] = {"toolset": name, "toolIds": ops}

    existing_tools = {short(t["name"]): t for t in c.list("tools")}
    for slug in src.agent_slugs():
        if slug not in agent_map or not in_scope(slug, scope):
            continue
        d = src.agent_def(slug)
        toolsets = [toolset_refs[ts] for ts in d.get("toolsets", []) if ts in toolset_refs]
        tools = []
        for ref in d.get("tools", []):
            resolved = _resolve_tool_ref(ref, c, agent_map, tool_map, existing_tools)
            if resolved:
                tools.append(resolved)
            else:
                print(f"  agent {slug}: unresolved tool ref {ref!r}")
        try:
            c.patch("agents", slug, {"toolsets": toolsets, "tools": tools},
                    update_mask="toolsets,tools")
            print(f"  agent {slug}: wired toolsets={len(toolsets)} tools={len(tools)}")
        except SystemExit as e:
            print(f"  agent {slug}: wiring FAILED ({str(e)[:250]})")


def wire_children(c: CES, src: Source, agent_map: dict[str, str], scope: set[str] | None) -> None:
    by_display = {a.get("displayName"): a["name"] for a in c.list("agents") if a.get("displayName")}
    for slug in src.agent_slugs():
        if slug not in agent_map or not in_scope(slug, scope):
            continue
        d = src.agent_def(slug)
        children = []
        for ref in d.get("childAgents", []):
            if ref.startswith("@display:"):
                name = by_display.get(ref.split(":", 1)[1])
            else:
                name = agent_map.get(ref)
            if name and name != agent_map[slug] and name not in children:
                children.append(name)
        try:
            c.patch("agents", slug, {"childAgents": children}, update_mask="childAgents")
            print(f"  {slug}.childAgents: set {len(children)}")
        except SystemExit as e:
            print(f"  {slug}.childAgents: FAILED ({str(e)[:200]})")


def wire_callbacks(c: CES, src: Source, scope: set[str] | None) -> None:
    for slug in src.agent_slugs():
        if not in_scope(slug, scope):
            continue
        cbs = src.agent_def(slug).get("callbacks", {})
        if not cbs:
            continue
        body, masks = {}, []
        for hook, specs in cbs.items():
            body[hook] = [{"description": s.get("description", ""),
                           "pythonCode": src.callback_code(s["file"])} for s in specs]
            masks.append(hook)
        try:
            c.patch("agents", slug, body, update_mask=",".join(masks))
            print(f"  agent {slug}: callbacks wired ({', '.join(masks)})")
        except SystemExit as e:
            print(f"  agent {slug}: callbacks FAILED ({str(e)[:250]})")


def patch_app(c: CES, src: Source, agent_map: dict[str, str]) -> None:
    cfg = src.app_config()
    if not cfg:
        print("  app: no app.json — skipped")
        return
    body, masks = {}, []
    for key in ("globalInstruction", "variableDeclarations", "modelSettings",
                "languageSettings", "loggingSettings", "errorHandlingSettings"):
        if key in cfg:
            body[key] = cfg[key]
            masks.append(key)
    root = cfg.get("rootAgent")
    if root:
        body["rootAgent"] = agent_map.get(root, root if "/" in root else f"{c.app_path}/agents/{root}")
        masks.append("rootAgent")
    if not masks:
        print("  app: app.json had no recognized keys — skipped")
        return
    try:
        c.app_patch(body, ",".join(masks))
        print(f"  app: patched ({', '.join(masks)})")
    except SystemExit as e:
        print(f"  app: PATCH FAILED ({str(e)[:250]})")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Sync local agent source -> CES draft")
    ap.add_argument("--src", default=".", help="source root holding agents/, toolsets/, tools/, callbacks/, app.json")
    ap.add_argument("--only", default="", help="comma-separated agent slugs to patch (scoped sync)")
    args = ap.parse_args()

    src = Source(pathlib.Path(args.src).resolve())
    if not src.agents_dir.is_dir():
        sys.exit(f"no agents/ directory under {src.root}")

    scope_raw = args.only.strip() or os.environ.get("SYNC_ONLY", "").strip()
    scope = {s.strip() for s in scope_raw.split(",") if s.strip()} or None
    if scope:
        unknown = scope - set(src.agent_slugs())
        if unknown:
            sys.exit(f"--only/SYNC_ONLY has unknown slug(s): {sorted(unknown)}; "
                     f"valid: {src.agent_slugs()}")

    c = CES()
    print(f"Target: {c.app_path}")
    if scope:
        print(f"Scope:  {sorted(scope)} — only these agents patched; "
              f"toolsets/tools/app config SKIPPED.\n")
    else:
        print("Scope:  FULL sync — every managed resource is touched.\n")

    if scope is None:
        print("== toolsets =="); toolset_map = ensure_toolsets(c, src); print()
        print("== standalone tools =="); tool_map = ensure_tools(c, src); print()
    else:
        toolset_map = resolve_toolsets_readonly(c, src)
        tool_map = {short(t["name"]): t["name"] for t in c.list("tools")}

    print("== agents =="); agent_map = ensure_agents(c, src, scope); print()
    print("== wire agent tools =="); wire_agents(c, src, toolset_map, agent_map, tool_map, scope); print()
    print("== wire children =="); wire_children(c, src, agent_map, scope); print()
    print("== wire callbacks =="); wire_callbacks(c, src, scope); print()

    if scope is None:
        print("== patch app =="); patch_app(c, src, agent_map); print()
    else:
        print("== patch app == SKIPPED (scoped sync)\n")

    print("Done. Verify with: ces-api inventory.py, then deploy with ces-deploy to go live.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
