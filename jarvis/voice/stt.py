"""
Jarvis OS — Speech-to-Text Engine.

Converts spoken audio into text.
"""

from __future__ import annotations

import os
import asyncio
import structlog
from pathlib import Path
from typing import Any, AsyncIterator

from jarvis.events.bus import Event, EventTypes, get_event_bus

logger = structlog.get_logger(__name__)


class SpeechToText:
    """
    Speech-to-text engine using Azure Cognitive Services.
    """

    def __init__(self, model_size: str = "base") -> None:
        self._model_size = model_size
        self._bus = get_event_bus()

    def _get_speech_config(self, language: str | None = None) -> Any:
        import azure.cognitiveservices.speech as speechsdk
        speech_key = os.environ.get("AZURE_SPEECH_KEY")
        service_region = os.environ.get("AZURE_SPEECH_REGION")
        if not speech_key or not service_region:
            logger.error("stt.azure_missing_credentials", msg="AZURE_SPEECH_KEY or AZURE_SPEECH_REGION not set")
            raise ValueError("Missing Azure Speech credentials (AZURE_SPEECH_KEY, AZURE_SPEECH_REGION)")
        
        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
        if language:
            speech_config.speech_recognition_language = language
        return speech_config

    async def transcribe_bytes(
        self,
        audio_bytes: bytes,
        language: str | None = None,
    ) -> str:
        """Transcribe audio bytes using Azure STT."""
        try:
            import azure.cognitiveservices.speech as speechsdk
            speech_config = self._get_speech_config(language)
            
            # Note: Azure expects a specific audio format, typically 16kHz 16-bit mono.
            push_stream = speechsdk.audio.PushAudioInputStream()
            audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
            speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
            
            push_stream.write(audio_bytes)
            push_stream.close()

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, speech_recognizer.recognize_once)

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                return result.text
            elif result.reason == speechsdk.ResultReason.NoMatch:
                logger.warning("stt.nomatch", msg="No speech could be recognized.")
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                logger.error("stt.canceled", reason=cancellation_details.reason, error_details=cancellation_details.error_details)
            return ""
        except Exception as e:
            logger.error("stt.error", error=str(e))
            return ""

    async def transcribe_file(
        self,
        filepath: str | Path,
        language: str | None = None,
    ) -> str:
        """Transcribe an audio file using Azure STT."""
        try:
            import azure.cognitiveservices.speech as speechsdk
            speech_config = self._get_speech_config(language)
            audio_config = speechsdk.audio.AudioConfig(filename=str(filepath))
            speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, speech_recognizer.recognize_once)

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                return result.text
            elif result.reason == speechsdk.ResultReason.NoMatch:
                logger.warning("stt.nomatch", msg="No speech could be recognized in file.")
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                logger.error("stt.canceled", reason=cancellation_details.reason, error_details=cancellation_details.error_details)
            return ""
        except Exception as e:
            logger.error("stt.file_error", error=str(e))
            return ""

    async def transcribe_stream(
        self,
        audio_bytes: bytes,
        chunk_duration_s: float = 2.0,
        language: str | None = None,
    ) -> AsyncIterator[str]:
        """Transcribe an audio stream using Azure STT."""
        # For simplicity, falling back to transcribe_bytes for the chunk
        text = await self.transcribe_bytes(audio_bytes, language)
        if text:
            yield text

    async def detect_language(self, audio_bytes: bytes) -> dict[str, Any]:
        """
        Language detection is disabled to ensure we stay strictly within the Azure Free (F0) tier.
        Auto-language detection can incur additional costs or require standard tier capabilities.
        Defaulting to English (en-US).
        """
        return {
            "language": "en-US",
            "probability": 1.0,
        }
