"""
Jarvis OS — Wake Word Detection.

Always-on, low-CPU listener that waits for the wake word "Jarvis"
before activating the voice pipeline.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Coroutine
from typing import Any

import structlog

from jarvis.events.bus import Event, EventTypes, get_event_bus

logger = structlog.get_logger(__name__)


class WakeWordDetector:
    """
    Detects the wake word "Jarvis" from a continuous audio stream.
    
    Uses a simple keyword-spotting approach with faster-whisper:
    continuously transcribes small audio chunks and checks for
    the wake word. This is CPU-efficient because we use the
    smallest Whisper model (tiny) for detection only.
    """

    WAKE_WORDS = {"jarvis", "hey jarvis", "ok jarvis", "hello jarvis"}

    def __init__(
        self,
        wake_words: set[str] | None = None,
        cooldown_seconds: float = 2.0,
    ) -> None:
        self._wake_words = wake_words or self.WAKE_WORDS
        self._cooldown = cooldown_seconds
        self._last_trigger = 0.0
        self._active = False
        self._bus = get_event_bus()
        self._on_wake: Callable[[], Coroutine[Any, Any, None]] | None = None

    def on_wake(self, callback: Callable[[], Coroutine[Any, Any, None]]) -> None:
        """Register an async callback to invoke when the wake word is detected."""
        self._on_wake = callback

    async def start(self) -> None:
        """
        Start listening for the wake word.

        This runs in a loop, capturing short audio segments and
        checking for the wake word using a lightweight STT model.
        """
        self._active = True
        logger.info("wake_word.listening", wake_words=list(self._wake_words))

        try:
            from jarvis.voice.stt import SpeechToText
            from jarvis.voice.audio import AudioRecorder, SAMPLE_RATE
        except ImportError as exc:
            logger.error("wake_word.missing_deps", error=str(exc))
            return

        # Use the smallest/fastest model for wake word detection
        stt = SpeechToText(model_size="tiny")
        recorder = AudioRecorder(sample_rate=SAMPLE_RATE)

        while self._active:
            try:
                # Record a short clip (1-3 seconds)
                audio = await recorder.record_until_silence(
                    silence_threshold=0.005,
                    silence_duration=0.8,
                    max_duration=3.0,
                )

                if not audio or len(audio) < SAMPLE_RATE:  # Less than 1 second
                    await asyncio.sleep(0.1)
                    continue

                # Transcribe with tiny model
                text = await stt.transcribe_bytes(audio)
                text_lower = text.strip().lower()

                if not text_lower:
                    continue

                # Check for wake word
                for wake_word in self._wake_words:
                    if wake_word in text_lower:
                        now = time.time()
                        if now - self._last_trigger < self._cooldown:
                            logger.debug("wake_word.cooldown")
                            break

                        self._last_trigger = now
                        logger.info("wake_word.detected", text=text_lower)

                        await self._bus.publish(Event(
                            type=EventTypes.WAKE_WORD_DETECTED,
                            data={"text": text_lower, "wake_word": wake_word},
                            source="wake_word",
                        ))

                        if self._on_wake:
                            await self._on_wake()

                        break

            except Exception as exc:
                logger.error("wake_word.error", error=str(exc))
                await asyncio.sleep(1.0)

    def stop(self) -> None:
        """Stop the wake word listener."""
        self._active = False
        logger.info("wake_word.stopped")

    @property
    def is_active(self) -> bool:
        return self._active
