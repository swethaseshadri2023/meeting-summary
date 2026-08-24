"""
Central configuration for the Meeting Summarizer backend.
All settings are read from environment variables (see .env.example).
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# --- ASR ---
ASR_PROVIDER = os.getenv("ASR_PROVIDER", "local").lower()  # "local" | "openai"
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# --- LLM ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# --- Storage ---
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "./data/meetings.db"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./data/uploads"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "200"))

# Make sure storage directories exist
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".mp4", ".webm", ".ogg", ".flac", ".aac"
}
