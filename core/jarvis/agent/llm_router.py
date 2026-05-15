"""J.A.R.V.I.S. — Multi-LLM Router (cost/capability-aware)

Routing by task tier:
  simple   -> local/free first   (Ollama -> Groq)
  medium   -> free cloud         (Groq -> Gemini Flash -> Anthropic Haiku -> Ollama)
  complex  -> capable/paid       (Anthropic Opus -> OpenAI -> Groq -> Gemini Flash)

Each tier is an ordered list of provider builders; the first one whose
credentials/health are available wins. Free/local is always preferred when it
can satisfy the tier — paid models are reached only when the tier demands them.
"""

import httpx
from typing import Optional
from langchain_core.language_models import BaseChatModel
from jarvis.config import config


# --- complexity inference --------------------------------------------------

# Keywords that signal a task needs a capable model. Spanish + English.
_COMPLEX_HINTS = (
    "audita", "auditoria", "refactor", "arquitectura", "architecture",
    "diseña", "design", "demuestra", "prove", "razona", "reasoning",
    "depura", "debug", "optimiza", "optimize", "analiza a fondo",
    "explica por que", "explain why", "plan", "estrategia",
)
_SIMPLE_HINTS = (
    "hola", "gracias", "resume", "summarize", "traduce", "translate",
    "formatea", "format", "lista", "list", "que hora", "what time",
)


def infer_tier(text: str, intent: Optional[str] = None) -> str:
    """Heuristic task tier from prompt text (+ optional IntentClassifier intent).

    Returns one of: "simple" | "medium" | "complex".
    """
    t = (text or "").lower()
    if any(h in t for h in _COMPLEX_HINTS):
        return "complex"
    # Long prompts tend to carry more reasoning load.
    if len(t) > 600:
        return "complex"
    if any(h in t for h in _SIMPLE_HINTS) and len(t) < 120:
        return "simple"
    if intent in {"greeting", "smalltalk", "thanks"}:
        return "simple"
    return "medium"


# --- provider health -------------------------------------------------------

def check_ollama_health() -> bool:
    """Check if Ollama is running and the primary model is available."""
    try:
        r = httpx.get(f"{config.OLLAMA_URL}/api/tags", timeout=3.0)
        if r.status_code != 200:
            return False
        models = [m["name"] for m in r.json().get("models", [])]
        return any(config.PRIMARY_MODEL in m for m in models)
    except Exception:
        return False


# --- provider builders -----------------------------------------------------
# Each returns a BaseChatModel or None (missing creds / missing package).

def _build_ollama() -> Optional[BaseChatModel]:
    if not check_ollama_health():
        return None
    try:
        from langchain_ollama import ChatOllama
        return ChatOllama(model=config.PRIMARY_MODEL, base_url=config.OLLAMA_URL, temperature=0.7)
    except ImportError:
        return None


def _build_groq() -> Optional[BaseChatModel]:
    if not config.GROQ_API_KEY:
        return None
    try:
        from langchain_groq import ChatGroq
        return ChatGroq(model=config.GROQ_MODEL, api_key=config.GROQ_API_KEY, temperature=0.7)
    except ImportError:
        return None


def _build_groq_model(model: str) -> Optional[BaseChatModel]:
    """Groq with an explicit model id (e.g. the best model for the complex tier)."""
    if not config.GROQ_API_KEY:
        return None
    try:
        from langchain_groq import ChatGroq
        return ChatGroq(model=model, api_key=config.GROQ_API_KEY, temperature=0.7)
    except ImportError:
        return None


def _build_gemini(model: Optional[str] = None) -> Optional[BaseChatModel]:
    key = getattr(config, "GEMINI_API_KEY", None) or getattr(config, "GOOGLE_API_KEY", None)
    if not key:
        return None
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        model = model or getattr(config, "GEMINI_MODEL", "gemini-2.5-flash")
        return ChatGoogleGenerativeAI(model=model, google_api_key=key, temperature=0.7)
    except ImportError:
        return None


