"""
Jarvis OS — Abstract AI Provider Interface.

Every AI provider (OpenCode, OpenRouter, Ollama) implements this
interface so the AI Router can swap providers transparently.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator


@dataclass
class Message:
    """A single message in a conversation."""

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str | list[dict[str, Any]]
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


@dataclass
class ChatResponse:
    """Standardised response from any AI provider."""

    content: str
    model: str
    provider: str
    usage: dict[str, int] = field(default_factory=dict)  # prompt_tokens, completion_tokens
    finish_reason: str = "stop"
    latency_ms: float = 0.0
    tool_calls: list[dict[str, Any]] | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamChunk:
    """A single chunk from a streaming response."""

    content: str = ""
    done: bool = False
    model: str = ""
    provider: str = ""


@dataclass
class ProviderHealth:
    """Health status of a provider."""

    name: str
    available: bool
    latency_ms: float = 0.0
    error: str | None = None
    model: str = ""


class AIProvider(ABC):
    """
    Abstract base class for all AI providers.

    Subclasses must implement ``chat()``, ``chat_stream()``, and
    ``health_check()``.
    """

    name: str = "base"

    @abstractmethod
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
        """Send messages and return a complete response."""
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a response token-by-token."""
        ...

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Check whether the provider is reachable and functioning."""
        ...

    # -- Helpers -----------------------------------------------------------

    @staticmethod
    def _messages_to_dicts(messages: list[Message]) -> list[dict[str, Any]]:
        """Convert ``Message`` objects to plain dicts for API calls."""
        result = []
        for m in messages:
            d: dict[str, Any] = {"role": m.role, "content": m.content}
            if m.name:
                d["name"] = m.name
            if m.tool_calls:
                d["tool_calls"] = m.tool_calls
            if m.tool_call_id:
                d["tool_call_id"] = m.tool_call_id
            result.append(d)
        return result

    @staticmethod
    def _timer() -> float:
        """Return a high-resolution timestamp in milliseconds."""
        return time.perf_counter() * 1000
