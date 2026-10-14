"""
Jarvis OS — Voice API Routes.

POST /api/voice/transcribe  — Upload audio and get transcription
POST /api/voice/speak       — Synthesize speech from text
GET  /api/voice/voices      — List available TTS voices
"""

from __future__ import annotations

import asyncio
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

    try:
        voices = await TextToSpeech.list_voices(language)
    except Exception:
        voices = []

    if not voices:
        voices = [
            {"name": "en-US-GuyNeural", "gender": "Male", "locale": "en-US"},
            {"name": "en-US-JennyNeural", "gender": "Female", "locale": "en-US"},
            {"name": "en-US-AriaNeural", "gender": "Female", "locale": "en-US"},
            {"name": "en-US-DavisNeural", "gender": "Male", "locale": "en-US"},
            {"name": "en-US-AndrewNeural", "gender": "Male", "locale": "en-US"},
            {"name": "en-US-BrianNeural", "gender": "Male", "locale": "en-US"},
            {"name": "en-GB-RyanNeural", "gender": "Male", "locale": "en-GB"},
            {"name": "en-GB-SoniaNeural", "gender": "Female", "locale": "en-GB"},
        ]
    return {"language": language, "count": len(voices), "voices": voices}


@router.websocket("/voice/stream")
async def transcribe_stream(ws: WebSocket):
    """
    WebSocket endpoint for real-time transcription.
    Client sends binary audio (webm/mp4/wav) chunks.
    Server processes with ultra-fast STT and streams transcription text back.
    """
    await ws.accept()
    import json

    import structlog

    from jarvis.voice.stt import SpeechToText
    logger = structlog.get_logger(__name__)

    stt = SpeechToText(model_size="base")

    try:
        while True:
            # Receive either binary audio bytes or text command
            message = await ws.receive()
            if message.get("type") == "websocket.disconnect":
                break

            audio_bytes = message.get("bytes")
            text_data = message.get("text")

            if text_data:
                try:
                    payload = json.loads(text_data)
                    action = payload.get("action")
                    if action == "ping":
                        await ws.send_json({"type": "pong"})
                        continue
                except Exception:
                    pass

            if not audio_bytes or len(audio_bytes) < 100:
                continue

            try:
                # Transcribe audio bytes directly (using Groq Whisper turbo or Azure)
                text = await stt.transcribe_bytes(audio_bytes, filename="audio.webm")
                await ws.send_json({"text": text, "done": False, "interim": True})
            except WebSocketDisconnect:
                raise
            except RuntimeError as e:
                if "close message has been sent" in str(e):
                    raise WebSocketDisconnect()
                logger.error("voice.stream.error", error=str(e))
                try:
                    await ws.send_json({"error": str(e), "text": ""})
                except Exception:
                    pass
            except Exception as e:
                logger.error("voice.stream.error", error=str(e))
                try:
                    await ws.send_json({"error": str(e), "text": ""})
                except Exception:
                    pass

    except WebSocketDisconnect:
        logger.debug("voice.stream.disconnected")
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        logger.error("voice.stream.fatal", error=str(exc))

@router.websocket("/voice/tts_stream")
async def tts_stream(ws: WebSocket):
    """
    WebSocket endpoint for real-time TTS streaming.
    Client sends text sentences. Server streams back base64 audio chunks.
    """
    await ws.accept()
    import structlog

    from jarvis.voice.tts import TextToSpeech

    logger = structlog.get_logger(__name__)
    tts = TextToSpeech(voice="en-US-GuyNeural")

    try:
        while True:
            data = await ws.receive_json()
            text = data.get("text", "")
            if not text:
                continue

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name

            try:
                # In a true streaming TTS (like ElevenLabs or Azure), we would yield chunks.
                # Here we synthesize the sentence chunk and return it.
                await tts.synthesize_to_file(text, tmp_path)

                with open(tmp_path, "rb") as f:
                    audio_bytes = f.read()

                audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                await ws.send_json({"audio_base64": audio_b64, "text": text})
            except WebSocketDisconnect:
                raise
            except RuntimeError as e:
                if "close message has been sent" in str(e):
                    raise WebSocketDisconnect()
                logger.error("voice.tts_stream.error", error=str(e))
                try:
                    await ws.send_json({"error": str(e)})
                except Exception:
                    pass
            except Exception as e:
                logger.error("voice.tts_stream.error", error=str(e))
                try:
                    await ws.send_json({"error": str(e)})
                except Exception:
                    pass
            finally:
                Path(tmp_path).unlink(missing_ok=True)

    except WebSocketDisconnect:
        logger.debug("voice.tts_stream.disconnected")
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        logger.error("voice.tts_stream.fatal", error=str(exc))
        try:
            await ws.send_json({"error": str(exc)})
        except Exception:
            pass

