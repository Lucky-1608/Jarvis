"""
Jarvis OS — Ollama Cloud AI Provider.

Connects to a remote Ollama Cloud instance.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
import structlog

from jarvis.config.settings import get_settings
from jarvis.providers.base import (
    AIProvider,
    APIKeyRotator,
    ChatResponse,
    Message,
    ProviderHealth,
    StreamChunk,
)

logger = structlog.get_logger(__name__)


class OllamaCloudProvider(AIProvider):
    """Ollama Cloud AI provider."""

    name = "ollama_cloud"

    def __init__(self) -> None:
        cfg = get_settings().ollama_cloud
        self._base_url = cfg.base_url.rstrip("/")
        self._default_model = cfg.model
        self._key_rotator = APIKeyRotator(cfg.api_keys, getattr(cfg, "api_key", ""))
        self._timeout = cfg.timeout
        self._max_retries = cfg.max_retries

    def _get_headers(self) -> dict[str, str]:
        headers = {}
        key = self._key_rotator.get_key()
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

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
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if tools:
            payload["tools"] = tools

        if response_format:
            payload["format"] = "json"

        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout, headers=self._get_headers()) as client:
                    resp = await client.post(
                        f"{self._base_url}/api/chat",
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                elapsed = self._timer() - start
                message = data.get("message", {})

                return ChatResponse(
                    content=message.get("content") or "",
                    model=data.get("model", model),
                    provider=self.name,
                    usage={
                        "prompt_tokens": data.get("prompt_eval_count", 0),
                        "completion_tokens": data.get("eval_count", 0),
                    },
                    finish_reason="stop" if data.get("done") else "length",
                    latency_ms=elapsed,
                    tool_calls=message.get("tool_calls"),
                    raw=data,
                )

            except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as exc:
                last_error = exc
                logger.warning(
                    "ollama_cloud.chat.retry",
                    attempt=attempt,
                    max_retries=self._max_retries,
                    error=str(exc),
                )
                if attempt == self._max_retries:
                    break

        raise ConnectionError(
            f"Ollama Cloud chat failed after {self._max_retries} attempts: {last_error}"
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
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=self._timeout, headers=self._get_headers()) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/api/chat",
                json=payload,
            ) as resp:
                resp.raise_for_status()
                import json

                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    message = data.get("message", {})
                    content = message.get("content", "")
                    done = data.get("done", False)

                    if content:
                        yield StreamChunk(
                            content=content,
                            model=data.get("model", model),
                            provider=self.name,
                        )

                    if done:
                        yield StreamChunk(done=True, model=model, provider=self.name)
                        return

    # -- Health check -------------------------------------------------------

    async def health_check(self) -> ProviderHealth:
        start = self._timer()
        try:
            async with httpx.AsyncClient(timeout=5, headers=self._get_headers()) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                elapsed = self._timer() - start
                return ProviderHealth(
                    name=self.name,
                    available=True,
                    latency_ms=elapsed,
                    model=", ".join(models[:5]) if models else self._default_model,
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
