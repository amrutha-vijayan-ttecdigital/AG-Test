"""Configuration for the voice (BidiRunSession) test runner.

Connection details come from the kit-root `.env` via the shared client's
`load_env()`; voice-specific knobs come from the environment with sane defaults.
Nothing is hardcoded to a machine — the audio cache defaults to the OS temp dir.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile
from dataclasses import dataclass, field


def _load_shared_env() -> dict:
    here = pathlib.Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / ".agents" / "scripts"
        if cand.is_dir():
            sys.path.insert(0, str(cand))
            break
    from ces_client import load_env  # type: ignore
    return load_env(require=False)


def _default_cache_dir() -> str:
    return os.environ.get("CES_VOICE_AUDIO_CACHE") or str(
        pathlib.Path(tempfile.gettempdir()) / "ces_voice_audio_cache"
    )


@dataclass
class VoiceConfig:
    env: dict = field(default_factory=_load_shared_env)

    # Resolved from .env / shared client
    project_id: str = ""
    region: str = ""
    app_id: str = ""
    deployment_id: str = ""
    account: str = ""
    host: str = ""

    # Behavior
    mode: str = os.getenv("CES_VOICE_MODE", "voice")          # voice (TTS->STT) | text (send text)
    use_draft: bool = os.getenv("CES_VOICE_DRAFT", "false").lower() == "true"
    use_tool_fakes: bool = os.getenv("CES_VOICE_TOOL_FAKES", "false").lower() == "true"

    # TTS / audio
    tts_engine: str = os.getenv("CES_VOICE_TTS", "auto")       # auto | gtts | say
    audio_cache_dir: str = field(default_factory=_default_cache_dir)
    sample_rate: int = 16000                                   # LINEAR16 over the WS path

    # Timing
    inter_turn_delay_s: float = 1.0
    max_turn_timeout_s: float = 30.0
    initial_response_timeout_s: float = 8.0
    endpointing_silence_ms: int = 2000

    def __post_init__(self) -> None:
        e = self.env
        self.project_id = self.project_id or e.get("GCP_PROJECT_ID", "")
        self.region = self.region or e.get("GCP_REGION", "us")
        self.app_id = self.app_id or e.get("CES_APP_ID", "") or e.get("CES_AGENT_ID", "")
        self.deployment_id = self.deployment_id or e.get("CES_DEPLOYMENT_ID", "")
        self.account = self.account or e.get("CES_USER", "") or e.get("GCP_ACCOUNT", "")
        self.host = self.host or e.get("CES_API_HOST", "ces.googleapis.com")

    @property
    def app_path(self) -> str:
        return f"projects/{self.project_id}/locations/{self.region}/apps/{self.app_id}"

    @property
    def deployment_path(self) -> str:
        return f"{self.app_path}/deployments/{self.deployment_id}"

    def session_path(self, session_id: str) -> str:
        return f"{self.app_path}/sessions/{session_id}"

    def ws_url(self) -> str:
        return (f"wss://{self.host}/ws/google.cloud.ces.v1.SessionService"
                f"/BidiRunSession/locations/{self.region}")

    def validate(self) -> list[str]:
        errors = []
        if not self.project_id:
            errors.append("GCP_PROJECT_ID not set")
        if not self.app_id:
            errors.append("CES_APP_ID / CES_AGENT_ID not set")
        if not self.deployment_id and not self.use_draft:
            errors.append("CES_DEPLOYMENT_ID not set (or pass --draft)")
        return errors
