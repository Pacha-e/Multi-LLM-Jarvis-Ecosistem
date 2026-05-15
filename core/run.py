#!/usr/bin/env python3
"""J.A.R.V.I.S. — Entry Point

Starts:
  - FastAPI server (always)
  - Telegram bot (if TELEGRAM_BOT_TOKEN set in jarvis.env)
  - openWakeWord listener (if openwakeword installed + microphone available)
"""

import asyncio
import os
import sys
import logging

import uvicorn
from jarvis.config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BANNER = r"""
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
  Just A Rather Very Intelligent System v2.0
  Personal AI Ecosystem — github.com/Pacha-e
"""


async def run_fastapi():
    """Run FastAPI + WebSocket server."""
    cfg = uvicorn.Config(
        "jarvis.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
        log_level="warning",  # Reduce noise
    )
    server = uvicorn.Server(cfg)
    await server.serve()


async def run_telegram():
    """Run Telegram bot if configured."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.info("[Telegram] Not configured (TELEGRAM_BOT_TOKEN not set)")
        return

    try:
        from jarvis.integrations.telegram_bot import JarvisTelegramBot
        bot = JarvisTelegramBot()
        logger.info("[Telegram] Starting bot...")
        await bot.run_async()
    except ImportError:
        logger.warning("[Telegram] python-telegram-bot not installed — pip install python-telegram-bot")
    except Exception as e:
        logger.error(f"[Telegram] Bot error: {e}")


async def index_knowledge_base():
    """Index Obsidian vault if configured."""
    vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "")
    if not vault_path:
        return

    try:
        from jarvis.agent.rag import get_rag, index_obsidian_vault
        rag = get_rag()
        count = index_obsidian_vault(rag, vault_path)
        logger.info(f"[RAG] Obsidian vault indexed: {count} chunks")
    except Exception as e:
        logger.warning(f"[RAG] Vault indexing failed: {e}")


async def main():
    try:
        print(BANNER)
    except UnicodeEncodeError:
        print("\n  J.A.R.V.I.S. v2.0 — Personal AI Ecosystem\n")
    print(f"  Web UI:  http://{config.HOST}:{config.PORT}")
    print(f"  Docs:    http://{config.HOST}:{config.PORT}/docs")

    # Show active features
    features = []
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        features.append("Telegram")
    if os.getenv("OBSIDIAN_VAULT_PATH"):
        features.append("RAG/Obsidian")
    if os.getenv("GROQ_API_KEY"):
        features.append("Groq")
    if os.getenv("ANTHROPIC_API_KEY"):
        features.append("Anthropic")

    if features:
        print(f"  Active:  {' | '.join(features)}")
    print()

    # Index knowledge base before starting (non-blocking)
    asyncio.create_task(index_knowledge_base())

    # Run all services concurrently
    tasks = [run_fastapi()]

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if telegram_token:
        tasks.append(run_telegram())

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
