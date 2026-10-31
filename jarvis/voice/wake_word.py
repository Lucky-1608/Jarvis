"""
Jarvis OS — Wake Word Detection.

Always-on, low-CPU listener that waits for the wake word "Jarvis"
before activating the voice pipeline.
"""

# pyright: reportMissingImports=false
from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Callable, Coroutine
from typing import Any

import structlog

logger: Any = structlog.get_logger(__name__)

from jarvis.events.bus import Event, EventTypes, get_event_bus


class WakeWordDetector:
    """
    Detects the wake word "Jarvis" from an audio stream.

    Uses an energy-gated acoustic buffer to detect human speech,
    then transcribes the speech segment using the configured STT engine
    (e.g. Azure Cognitive Services, Groq) to check for wake words.
    """

    WAKE_WORDS = {"jarvis", "hey jarvis", "hi jarvis", "ok jarvis", "okay jarvis", "hello jarvis"}

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
        self._on_wake: Callable[..., Any] | None = None
        self._recorder: Any | None = None
        self._subscribed_external = False

    def on_wake(self, callback: Callable[..., Any]) -> None:
        """Register an async or sync callback to invoke when the wake word is detected."""
        self._on_wake = callback

    def _activate_pc_window(self) -> None:
        """Bring Jarvis window to the foreground on the PC."""
        import sys

        # 1. Forward to connected PC companion if running in backend/server mode
        try:
            from jarvis.server.companion_manager import companion_manager
            if companion_manager.has_companions():
                asyncio.create_task(
                    companion_manager.broadcast_command(
                        "show_window",
                        {},
                        target_device="pc",
                    )
                )
        except Exception:
            pass

        # 2. If running locally on Windows PC, directly restore and focus the window
        if sys.platform == "win32":
            try:
                import pygetwindow as gw  # type: ignore[import-not-found,import-untyped]
                for title in ["Jarvis Companion OS", "Jarvis"]:
                    wins = gw.getWindowsWithTitle(title)
                    if wins:
                        w = wins[0]
                        if w.isMinimized:
                            w.restore()
                        w.activate()
                        break
            except Exception:
                pass

    async def _dispatch_wake_callback(self, text: str = "") -> None:
        """Safely invoke registered callback with or without arguments, async or sync."""
        if not self._on_wake:
            return

        import inspect
        try:
            sig = inspect.signature(self._on_wake)
            accepts_args = len(sig.parameters) > 0
            if inspect.iscoroutinefunction(self._on_wake):
                if accepts_args:
                    await self._on_wake(text)
                else:
                    await self._on_wake()
            else:
                if accepts_args:
                    self._on_wake(text)
                else:
                    self._on_wake()
        except Exception as exc:
            logger.error("wake_word.callback_error", error=str(exc))

    async def start(self) -> None:
        """
        Start listening for the wake word.

        This runs in a loop, capturing short audio segments and
        checking for the wake word using the configured STT model.
        """
        self._active = True
        logger.info("wake_word.listening", wake_words=list(self._wake_words))

        # Subscribe to external companion wake word events (e.g. from mobile or desktop companion WebSocket)
        if not self._subscribed_external:
            async def _handle_external_wake(event: Event) -> None:
                if event.source == "wake_word":
                    return  # Ignore events published by ourselves
                logger.info("wake_word.external_detected", source=event.source, data=event.data)
                self._activate_pc_window()
                event_text = str(event.data.get("text", "") or event.data.get("wake_word", ""))
                await self._dispatch_wake_callback(event_text)

            self._bus.subscribe(EventTypes.WAKE_WORD_DETECTED, _handle_external_wake)
            self._subscribed_external = True

        try:
            from jarvis.voice.audio import SAMPLE_RATE, AudioRecorder
            from jarvis.voice.stt import SpeechToText
        except ImportError as exc:
            logger.error("wake_word.missing_deps", error=str(exc))
            self._active = False
            return

        # Check for microphone availability before entering loop
        try:
            import sounddevice as sd  # type: ignore[import-not-found,import-untyped]
            devices = sd.query_devices()
            has_input = any(d.get("max_input_channels", 0) > 0 for d in devices)
            if not has_input:
                logger.warning("wake_word.no_input_devices", details="No microphone found on system. Wake word listener paused.")
                # Keep active so external companion events still trigger, but skip local recording loop
                while self._active:
                    await asyncio.sleep(2.0)
                return
        except Exception as e:
            logger.warning("wake_word.device_query_error", error=str(e))

        stt = SpeechToText()
        self._recorder = AudioRecorder(sample_rate=SAMPLE_RATE)
        consecutive_errors = 0

        while self._active:
            try:
                # Capture audio when speech above energy threshold is detected
                audio = await self._recorder.record_speech_segment(
                    energy_threshold=0.02,
                    silence_duration=0.6,
                    max_duration=3.2,
                    listen_timeout=1.8,
                )

                consecutive_errors = 0  # Reset error count on successful capture

                if not audio or len(audio) < SAMPLE_RATE * 0.5:
                    await asyncio.sleep(0.05)
                    continue

                # Transcribe speech with configured STT engine (e.g. Azure, Groq)
                text = await stt.transcribe_bytes(audio)

                text_lower = text.strip().lower()

                if not text_lower:
                    continue

                # Check for wake word (strip punctuation for robust matching)
                text_clean = re.sub(r"[^\w\s]", " ", text_lower)
                for wake_word in self._wake_words:
                    if wake_word in text_lower or wake_word in text_clean:
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

                        # Unminimize/show window on PC
                        self._activate_pc_window()

                        # Dispatch registered callback
                        await self._dispatch_wake_callback(text_lower)

                        break

            except Exception as exc:
                consecutive_errors += 1
                backoff = min(1.0 * (2 ** (consecutive_errors - 1)), 10.0)
                logger.error("wake_word.error", error=str(exc), retry_in_seconds=backoff)
                await asyncio.sleep(backoff)

    def stop(self) -> None:
        """Stop the wake word listener."""
        self._active = False
        if self._recorder:
            try:
                self._recorder.stop()
            except Exception:
                pass
        logger.info("wake_word.stopped")

    @property
    def is_active(self) -> bool:
        return self._active
