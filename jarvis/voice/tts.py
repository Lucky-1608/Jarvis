"""
Jarvis OS — Text-to-Speech Engine.

Converts Jarvis's text responses into spoken audio.

Spec Volume 7:
  Primary: Edge-TTS
  Fallback: pyttsx3
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any

import structlog

from jarvis.events.bus import Event, EventTypes, get_event_bus

logger = structlog.get_logger(__name__)

# Default voice — Microsoft's high-quality neural voices
DEFAULT_VOICE = "en-US-GuyNeural"  # Male, professional
ALTERNATIVE_VOICES = {
    "male": "en-US-GuyNeural",
    "female": "en-US-JennyNeural",
    "british_male": "en-GB-RyanNeural",
    "british_female": "en-GB-SoniaNeural",
    "indian_male": "en-IN-PrabhatNeural",
    "indian_female": "en-IN-NeerjaNeural",
}


class TextToSpeech:
    """
    Text-to-speech engine with Edge-TTS (primary) and pyttsx3 (fallback).

    Edge-TTS provides high-quality neural voices for free via
    Microsoft's Edge browser TTS service. Falls back to pyttsx3
    for offline operation.
    """

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        rate: str = "+0%",
        volume: str = "+0%",
    ) -> None:
        self._voice = voice
        self._rate = rate
        self._volume = volume
        self._bus = get_event_bus()
        self._is_speaking = False
        self._stop_requested = False

    # -- Edge-TTS (primary) -------------------------------------------------

    async def speak(self, text: str) -> None:
        """
        Speak the given text aloud using Edge-TTS.

        Falls back to pyttsx3 if Edge-TTS is unavailable.
        """
        if not text or not text.strip():
            return

        self._is_speaking = True
        self._stop_requested = False

        await self._bus.publish(Event(
            type=EventTypes.TTS_STARTED,
            data={"text": text[:100], "voice": self._voice},
            source="tts",
        ))

        try:
            await self._speak_edge_tts(text)
        except Exception as exc:
            logger.warning("tts.edge_tts_failed", error=str(exc))
            try:
                await self._speak_pyttsx3(text)
            except Exception as fallback_exc:
                logger.error("tts.all_failed", error=str(fallback_exc))
        finally:
            self._is_speaking = False
            await self._bus.publish(Event(
                type=EventTypes.TTS_COMPLETED,
                data={"text": text[:100]},
                source="tts",
            ))

    async def _speak_edge_tts(self, text: str) -> None:
        """Synthesize and play speech using Edge-TTS."""
        try:
            import edge_tts
        except ImportError:
            raise RuntimeError(
                "edge-tts is required for speech synthesis. "
                "Install with: pip install 'jarvis-os[voice]'"
            )

        # Create a temp file for the audio
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            communicate = edge_tts.Communicate(
                text,
                voice=self._voice,
                rate=self._rate,
                volume=self._volume,
            )
            await communicate.save(tmp_path)

            if self._stop_requested:
                return

            # Play the audio
            from jarvis.voice.audio import AudioPlayer
            await AudioPlayer.play_file(tmp_path)

        finally:
            Path(tmp_path).unlink(missing_ok=True)

        logger.debug("tts.edge_tts_done", text_preview=text[:50])

    async def _speak_pyttsx3(self, text: str) -> None:
        """Fallback: speak using pyttsx3 (offline, lower quality)."""
        try:
            import pyttsx3
        except ImportError:
            raise RuntimeError("pyttsx3 is not installed for offline TTS fallback.")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._pyttsx3_sync, text)

    @staticmethod
    def _pyttsx3_sync(text: str) -> None:
        """Synchronous pyttsx3 speech (runs in thread pool)."""
        import pyttsx3

        engine = pyttsx3.init()
        engine.setProperty("rate", 175)
        engine.setProperty("volume", 0.9)

        # Try to set a good voice
        voices = engine.getProperty("voices")
        for voice in voices:
            if "david" in voice.name.lower() or "mark" in voice.name.lower():
                engine.setProperty("voice", voice.id)
                break

        engine.say(text)
        engine.runAndWait()

    # -- Synthesis to file --------------------------------------------------

    async def synthesize_to_file(
        self,
        text: str,
        output_path: str | Path,
    ) -> Path:
        """Synthesize speech to an audio file (MP3) without playing."""
        try:
            import edge_tts
        except ImportError:
            raise RuntimeError("edge-tts is required for speech synthesis.")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        communicate = edge_tts.Communicate(
            text,
            voice=self._voice,
            rate=self._rate,
            volume=self._volume,
        )
        await communicate.save(str(output_path))

        logger.info("tts.synthesized_to_file", path=str(output_path))
        return output_path

    # -- Controls -----------------------------------------------------------

    def stop(self) -> None:
        """Interrupt speech playback (barge-in support)."""
        self._stop_requested = True
        self._is_speaking = False
        logger.debug("tts.interrupted")

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    def set_voice(self, voice: str) -> None:
        """Change the TTS voice."""
        self._voice = voice
        logger.info("tts.voice_changed", voice=voice)

    def set_rate(self, rate: str) -> None:
        """Change speech rate (e.g., '+10%', '-20%')."""
        self._rate = rate

    @staticmethod
    async def list_voices(language: str = "en") -> list[dict[str, str]]:
        """List available Edge-TTS voices for a language."""
        try:
            import edge_tts
            voices = await edge_tts.list_voices()
            return [
                {
                    "name": v["ShortName"],
                    "gender": v["Gender"],
                    "locale": v["Locale"],
                }
                for v in voices
                if v["Locale"].startswith(language)
            ]
        except ImportError:
            return []
