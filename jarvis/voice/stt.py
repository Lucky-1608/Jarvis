"""
Jarvis OS — Speech-to-Text Engine.

Converts spoken audio into text.
(Local STT models have been removed/disabled per user request)
"""

from __future__ import annotations

import structlog
from pathlib import Path
from typing import Any, AsyncIterator

from jarvis.events.bus import Event, EventTypes, get_event_bus

logger = structlog.get_logger(__name__)


class SpeechToText:
    """
    Speech-to-text engine.
    (Disabled)
    """

    def __init__(self, model_size: str = "base") -> None:
        self._model_size = model_size
        self._bus = get_event_bus()

    async def transcribe_bytes(
        self,
        audio_bytes: bytes,
        language: str | None = None,
    ) -> str:
        """Disabled STT."""
        logger.warning("stt.disabled", msg="SpeechToText is disabled.")
        return ""

    async def transcribe_file(
        self,
        filepath: str | Path,
        language: str | None = None,
    ) -> str:
        """Disabled STT."""
        logger.warning("stt.disabled", msg="SpeechToText is disabled.")
        return ""

    async def transcribe_stream(
        self,
        audio_bytes: bytes,
        chunk_duration_s: float = 2.0,
        language: str | None = None,
    ) -> AsyncIterator[str]:
        """Disabled STT."""
        logger.warning("stt.disabled", msg="SpeechToText is disabled.")
        if False:
            yield ""

    async def detect_language(self, audio_bytes: bytes) -> dict[str, Any]:
        """Disabled STT."""
        logger.warning("stt.disabled", msg="SpeechToText is disabled.")
        return {
            "language": "unknown",
            "probability": 0.0,
        }
