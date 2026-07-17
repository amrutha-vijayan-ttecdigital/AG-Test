"""Execution engine for the text/routing eval harness.

Runs each test case through its turns against one CES session (sync, on the
shared client). Seeds session variables on the first turn, threads
`updatedVariables` forward so `params` assertions see accumulated state, and
stops a case at its first failing turn.
"""
from __future__ import annotations

import re
import time
import uuid
from datetime import date, datetime, timedelta

import assertions as A  # sibling module (script dir is on sys.path)
from loader import TestCase

_DATE_RE = re.compile(r"\{\{date:([a-z]+)([+-]\d+)w\}\}", re.IGNORECASE)
_WEEKDAY = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6}


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def resolve_dates(text: str, today: date | None = None) -> str:
    """Expand {{date:friday+1w}} -> 'July 11th' relative to today."""
    if not text:
        return text
    base = today or datetime.now().date()

    def repl(m: re.Match) -> str:
        wd = _WEEKDAY.get(m.group(1).lower())
        if wd is None:
            return m.group(0)
        target = base + timedelta(days=(wd - base.weekday()) % 7) + timedelta(weeks=int(m.group(2)))
        return f"{target.strftime('%B')} {_ordinal(target.day)}"

    return _DATE_RE.sub(repl, text)


def run_test_case(tc: TestCase, client, *, deployment_id=None, use_tool_fakes=False,
                  entry_agent=None) -> dict:
    session_id = f"eval-{uuid.uuid4().hex[:12]}"
    state: dict = dict(tc.session_params or {})
    seed = dict(tc.session_params or {})
    turns_out: list[dict] = []
    passed = True
    total_ms = 0.0
    error = ""

    def _run(text: str):
        return client.run_session(
            session_id, text=resolve_dates(text), variables=seed or None,
            deployment_id=deployment_id, use_tool_fakes=use_tool_fakes, entry_agent=entry_agent,
        )

    try:
        # Optional opening turn (e.g. "<event>session start</event>").
        if tc.start_utterance:
            t0 = time.monotonic()
            resp = _run(tc.start_utterance)
            seed = {}
            elapsed = (time.monotonic() - t0) * 1000
            total_ms += elapsed
            state = A.merge_params(state, A.extract_updated_variables(resp))
            turns_out.append(_record(-1, tc.start_utterance, resp, [], elapsed))

        for i, turn in enumerate(tc.turns):
            t0 = time.monotonic()
            resp = _run(turn.user)
            seed = {}
            elapsed = (time.monotonic() - t0) * 1000
            total_ms += elapsed
            state = A.merge_params(state, A.extract_updated_variables(resp))

            checks: list[A.AssertionResult] = []
            if turn.expect.expected_tool:
                checks.append(A.assert_tool_invoked(resp, turn.expect.expected_tool))
            if turn.expect.agent_route:
                checks.append(A.assert_agent_route(resp, turn.expect.agent_route))
            if turn.expect.keywords:
                checks.append(A.assert_keywords(resp, turn.expect.keywords))
            if turn.expect.params:
                checks.append(A.assert_params(state, turn.expect.params))
            checks.append(A.assert_latency(elapsed))

            rec = _record(i, turn.user, resp, checks, elapsed)
            turns_out.append(rec)
            if not rec["passed"]:
                passed = False
                break
    except (SystemExit, Exception) as e:  # SystemExit: client raises it on HTTP error
        passed = False
        error = str(e)

    return {
        "test_name": tc.display_name,
        "session_id": session_id,
        "passed": passed,
        "total_latency_ms": round(total_ms, 1),
        "error": error,
        "turns": turns_out,
    }


def _record(idx: int, user: str, resp: dict, checks, elapsed_ms: float) -> dict:
    return {
        "turn_index": idx,
        "user": user,
        "response_text": A.extract_text(resp),
        "agent_route": " -> ".join(A.extract_agents(resp)),
        "tools_called": A.extract_tools(resp),
        "latency_ms": round(elapsed_ms, 1),
        "passed": all(a.passed for a in checks) if checks else True,
        "assertions": [vars(a) for a in checks],
    }


def run_all(test_cases, client, *, on_result=None, **kw) -> list[dict]:
    results = []
    for tc in test_cases:
        r = run_test_case(tc, client, **kw)
        results.append(r)
        if on_result:
            on_result(r)
    return results
