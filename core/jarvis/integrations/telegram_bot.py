"""J.A.R.V.I.S. — Telegram Bot Integration

Gives you full JARVIS access from your phone 24/7.

Setup:
  1. Create bot via @BotFather → get TELEGRAM_BOT_TOKEN
  2. Get your chat ID via @userinfobot → TELEGRAM_ALLOWED_USERS
  3. Set in jarvis.env:
       TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
       TELEGRAM_ALLOWED_USERS=123456789  (comma-separated for multiple)

Features:
  - /start — greeting + status
  - /status — provider, memory count, uptime
  - /clear — clear session memory
  - /voice <url> — transcribe audio URL (future)
  - Any text → JARVIS response (streaming)
  - Voice messages → STT → JARVIS → text response
  - Photo → describe image (future, needs vision model)

Usage:
    python -m jarvis.integrations.telegram_bot
    # Or via run.py with TELEGRAM_BOT_TOKEN set
"""

import asyncio
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

START_TIME = time.time()


def _uptime() -> str:
    secs = int(time.time() - START_TIME)
    h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
    return f"{h}h {m}m {s}s"


def get_allowed_users() -> set[int]:
    raw = os.getenv("TELEGRAM_ALLOWED_USERS", "")
    if not raw:
        return set()
    return {int(u.strip()) for u in raw.split(",") if u.strip().isdigit()}


