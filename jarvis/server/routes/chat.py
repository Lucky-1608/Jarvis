"""
Jarvis OS — Chat API Routes.

POST /api/chat          — Send a message, get a full response
WS   /api/chat/stream   — Streaming chat via WebSocket
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from jarvis.server.dependencies import get_brain

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to Jarvis")
    stream: bool = Field(False, description="Whether to stream the response")


class ChatResponse(BaseModel):
    content: str
    provider: str = ""
    model: str = ""
    latency_ms: float = 0.0
    plan: dict | None = None
    tool_results: list[dict] = []


# ---------------------------------------------------------------------------
# REST endpoint
# ---------------------------------------------------------------------------
@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message to Jarvis and receive a response."""
    brain = get_brain()
    try:
        result = await brain.process(request.message)
        return ChatResponse(
            content=result.content,
            provider=result.provider,
            model=result.model,
            latency_ms=round(result.latency_ms, 1),
            plan=result.plan,
            tool_results=result.tool_results,
        )
    except Exception as e:
        # Fallback for demo purposes if no API key is configured
        return ChatResponse(
            content=f"I am JARVIS. (Demo Mode: {str(e)}) Please configure a valid API key in .env to enable my AI capabilities.",
            provider="demo_fallback",
            model="offline",
            latency_ms=0.0
        )


# ---------------------------------------------------------------------------
# WebSocket streaming endpoint
# ---------------------------------------------------------------------------
@router.websocket("/chat/stream")
async def chat_stream(ws: WebSocket):
    """
    Streaming chat via WebSocket.

    Client sends: ``{"message": "..."}``
    Server streams: ``{"chunk": "...", "done": false}`` per token,
                    ``{"chunk": "", "done": true}`` at end.
    """
    await ws.accept()
    brain = get_brain()

    try:
        while True:
            data = await ws.receive_text()
            payload = json.loads(data)
            message = payload.get("message", "")

            if not message:
                await ws.send_json({"error": "No message provided"})
                continue

            async for chunk in brain.process_stream(message):
                await ws.send_json({
                    "chunk": chunk.content,
                    "done": chunk.done,
                    "provider": chunk.provider,
                    "model": chunk.model,
                })

    except WebSocketDisconnect:
        pass
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        try:
            await ws.send_json({"error": str(exc)})
        except Exception:
            pass
