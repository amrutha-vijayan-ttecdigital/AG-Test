"""Voice test execution engine — load packs, run turns, collect results.

Seeds session variables straight from each case's `sessionParams`/`seedVariables`
(no environment-specific fixture logic). A case runs: optional start turn ->
optional agent-first opening -> scripted turns, stopping at the first failure.
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

import httpx

from assertions import run_assertions
from config import VoiceConfig
from result import VoiceTurnResult


@dataclass
class VoiceTurn:
    user: str
    expect: dict = field(default_factory=dict)


@dataclass
class VoiceTestCase:
    display_name: str
    turns: list[VoiceTurn] = field(default_factory=list)
    start_text: str = ""
    start_expect: dict = field(default_factory=dict)
    initial_expect: dict = field(default_factory=dict)
    seed_variables: dict = field(default_factory=dict)
    notes: str = ""


@dataclass
class TurnRecord:
    turn_index: int
    user_text: str
    transcript: str
    agent_response: str
    tools_called: list[str]
    agent_route: str
    total_latency_ms: float
    response_latency_ms: float
    mode: str
    assertions: list[dict]
    error: str = ""

    @property
    def passed(self) -> bool:
        return all(a["passed"] for a in self.assertions) if self.assertions else True


@dataclass
class TestCaseResult:
    test_name: str
    session_id: str
    passed: bool
    turns: list[TurnRecord] = field(default_factory=list)
    total_latency_ms: float = 0.0
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "test_name": self.test_name, "session_id": self.session_id, "passed": self.passed,
            "total_latency_ms": round(self.total_latency_ms, 1), "error": self.error,
            "turns": [{
                "turn_index": t.turn_index, "user_text": t.user_text, "transcript": t.transcript,
                "agent_response": t.agent_response, "tools_called": t.tools_called,
                "agent_route": t.agent_route, "total_latency_ms": t.total_latency_ms,
                "response_latency_ms": t.response_latency_ms, "mode": t.mode,
                "passed": t.passed, "assertions": t.assertions, "error": t.error,
            } for t in self.turns],
        }


def load_voice_tests(path: str | pathlib.Path) -> list[VoiceTestCase]:
    raw = json.loads(pathlib.Path(path).read_text())
    cases = []
    for tc in raw.get("testCases", []):
        turns = [VoiceTurn(user=t["user"], expect=t.get("expect", {})) for t in tc.get("turns", [])]
        cases.append(VoiceTestCase(
            display_name=tc.get("displayName", "unnamed"),
            turns=turns,
            start_text=tc.get("startText", ""),
            start_expect=tc.get("startExpect", {}),
            initial_expect=tc.get("initialExpect", {}),
            seed_variables=tc.get("seedVariables", tc.get("sessionParams", {})),
            notes=tc.get("notes", ""),
        ))
    return cases


def _token(cfg: VoiceConfig) -> str:
    import os
    env = os.environ.copy()
    if cfg.account:
        env["CLOUDSDK_CORE_ACCOUNT"] = cfg.account
    try:
        return subprocess.check_output(["gcloud", "auth", "print-access-token"],
                                       text=True, env=env, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return subprocess.check_output(
            ["gcloud", "auth", "application-default", "print-access-token"], text=True, env=env).strip()


async def _seed_start_turn(cfg: VoiceConfig, session_id: str, start_text: str,
                           seed: dict) -> VoiceTurnResult:
    """Run an explicit opening via REST runSession, seeding variables on input."""
    url = f"https://{cfg.host}/v1/{cfg.app_path}/sessions/{session_id}:runSession"
    config: dict[str, Any] = {"session": cfg.session_path(session_id)}
    if not cfg.use_draft:
        config["deployment"] = cfg.deployment_path
    if cfg.use_tool_fakes:
        config["useToolFakes"] = True
    inputs = ([{"variables": seed}] if seed else []) + [{"text": start_text}]
    start = asyncio.get_running_loop().time()
    async with httpx.AsyncClient(timeout=120.0) as http:
        resp = await http.post(url, headers={
            "Authorization": f"Bearer {_token(cfg)}", "Content-Type": "application/json",
            "x-goog-user-project": cfg.project_id}, json={"config": config, "inputs": inputs})
    elapsed = (asyncio.get_running_loop().time() - start) * 1000
    if resp.status_code >= 400:
        return VoiceTurnResult(session_id=session_id, turn_index=-1, mode="seed",
                               user_text=start_text, transcript=start_text,
                               total_latency_ms=round(elapsed, 1),
                               error=f"runSession {resp.status_code}: {resp.text[:300]}")
    body = resp.json()
    diag = next((o.get("diagnosticInfo", {}) for o in body.get("outputs", []) if o.get("diagnosticInfo")), {})
    from ws_client import _extract_agent_route, _extract_tool_calls
    text = "".join(o.get("text", "") for o in body.get("outputs", []))
    return VoiceTurnResult(session_id=session_id, turn_index=-1, mode="seed", user_text=start_text,
                           transcript=start_text, agent_response_text=text,
                           tools_called=_extract_tool_calls(diag), agent_route=_extract_agent_route(diag),
                           total_latency_ms=round(elapsed, 1), response_latency_ms=round(elapsed, 1),
                           raw_response=body)


def _record(idx: int, user: str, res: VoiceTurnResult, expect: dict, cfg: VoiceConfig) -> TurnRecord:
    checks = run_assertions(res, expect)
    if res.error:
        checks.append({"passed": False, "type": "transport_error", "expected": "no error",
                       "actual": res.error, "message": res.error})
    return TurnRecord(idx, user, res.transcript, res.agent_response_text, res.tools_called,
                      res.agent_route, res.total_latency_ms, res.response_latency_ms, res.mode, checks,
                      res.error)


async def run_voice_test(tc: VoiceTestCase, client, cfg: VoiceConfig) -> TestCaseResult:
    session_id = f"voice-{uuid.uuid4().hex[:8]}"
    records: list[TurnRecord] = []
    total = 0.0
    passed = True
    try:
        if tc.start_text:
            res = await _seed_start_turn(cfg, session_id, tc.start_text, tc.seed_variables)
            rec = _record(-1, tc.start_text, res, tc.start_expect or tc.initial_expect, cfg)
            records.append(rec)
            total += res.total_latency_ms
            if not rec.passed:
                return TestCaseResult(tc.display_name, session_id, False, records, total)
            if tc.turns:
                await asyncio.sleep(cfg.inter_turn_delay_s)
        elif cfg.mode == "voice" and hasattr(client, "receive_opening") and tc.initial_expect:
            opening = await client.receive_opening(session_id)
            if opening is not None:
                rec = _record(-1, "<session start>", opening, tc.initial_expect, cfg)
                records.append(rec)
                total += opening.total_latency_ms
                if not rec.passed:
                    return TestCaseResult(tc.display_name, session_id, False, records, total)
                if tc.turns:
                    await asyncio.sleep(cfg.inter_turn_delay_s)

        for i, turn in enumerate(tc.turns):
            res = await client.run_turn(text=turn.user, session_id=session_id, turn_index=i)
            rec = _record(i, turn.user, res, turn.expect, cfg)
            records.append(rec)
            total += res.total_latency_ms
            if not rec.passed or res.error:
                passed = False
                break
            if i < len(tc.turns) - 1 and "end_session" in res.tools_called:
                rec.assertions.append({"passed": False, "type": "unexpected_end_session",
                                       "expected": "session stays open", "actual": "end_session called",
                                       "message": "Session ended before later scripted turns"})
                passed = False
                break
    except Exception as e:
        return TestCaseResult(tc.display_name, session_id, False, records, total, error=str(e))
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            await close()
    return TestCaseResult(tc.display_name, session_id, passed, records, total)


async def run_all_voice_tests(test_cases, client, cfg: VoiceConfig,
                              on_result: Callable | None = None) -> list[TestCaseResult]:
    results = []
    for tc in test_cases:
        r = await run_voice_test(tc, client, cfg)
        results.append(r)
        if on_result:
            on_result(r)
    return results
