"""Assertions over a VoiceTurnResult. Each returns a dict for the result JSON."""
from __future__ import annotations

from result import VoiceTurnResult


def _r(passed: bool, atype: str, expected: str, actual: str, msg: str) -> dict:
    return {"passed": passed, "type": atype, "expected": expected, "actual": actual, "message": msg}


def assert_tool_invoked(turn: VoiceTurnResult, expected: str) -> dict:
    found = any(expected in t for t in turn.tools_called)
    return _r(found, "tool_invoked", expected, ", ".join(turn.tools_called) or "(none)",
              f"Tool {expected!r} {'found' if found else 'NOT found'}")


def assert_agent_route(turn: VoiceTurnResult, expected: str) -> dict:
    actual = turn.agent_route
    passed = bool(actual) and expected.lower() in actual.lower()
    return _r(passed, "agent_route", expected, actual or "(none)",
              f"Route {'matches' if passed else 'MISMATCH'}")


def assert_keywords(turn: VoiceTurnResult, keywords: list[str]) -> dict:
    text = turn.agent_response_text.lower()
    missing = [k for k in keywords if k.lower() not in text]
    return _r(not missing, "keywords", ", ".join(keywords),
              "all found" if not missing else f"missing: {', '.join(missing)}",
              "Keywords present" if not missing else f"MISSING: {', '.join(missing)}")


def assert_transcript_contains(turn: VoiceTurnResult, expected: str) -> dict:
    """Did STT hear roughly what we said? (voice mode sanity check)"""
    passed = expected.lower() in turn.transcript.lower()
    return _r(passed, "transcript", expected, turn.transcript or "(none)",
              f"Transcript {'contains' if passed else 'MISSING'} {expected!r}")


def assert_latency(turn: VoiceTurnResult, max_ms: float = 20000.0) -> dict:
    passed = turn.total_latency_ms <= max_ms
    return _r(passed, "latency", f"<= {max_ms:.0f}ms", f"{turn.total_latency_ms:.0f}ms",
              f"Latency {turn.total_latency_ms:.0f}ms {'OK' if passed else 'EXCEEDED'}")


def run_assertions(turn: VoiceTurnResult, expect: dict, max_latency_ms: float = 20000.0) -> list[dict]:
    results = []
    if expect.get("expected_tool_invocation"):
        results.append(assert_tool_invoked(turn, expect["expected_tool_invocation"]))
    if expect.get("Agent route path"):
        results.append(assert_agent_route(turn, expect["Agent route path"]))
    if expect.get("keywords"):
        results.append(assert_keywords(turn, expect["keywords"]))
    if expect.get("transcript_contains"):
        results.append(assert_transcript_contains(turn, expect["transcript_contains"]))
    results.append(assert_latency(turn, max_latency_ms))
    return results
