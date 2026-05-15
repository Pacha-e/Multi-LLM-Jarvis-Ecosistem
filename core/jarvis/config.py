"""J.A.R.V.I.S. — Centralized Configuration"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load from jarvis.env if exists, else fall back to os env
_env_path = Path("jarvis.env")
if _env_path.exists():
    load_dotenv(_env_path)
else:
    load_dotenv()


class Config:
    # Ollama
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    PRIMARY_MODEL: str = os.getenv("PRIMARY_MODEL", "qwen2.5:3b")

    # Groq
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    # Anthropic
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Whisper STT
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cuda")
    WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "float16")

    # TTS
    TTS_ENGINE: str = os.getenv("TTS_ENGINE", "pyttsx3")
    TTS_RATE: int = int(os.getenv("TTS_RATE", "180"))
    TTS_VOLUME: float = float(os.getenv("TTS_VOLUME", "0.9"))

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Database
    DB_PATH: str = os.getenv("DB_PATH", "data/jarvis.db")

    # External APIs
    BRAVE_API_KEY: str = os.getenv("BRAVE_API_KEY", "")
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")

    # Reels pipeline (metadata -> Whisper -> Obsidian)
    # Repo layout: this file is core/jarvis/config.py -> repo root = parents[2].
    _REPO_ROOT: Path = Path(__file__).resolve().parents[2]
    OBSIDIAN_VAULT: str = os.getenv(
        "OBSIDIAN_VAULT",
        os.path.expanduser("~/Documents/OBSIDIAN/CLAUDE CODE"),
    )
    REELS_DIR: str = os.getenv("REELS_DIR", "")  # empty -> <OBSIDIAN_VAULT>/Reels at runtime
    # Dedicated browser profile for scraping. NEVER the personal Chrome profile.
    BROWSER_PROFILE_DIR: str = os.getenv(
        "BROWSER_PROFILE_DIR",
        str(_REPO_ROOT / "runtime" / "openclaw-jarvis" / "var" / "browser-profile"),
    )
    # Temp download dir for reel videos (gitignored under var/).
    REELS_TMP_DIR: str = os.getenv(
        "REELS_TMP_DIR",
        str(_REPO_ROOT / "runtime" / "openclaw-jarvis" / "var" / "reels-tmp"),
    )
    # Apify is a PAID fallback, last resort only. Empty token -> Apify disabled.
    APIFY_TOKEN: str = os.getenv("APIFY_TOKEN", "")

    # Personality
    JARVIS_NAME: str = os.getenv("JARVIS_NAME", "J.A.R.V.I.S.")
    USER_NAME: str = os.getenv("USER_NAME", "Emmanuel")

    SYSTEM_PROMPT: str = f"""You are {os.getenv('JARVIS_NAME', 'J.A.R.V.I.S.')}, an advanced AI assistant.
You are helpful, precise, and slightly witty — like the AI from Iron Man.
You address the user as {os.getenv('USER_NAME', 'Emmanuel')}.
You respond concisely and accurately. When using tools, explain what you're doing briefly.
Always respond in the same language the user uses (Spanish or English)."""


config = Config()
