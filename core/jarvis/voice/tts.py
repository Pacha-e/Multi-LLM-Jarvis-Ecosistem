"""J.A.R.V.I.S. — Text-to-Speech (pyttsx3 + gTTS)"""

import logging
import threading
from io import BytesIO
from jarvis.config import config

logger = logging.getLogger(__name__)


class Pyttsx3TTS:
    """Offline TTS using pyttsx3."""

    def __init__(self):
        self.engine = None
        self._lock = threading.Lock()
        self._init_engine()

    def _init_engine(self):
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", config.TTS_RATE)
            self.engine.setProperty("volume", config.TTS_VOLUME)
            # Try to set a decent voice
            voices = self.engine.getProperty("voices")
            for v in voices:
                if "spanish" in v.name.lower() or "es" in v.id.lower():
                    self.engine.setProperty("voice", v.id)
                    break
            logger.info("[TTS] pyttsx3 initialized")
        except Exception as e:
            logger.warning(f"[TTS] pyttsx3 init failed: {e}")
            self.engine = None

    def speak(self, text: str):
        if not self.engine:
            return
        with self._lock:
            self.engine.say(text)
            self.engine.runAndWait()

    def is_available(self) -> bool:
        return self.engine is not None


class GttsTTS:
    """Online TTS using Google Text-to-Speech."""

    def speak(self, text: str, lang: str = "es"):
        try:
            from gtts import gTTS
            import pygame
            tts = gTTS(text=text, lang=lang, slow=False)
            mp3_fp = BytesIO()
            tts.write_to_fp(mp3_fp)
            mp3_fp.seek(0)

            pygame.mixer.init()
            pygame.mixer.music.load(mp3_fp, "mp3")
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
        except Exception as e:
            logger.error(f"[TTS] gTTS error: {e}")

    def is_available(self) -> bool:
        try:
            import gtts
            return True
        except ImportError:
            return False


class TTSManager:
    """Manages TTS engines with fallback."""

    def __init__(self):
        self.engine_name = config.TTS_ENGINE
        self.pyttsx3 = Pyttsx3TTS()
        self.gtts = GttsTTS()

    def speak(self, text: str):
        if self.engine_name == "pyttsx3" and self.pyttsx3.is_available():
            self.pyttsx3.speak(text)
        elif self.engine_name == "gtts" and self.gtts.is_available():
            self.gtts.speak(text)
        elif self.pyttsx3.is_available():
            self.pyttsx3.speak(text)
        else:
            logger.warning(f"[TTS] No TTS engine available. Text: {text[:50]}")

    def speak_async(self, text: str):
        t = threading.Thread(target=self.speak, args=(text,), daemon=True)
        t.start()


# Singleton
tts = TTSManager()
