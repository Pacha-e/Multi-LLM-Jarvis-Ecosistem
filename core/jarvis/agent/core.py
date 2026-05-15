"""J.A.R.V.I.S. — LangGraph ReAct Agent Core

Architecture:
- LangGraph ReAct: Reason → Act → Observe loop
- Memory digest: top-5 long-term facts injected into system prompt
- RAG: personal knowledge base (Obsidian vault) retrieved per query
- Task-list planner: pre-agentic multi-step decomposition
- Multi-LLM router: Ollama → Groq → Anthropic → OpenAI failover
"""

import json
import logging
import os
from typing import AsyncIterator
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from jarvis.config import config
from jarvis.agent.memory import JarvisMemory
from jarvis.agent.llm_router import get_langchain_llm, get_active_provider
from jarvis.agent.tools import JARVIS_TOOLS
from jarvis.agent.personas import persona_manager
from jarvis.agent.router import jarvis_router

# Tool dispatch map for fallback JSON-tool-call handling
_TOOL_MAP = {t.name: t for t in JARVIS_TOOLS}

logger = logging.getLogger(__name__)

# ── Task-list planner prompt ──────────────────────────────────────────────────
PLANNER_PROMPT = """Before responding, if the request involves multiple steps,
briefly plan them as a numbered list (max 3 items). Then execute each step.
Keep the plan internal — only show results to the user.
IMPORTANT: Always respond with natural language text. Never output raw JSON or tool call syntax as your final answer."""

# ── RAG lazy loader ───────────────────────────────────────────────────────────
_rag = None

def _get_rag():
    global _rag
    if _rag is None:
        try:
            from jarvis.agent.rag import get_rag
            _rag = get_rag()
        except Exception as e:
            logger.debug(f"[Agent] RAG unavailable: {e}")
            _rag = False  # Disable after first failure
    return _rag if _rag else None


