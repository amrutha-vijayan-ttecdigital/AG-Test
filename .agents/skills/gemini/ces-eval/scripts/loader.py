"""Test-case loader for the CES text/routing eval harness.

Test file format (JSON):

    {
      "description": "what this pack covers",
      "startUtterance": "<event>session start</event>",   // optional, applied to every case
      "testCases": [
        {
          "displayName": "route_billing",
          "notes": "billing intent should reach the billing agent",
          "channel": "text",
          "sessionParams": { "callerId": "+15551234567" },  // seed variables
          "startUtterance": "...",                           // optional per-case override
          "turns": [
            { "user": "I have a question about a charge",
              "expect": {
                "Agent route path": "router -> billing",
                "expected_tool_invocation": "get_account_summary",
                "contains": ["charge", "account"],
                "params": { "callType": "billing_dispute" }
              }
            }
          ]
        }
      ]
    }

`expect` keys (all optional): "Agent route path", "expected_tool_invocation",
"contains" (or "keywords"), "params". Date templates like {{date:friday+1w}} in
`user`/`startUtterance` resolve to a real upcoming date at run time.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Expect:
    agent_route: str = ""
    expected_tool: str = ""
    keywords: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Turn:
    user: str
    expect: Expect


@dataclass
class TestCase:
    display_name: str
    notes: str = ""
    turns: list[Turn] = field(default_factory=list)
    channel: str = "text"
    session_params: dict[str, Any] = field(default_factory=dict)
    start_utterance: str = ""
    scenario_id: str = ""


def _parse_expect(raw: dict) -> Expect:
    contains = raw.get("contains", raw.get("keywords", []))
    keywords = [contains] if isinstance(contains, str) else list(contains or [])
    return Expect(
        agent_route=raw.get("Agent route path", "") or raw.get("agent_route", ""),
        expected_tool=raw.get("expected_tool_invocation", "") or raw.get("expected_tool", ""),
        keywords=keywords,
        params=raw.get("params", {}),
    )


def load_test_cases(path: str | Path) -> list[TestCase]:
    raw = json.loads(Path(path).read_text())
    if not isinstance(raw, dict) or "testCases" not in raw:
        raise ValueError(f"{path}: expected an object with a 'testCases' array")
    global_start = raw.get("startUtterance", "")
    cases = []
    for tc in raw["testCases"]:
        turns = [Turn(user=t.get("user", ""), expect=_parse_expect(t.get("expect", {})))
                 for t in tc.get("turns", [])]
        cases.append(TestCase(
            display_name=tc.get("displayName", "unnamed"),
            notes=tc.get("notes", ""),
            turns=turns,
            channel=tc.get("channel", "text"),
            session_params=tc.get("sessionParams", {}),
            start_utterance=tc.get("startUtterance", global_start),
            scenario_id=tc.get("scenarioId", ""),
        ))
    return cases
