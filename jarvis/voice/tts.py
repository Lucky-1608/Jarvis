"""
Jarvis OS — Text-to-Speech Engine.

Converts Jarvis's text responses into spoken audio.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import httpx
import structlog

from jarvis.config.settings import get_settings
from jarvis.events.bus import Event, EventTypes, get_event_bus
from jarvis.providers.base import APIKeyRotator

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
        self._settings = get_settings()
        self._elevenlabs_rotator = APIKeyRotator(
            self._settings.elevenlabs.api_keys,
            self._settings.elevenlabs.api_key
        )

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
        """Primary TTS implementation based on configured provider."""
        provider = self._settings.tts_provider
        if provider == "elevenlabs":
            await self._speak_elevenlabs(text)
        elif provider == "edge_tts":
            await self._speak_edge_tts(text)
        else:
            raise ValueError(f"Unknown TTS provider: {provider}")

    async def _speak_elevenlabs(self, text: str) -> None:
        """ElevenLabs TTS implementation."""
        api_key = self._elevenlabs_rotator.get_key()
        if not api_key:
            raise ValueError("ElevenLabs API key not configured.")

        voice_id = getattr(self, "_voice_id", None) or self._settings.elevenlabs.voice_id
        url = f"{self._settings.elevenlabs.base_url.rstrip('/')}/v1/text-to-speech/{voice_id}"

        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "text": text,
            "model_id": self._settings.elevenlabs.model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            async with httpx.AsyncClient(timeout=self._settings.elevenlabs.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                with open(tmp_path, "wb") as f:
                    f.write(response.content)

            if self._stop_requested:
                return

            from jarvis.voice.audio import AudioPlayer
            await AudioPlayer.play_file(tmp_path)
            logger.debug("tts.elevenlabs_done", text_preview=text[:50])

        finally:
            Path(tmp_path).unlink(missing_ok=True)


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
        """Synthesize speech to an audio file (MP3) without playing."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            provider = self._settings.tts_provider
            if provider == "elevenlabs":
                return await self._synthesize_elevenlabs_to_file(text, output_path)
            elif provider == "edge_tts":
                return await self._synthesize_edge_tts_to_file(text, output_path)
            else:
                raise ValueError(f"Unknown TTS provider: {provider}")
        except httpx.HTTPStatusError as exc:
            logger.warning("tts.synthesize_primary_failed", error=str(exc), response=exc.response.text)
            return await self._synthesize_edge_tts_to_file(text, output_path)
        except Exception as exc:
            logger.warning("tts.synthesize_primary_failed", error=str(exc))
            return await self._synthesize_edge_tts_to_file(text, output_path)

    async def _synthesize_elevenlabs_to_file(self, text: str, output_path: Path) -> Path:
        """Synthesize using ElevenLabs."""
        api_key = self._elevenlabs_rotator.get_key()
        if not api_key:
            raise ValueError("ElevenLabs API key not configured.")

        voice_id = getattr(self, "_voice_id", None) or self._settings.elevenlabs.voice_id
        url = f"{self._settings.elevenlabs.base_url.rstrip('/')}/v1/text-to-speech/{voice_id}"

        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "text": text,
            "model_id": self._settings.elevenlabs.model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        async with httpx.AsyncClient(timeout=self._settings.elevenlabs.timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(response.content)

        logger.info("tts.synthesized_elevenlabs_to_file", path=str(output_path))
        return output_path


    async def _synthesize_edge_tts_to_file(
        self,
        text: str,
        output_path: Path,
    ) -> Path:
        """Fallback: Synthesize speech to an audio file using Edge-TTS."""
        try:
            import edge_tts
        except ImportError:
            raise RuntimeError("edge-tts is required for speech synthesis.")

        communicate = edge_tts.Communicate(
            text,
            voice=self._voice,
            rate=self._rate,
            volume=self._volume,
        )
        await communicate.save(str(output_path))

        logger.info("tts.synthesized_edge_tts_to_file", path=str(output_path))
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
