"""Assertions over a CES runSession response.

The CES diagnostic trace carries the agent chain (message `role`s), the tools
invoked (`chunks[].toolCall.displayName`), and session-variable writes
(`chunks[].updatedVariables`). These helpers pull those out and check them
tolerantly — agent-route matching is case- and separator-insensitive so
"router -> billing" matches roles "Router" / "Billing".
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

EMPTY = ("", None, [], {}, ())


@dataclass
class AssertionResult:
    passed: bool
    type: str
    expected: str
    actual: str
    message: str


# ---- extraction -----------------------------------------------------------

def extract_text(response: dict) -> str:
    parts = [out["text"] for out in response.get("outputs", []) if out.get("text")]
    cleaned = re.sub(r"<state_update>.*?</state_update>", " ", " ".join(parts),
                     flags=re.IGNORECASE | re.DOTALL)
    return re.sub(r"\s+", " ", cleaned).strip()


def extract_agents(response: dict) -> list[str]:
    skip = {"user", "model", "system", "assistant", "function"}
    agents: list[str] = []
    for out in response.get("outputs", []):
        for msg in out.get("diagnosticInfo", {}).get("messages", []):
            role = msg.get("role", "")
            if role and role not in skip and role not in agents:
                agents.append(role)
    return agents


def extract_tools(response: dict) -> list[str]:
    tools: list[str] = []
    for out in response.get("outputs", []):
        for msg in out.get("diagnosticInfo", {}).get("messages", []):
            for chunk in msg.get("chunks", []):
                name = chunk.get("toolCall", {}).get("displayName", "")
                if name:
                    tools.append(name)
    return tools


def extract_updated_variables(response: dict) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for out in response.get("outputs", []):
        for msg in out.get("diagnosticInfo", {}).get("messages", []):
            for chunk in msg.get("chunks", []):
                upd = chunk.get("updatedVariables")
                if isinstance(upd, dict):
                    merged.update(upd)
    return merged


def merge_params(current: dict | None, updates: dict | None) -> dict:
    merged = dict(current or {})
    for k, v in (updates or {}).items():
        if isinstance(merged.get(k), dict) and isinstance(v, dict):
            merged[k] = merge_params(merged[k], v)
        elif v in EMPTY and merged.get(k) not in EMPTY:
            continue
        else:
            merged[k] = v
    return merged


# ---- assertions -----------------------------------------------------------

def _norm(s: str) -> str:
    return "".join(c for c in s.lower() if c.isalnum())


def assert_tool_invoked(response: dict, expected: str) -> AssertionResult:
    tools = extract_tools(response)
    found = any(expected in t for t in tools)
    return AssertionResult(found, "tool_invoked", expected, ", ".join(tools) or "(none)",
                           f"Tool {expected!r} {'found' if found else 'NOT found'}")


def assert_agent_route(response: dict, route: str) -> AssertionResult:
    agents = extract_agents(response)
    actual = " -> ".join(agents) or "(none)"
    expected_each = [a.strip() for a in route.split("->")]
    passed = all(any(_norm(exp) in _norm(a) for a in agents) for exp in expected_each)
    return AssertionResult(passed, "agent_route", route, actual,
                           "Route matches" if passed else "Route MISMATCH")


def assert_keywords(response: dict, keywords: list[str]) -> AssertionResult:
    text = extract_text(response).lower()
    missing = [k for k in keywords if k.lower() not in text]
    return AssertionResult(not missing, "keywords", ", ".join(keywords),
                           "all found" if not missing else f"missing: {', '.join(missing)}",
                           "Keywords present" if not missing else f"MISSING: {', '.join(missing)}")


def _match_value(actual: Any, expected: Any) -> bool:
    if expected == "~nonempty":
        return actual not in EMPTY
    if expected == "~iso-date":
        return isinstance(actual, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", actual) is not None
    if isinstance(expected, bool):
        return bool(actual) == expected
    if isinstance(expected, (int, float)):
        return actual == expected
    return str(actual or "").strip().lower() == str(expected or "").strip().lower()


def assert_params(state: dict, expected: dict) -> AssertionResult:
    mismatches = [f"{k}={state.get(k)!r} (expected {v!r})"
                  for k, v in expected.items() if not _match_value(state.get(k), v)]
    return AssertionResult(not mismatches, "session_params",
                           json.dumps(expected, sort_keys=True),
                           json.dumps(state, sort_keys=True, default=str),
                           "All params matched" if not mismatches else "; ".join(mismatches))


def assert_latency(elapsed_ms: float, max_ms: float = 10000.0) -> AssertionResult:
    passed = elapsed_ms <= max_ms
    return AssertionResult(passed, "latency", f"<= {max_ms:.0f}ms", f"{elapsed_ms:.0f}ms",
                           f"Latency {elapsed_ms:.0f}ms {'OK' if passed else f'EXCEEDS {max_ms:.0f}ms'}")
