#!/usr/bin/env python3
"""Voice (BidiRunSession) test runner for a CES Agent Studio app.

Streams TTS audio (or text) over the WebSocket BidiRunSession endpoint and
asserts on the agent route, tools invoked, response keywords, STT transcript,
and latency.

    python .agents/skills/gemini/ces-voice-test/scripts/run_voice.py --test-file pack.json
    python .agents/skills/gemini/ces-voice-test/scripts/run_voice.py --test-file pack.json --mode text
    python .agents/skills/gemini/ces-voice-test/scripts/run_voice.py --test-file pack.json --draft --output results.json

Targets the deployment in CES_DEPLOYMENT_ID by default (callback return values
and the real telephony path only apply on a deployment). Pass --draft to hit the
draft for quick checks of raw-model behavior.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys
import time

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from config import VoiceConfig          # noqa: E402
from engine import load_voice_tests, run_all_voice_tests, TestCaseResult  # noqa: E402
from ws_client import WSBidiClient      # noqa: E402


def print_result(r: TestCaseResult) -> None:
    icon = "+" if r.passed else "x"
    print(f"\n  [{icon}] {r.test_name}: {'PASS' if r.passed else 'FAIL'} ({r.total_latency_ms:.0f}ms)")
    for t in r.turns:
        print(f"      Turn {t.turn_index} [{t.mode}] api={t.response_latency_ms:.0f}ms")
        print(f"        User : {t.user_text[:80]}")
        if t.transcript and t.transcript.strip().lower() != t.user_text.strip().lower():
            print(f"        STT  : {t.transcript[:80]!r}")
        if t.agent_response:
            print(f"        Agent: {t.agent_response[:120]}")
        if t.tools_called:
            print(f"        Tools: {', '.join(t.tools_called)}")
        if t.agent_route:
            print(f"        Route: {t.agent_route}")
        for a in t.assertions:
            print(f"        {'✓' if a['passed'] else '✗'} [{a['type']}] {a['message']}")


async def main() -> None:
    ap = argparse.ArgumentParser(description="CES voice (BidiRunSession) test runner")
    ap.add_argument("--test-file", required=True)
    ap.add_argument("--output", help="write JSON results here")
    ap.add_argument("--mode", choices=["voice", "text"], default=None,
                    help="voice: TTS->STT (default); text: send text over the socket (no TTS)")
    ap.add_argument("--draft", action="store_true", help="hit the draft instead of CES_DEPLOYMENT_ID")
    ap.add_argument("--tool-fakes", action="store_true", help="set useToolFakes for the session")
    args = ap.parse_args()

    cfg = VoiceConfig()
    if args.mode:
        cfg.mode = args.mode
    if args.draft:
        cfg.use_draft = True
    if args.tool_fakes:
        cfg.use_tool_fakes = True

    errors = cfg.validate()
    if errors:
        print("Configuration errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    test_cases = load_voice_tests(args.test_file)
    print("=" * 60)
    print("  CES Voice (BidiRunSession) Test Runner")
    print("=" * 60)
    print(f"  App:    {cfg.app_path}")
    print(f"  Target: {'DRAFT' if cfg.use_draft else 'deployment ' + cfg.deployment_id}")
    print(f"  Mode:   {cfg.mode}  ({'TTS -> CES STT' if cfg.mode == 'voice' else 'text over WebSocket'})")
    print(f"  Tests:  {len(test_cases)} from {args.test_file}")
    print("-" * 60)

    client = WSBidiClient(cfg)
    t0 = time.monotonic()
    results = await run_all_voice_tests(test_cases, client, cfg, on_result=print_result)
    elapsed = time.monotonic() - t0

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    print("\n" + "=" * 60)
    print(f"  Results: {passed} passed, {failed} failed, {len(results)} total ({elapsed:.1f}s)")
    print("=" * 60)

    if args.output:
        pathlib.Path(args.output).write_text(json.dumps(
            {"summary": {"total": len(results), "passed": passed, "failed": failed,
                         "mode": cfg.mode}, "results": [r.to_dict() for r in results]}, indent=2))
        print(f"Results -> {args.output}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
