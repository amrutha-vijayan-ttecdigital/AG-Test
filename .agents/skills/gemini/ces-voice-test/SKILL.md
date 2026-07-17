---
name: ces-voice-test
description: Voice test harness for a CES Agent Studio app over the WebSocket BidiRunSession endpoint. Streams TTS audio (or text) at real-time, then asserts on the STT transcript, agent route, tools invoked, response keywords, and latency. This is the only tier that exercises the real speech pipeline and applied callback behavior — run it against a deployment, not the draft.
---

# Voice (BidiRunSession) test harness

Drives the app the way a phone caller does: audio in over a streaming
WebSocket, real STT, real agent audio out. It catches what the text eval can't —
STT mishears, speech-only callback bugs (e.g. reading user input from `.text`
instead of `.transcript`), and behavior that only appears once a version is
deployed.

## Purpose

For each turn the runner either synthesizes the utterance to 16kHz LINEAR16 and
streams it at ~1× real-time (`--mode voice`), or sends the text directly over the
socket (`--mode text`, no TTS needed). It then asserts on:

| `expect` key | checks |
|---|---|
| `Agent route path` | agent chain (substring, case-insensitive) |
| `expected_tool_invocation` | a tool was invoked |
| `keywords` | the agent's response text contains these |
| `transcript_contains` | STT heard roughly what was said (voice-mode sanity) |

Latency is always checked. The socket is reconnected per turn while the CES
`session_id` preserves conversation state — this matches observed backend
behavior better than one socket for the whole call.

## ⚠️ Test a deployment, not the draft

The **draft does not apply callback return values** and may not route through the
real telephony path, so a draft run shows raw-model behavior — not what a caller
gets. `run_voice.py` targets the deployment in `CES_DEPLOYMENT_ID` by default.
Use `--draft` only for quick raw-model checks. Typical loop:

```
edit -> ces-sync (draft) -> ces-deploy (cut version, repoint a test deployment) -> ces-voice-test
```

## Setup

```bash
pip install -r .agents/skills/gemini/ces-voice-test/scripts/requirements.txt
# For --mode voice you also need a TTS engine:
#   - google (default fallback): uses the Google Cloud Text-to-Speech API.
#     Requires no local TTS engine or ffmpeg! (Ensure the API is enabled on your GCP project).
#   - gtts (requires ffmpeg): pip install gtts
#   - say (requires ffmpeg, macOS only)
# --mode text needs neither TTS nor ffmpeg.
```

## Usage

```bash
RUN=.agents/skills/gemini/ces-voice-test/scripts/run_voice.py

# Voice smoke against the deployment (real STT pipeline)
python $RUN --test-file .agents/skills/gemini/ces-voice-test/examples/voice_smoke.json

# Text over the socket — fast, no TTS/ffmpeg (good for CI routing checks)
python $RUN --test-file pack.json --mode text

# Quick raw-model check against the draft, save results
python $RUN --test-file pack.json --draft --output results.json
```

## Test file format

See `examples/voice_smoke.json`. A case has `turns` (each `{ "user", "expect" }`),
an optional `startText` for an explicit opening (e.g. `<event>session start</event>`)
with `startExpect`, an optional `initialExpect` for an agent-first opening, and
`seedVariables` to seed session state (e.g. a caller id) on the first turn.

## Options

* `--test-file PATH` — the JSON pack (required).
* `--mode voice|text` — TTS→STT (default) or send text over the socket.
* `--draft` — hit the draft instead of `CES_DEPLOYMENT_ID`.
* `--tool-fakes` — set `useToolFakes` for the session.
* `--output PATH` — write full JSON results.

## Environment knobs

`CES_VOICE_MODE`, `CES_VOICE_DRAFT`, `CES_VOICE_TOOL_FAKES`, `CES_VOICE_TTS`
(`auto|gtts|say`), and `CES_VOICE_AUDIO_CACHE` (defaults to the OS temp dir).

## Scope

This skill implements the **WebSocket** BidiRunSession path — documented,
dependency-light, and the supported default. A gRPC/regional-endpoint path
exists but needs the `google-cloud-ces` SDK and telephony-gated REP endpoint
access, so it is intentionally not bundled here.
