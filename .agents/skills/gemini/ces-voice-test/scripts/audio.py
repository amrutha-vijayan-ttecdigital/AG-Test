"""Audio pipeline for the voice path: text -> TTS -> 16kHz LINEAR16 raw.

TTS engines (auto-detected): `gtts-cli` (pip install gtts) or macOS `say`.
`ffmpeg` is used to normalize to 16kHz mono s16. Output is cached by text hash so
re-running a pack doesn't re-synthesize. Nothing is written outside the
configured cache dir (defaults to the OS temp dir).
"""
from __future__ import annotations

import asyncio
import hashlib
import shutil
import subprocess
import time
import wave
from pathlib import Path


def _pick_engine(engine: str) -> str:
    if engine != "auto":
        return engine
    try:
        import sys
        from pathlib import Path
        for parent in Path(__file__).resolve().parents:
            cand = parent / ".agents" / "scripts"
            if cand.is_dir():
                if str(cand) not in sys.path:
                    sys.path.insert(0, str(cand))
                break
        from ces_client import CES
        c = CES()
        if c.project:
            return "google"
    except Exception:
        pass

    if shutil.which("gtts-cli"):
        return "gtts"
    if shutil.which("say"):
        return "say"
    raise RuntimeError(
        "No TTS engine found. Install gTTS (`pip install gtts`) or run on macOS "
        "(`say`). Or use `--mode text` to send text over the WebSocket without TTS."
    )


def _to_wav_16k(src: Path, dst: Path) -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is required to normalize audio to 16kHz mono")
    subprocess.run(["ffmpeg", "-y", "-i", str(src), "-ar", "16000", "-ac", "1",
                    "-sample_fmt", "s16", str(dst)], check=True, capture_output=True)


def _synthesize_google_tts(text: str, out_wav: Path) -> None:
    import json
    import base64
    import urllib.request
    import urllib.error
    
    import sys
    from pathlib import Path
    for parent in Path(__file__).resolve().parents:
        cand = parent / ".agents" / "scripts"
        if cand.is_dir():
            if str(cand) not in sys.path:
                sys.path.insert(0, str(cand))
            break
    from ces_client import CES
    
    try:
        ces_inst = CES()
        token = ces_inst._get_token()
        project = ces_inst.project
    except Exception as e:
        raise RuntimeError(f"Failed to authenticate with gcloud for Google Cloud TTS: {e}")

    url = "https://texttospeech.googleapis.com/v1/text:synthesize"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-goog-user-project": project,
    }
    body = {
        "input": {
            "text": text
        },
        "voice": {
            "languageCode": "en-US",
            "ssmlGender": "NEUTRAL"
        },
        "audioConfig": {
            "audioEncoding": "LINEAR16",
            "sampleRateHertz": 16000
        }
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read().decode("utf-8"))
            audio_content = base64.b64decode(resp["audioContent"])
            out_wav.write_bytes(audio_content)
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode('utf-8')
        if "Text-to-Speech API has not been used" in err_msg or "ServiceDisabled" in err_msg:
            raise RuntimeError(
                f"Google Cloud Text-to-Speech API is not enabled in project {project}. "
                f"Enable it in the Google Cloud Console or set CES_VOICE_TTS=gtts / say "
                f"and install local dependencies. Details: {err_msg}"
            )
        raise RuntimeError(f"Google Cloud TTS API HTTP {e.code} error: {err_msg}")
    except Exception as e:
        raise RuntimeError(f"Google Cloud TTS API call failed: {e}")


def text_to_wav(text: str, out_wav: Path, engine: str) -> None:
    eng = _pick_engine(engine)
    if eng == "google":
        _synthesize_google_tts(text, out_wav)
    elif eng == "gtts":
        mp3 = out_wav.with_suffix(".mp3")
        subprocess.run(["gtts-cli", text, "-l", "en", "-o", str(mp3)], check=True, capture_output=True)
        _to_wav_16k(mp3, out_wav)
        mp3.unlink(missing_ok=True)
    elif eng == "say":
        aiff = out_wav.with_suffix(".aiff")
        subprocess.run(["say", "-o", str(aiff), text], check=True, capture_output=True)
        _to_wav_16k(aiff, out_wav)
        aiff.unlink(missing_ok=True)
    else:
        raise ValueError(f"Unknown TTS engine: {eng}")


def prepare_linear16(text: str, cache_dir: str, engine: str) -> Path:
    """text -> 16kHz LINEAR16 raw bytes file. Cached by content hash."""
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    key = hashlib.md5(text.encode()).hexdigest()[:12]
    raw_path = cache / f"{key}_l16.raw"
    if raw_path.exists():
        return raw_path

    wav = cache / f"{key}.wav"
    text_to_wav(text, wav, engine)
    with wave.open(str(wav), "rb") as wf:
        if wf.getframerate() != 16000 or wf.getnchannels() != 1:
            wav16 = cache / f"{key}_16k.wav"
            _to_wav_16k(wav, wav16)
            with wave.open(str(wav16), "rb") as wf2:
                raw = wf2.readframes(wf2.getnframes())
            wav16.unlink(missing_ok=True)
        else:
            raw = wf.readframes(wf.getnframes())
    raw_path.write_bytes(raw)
    wav.unlink(missing_ok=True)
    return raw_path


class AsyncPacer:
    """Paces a loop to a fixed interval without cumulative drift (real-time send)."""

    def __init__(self, interval_s: float):
        self.interval_s = interval_s
        self.next_time = time.monotonic()

    async def pace(self) -> None:
        self.next_time += self.interval_s
        delay = self.next_time - time.monotonic()
        if delay > 0:
            await asyncio.sleep(delay)