class JarvisAgent:
    def __init__(self):
        self.memory = JarvisMemory(config.DB_PATH)
        self._checkpointer = MemorySaver()
        self._rag_enabled = os.getenv("RAG_ENABLED", "true").lower() == "true"
        self._build_agent()

    def _build_agent(self):
        """Build/rebuild agent — called on init and on LLM provider failover."""
        llm = get_langchain_llm()
        self.agent = create_react_agent(
            llm,
            JARVIS_TOOLS,
            checkpointer=self._checkpointer,
        )
        self.provider_info = get_active_provider()
        logger.info(f"[Agent] Built with provider: {self.provider_info.get('provider','unknown')}")

    def _get_thread_config(self, session_id: str) -> dict:
        return {"configurable": {"thread_id": session_id}}

    def _build_system_messages(self, session_id: str, user_message: str = "") -> list:
        """Build system context: persona prompt + memory digest + RAG + planner."""
        # Use persona system prompt (replaces static config.SYSTEM_PROMPT)
        base_prompt = persona_manager.current_system_prompt

        # Memory digest — inject relevant long-term facts
        memories = self.memory.get_all_memories()[:5]
        memory_digest = ""
        if memories:
            facts = "\n".join(f"- {m['key']}: {m['value']}" for m in memories[:5])
            memory_digest = f"\n\nKnown facts about the user:\n{facts}"

        # RAG — retrieve relevant personal knowledge
        rag_context = ""
        if self._rag_enabled and user_message:
            try:
                rag = _get_rag()
                if rag:
                    rag_context_raw = rag.retrieve(user_message)
                    if rag_context_raw:
                        rag_context = f"\n\n{rag_context_raw}"
            except Exception as e:
                logger.debug(f"[Agent] RAG retrieve error: {e}")

        system_content = (
            base_prompt
            + memory_digest
            + rag_context
            + "\n\n"
            + PLANNER_PROMPT
        )

        return [SystemMessage(content=system_content)]

    def _fix_tool_call_response(self, response: str) -> str:
        """If model returns raw JSON tool-call, execute it and return result."""
        import re as _re
        # Remove markdown code blocks
        text = _re.sub(r"```(?:json)?\s*", "", response).strip().rstrip("`").strip()
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "name" in data and "arguments" in data:
                tool_name = data["name"]
                args = data.get("arguments", {})
                # Filter out null/invalid args
                clean_args = {k: v for k, v in args.items() if v is not None and isinstance(v, (str, int, float, bool))}
                if tool_name in _TOOL_MAP:
                    tool = _TOOL_MAP[tool_name]
                    logger.info(f"[Agent] Executing tool from JSON response: {tool_name}({clean_args})")
                    try:
                        result = tool.invoke(clean_args)
                        return str(result)
                    except Exception as e:
                        logger.warning(f"[Agent] Tool {tool_name} failed: {e}")
                        return f"[Tool {tool_name} failed: {e}]"
        except (json.JSONDecodeError, ValueError):
            pass
        return response

    async def chat(self, message: str, session_id: str = "default", channel: str = "web") -> str:
        """Chat — returns full response string. Supports persona switching via /persona cmd."""
        # Check for persona switch command
        requested_persona = persona_manager.detect_persona_from_message(message)
        if requested_persona:
            persona = persona_manager.set_persona(requested_persona)
            if persona:
                return f"{persona.emoji} Modo activado: **{persona.display_name}**\n{persona.description}"

        # Route intent (for logging / future sub-agent routing)
        route = jarvis_router.classify_intent(message)
        logger.debug(f"[Router] intent={route.intent.value} confidence={route.confidence:.2f} persona={route.suggested_persona}")

        # Auto-suggest persona based on intent (non-intrusive)
        if route.confidence > 0.7 and route.suggested_persona != persona_manager.current_name:
            logger.info(f"[Router] Suggest persona switch: {route.suggested_persona}")

        self.memory.add_message(session_id, "user", message)

        messages = self._build_system_messages(session_id, message) + [
            HumanMessage(content=message)
        ]

        try:
            result = await self.agent.ainvoke(
                {"messages": messages},
                config=self._get_thread_config(session_id),
            )
            response = result["messages"][-1].content
        except Exception as e:
            logger.warning(f"[Agent] Primary provider failed ({e}), trying failover...")
            self._build_agent()
            result = await self.agent.ainvoke(
                {"messages": messages},
                config=self._get_thread_config(session_id),
            )
            response = result["messages"][-1].content

        # Fix models that return raw JSON tool-calls instead of natural text
        response = self._fix_tool_call_response(response)

        self.memory.add_message(session_id, "assistant", response)
        return response

    async def chat_stream(self, message: str, session_id: str = "default") -> AsyncIterator[str]:
        """Streaming chat — yields response chunks with tool trace visibility."""
        self.memory.add_message(session_id, "user", message)

        messages = self._build_system_messages(session_id, message) + [
            HumanMessage(content=message)
        ]

        full_response = ""
        try:
            async for chunk in self.agent.astream(
                {"messages": messages},
                config=self._get_thread_config(session_id),
                stream_mode="messages",
            ):
                if isinstance(chunk, tuple):
                    msg, meta = chunk
                    if hasattr(msg, "content") and isinstance(msg.content, str):
                        if meta.get("langgraph_node") == "agent" and msg.content:
                            full_response += msg.content
                            yield msg.content
        except Exception as e:
            logger.error(f"[Agent] Stream error: {e}")
            # Fallback to non-streaming
            try:
                response = await self.chat(message, session_id)
                yield response
                return
            except Exception:
                yield "Lo siento, hubo un error procesando tu solicitud. Intenta de nuevo."
                return

        if full_response:
            self.memory.add_message(session_id, "assistant", full_response)

    def get_provider(self) -> dict:
        return self.provider_info

    def get_history(self, session_id: str) -> list[dict]:
        return self.memory.get_history(session_id)

    def clear_session(self, session_id: str):
        self.memory.clear_session(session_id)

    def rebuild(self):
        """Force LLM provider re-detection (e.g., after Ollama restart)."""
        self._build_agent()
        return self.provider_info

    def set_persona(self, name: str) -> dict:
        """Switch active persona. Returns persona info or error."""
        persona = persona_manager.set_persona(name)
        if persona:
            return {"ok": True, "persona": persona.name, "display": persona.display_name, "emoji": persona.emoji}
        return {"ok": False, "error": f"Unknown persona '{name}'", "available": [p["name"] for p in persona_manager.list_personas()]}

    def list_personas(self) -> list[dict]:
        return persona_manager.list_personas()

    def get_current_persona(self) -> dict:
        p = persona_manager.get_current()
        return {"name": p.name, "display": p.display_name, "emoji": p.emoji, "description": p.description}


# Singleton
jarvis = JarvisAgent()
