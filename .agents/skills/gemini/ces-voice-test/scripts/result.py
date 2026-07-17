"""Result type for a single voice turn (one user utterance -> agent response)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VoiceTurnResult:
    session_id: str
    turn_index: int
    mode: str                       # "voice" | "text" | "opening"
    user_text: str
    transcript: str = ""            # STT transcript (voice) or echo (text)
    agent_response_text: str = ""
    tools_called: list[str] = field(default_factory=list)
    agent_route: str = ""
    audio_duration_s: float = 0.0
    streaming_duration_s: float = 0.0
    response_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    agent_audio: bytes = b""        # raw agent audio (LINEAR16) from the stream
    agent_audio_sample_rate: int = 0
    raw_response: dict = field(default_factory=dict)
    error: str = ""
