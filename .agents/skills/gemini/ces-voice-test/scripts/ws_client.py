"""WebSocket BidiRunSession client for CES.

Uses the documented WebSocket endpoint (no gRPC C-core, no SDK build step).
Two input modes per turn:
  - text:  send the utterance text directly (fast; exercises routing + agent audio out)
  - voice: TTS the utterance to 16kHz LINEAR16 and stream it at ~1x real-time
           (exercises the real STT pipeline end-to-end)

The socket behaves like a single-turn channel, so a fresh connection is opened
per turn while the CES `session_id` preserves conversation state across turns —
this matches observed backend behavior better than one socket for the whole call.
"""
from __future__ import annotations

import asyncio
import base64
import json
import pathlib
import sys
import time

import websockets

from config import VoiceConfig
from result import VoiceTurnResult


def _shared_token() -> str:
    here = pathlib.Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / ".agents" / "scripts"
        if cand.is_dir():
            sys.path.insert(0, str(cand))
            break
    from ces_client import CES  # type: ignore
    return CES()._get_token()


class WSBidiClient:
    def __init__(self, cfg: VoiceConfig) -> None:
        self.cfg = cfg
        self._ws = None
        self._turn_index = 0

    # ---- connection -------------------------------------------------------
    async def connect(self, session_id: str, entry_agent: str | None = None) -> None:
        token = _shared_token()
        self._ws = await websockets.connect(
            self.cfg.ws_url(),
            additional_headers={
                "Authorization": f"Bearer {token}",
                "x-goog-user-project": self.cfg.project_id,
            },
            max_size=10 * 1024 * 1024,
            ping_interval=20, ping_timeout=10,
        )
        config = {
            "session": self.cfg.session_path(session_id),
            "inputAudioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 16000},
            "outputAudioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 16000},
        }
        if not self.cfg.use_draft:
            config["deployment"] = self.cfg.deployment_path
        if self.cfg.use_tool_fakes:
            config["useToolFakes"] = True
        if entry_agent:
            config["entryAgent"] = f"{self.cfg.app_path}/agents/{entry_agent}"
        await self._ws.send(json.dumps({"config": config}))
        # Let the backend settle the socket-level session before audio frames.
        await asyncio.sleep(0.75)

    async def close(self) -> None:
        if self._ws:
            await self._ws.close()
            self._ws = None

    # ---- receive ----------------------------------------------------------
    async def _collect(self, *, session_id, turn_idx, mode, user_text, turn_start,
                       stream_end, audio_duration_s, timeout_s=None) -> VoiceTurnResult:
        text_chunks: list[str] = []
        audio_chunks: list[bytes] = []
        transcript = ""
        tools: list[str] = []
        route = ""
        raw: dict = {}
        try:
            while True:
                msg = json.loads(await asyncio.wait_for(
                    self._ws.recv(), timeout=timeout_s or self.cfg.max_turn_timeout_s))
                if "recognitionResult" in msg:
                    transcript = msg["recognitionResult"].get("transcript", "") or transcript
                out = msg.get("sessionOutput")
                if out:
                    if out.get("text"):
                        text_chunks.append(out["text"])
                    if out.get("audio"):
                        audio_chunks.append(base64.b64decode(out["audio"]))
                    if out.get("diagnosticInfo"):
                        raw = {"outputs": [out]}
                        tools = _extract_tool_calls(out["diagnosticInfo"])
                        route = _extract_agent_route(out["diagnosticInfo"])
                    if out.get("turnCompleted"):
                        raw = raw or {"outputs": [out]}
                        break
                if "endSession" in msg:
                    break
        except asyncio.TimeoutError:
            return self._mk(session_id, turn_idx, mode, user_text, transcript or user_text,
                            text_chunks, tools, route, audio_duration_s, turn_start,
                            error=f"Timed out after {(timeout_s or self.cfg.max_turn_timeout_s):.1f}s",
                            raw=raw)
        except Exception as exc:
            return self._mk(session_id, turn_idx, mode, user_text, transcript or user_text,
                            text_chunks, tools, route, audio_duration_s, turn_start,
                            error=str(exc), raw=raw)

        turn_end = time.monotonic()
        return VoiceTurnResult(
            session_id=session_id, turn_index=turn_idx, mode=mode, user_text=user_text,
            transcript=transcript or user_text, agent_response_text="".join(text_chunks),
            tools_called=tools, agent_route=route, audio_duration_s=round(audio_duration_s, 3),
            streaming_duration_s=round(stream_end - turn_start, 3),
            response_latency_ms=round((turn_end - stream_end) * 1000, 1),
            total_latency_ms=round((turn_end - turn_start) * 1000, 1),
            agent_audio=b"".join(audio_chunks), agent_audio_sample_rate=16000, raw_response=raw)

    def _mk(self, session_id, turn_idx, mode, user_text, transcript, text_chunks, tools,
            route, audio_duration_s, turn_start, *, error, raw) -> VoiceTurnResult:
        return VoiceTurnResult(
            session_id=session_id, turn_index=turn_idx, mode=mode, user_text=user_text,
            transcript=transcript, agent_response_text="".join(text_chunks), tools_called=tools,
            agent_route=route, audio_duration_s=round(audio_duration_s, 3),
            total_latency_ms=round((time.monotonic() - turn_start) * 1000, 1), error=error,
            raw_response=raw)

    async def receive_opening(self, session_id: str) -> VoiceTurnResult | None:
        """Wait for an agent-first opening after connect; None if none arrives."""
        if self._ws is None:
            await self.connect(session_id)
        turn_start = time.monotonic()
        try:
            res = await self._collect(session_id=session_id, turn_idx=-1, mode="opening",
                                      user_text="<session start>", turn_start=turn_start,
                                      stream_end=turn_start, audio_duration_s=0.0,
                                      timeout_s=self.cfg.initial_response_timeout_s)
            if res.error and res.error.startswith("Timed out"):
                return None
            return res
        finally:
            await self.close()

    # ---- send -------------------------------------------------------------
    async def run_turn(self, text: str, session_id: str, turn_index: int = 0) -> VoiceTurnResult:
        if self.cfg.mode == "text":
            res = await self.send_text(text, session_id)
        else:
            res = await self.send_audio(text, session_id)
        res.turn_index = turn_index
        return res

    async def send_text(self, text: str, session_id: str) -> VoiceTurnResult:
        turn_start = time.monotonic()
        idx = self._turn_index
        self._turn_index += 1
        await self.connect(session_id)
        try:
            await self._ws.send(json.dumps({"realtimeInput": {"text": text}}))
            return await self._collect(session_id=session_id, turn_idx=idx, mode="text",
                                       user_text=text, turn_start=turn_start,
                                       stream_end=turn_start, audio_duration_s=0.0)
        finally:
            await self.close()

    async def send_audio(self, text: str, session_id: str) -> VoiceTurnResult:
        from audio import prepare_linear16, AsyncPacer
        turn_start = time.monotonic()
        idx = self._turn_index
        self._turn_index += 1
        duration = 0.0
        await self.connect(session_id)
        try:
            chunk_size, sleep_s = 640, 0.020  # 20ms of 16kHz s16 mono
            pacer = AsyncPacer(sleep_s)
            silence = b"\x00" * chunk_size
            silence_count = int(self.cfg.endpointing_silence_ms / 20)

            if text.strip():
                raw = (await asyncio.to_thread(
                    prepare_linear16, text, self.cfg.audio_cache_dir, self.cfg.tts_engine)).read_bytes()
                duration = len(raw) / (16000 * 2)
                for _ in range(12):  # ~240ms leading silence for short utterances
                    await self._ws.send(json.dumps({"realtimeInput": {
                        "audio": base64.b64encode(silence).decode(), "willContinue": True}}))
                    await pacer.pace()
                for i in range(0, len(raw), chunk_size):
                    await self._ws.send(json.dumps({"realtimeInput": {
                        "audio": base64.b64encode(raw[i:i + chunk_size]).decode(), "willContinue": True}}))
                    await pacer.pace()
            else:
                silence_count = max(silence_count, int(8.0 / sleep_s))  # model a silent caller
                duration = silence_count * sleep_s

            for _ in range(silence_count):
                await self._ws.send(json.dumps({"realtimeInput": {
                    "audio": base64.b64encode(silence).decode(), "willContinue": True}}))
                await pacer.pace()
            await self._ws.send(json.dumps({"realtimeInput": {"audio": "", "willContinue": False}}))
            stream_end = time.monotonic()

            return await self._collect(session_id=session_id, turn_idx=idx, mode="voice",
                                       user_text=text, turn_start=turn_start,
                                       stream_end=stream_end, audio_duration_s=duration)
        except Exception as exc:
            return self._mk(session_id, idx, "voice", text, text, [], [], "", duration,
                            turn_start, error=str(exc), raw={})
        finally:
            await self.close()


# ---- extraction helpers ---------------------------------------------------

def _extract_tool_calls(diag: dict) -> list[str]:
    tools: list[str] = []
    for msg in diag.get("messages", []):
        for chunk in msg.get("chunks", []):
            tc = chunk.get("toolCall")
            if tc:
                name = tc.get("displayName") or (tc.get("tool", "").split("/")[-1])
                if name and name not in tools:
                    tools.append(name)
    return tools


def _extract_agent_route(diag: dict) -> str:
    route: list[str] = []
    agent = diag.get("agentName", "")
    if agent:
        route.append(agent.split("/")[-1])
    for msg in diag.get("messages", []):
        role = msg.get("role", "")
        if role and role != "user" and role not in route:
            route.append(role)
    return " -> ".join(route)