class JarvisTelegramBot:
    """
    Telegram bot wrapper around JarvisAgent.
    Uses python-telegram-bot v20+ (async).
    """

    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.allowed_users = get_allowed_users()
        self._app = None
        self._agent = None

    def _get_agent(self):
        """Lazy-load agent to avoid circular imports."""
        if self._agent is None:
            from jarvis.agent.core import jarvis
            self._agent = jarvis
        return self._agent

    def _check_auth(self, user_id: int) -> bool:
        if not self.allowed_users:
            return True  # No restriction set — allow all (not recommended)
        return user_id in self.allowed_users

    def _session_id(self, user_id: int) -> str:
        return f"telegram_{user_id}"

    async def cmd_start(self, update, context):
        user = update.effective_user
        if not self._check_auth(user.id):
            await update.message.reply_text("🔒 Acceso no autorizado.")
            return

        agent = self._get_agent()
        provider = agent.get_provider()
        pname = provider.get("provider", "unknown")

        text = (
            f"⚡ *J.A.R.V.I.S. Online*\n\n"
            f"Hola {user.first_name}. Sistemas operativos.\n\n"
            f"🧠 LLM: `{pname}`\n"
            f"⏱ Uptime: `{_uptime()}`\n\n"
            f"Envía cualquier mensaje para chatear.\n"
            f"Comandos: /status /clear /help"
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_status(self, update, context):
        if not self._check_auth(update.effective_user.id):
            return

        agent = self._get_agent()
        provider = agent.get_provider()
        session_id = self._session_id(update.effective_user.id)
        history = agent.get_history(session_id)

        text = (
            f"📊 *Estado J.A.R.V.I.S.*\n\n"
            f"🤖 Proveedor: `{provider.get('provider', 'none')}`\n"
            f"📝 Mensajes sesión: `{len(history)}`\n"
            f"⏱ Uptime: `{_uptime()}`\n"
        )

        # Ollama health
        try:
            from jarvis.agent.llm_router import check_ollama_health
            ollama_ok = check_ollama_health()
            text += f"🟢 Ollama: `{'online' if ollama_ok else 'offline'}`\n"
        except Exception:
            pass

        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_clear(self, update, context):
        if not self._check_auth(update.effective_user.id):
            return

        agent = self._get_agent()
        session_id = self._session_id(update.effective_user.id)
        agent.clear_session(session_id)
        await update.message.reply_text("🗑 Sesión limpiada. ¿En qué puedo ayudarte?")

    async def cmd_help(self, update, context):
        if not self._check_auth(update.effective_user.id):
            return

        text = (
            "⚡ *J.A.R.V.I.S. Comandos*\n\n"
            "/start — Saludo e info\n"
            "/status — Estado del sistema\n"
            "/clear — Limpiar memoria de sesión\n"
            "/help — Esta ayuda\n\n"
            "_Envía cualquier texto para chatear._\n"
            "_Envía un audio para transcripción automática._"
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    async def handle_message(self, update, context):
        """Handle text messages with streaming response."""
        user = update.effective_user
        if not self._check_auth(user.id):
            await update.message.reply_text("🔒 Acceso no autorizado.")
            return

        text = update.message.text
        if not text:
            return

        session_id = self._session_id(user.id)
        agent = self._get_agent()

        # Send typing indicator
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )

        try:
            # Collect streaming response
            response_parts = []
            async for chunk in agent.chat_stream(text, session_id=session_id):
                response_parts.append(chunk)

            response = "".join(response_parts).strip()
            if not response:
                response = "No obtuve respuesta del modelo. Intenta de nuevo."

            # Telegram message limit is 4096 chars
            if len(response) > 4096:
                # Split into chunks
                for i in range(0, len(response), 4096):
                    await update.message.reply_text(response[i:i+4096])
            else:
                await update.message.reply_text(response)

        except Exception as e:
            logger.error(f"[Telegram] Message handler error: {e}")
            await update.message.reply_text(
                f"⚠️ Error procesando tu mensaje: {str(e)[:200]}"
            )

    async def handle_voice(self, update, context):
        """Handle voice messages — download, transcribe, chat."""
        user = update.effective_user
        if not self._check_auth(user.id):
            return

        try:
            import tempfile
            from jarvis.voice.stt import WhisperSTT

            # Download voice file
            voice_file = await context.bot.get_file(update.message.voice.file_id)
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
                tmp_path = f.name

            await voice_file.download_to_drive(tmp_path)

            # Transcribe
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action="typing"
            )
            stt = WhisperSTT()
            transcription = stt.transcribe(tmp_path)

            if not transcription:
                await update.message.reply_text("❓ No pude transcribir el audio.")
                return

            # Echo transcription
            await update.message.reply_text(f"🎤 _\"{transcription}\"_", parse_mode="Markdown")

            # Process as text
            fake_msg = update.message
            update.message._text = transcription
            await self.handle_message(update, context)

        except Exception as e:
            logger.error(f"[Telegram] Voice handler error: {e}")
            await update.message.reply_text(f"⚠️ Error con el audio: {str(e)[:200]}")
        finally:
            try:
                import os
                os.unlink(tmp_path)
            except Exception:
                pass

    def build_app(self):
        """Build the Telegram Application."""
        try:
            from telegram.ext import (
                Application, CommandHandler, MessageHandler, filters
            )
        except ImportError:
            raise ImportError(
                "python-telegram-bot not installed.\n"
                "pip install python-telegram-bot"
            )

        if not self.token:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN not set.\n"
                "Get one from @BotFather on Telegram."
            )

        app = Application.builder().token(self.token).build()

        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("status", self.cmd_status))
        app.add_handler(CommandHandler("clear", self.cmd_clear))
        app.add_handler(CommandHandler("help", self.cmd_help))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(MessageHandler(filters.VOICE, self.handle_voice))

        self._app = app
        return app

    def run(self):
        """Run bot with polling (blocking)."""
        logger.info("[Telegram] Starting J.A.R.V.I.S. Telegram bot...")
        app = self.build_app()

        if not self.allowed_users:
            logger.warning(
                "[Telegram] TELEGRAM_ALLOWED_USERS not set — bot accessible to anyone!"
            )
        else:
            logger.info(f"[Telegram] Authorized users: {self.allowed_users}")

        app.run_polling(drop_pending_updates=True)

    async def run_async(self):
        """Run bot alongside FastAPI (non-blocking)."""
        app = self.build_app()
        async with app:
            await app.start()
            await app.updater.start_polling(drop_pending_updates=True)
            logger.info("[Telegram] Bot running (async mode)")
            # Keep running until stopped
            await asyncio.Event().wait()


def start_telegram_bot():
    """Entry point for standalone bot."""
    logging.basicConfig(level=logging.INFO)
    bot = JarvisTelegramBot()
    bot.run()


if __name__ == "__main__":
    start_telegram_bot()
