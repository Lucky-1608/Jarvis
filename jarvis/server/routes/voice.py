"""
Jarvis OS — Voice API Routes.

POST /api/voice/transcribe  — Upload audio and get transcription
POST /api/voice/speak       — Synthesize speech from text
GET  /api/voice/voices      — List available TTS voices
"""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

router = APIRouter()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class SpeakRequest(BaseModel):
    text: str = Field(..., description="Text to speak")
    voice: str = Field("en-US-GuyNeural", description="TTS voice name")


class TranscriptionResponse(BaseModel):
    text: str
    language: str = ""
    duration_s: float = 0.0


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/voice/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Upload an audio file and receive a text transcription.

    Accepts WAV, MP3, or raw PCM audio.
    """
    from jarvis.voice.stt import SpeechToText

    stt = SpeechToText(model_size="base")

    # Save uploaded file to temp
    content = await file.read()
    suffix = Path(file.filename or "audio.wav").suffix or ".wav"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        text = await stt.transcribe_file(tmp_path)
        return TranscriptionResponse(text=text)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/voice/speak")
async def speak_text(request: SpeakRequest):
    """
    Synthesize text to speech and return the audio as base64 MP3.
    """
    from jarvis.voice.tts import TextToSpeech

    tts = TextToSpeech(voice=request.voice)

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        await tts.synthesize_to_file(request.text, tmp_path)

        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()

        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        return {
            "audio_base64": audio_b64,
            "format": "mp3",
            "voice": request.voice,
            "size_bytes": len(audio_bytes),
        }
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.get("/voice/voices")
async def list_voices(language: str = "en"):
    """List available TTS voices for a language."""
    from jarvis.voice.tts import TextToSpeech

    voices = await TextToSpeech.list_voices(language)
    return {"language": language, "count": len(voices), "voices": voices}


@router.websocket("/voice/stream")
async def transcribe_stream(ws: WebSocket):
    """
    WebSocket endpoint for real-time transcription.
    Client sends binary audio (webm/mp4/wav) chunks.
    Server writes cumulative audio to a temp file, runs STT, and returns text.
    """
    await ws.accept()
    from jarvis.voice.stt import SpeechToText
    import structlog
    logger = structlog.get_logger(__name__)

    stt = SpeechToText(model_size="base")

    try:
        while True:
            # Receive cumulative audio payload from client
            audio_bytes = await ws.receive_bytes()
            if not audio_bytes:
                continue

            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            try:
                # Transcribe the cumulative audio file
                text = await stt.transcribe_file(tmp_path)
                await ws.send_json({"text": text, "done": False})
            except Exception as e:
                logger.error("voice.stream.error", error=str(e))
                await ws.send_json({"error": str(e)})
            finally:
                Path(tmp_path).unlink(missing_ok=True)

    except WebSocketDisconnect:
        logger.debug("voice.stream.disconnected")
    except Exception as exc:
        logger.error("voice.stream.fatal", error=str(exc))
        try:
            await ws.send_json({"error": str(exc)})
        except Exception:
            pass
