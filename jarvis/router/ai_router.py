"""
Jarvis OS — AI Router.

Selects the best AI provider for each request, handles fallback,
tracks latency, and provides a unified interface to the brain.

Routing strategy (from spec Volume 5):
  - Simple deterministic → Python (no LLM needed)
  - Complex reasoning   → OpenCode (primary) / Cloud fallback
  - Vision              → NVIDIA NIM (Phase 2)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import structlog

from jarvis.config.settings import get_settings
from jarvis.events.bus import Event, EventTypes, get_event_bus
from jarvis.providers.base import (
    AIProvider,
    ChatResponse,
    Message,
    ProviderHealth,
    StreamChunk,
)
from jarvis.providers.gemini import GeminiProvider
from jarvis.providers.grok import GrokProvider
from jarvis.providers.nvidia import NvidiaNimProvider
from jarvis.providers.ollama_cloud import OllamaCloudProvider
from jarvis.providers.opencode import OpenCodeProvider

logger = structlog.get_logger(__name__)

# Map of provider name → class
PROVIDER_REGISTRY: dict[str, type[AIProvider]] = {
    "opencode": OpenCodeProvider,
    "ollama_cloud": OllamaCloudProvider,
    "nvidia": NvidiaNimProvider,
    "grok": GrokProvider,
    "gemini": GeminiProvider,
}


class AIRouter:
    """
    Intelligent AI model router.

    Responsibilities:
    - Select the right provider based on task complexity
    - Automatic fallback when the primary provider fails
    - Track latency and usage metrics
    - Provide a unified ``chat()`` / ``chat_stream()`` interface
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._primary_name = settings.ai_primary_provider

        # Handle multiple fallback providers separated by comma
        fallback_str = getattr(settings, 'ai_fallback_providers', getattr(settings, 'ai_fallback_provider', ''))
        self._fallback_names = [n.strip() for n in fallback_str.split(',') if n.strip()]

        self._providers: dict[str, AIProvider] = {}
        self._metrics: dict[str, list[float]] = {}  # provider → latency samples
        self._bus = get_event_bus()

        # Eagerly instantiate configured providers
        names_to_load = set([self._primary_name] + self._fallback_names)
        for name in names_to_load:
            if name in PROVIDER_REGISTRY:
                self._providers[name] = PROVIDER_REGISTRY[name]()
                self._metrics[name] = []

        logger.info(
            "ai_router.init",
            primary=self._primary_name,
            fallbacks=self._fallback_names,
            providers=list(self._providers.keys()),
        )

    # -- Provider access ----------------------------------------------------

    def get_provider(self, name: str) -> AIProvider | None:
        """Return a specific provider by name, or ``None``."""
        if name not in self._providers and name in PROVIDER_REGISTRY:
            self._providers[name] = PROVIDER_REGISTRY[name]()
            self._metrics[name] = []
        return self._providers.get(name)

    @property
    def primary(self) -> AIProvider:
        """Return the primary provider."""
        provider = self.get_provider(self._primary_name)
        if provider is None:
            raise RuntimeError(f"Primary provider '{self._primary_name}' not available")
        return provider

    @property
    def fallbacks(self) -> list[AIProvider]:
        """Return the list of fallback providers."""
        return [self.get_provider(name) for name in self._fallback_names if self.get_provider(name) is not None]

    @property
    def fallback(self) -> AIProvider | None:
        """Return the first fallback provider (for backwards compatibility)."""
        fallbacks = self.fallbacks
        return fallbacks[0] if fallbacks else None

    # -- Unified chat interface --------------------------------------------

    async def chat(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        provider: str | None = None,
    ) -> ChatResponse:
        """
        Send a chat request to the best available provider.

        Tries the primary provider first; on failure, falls back
        to the configured fallback.
        """
        target_provider = self.get_provider(provider) if provider else None
        providers_to_try = (
            [target_provider]
            if target_provider
            else [self.primary] + self.fallbacks
        )

        last_error: Exception | None = None
        for prov in providers_to_try:
            if prov is None:
                continue
            try:
                await self._bus.publish(Event(
                    type=EventTypes.PROVIDER_SELECTED,
                    data={"provider": prov.name, "model": model or "default"},
                    source="ai_router",
                ))

                response = await prov.chat(
                    messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                    response_format=response_format,
                )

                # Track metrics
                self._metrics.setdefault(prov.name, []).append(response.latency_ms)
                if len(self._metrics[prov.name]) > 100:
                    self._metrics[prov.name] = self._metrics[prov.name][-100:]

                logger.info(
                    "ai_router.chat.success",
                    provider=prov.name,
                    model=response.model,
                    latency_ms=round(response.latency_ms, 1),
                    tokens=response.usage,
                )
                return response

            except Exception as exc:
                last_error = exc
                logger.warning(
                    "ai_router.chat.failed",
                    provider=prov.name,
                    error=str(exc),
                )

        raise ConnectionError(
            f"All AI providers failed. Last error: {last_error}"
        )

    async def chat_stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        provider: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream a response from the best available provider.

        Falls back to the secondary provider on failure.
        """
        target_provider = self.get_provider(provider) if provider else None
        providers_to_try = (
            [target_provider]
            if target_provider
            else [self.primary] + self.fallbacks
        )

        last_error: Exception | None = None
        for prov in providers_to_try:
            if prov is None:
                continue
            try:
                await self._bus.publish(Event(
                    type=EventTypes.PROVIDER_SELECTED,
                    data={"provider": prov.name, "model": model or "default", "streaming": True},
                    source="ai_router",
                ))

                async for chunk in prov.chat_stream(
                    messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    yield chunk
                return  # Success — exit the fallback loop

            except Exception as exc:
                last_error = exc
                logger.warning(
                    "ai_router.stream.failed",
                    provider=prov.name,
                    error=str(exc),
                )

        raise ConnectionError(
            f"All AI providers failed for streaming. Last error: {last_error}"
        )

    # -- Health / metrics ---------------------------------------------------

    async def health_check(self) -> dict[str, ProviderHealth]:
        """Check health of all registered providers."""
        import asyncio
        from jarvis.providers.base import ProviderHealth

        results = {}
        names = list(self._providers.keys())
        
        async def _check(name: str):
            try:
                # Add a 5-second timeout per provider
                return await asyncio.wait_for(self._providers[name].health_check(), timeout=5.0)
            except Exception as e:
                return ProviderHealth(name=name, available=False, latency_ms=0, error=str(e))

        tasks = [_check(name) for name in names]
        health_results = await asyncio.gather(*tasks)

        for name, res in zip(names, health_results):
            results[name] = res
        return results

    def get_metrics(self) -> dict[str, dict[str, Any]]:
        """Return latency metrics for all providers."""
        out = {}
        for name, samples in self._metrics.items():
            if samples:
                out[name] = {
                    "count": len(samples),
                    "avg_ms": round(sum(samples) / len(samples), 1),
                    "min_ms": round(min(samples), 1),
                    "max_ms": round(max(samples), 1),
                    "last_ms": round(samples[-1], 1),
                }
            else:
                out[name] = {"count": 0}
        return out
