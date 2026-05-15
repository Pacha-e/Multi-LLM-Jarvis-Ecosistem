"""J.A.R.V.I.S. — Multi-LLM Router
Priority: Ollama local -> Groq free -> Anthropic -> OpenAI
"""

import httpx
from typing import Optional
from langchain_core.language_models import BaseChatModel
from jarvis.config import config


def check_ollama_health() -> bool:
    """Check if Ollama is running and the primary model is available."""
    try:
        r = httpx.get(f"{config.OLLAMA_URL}/api/tags", timeout=3.0)
        if r.status_code != 200:
            return False
        models = [m["name"] for m in r.json().get("models", [])]
        # Accept partial match (e.g. "qwen2.5:3b" matches "qwen2.5:3b")
        return any(config.PRIMARY_MODEL in m for m in models)
    except Exception:
        return False


def get_langchain_llm() -> BaseChatModel:
    """Return the best available LLM in priority order."""

    # 1. Ollama (local, free)
    if check_ollama_health():
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=config.PRIMARY_MODEL,
                base_url=config.OLLAMA_URL,
                temperature=0.7,
            )
        except ImportError:
            pass

    # 2. Groq (cloud, free tier)
    if config.GROQ_API_KEY:
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=config.GROQ_MODEL,
                api_key=config.GROQ_API_KEY,
                temperature=0.7,
            )
        except ImportError:
            pass

    # 3. Anthropic
    if config.ANTHROPIC_API_KEY:
        try:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model="claude-haiku-4-5-20251001",
                api_key=config.ANTHROPIC_API_KEY,
                temperature=0.7,
            )
        except ImportError:
            pass

    # 4. OpenAI
    if config.OPENAI_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model="gpt-4o-mini",
                api_key=config.OPENAI_API_KEY,
                temperature=0.7,
            )
        except ImportError:
            pass

    raise RuntimeError(
        "No LLM available. Install Ollama or set GROQ_API_KEY/ANTHROPIC_API_KEY/OPENAI_API_KEY."
    )


def get_active_provider() -> dict:
    """Return info about which provider would be used."""
    if check_ollama_health():
        return {"provider": "ollama", "model": config.PRIMARY_MODEL, "cost": "free", "local": True}
    if config.GROQ_API_KEY:
        return {"provider": "groq", "model": config.GROQ_MODEL, "cost": "free", "local": False}
    if config.ANTHROPIC_API_KEY:
        return {"provider": "anthropic", "model": "claude-haiku-4-5-20251001", "cost": "paid", "local": False}
    if config.OPENAI_API_KEY:
        return {"provider": "openai", "model": "gpt-4o-mini", "cost": "paid", "local": False}
    return {"provider": "none", "model": None, "cost": None, "local": False}
