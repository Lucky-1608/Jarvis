"""
Jarvis OS — Google Gemini AI Provider.

Cloud fallback provider using Google's Gemini models via their
OpenAI-compatible chat completions API endpoint.
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx
import structlog

from jarvis.config.settings import get_settings
from jarvis.providers.base import (
    AIProvider,
    ChatResponse,
    Message,
    ProviderHealth,
    StreamChunk,
)

logger = structlog.get_logger(__name__)


class GeminiProvider(AIProvider):
    """Google Gemini cloud AI provider — multimodal fallback."""

    name = "gemini"

    def __init__(self) -> None:
        cfg = get_settings().gemini
        self._api_key = cfg.api_key
        self._base_url = cfg.base_url.rstrip("/")
        self._default_model = cfg.model
        self._timeout = cfg.timeout
        self._max_retries = cfg.max_retries

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

    # -- Chat (non-streaming) -----------------------------------------------

    async def chat(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> ChatResponse:
        model = model or self._default_model
        start = self._timer()

        payload: dict[str, Any] = {
            "model": model,
            "messages": self._messages_to_dicts(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
        if response_format:
            payload["response_format"] = response_format

        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(
                        f"{self._base_url}/chat/completions",
                        json=payload,
                        headers=self._headers(),
                    )
                    resp.raise_for_status()
                    data = resp.json()

                choice = data["choices"][0]
                elapsed = self._timer() - start

                return ChatResponse(
                    content=choice["message"].get("content") or "",
                    model=data.get("model", model),
                    provider=self.name,
                    usage=data.get("usage", {}),
                    finish_reason=choice.get("finish_reason", "stop"),
                    latency_ms=elapsed,
                    tool_calls=choice["message"].get("tool_calls"),
                    raw=data,
                )

            except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as exc:
                last_error = exc
                logger.warning(
                    "gemini.chat.retry",
                    attempt=attempt,
                    max_retries=self._max_retries,
                    error=str(exc),
                )
                if attempt == self._max_retries:
                    break

        raise ConnectionError(
            f"Gemini chat failed after {self._max_retries} attempts: {last_error}"
        )

    # -- Chat (streaming) ---------------------------------------------------

    async def chat_stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamChunk]:
        model = model or self._default_model

        payload = {
            "model": model,
            "messages": self._messages_to_dicts(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        yield StreamChunk(done=True, model=model, provider=self.name)
                        return

                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield StreamChunk(
                            content=content,
                            model=data.get("model", model),
                            provider=self.name,
                        )

    # -- Health check -------------------------------------------------------

    async def health_check(self) -> ProviderHealth:
        start = self._timer()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self._base_url}/models",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                elapsed = self._timer() - start
                return ProviderHealth(
                    name=self.name,
                    available=True,
                    latency_ms=elapsed,
                    model=self._default_model,
                )
        except Exception as exc:
            elapsed = self._timer() - start
            return ProviderHealth(
                name=self.name,
                available=False,
                latency_ms=elapsed,
                error=str(exc),
                model=self._default_model,
            )
