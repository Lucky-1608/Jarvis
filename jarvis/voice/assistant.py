"""
Jarvis OS — Voice Assistant Loop.

The complete voice interaction pipeline that ties together:
  Wake Word → STT → Brain → TTS

Spec Volume 7 Audio Pipeline:
  Microphone → Wake Word → STT → Router → Planner → Executor → TTS

This module provides the high-level ``VoiceAssistant`` class
that manages the entire conversational voice loop.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from jarvis.events.bus import Event, EventTypes, get_event_bus

logger = structlog.get_logger(__name__)


class VoiceAssistant:
    """
    Full voice assistant combining wake word, STT, Brain, and TTS.

    Modes:
    - **Wake Word Mode**: Listens for "Jarvis", then processes one command.
    - **Push-to-Talk Mode**: Records when triggered, processes, responds.
    - **Continuous Mode**: Always listening (no wake word required).
    """

    def __init__(self) -> None:
        self._bus = get_event_bus()
        self._active = False
        self._mode = "push_to_talk"  # Default mode

        # Lazy-loaded components
        self._brain = None
        self._stt = None
        self._tts = None
        self._recorder = None
        self._wake_word = None

    async def _ensure_components(self) -> None:
        """Lazily initialize all voice components."""
        if self._brain is not None:
            return

        from jarvis.brain.jarvis_brain import JarvisBrain
        from jarvis.voice.stt import SpeechToText
        from jarvis.voice.tts import TextToSpeech
        from jarvis.voice.audio import AudioRecorder

        self._brain = JarvisBrain()
        await self._brain.initialize()

        self._stt = SpeechToText(model_size="base")
        self._tts = TextToSpeech()
        self._recorder = AudioRecorder()

        logger.info("voice_assistant.initialized")

    # -- Push-to-Talk (default for CLI) -------------------------------------

    async def listen_and_respond(self) -> dict[str, Any]:
        """
        Single interaction cycle: record → transcribe → process → speak.

        Returns a dict with the transcribed text and Jarvis's response.
        """
        await self._ensure_components()

        # 1. Record audio
        logger.info("voice_assistant.listening")
        audio = await self._recorder.record_until_silence(
            silence_threshold=0.01,
            silence_duration=1.5,
            max_duration=30.0,
        )

        if not audio or len(audio) < 16000:  # Less than 1 second
            return {"text": "", "response": "", "error": "No speech detected"}

        # 2. Transcribe
        text = await self._stt.transcribe_bytes(audio)
        if not text or not text.strip():
            return {"text": "", "response": "", "error": "Could not understand audio"}

        logger.info("voice_assistant.heard", text=text)

        # 3. Process with brain
        result = await self._brain.process(text)

        # 4. Speak the response
        await self._tts.speak(result.content)

        return {
            "text": text,
            "response": result.content,
            "provider": result.provider,
            "model": result.model,
            "latency_ms": round(result.latency_ms, 1),
        }

    # -- Wake Word Mode -----------------------------------------------------

    async def start_wake_word_mode(self) -> None:
        """
        Start the full wake-word-activated voice loop.

        Listens for "Jarvis" → records command → processes → speaks → repeats.
        """
        await self._ensure_components()

        from jarvis.voice.wake_word import WakeWordDetector

        self._active = True
        self._mode = "wake_word"

        self._wake_word = WakeWordDetector()
        self._wake_word.on_wake(self._on_wake_word_detected)

        logger.info("voice_assistant.wake_word_mode_started")

        # Greeting
        await self._tts.speak("Jarvis is ready. Say 'Jarvis' to begin.")

        # Start the wake word listener (this blocks)
        await self._wake_word.start()

    async def _on_wake_word_detected(self) -> None:
        """Called when the wake word is detected."""
        logger.info("voice_assistant.wake_word_triggered")

        # Play a brief acknowledgment sound (or speak)
        await self._tts.speak("Yes?")

        # Listen for the actual command
        result = await self.listen_and_respond()

        if result.get("error"):
            await self._tts.speak("I didn't catch that. Try again.")

    # -- Continuous Mode ----------------------------------------------------

    async def start_continuous_mode(self) -> None:
        """
        Continuous conversation mode — no wake word needed.

        Keeps listening, processing, and responding until stopped.
        """
        await self._ensure_components()

        self._active = True
        self._mode = "continuous"

        logger.info("voice_assistant.continuous_mode_started")
        await self._tts.speak("Continuous mode active. I'm always listening.")

        while self._active:
            try:
                result = await self.listen_and_respond()

                if result.get("error"):
                    await asyncio.sleep(0.5)
                    continue

                # Check for stop commands
                text_lower = result.get("text", "").lower()
                if any(cmd in text_lower for cmd in ["stop listening", "exit", "quit", "goodbye"]):
                    await self._tts.speak("Goodbye.")
                    self.stop()
                    break

            except Exception as exc:
                logger.error("voice_assistant.continuous_error", error=str(exc))
                await asyncio.sleep(1.0)

    # -- Controls -----------------------------------------------------------

    def stop(self) -> None:
        """Stop the voice assistant."""
        self._active = False
        if self._wake_word:
            self._wake_word.stop()
        if self._tts:
            self._tts.stop()
        logger.info("voice_assistant.stopped")

    def interrupt(self) -> None:
        """Interrupt current speech (barge-in)."""
        if self._tts:
            self._tts.stop()

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def mode(self) -> str:
        return self._mode

    async def shutdown(self) -> None:
        """Full shutdown of voice assistant and brain."""
        self.stop()
        if self._brain:
            await self._brain.shutdown()
        logger.info("voice_assistant.shutdown_complete")
