"""
Jarvis OS — Text-to-Speech Engine.

Converts Jarvis's text responses into spoken audio.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import structlog

from jarvis.events.bus import Event, EventTypes, get_event_bus

logger = structlog.get_logger(__name__)

# Default voice
DEFAULT_VOICE = "en-US-GuyNeural"
ALTERNATIVE_VOICES = {}


class TextToSpeech:
    """
    Text-to-speech engine.
    Primary TTS is currently disabled/stubbed.
    Edge-TTS is used as the fallback.
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

    async def speak(self, text: str) -> None:
        """Speak the text, falling back to Edge-TTS."""
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
            await self._speak_primary(text)
        except Exception as exc:
            logger.warning("tts.primary_failed", error=str(exc))
            try:
                await self._speak_edge_tts(text)
            except Exception as fallback_exc:
                logger.error("tts.all_failed", error=str(fallback_exc))
        finally:
            self._is_speaking = False
            await self._bus.publish(Event(
                type=EventTypes.TTS_COMPLETED,
                data={"text": text[:100]},
                source="tts",
            ))

    async def _speak_primary(self, text: str) -> None:
        """Primary TTS implementation (currently stubbed)."""
        raise NotImplementedError("Primary TTS is not configured. Falling back.")

    async def _speak_edge_tts(self, text: str) -> None:
        """Fallback: Synthesize and play speech using Edge-TTS."""
        try:
            import edge_tts
        except ImportError:
            raise RuntimeError(
                "edge-tts is required for fallback speech synthesis. "
                "Install with: pip install edge-tts"
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

    async def synthesize_to_file(
        self,
        text: str,
        output_path: str | Path,
    ) -> Path:
        """Synthesize speech to an audio file (MP3) without playing, using Edge-TTS."""
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

    def stop(self) -> None:
        """Interrupt speech playback."""
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
        """Change speech rate."""
        self._rate = rate

    @staticmethod
    async def list_voices(language: str = "en") -> list[dict[str, str]]:
        """List available Edge-TTS voices."""
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
