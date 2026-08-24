"""
Transcription layer.

Two interchangeable providers, selected via ASR_PROVIDER env var:

  - "local"  -> faster-whisper running on this machine (default, free, no API key)
  - "openai" -> OpenAI's hosted Whisper API (requires OPENAI_API_KEY)

Swapping in Google Speech-to-Text or Azure Speech would mean adding another
`_transcribe_with_x()` function and a branch in `transcribe_audio()` -- the
rest of the app (main.py, summarizer.py) doesn't need to change.
"""
from pathlib import Path
from functools import lru_cache

from config import ASR_PROVIDER, WHISPER_MODEL_SIZE, OPENAI_API_KEY


@lru_cache(maxsize=1)
def _get_local_model():
    """Lazily load the faster-whisper model once and reuse it across requests."""
    from faster_whisper import WhisperModel
    # "int8" compute type keeps CPU inference fast and memory-light.
    return WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")


def _transcribe_local(audio_path: Path) -> str:
    model = _get_local_model()
    segments, _info = model.transcribe(str(audio_path), beam_size=5, vad_filter=True)
    return " ".join(segment.text.strip() for segment in segments).strip()


def _transcribe_openai(audio_path: Path) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    with open(audio_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
        )
    return result.text.strip()


def transcribe_audio(audio_path: Path) -> str:
    """Transcribe an audio file to plain text using the configured provider."""
    if ASR_PROVIDER == "openai":
        return _transcribe_openai(audio_path)
    return _transcribe_local(audio_path)