def _build_anthropic(model: str) -> Optional[BaseChatModel]:
    if not config.ANTHROPIC_API_KEY:
        return None
    try:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, api_key=config.ANTHROPIC_API_KEY, temperature=0.7)
    except ImportError:
        return None


def _build_openai(model: str, reasoning_effort: Optional[str] = None) -> Optional[BaseChatModel]:
    if not config.OPENAI_API_KEY:
        return None
    try:
        from langchain_openai import ChatOpenAI
        kwargs = {"model": model, "api_key": config.OPENAI_API_KEY}
        if reasoning_effort:
            # Reasoning models (gpt-5.x) ignore temperature; expose effort tier instead.
            kwargs["reasoning_effort"] = reasoning_effort
        else:
            kwargs["temperature"] = 0.7
        return ChatOpenAI(**kwargs)
    except ImportError:
        return None


# --- tier routing tables ---------------------------------------------------
# Ordered (name, cost, model, builder) chains. First non-None builder wins.

_SONNET = "claude-sonnet-4-6"
_GPT5 = "gpt-5.5"
_GROQ_FREE = config.GROQ_MODEL
_GROQ_BEST = getattr(config, "GROQ_BEST_MODEL", "llama-3.3-70b-versatile")
_GEMINI_FLASH = getattr(config, "GEMINI_MODEL", "gemini-2.5-flash")
_GEMINI_COMPLEX = getattr(config, "GEMINI_COMPLEX_MODEL", "gemini-3-flash-preview")

_TIERS = {
    "simple": [
        ("ollama",  "free", None,          _build_ollama),
        ("groq",    "free", _GROQ_FREE,    _build_groq),
        ("gemini",  "free", _GEMINI_FLASH, _build_gemini),
    ],
    "medium": [
        ("groq",      "free", _GROQ_FREE,    _build_groq),
        ("gemini",    "free", _GEMINI_FLASH, _build_gemini),
        ("ollama",    "free", None,          _build_ollama),
        ("anthropic", "paid", _SONNET,       lambda: _build_anthropic(_SONNET)),
        ("openai",    "paid", "gpt-4o",      lambda: _build_openai("gpt-4o")),
    ],
    "complex": [
        ("openai",  "paid", _GPT5,       lambda: _build_openai(_GPT5, reasoning_effort="xhigh")),
        ("groq",    "free", _GROQ_BEST,  lambda: _build_groq_model(_GROQ_BEST)),
        ("gemini",  "free", _GEMINI_COMPLEX, lambda: _build_gemini(_GEMINI_COMPLEX)),
    ],
}


def get_langchain_llm(tier: str = "medium") -> BaseChatModel:
    """Return the best available LLM for the given task tier.

    tier: "simple" | "medium" | "complex" (defaults to "medium").
    Falls back across the tier chain; raises RuntimeError if none available.
    """
    chain = _TIERS.get(tier, _TIERS["medium"])
    for _name, _cost, _model, builder in chain:
        llm = builder()
        if llm is not None:
            return llm
    raise RuntimeError(
        f"No LLM available for tier '{tier}'. "
        "Install Ollama or set GROQ_API_KEY/GEMINI_API_KEY/ANTHROPIC_API_KEY/OPENAI_API_KEY."
    )


def route(text: str, intent: Optional[str] = None) -> BaseChatModel:
    """One-shot: infer tier from text and return the routed LLM."""
    return get_langchain_llm(infer_tier(text, intent))


def get_active_provider(tier: str = "medium") -> dict:
    """Return info about which provider would be used for a tier (no instantiation)."""
    chain = _TIERS.get(tier, _TIERS["medium"])
    for name, cost, model, builder in chain:
        # Probe availability by attempting the build.
        if builder() is not None:
            return {
                "provider": name,
                "model": model if model is not None else config.PRIMARY_MODEL,
                "cost": cost,
                "local": name == "ollama",
                "tier": tier,
            }
    return {"provider": "none", "model": None, "cost": None, "local": False, "tier": tier}
