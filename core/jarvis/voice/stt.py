"""J.A.R.V.I.S. — Speech-to-Text (Faster-Whisper)"""

import io
import os
import logging
from typing import Optional
from pathlib import Path

from jarvis.config import config

logger = logging.getLogger(__name__)

WAKE_WORDS = ["jarvis", "j.a.r.v.i.s", "hey jarvis", "oye jarvis"]


class WhisperSTT:
    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(
                config.WHISPER_MODEL,
                device=config.WHISPER_DEVICE,
                compute_type=config.WHISPER_COMPUTE_TYPE,
            )
            logger.info(f"[STT] Faster-Whisper loaded: {config.WHISPER_MODEL} on {config.WHISPER_DEVICE}")
        except Exception as e:
            logger.warning(f"[STT] GPU load failed ({e}), falling back to CPU")
            try:
                from faster_whisper import WhisperModel
                self.model = WhisperModel(
                    config.WHISPER_MODEL,
                    device="cpu",
                    compute_type="int8",
                )
                logger.info("[STT] Faster-Whisper loaded on CPU")
            except Exception as e2:
                logger.error(f"[STT] Could not load Whisper: {e2}")
                self.model = None

    def transcribe_audio(self, audio_bytes: bytes, language: str = None) -> str:
        """Transcribe audio bytes to text."""
        if not self.model:
            return ""
        try:
            audio_io = io.BytesIO(audio_bytes)
            segments, info = self.model.transcribe(
                audio_io,
                language=language,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
            )
            text = " ".join(seg.text for seg in segments).strip()
            return text
        except Exception as e:
            logger.error(f"[STT] Transcription error: {e}")
            return ""

    def transcribe_file(self, file_path: str, language: str = None) -> str:
        """Transcribe audio file to text."""
        if not self.model:
            return ""
        try:
            segments, info = self.model.transcribe(
                file_path,
                language=language,
                vad_filter=True,
            )
            return " ".join(seg.text for seg in segments).strip()
        except Exception as e:
            logger.error(f"[STT] File transcription error: {e}")
            return ""

    def listen_once(self, timeout: float = 5.0) -> str:
        """Listen from microphone for one utterance."""
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=15)
            audio_bytes = audio.get_wav_data()
            return self.transcribe_audio(audio_bytes)
        except Exception as e:
            logger.error(f"[STT] Microphone error: {e}")
            return ""

    @staticmethod
    def contains_wake_word(text: str) -> bool:
        text_lower = text.lower().strip()
        return any(w in text_lower for w in WAKE_WORDS)

    @staticmethod
    def extract_command(text: str) -> str:
        """Remove wake word from start of text."""
        text_lower = text.lower()
        for w in WAKE_WORDS:
            if text_lower.startswith(w):
                return text[len(w):].strip().lstrip(",.:").strip()
        return text


# Singleton
stt = WhisperSTT()
