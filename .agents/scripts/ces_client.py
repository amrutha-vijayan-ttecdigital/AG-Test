#!/usr/bin/env python3
"""Generic CES / Agent Studio REST client (v1 + v1beta).

Shared foundation for every `ces-*` skill in this kit. Reads connection
details from the kit-root `.env`, obtains a Google access token via the
active gcloud account (falling back to Application Default Credentials),
and talks to the CES API.

This is a *library*. The `ces-api` skill's `ces.py` is the CLI wrapper;
`ces-sync`, `ces-deploy`, `ces-eval`, and `ces-voice-test` all import this
class so there is exactly one copy of the request/auth/LRO logic.

Config (kit-root `.env`, env vars override the file):
    GCP_PROJECT_ID       required — GCP project id
    GCP_REGION           location  (default: us)
    CES_APP_ID           the app id under apps/{app} (CES_AGENT_ID also accepted —
                         it is the id in the Agent Studio console URL)
    CES_DEPLOYMENT_ID    optional — a deployment id (used by run_session / deploy)
    CES_API_HOST         optional — host override (default: ces.googleapis.com)
    CES_USER / GCP_ACCOUNT  optional — gcloud account to mint the token with

CES is global; the location lives in the URL path, not the host.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_HOST = "ces.googleapis.com"
DEFAULT_LOCATION = "us"


def find_kit_root(start: pathlib.Path | None = None) -> pathlib.Path:
    """Walk up from `start` to the directory that holds `.agents` / `.env`.

    Falls back to three levels above this file (…/.agents/scripts/ -> kit root)
    when no marker is found, so the client still works if `.env` is absent.
    """
    here = (start or pathlib.Path(__file__)).resolve()
    for parent in [here, *here.parents]:
        if (parent / ".agents").is_dir() or (parent / ".env").is_file() or (parent / "setup.sh").is_file():
            return parent
    return pathlib.Path(__file__).resolve().parents[2]


def _parse_env_file(path: pathlib.Path) -> dict:
    env: dict = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def load_env(export_to_environ: bool = False, *, require: bool = True) -> dict:
    """Load `.env` from the kit root, then layer real environment variables on top.

    Normalizes the kit's `CES_AGENT_ID` (console-URL id) and `CES_APP_ID` to a
    single `CES_APP_ID`. Set `require=False` to skip the missing-key check (the
    CLI uses that for `--help`-style paths).
    """
    root = find_kit_root()
    env = _parse_env_file(root / ".env")

    # Real environment variables win over the file.
    for k in list(env.keys()) + [
        "GCP_PROJECT_ID", "GCP_REGION", "CES_APP_ID", "CES_AGENT_ID",
        "CES_DEPLOYMENT_ID", "CES_API_HOST", "CES_USER", "GCP_ACCOUNT",
    ]:
        if os.environ.get(k):
            env[k] = os.environ[k]

    # CES_AGENT_ID (the id in the Agent Studio console URL) == the app id.
    if not env.get("CES_APP_ID") and env.get("CES_AGENT_ID"):
        env["CES_APP_ID"] = env["CES_AGENT_ID"]
    env.setdefault("GCP_REGION", DEFAULT_LOCATION)

    if require:
        missing = [k for k in ("GCP_PROJECT_ID", "CES_APP_ID") if not env.get(k)]
        if missing:
            sys.exit(
                f"Missing {', '.join(missing)} in {root / '.env'} or environment. "
                f"Run ./setup.sh and fill in .env."
            )

    if export_to_environ:
        for k, v in env.items():
            os.environ.setdefault(k, v)
    return env


class CES:
    """Thin REST wrapper around apps/{app} and its sub-collections."""

    def __init__(self, env: dict | None = None, *, beta: bool = False):
        self.env = env or load_env()
        self.project = self.env["GCP_PROJECT_ID"]
        self.location = self.env.get("GCP_REGION", DEFAULT_LOCATION)
        self.app = self.env["CES_APP_ID"]
        self.deployment_id = self.env.get("CES_DEPLOYMENT_ID", "")
        self.version = "v1beta" if beta else "v1"
        self._host = self.env.get("CES_API_HOST") or DEFAULT_HOST
        self._account = self.env.get("CES_USER") or self.env.get("GCP_ACCOUNT") or ""
        self._token: str | None = None

    # ---- auth -------------------------------------------------------------
    def _get_token(self) -> str:
        """Mint an access token via the active gcloud account, fall back to ADC."""
        if self._token:
            return self._token
        env = os.environ.copy()
        if self._account:
            env["CLOUDSDK_CORE_ACCOUNT"] = self._account
        try:
            self._token = subprocess.check_output(
                ["gcloud", "auth", "print-access-token"],
                text=True, env=env, stderr=subprocess.DEVNULL,
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Active-account token unavailable (often: refresh token expired).
            # ADC has its own refresh path, so long sessions don't break.
            try:
                self._token = subprocess.check_output(
                    ["gcloud", "auth", "application-default", "print-access-token"],
                    text=True, env=env, stderr=subprocess.DEVNULL,
                ).strip()
            except (subprocess.CalledProcessError, FileNotFoundError) as err:
                raise RuntimeError("Failed to retrieve Google Access Token via active gcloud account or ADC.") from err
        return self._token

    # ---- URL builders -----------------------------------------------------
    @property
    def app_path(self) -> str:
        return f"projects/{self.project}/locations/{self.location}/apps/{self.app}"

    def _app_url(self, path: str = "", version: str | None = None) -> str:
        base = f"https://{self._host}/{version or self.version}/{self.app_path}"
        return f"{base}/{path}" if path else base

    def _abs_url(self, name: str) -> str:
        """Build a URL from a fully-qualified resource name or operation name."""
        return f"https://{self._host}/{self.version}/{name}"

    # ---- HTTP -------------------------------------------------------------
    def _request(self, method: str, url: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            url, data=data, method=method,
            headers={
                "Authorization": f"Bearer {self._get_token()}",
                "Content-Type": "application/json",
                "x-goog-user-project": self.project,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raise SystemExit(f"HTTP {e.code} {method} {url}\n{e.read().decode()}")

    # ---- verbs ------------------------------------------------------------
    def app_get(self) -> dict:
        return self._request("GET", self._app_url())

    def app_patch(self, body: dict, update_mask: str) -> dict:
        url = self._app_url() + f"?updateMask={urllib.parse.quote(update_mask)}"
        return self._request("PATCH", url, body)

    def list(self, collection: str) -> list[dict]:
        items, token = [], None
        while True:
            url = self._app_url(collection)
            if token:
                url += f"?pageToken={urllib.parse.quote(token)}"
            resp = self._request("GET", url)
            key = next((k for k in resp if k != "nextPageToken"), None)
            if key and isinstance(resp.get(key), list):
                items.extend(resp[key])
            token = resp.get("nextPageToken")
            if not token:
                break
        return items

    def get(self, collection: str, resource_id: str) -> dict:
        return self._request("GET", self._app_url(f"{collection}/{resource_id}"))

    def create(self, collection: str, body: dict) -> dict:
        return self._request("POST", self._app_url(collection), body)

    def post_with_id(self, collection: str, resource_id: str, body: dict) -> dict:
        """POST with an explicit resource id (?{collection-singular}Id=...)."""
        param = {
            "agents": "agentId", "tools": "toolId", "toolsets": "toolsetId",
            "examples": "exampleId", "guardrails": "guardrailId",
            "deployments": "deploymentId", "versions": "versionId",
        }.get(collection, "resourceId")
        url = self._app_url(collection) + f"?{param}={urllib.parse.quote(resource_id)}"
        return self._request("POST", url, body)

    def patch(self, collection: str, resource_id: str, body: dict,
              update_mask: str | None = None) -> dict:
        if update_mask is None:
            update_mask = ",".join(body.keys())
        url = (self._app_url(f"{collection}/{resource_id}")
               + f"?updateMask={urllib.parse.quote(update_mask)}")
        return self._request("PATCH", url, body)

    def delete(self, collection: str, resource_id: str) -> dict:
        return self._request("DELETE", self._app_url(f"{collection}/{resource_id}"))

    # ---- long-running operations -----------------------------------------
    def wait_op(self, op: dict, label: str = "operation", *, tries: int = 120,
                interval: float = 2.0) -> dict:
        """Resolve a possibly-long-running operation to its final response."""
        name = op.get("name", "")
        if op.get("done") or "/operations/" not in name:
            return op.get("response", op)
        for _ in range(tries):
            time.sleep(interval)
            st = self._request("GET", self._abs_url(name))
            if st.get("done"):
                if st.get("error"):
                    raise SystemExit(f"{label}: {json.dumps(st['error'], indent=2)}")
                return st.get("response", st)
        raise SystemExit(f"{label}: timed out after {tries * interval:.0f}s")

    def retrieve_tools(self, toolset_name: str) -> list[dict]:
        """List the operations a toolset exposes (toolset:retrieveTools)."""
        return self._request("POST", self._abs_url(f"{toolset_name}:retrieveTools"), {}).get("tools", [])

    # ---- sessions ---------------------------------------------------------
    def run_session(self, session_id: str, text: str | None = None, *,
                    variables: dict | None = None, deployment_id: str | None = None,
                    use_tool_fakes: bool = False, entry_agent: str | None = None) -> dict:
        """Run one synchronous turn against the draft (default) or a deployment.

        Passing `deployment_id` (or relying on CES_DEPLOYMENT_ID via the helper)
        targets a cut version; omit it to hit the draft / current settings. Set
        `use_tool_fakes=True` to exercise routing without real backends (only
        fakes tools that have a fake configured).
        """
        config: dict = {"session": f"{self.app_path}/sessions/{session_id}"}
        if deployment_id:
            config["deployment"] = f"{self.app_path}/deployments/{deployment_id}"
        if use_tool_fakes:
            config["useToolFakes"] = True
        if entry_agent:
            config["entryAgent"] = f"{self.app_path}/agents/{entry_agent}"

        inputs: list[dict] = []
        if variables:
            inputs.append({"variables": variables})
        if text is not None:
            inputs.append({"text": text})
        if not inputs:
            raise ValueError("run_session requires text and/or variables")

        url = self._app_url(f"sessions/{session_id}:runSession")
        return self._request("POST", url, {"config": config, "inputs": inputs})


def short(name: str | None) -> str:
    """Last path segment of a resource name (the bare id)."""
    return (name or "").rsplit("/", 1)[-1]
