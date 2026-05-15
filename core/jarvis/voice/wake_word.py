"""J.A.R.V.I.S. — Wake Word Detection

Two-tier strategy:
  1. openWakeWord (ML model, accurate) — preferred
  2. String matching fallback — always available

openWakeWord uses pre-trained ONNX models from:
  https://github.com/dscripka/openWakeWord

Supported wake words (built-in models):
  - "hey_jarvis" (custom via fine-tuning)
  - "hey_mycroft" (open source, similar energy)
  - "alexa" (repurposed)

For custom "hey jarvis" model:
  pip install openwakeword
  python -c "import openwakeword; openwakeword.utils.download_models()"
"""

import logging
import threading
from typing import Callable, Optional
import numpy as np

logger = logging.getLogger(__name__)

# ── String-match fallback (always works, no deps) ────────────────────────────
WAKE_WORDS_STRING = [
    "jarvis",
    "hey jarvis",
    "oye jarvis",
    "ok jarvis",
    "hola jarvis",
    "ey jarvis",
]


def string_match_wake_word(text: str) -> bool:
    """Fast string-based wake word check (used as fallback)."""
    t = text.lower().strip()
    return any(ww in t for ww in WAKE_WORDS_STRING)


def extract_command_from_text(text: str) -> str:
    """Remove wake word prefix from text."""
    t = text.lower().strip()
    for ww in sorted(WAKE_WORDS_STRING, key=len, reverse=True):
        if t.startswith(ww):
            return text[len(ww):].strip()
    return text.strip()


# ── openWakeWord detector ─────────────────────────────────────────────────────
class OpenWakeWordDetector:
    """
    ML-based wake word detector using openWakeWord.

    Usage:
        detector = OpenWakeWordDetector(threshold=0.5)
        if detector.available:
            detector.start(callback=on_wake)
        else:
            # use string matching via STT
            pass

    Callback signature: callback(wake_word: str)
    """

    SAMPLE_RATE = 16000
    CHUNK_SIZE = 1280  # 80ms at 16kHz — openWakeWord requirement

    # Models to load — in priority order
    # "hey_jarvis" requires fine-tuned model (see docs/train_wake_word.md)
    # Fallback to available pre-trained models
    MODEL_NAMES = [
        "hey_jarvis",   # custom trained (if available)
        "alexa",        # pre-trained, repurposed
        "hey_mycroft",  # pre-trained
    ]

    def __init__(self, threshold: float = 0.5, model_name: Optional[str] = None):
        self.threshold = threshold
        self.model_name = model_name
        self.available = False
        self._oww = None
        self._stream = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._active_model: Optional[str] = None

        self._init_model()

    def _init_model(self):
        try:
            import openwakeword
            from openwakeword.model import Model

            # Try loading in priority order
            models_to_try = [self.model_name] if self.model_name else self.MODEL_NAMES
            for model in models_to_try:
                try:
                    self._oww = Model(wakeword_models=[model], inference_framework="onnx")
                    self._active_model = model
                    self.available = True
                    logger.info(f"[WakeWord] openWakeWord loaded: {model}")
                    break
                except Exception as e:
                    logger.debug(f"[WakeWord] Model {model} unavailable: {e}")

            if not self.available:
                # Try loading default bundled models
                self._oww = Model(inference_framework="onnx")
                first_model = list(self._oww.models.keys())[0]
                self._active_model = first_model
                self.available = True
                logger.info(f"[WakeWord] openWakeWord loaded default: {first_model}")

        except ImportError:
            logger.info("[WakeWord] openWakeWord not installed — using string matching fallback")
            logger.info("[WakeWord] Install: pip install openwakeword")
        except Exception as e:
            logger.warning(f"[WakeWord] openWakeWord init failed: {e}")

    def predict_chunk(self, audio_chunk: np.ndarray) -> tuple[bool, float, str]:
        """
        Process one audio chunk.
        Returns (wake_detected, confidence, model_name)
        audio_chunk: np.ndarray of int16, shape (CHUNK_SIZE,)
        """
        if not self.available or self._oww is None:
            return False, 0.0, ""

        try:
            pred = self._oww.predict(audio_chunk)
            for model_name, score in pred.items():
                if score >= self.threshold:
                    logger.info(f"[WakeWord] Detected '{model_name}' conf={score:.3f}")
                    return True, float(score), model_name
        except Exception as e:
            logger.error(f"[WakeWord] Predict error: {e}")

        return False, 0.0, ""

    def start(self, callback: Callable[[str], None]):
        """Start continuous microphone listening in background thread."""
        if not self.available:
            logger.warning("[WakeWord] openWakeWord unavailable — cannot start")
            return False

        try:
            import pyaudio
        except ImportError:
            logger.error("[WakeWord] pyaudio not installed — pip install pyaudio")
            return False

        self._running = True
        self._callback = callback
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info(f"[WakeWord] Listening for '{self._active_model}'...")
        return True

    def _listen_loop(self):
        import pyaudio

        pa = pyaudio.PyAudio()
        stream = pa.open(
            rate=self.SAMPLE_RATE,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.CHUNK_SIZE,
        )
        logger.info("[WakeWord] Microphone stream open")

        try:
            while self._running:
                raw = stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
                chunk = np.frombuffer(raw, dtype=np.int16)
                detected, conf, model = self.predict_chunk(chunk)
                if detected:
                    self._callback(model)
        except Exception as e:
            logger.error(f"[WakeWord] Listen loop error: {e}")
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("[WakeWord] Stopped")


# ── Unified wake word API ─────────────────────────────────────────────────────
class WakeWordEngine:
    """
    Unified wake word interface.
    Tries openWakeWord first, falls back to STT + string matching.
    """

    def __init__(self, threshold: float = 0.5):
        self.oww = OpenWakeWordDetector(threshold=threshold)
        self.mode = "openwakeword" if self.oww.available else "string_match"
        logger.info(f"[WakeWord] Mode: {self.mode}")

    @property
    def is_ml_mode(self) -> bool:
        return self.mode == "openwakeword"

    def check_text(self, text: str) -> bool:
        """String-match check (used in STT-first pipeline)."""
        return string_match_wake_word(text)

    def extract_command(self, text: str) -> str:
        return extract_command_from_text(text)

    def start_always_on(self, on_wake: Callable[[str], None]) -> bool:
        """
        Start always-on ML wake word detection.
        Returns True if started successfully.
        If False, caller should use STT-first approach instead.
        """
        if self.is_ml_mode:
            return self.oww.start(on_wake)
        return False

    def stop(self):
        if self.is_ml_mode:
            self.oww.stop()


# Module-level singleton
wake_engine = WakeWordEngine()
