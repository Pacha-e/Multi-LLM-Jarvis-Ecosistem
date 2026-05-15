"""J.A.R.V.I.S. — Multi-Channel Intent Router
Inspired by OpenClaw orchestration pattern (reel 3).
Routes requests to specialized sub-agents based on intent.
"""

import re
import logging
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """17-intent classification inspired by rezaulhreza/jarvis."""
    # Information retrieval
    SEARCH = "search"
    WEATHER = "weather"
    NEWS = "news"
    # System & tools
    SYSTEM_INFO = "system_info"
    CALCULATE = "calculate"
    REMINDER = "reminder"
    # Memory
    REMEMBER = "remember"
    RECALL = "recall"
    # Coding
    CODE = "code"
    DEBUG = "debug"
    EXPLAIN = "explain"
    # Creative
    WRITE = "write"
    BRAINSTORM = "brainstorm"
    # Planning
    PLAN = "plan"
    SUMMARIZE = "summarize"
    # General
    CHAT = "chat"
    UNKNOWN = "unknown"


@dataclass
class RouteDecision:
    intent: IntentType
    confidence: float
    suggested_persona: str
    use_tools: list[str]
    reasoning: str


# Intent patterns — fast keyword-based classifier (no ML needed for routing)
INTENT_PATTERNS: list[tuple[IntentType, list[str], str]] = [
    (IntentType.WEATHER, ["clima", "weather", "temperatura", "lluvia", "sol", "pronóstico", "forecast"], "jarvis"),
    (IntentType.CALCULATE, ["calcula", "calculate", "cuanto es", "resultado de", "matemática", "integral", "derivada", "√", "^", "%"], "jarvis"),
    (IntentType.SYSTEM_INFO, ["cpu", "ram", "memoria", "disco", "sistema", "system", "recursos", "gpu"], "jarvis"),
    (IntentType.SEARCH, ["busca", "search", "encuentra", "investiga", "qué es", "quién es", "dónde", "cuándo fue", "noticias"], "researcher"),
    (IntentType.CODE, ["código", "code", "función", "function", "class", "implementa", "escribe un script", "programa que", "python", "javascript", "rust"], "coder"),
    (IntentType.DEBUG, ["error", "bug", "falla", "exception", "traceback", "no funciona", "arregla", "fix", "debug"], "coder"),
    (IntentType.EXPLAIN, ["explica", "explain", "cómo funciona", "qué hace", "por qué", "entiende", "describe"], "researcher"),
    (IntentType.REMEMBER, ["recuerda", "remember", "guarda", "anota", "memoriza", "no olvides"], "jarvis"),
    (IntentType.RECALL, ["recuerda qué", "qué guardaste", "busca en memoria", "recall", "qué sé sobre", "olvido"], "jarvis"),
    (IntentType.WRITE, ["escribe", "redacta", "draft", "compone", "carta", "email", "ensayo", "artículo"], "creative"),
    (IntentType.BRAINSTORM, ["ideas", "brainstorm", "propón", "alternativas", "opciones para", "cómo podría", "qué formas"], "creative"),
    (IntentType.PLAN, ["planifica", "plan", "organiza", "proyecto", "tareas", "cronograma", "roadmap", "pasos para"], "planner"),
    (IntentType.SUMMARIZE, ["resume", "summarize", "resumen de", "en pocas palabras", "tl;dr", "sintetiza"], "researcher"),
    (IntentType.NEWS, ["noticias", "news", "últimas", "recent", "hoy", "today", "actualidad"], "researcher"),
]

# Channel-specific routing (OpenClaw-inspired multi-channel concept)
CHANNEL_CONFIG = {
    "web": {"max_tokens": 2048, "stream": True, "tools": True},
    "telegram": {"max_tokens": 1024, "stream": False, "tools": True},
    "voice": {"max_tokens": 512, "stream": False, "tools": False},  # Voice needs short responses
    "api": {"max_tokens": 4096, "stream": True, "tools": True},
}


class JarvisRouter:
    """Routes messages to appropriate persona and tools based on intent."""

    def __init__(self):
        self._compiled_patterns = [
            (intent, [p.lower() for p in patterns], persona)
            for intent, patterns, persona in INTENT_PATTERNS
        ]

    def classify_intent(self, message: str) -> RouteDecision:
        """Fast keyword-based intent classification."""
        msg_lower = message.lower()

        best_intent = IntentType.CHAT
        best_confidence = 0.3
        best_persona = "jarvis"
        matched_keywords = []

        for intent, patterns, persona in self._compiled_patterns:
            hits = [p for p in patterns if p in msg_lower]
            if hits:
                confidence = min(0.95, 0.5 + len(hits) * 0.15)
                if confidence > best_confidence:
                    best_intent = intent
                    best_confidence = confidence
                    best_persona = persona
                    matched_keywords = hits

        # Determine tools to activate
        use_tools = self._select_tools(best_intent)

        return RouteDecision(
            intent=best_intent,
            confidence=best_confidence,
            suggested_persona=best_persona,
            use_tools=use_tools,
            reasoning=f"Keywords: {matched_keywords}" if matched_keywords else "Default chat",
        )

    def _select_tools(self, intent: IntentType) -> list[str]:
        """Map intent to relevant tools."""
        tool_map = {
            IntentType.WEATHER: ["get_weather"],
            IntentType.SEARCH: ["web_search", "scrape_url"],
            IntentType.NEWS: ["web_search"],
            IntentType.SYSTEM_INFO: ["get_system_info"],
            IntentType.CALCULATE: ["calculate"],
            IntentType.REMEMBER: ["remember_fact"],
            IntentType.RECALL: ["recall_fact", "search_memory"],
            IntentType.CODE: ["web_search", "scrape_url"],
            IntentType.DEBUG: ["web_search"],
            IntentType.EXPLAIN: ["web_search", "scrape_url"],
            IntentType.WRITE: [],
            IntentType.BRAINSTORM: [],
            IntentType.PLAN: ["get_current_datetime"],
            IntentType.SUMMARIZE: ["scrape_url"],
            IntentType.CHAT: ["get_current_datetime"],
            IntentType.UNKNOWN: [],
        }
        return tool_map.get(intent, [])

    def get_channel_config(self, channel: str) -> dict:
        """Get configuration for a specific channel."""
        return CHANNEL_CONFIG.get(channel, CHANNEL_CONFIG["web"])

    def should_use_streaming(self, channel: str) -> bool:
        return self.get_channel_config(channel).get("stream", True)

    def get_max_tokens(self, channel: str) -> int:
        return self.get_channel_config(channel).get("max_tokens", 2048)


# Singleton
jarvis_router = JarvisRouter()
