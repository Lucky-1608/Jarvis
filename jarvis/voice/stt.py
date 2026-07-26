"""
Jarvis OS — Speech-to-Text Engine.

Converts spoken audio into text using faster-whisper.

Spec Volume 7:
  Primary: faster-whisper
  Requirements: Streaming transcription, language detection, partial results
"""

from __future__ import annotations

import io
import tempfile
import wave
from pathlib import Path
from typing import Any, AsyncIterator

import structlog

from jarvis.events.bus import Event, EventTypes, get_event_bus
from jarvis.voice.audio import SAMPLE_RATE, SAMPLE_WIDTH, pcm_to_wav

logger = structlog.get_logger(__name__)

# Lazy-loaded model instance
_whisper_model = None


def _get_whisper_model(model_size: str = "base"):
    """Lazily load the faster-whisper model."""
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel

            logger.info("stt.loading_model", model=model_size)
            _whisper_model = WhisperModel(
                model_size,
                device="cpu",       # Use "cuda" if GPU available
                compute_type="int8",  # Fast on CPU
            )
            logger.info("stt.model_loaded", model=model_size)
        except ImportError:
            raise RuntimeError(
                "faster-whisper is required for speech recognition. "
                "Install with: pip install 'jarvis-os[voice]'"
            )
    return _whisper_model


class SpeechToText:
    """
    Speech-to-text engine using faster-whisper.

    Supports:
    - Full transcription from audio bytes or files
    - Language detection
    - Partial / streaming results (via chunked processing)
    """

    def __init__(self, model_size: str = "base") -> None:
        self._model_size = model_size
        self._bus = get_event_bus()

    async def transcribe_bytes(
        self,
        audio_bytes: bytes,
        language: str | None = None,
    ) -> str:
        """
        Transcribe raw PCM audio bytes to text.

        Expects 16kHz, mono, 16-bit PCM.
        """
        if not audio_bytes:
            return ""

        # Convert PCM to WAV (faster-whisper needs a file-like object)
        wav_bytes = pcm_to_wav(audio_bytes)

        # Write to temp file (faster-whisper reads from file path)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_bytes)
            tmp_path = tmp.name

        try:
            text = await self.transcribe_file(tmp_path, language=language)
            return text
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def transcribe_file(
        self,
        filepath: str | Path,
        language: str | None = None,
    ) -> str:
        """Transcribe an audio file (WAV, MP3, etc.) to text."""
        filepath = str(filepath)
        model = _get_whisper_model(self._model_size)

        logger.debug("stt.transcribing", file=filepath)

        await self._bus.publish(Event(
            type=EventTypes.SPEECH_STARTED,
            data={"file": filepath},
            source="stt",
        ))

        # Run transcription (CPU-bound, run in executor)
        import asyncio
        loop = asyncio.get_event_loop()
        segments, info = await loop.run_in_executor(
            None,
            lambda: model.transcribe(
                filepath,
                language=language,
                beam_size=5,
                vad_filter=True,  # Filter out silence
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200,
                ),
            ),
        )

        # Collect all segments into full text
        texts = []
        for segment in segments:
            texts.append(segment.text.strip())

        full_text = " ".join(texts).strip()

        await self._bus.publish(Event(
            type=EventTypes.STT_RESULT,
            data={
                "text": full_text,
                "language": info.language if hasattr(info, "language") else "unknown",
                "language_probability": (
                    round(info.language_probability, 3)
                    if hasattr(info, "language_probability")
                    else 0.0
                ),
                "duration_s": round(info.duration, 2) if hasattr(info, "duration") else 0.0,
            },
            source="stt",
        ))

        logger.info(
            "stt.transcribed",
            text_preview=full_text[:80],
            language=getattr(info, "language", "unknown"),
            duration_s=round(getattr(info, "duration", 0), 2),
        )
        return full_text

    async def transcribe_stream(
        self,
        audio_bytes: bytes,
        chunk_duration_s: float = 2.0,
        language: str | None = None,
    ) -> AsyncIterator[str]:
        """
        Stream partial transcription results from audio.

        Splits audio into chunks and transcribes each, yielding
        intermediate results for real-time display.
        """
        bytes_per_chunk = int(SAMPLE_RATE * SAMPLE_WIDTH * chunk_duration_s)
        offset = 0

        while offset < len(audio_bytes):
            chunk = audio_bytes[offset : offset + bytes_per_chunk]
            offset += bytes_per_chunk

            if len(chunk) < SAMPLE_RATE:  # Skip very short chunks
                continue

            text = await self.transcribe_bytes(chunk, language=language)
            if text:
                yield text

    async def detect_language(self, audio_bytes: bytes) -> dict[str, Any]:
        """Detect the spoken language from audio."""
        wav_bytes = pcm_to_wav(audio_bytes[:SAMPLE_RATE * SAMPLE_WIDTH * 5])  # First 5 seconds

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_bytes)
            tmp_path = tmp.name

        try:
            model = _get_whisper_model(self._model_size)

            import asyncio
            loop = asyncio.get_event_loop()
            _, info = await loop.run_in_executor(
                None,
                lambda: model.transcribe(tmp_path, beam_size=1),
            )

            return {
                "language": getattr(info, "language", "unknown"),
                "probability": round(getattr(info, "language_probability", 0), 3),
            }
        finally:
            Path(tmp_path).unlink(missing_ok=True)
