"""
Jarvis OS — Chat API Routes.

POST /api/chat          — Send a message, get a full response
WS   /api/chat/stream   — Streaming chat via WebSocket
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from jarvis.server.auth import authenticate_websocket
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
    except ConnectionError as e:
        # All AI providers failed (rate-limit, timeout, network)
        error_str = str(e).lower()
        if "rate" in error_str or "cooldown" in error_str or "429" in error_str:
            raise HTTPException(
                status_code=429,
                detail="All AI providers are currently rate-limited. Please wait a moment and try again.",
            )
        elif "timeout" in error_str:
            raise HTTPException(
                status_code=504,
                detail="AI provider request timed out. The service may be overloaded — please try again.",
            )
        else:
            raise HTTPException(
                status_code=502,
                detail=f"Could not reach any AI provider. Check your network and provider configuration. ({e})",
            )
    except RuntimeError as e:
        error_str = str(e)
        if "not available" in error_str:
            raise HTTPException(
                status_code=503,
                detail=f"No AI provider is configured. Please add a valid provider and API key in your .env file. ({e})",
            )
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {e}",
        )
    except Exception as e:
        error_str = str(e).lower()
        if "api" in error_str and ("key" in error_str or "auth" in error_str or "401" in error_str or "403" in error_str):
            raise HTTPException(
                status_code=401,
                detail="AI provider authentication failed. Please check your API key in the .env file.",
            )
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while processing your request: {e}",
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
    if not await authenticate_websocket(ws):
        return
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
