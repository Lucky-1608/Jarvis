"""
Jarvis OS — Abstract AI Provider Interface.

Every AI provider (OpenCode, OpenRouter, Ollama) implements this
interface so the AI Router can swap providers transparently.
"""

from __future__ import annotations

import datetime
import email.utils
import json
import re
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any


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
    cooldown_remaining: int = 0


def parse_cooldown_duration(
    response: Any | None = None,
    error_str: str = "",
    default: int = 60,
) -> int:
    """
    Extract the cooldown duration (in seconds) from HTTP headers, error bodies,
    or exception strings across multiple providers (Groq, OpenAI, Google, etc.).
    """
    # 1. Check HTTP headers if response object is provided
    if response is not None:
        headers = getattr(response, "headers", {})
        retry_after = headers.get("retry-after") or headers.get("Retry-After")
        if retry_after:
            try:
                # May be integer or float seconds
                return max(1, int(float(retry_after)))
            except ValueError:
                # May be HTTP-date
                try:
                    dt = email.utils.parsedate_to_datetime(retry_after)
                    return max(1, int((dt - datetime.datetime.now(datetime.UTC)).total_seconds()))
                except Exception:
                    pass

        # Also inspect response text if available
        if not error_str and hasattr(response, "text"):
            try:
                error_str = response.text
            except Exception:
                pass

    text = (error_str or "").lower()

    # 2. Check JSON response structure
    if "{" in text and "}" in text:
        try:
            data = json.loads(text)
            err = data.get("error", {})
            if isinstance(err, dict):
                msg = err.get("message", "")
                if msg:
                    text = f"{text} {msg.lower()}"
                retry_in = err.get("retry_after") or err.get("retryAfter")
                if retry_in:
                    return max(1, int(float(retry_in)))
        except Exception:
            pass

    # 3. Match Groq-style "try again in Xm Ys" or "try again in Xs"
    m = re.search(r"try again in\s*(\d+)\s*m(?:in(?:ute)?s?)?\s*([0-9]+(?:\.[0-9]+)?)\s*s", text)
    if m:
        return int(float(m.group(1)) * 60 + float(m.group(2))) + 2

    m = re.search(r"try again in\s*([0-9]+(?:\.[0-9]+)?)\s*(?:s(?:ec(?:ond)?s?)?|seconds?)?", text)
    if m and m.group(1):
        return max(1, int(float(m.group(1)))) + 2

    m = re.search(r"retry(?:\s+after|\s+in)?\s*(\d+)\s*(?:s|sec|seconds)?", text)
    if m:
        return max(1, int(m.group(1))) + 2

    m = re.search(r"wait\s*(\d+)\s*(?:s|sec|seconds)?", text)
    if m:
        return max(1, int(m.group(1))) + 2

    return default


class APIKeyRotator:
    """Rotates through a list of API keys in a round-robin fashion."""

    def __init__(self, api_keys_str: str | list[str], api_key: str = ""):
        self.keys: list[str] = []
        if isinstance(api_keys_str, list):
            self.keys = [k.strip() for k in api_keys_str if k.strip()]
        elif api_keys_str:
            self.keys = [k.strip() for k in api_keys_str.split(",") if k.strip()]
        if not self.keys and api_key:
            self.keys = [api_key.strip()]
        self._index = 0

    @property
    def key_count(self) -> int:
        return len(self.keys)

    @property
    def has_multiple_keys(self) -> bool:
        return len(self.keys) > 1

    def get_key(self) -> str:
        """Returns the current key."""
        if not self.keys:
            return ""
        return self.keys[self._index % len(self.keys)]

    def rotate(self) -> str:
        """Move to the next key in the rotation and return it."""
        self._index += 1
        return self.get_key()


class AIProvider(ABC):
    """
    Abstract base class for all AI providers.

    Subclasses must implement ``chat()``, ``chat_stream()``, and
    ``health_check()``.
    """

    name: str = "base"

    def __init__(self) -> None:
        self._cooldown_until: float = 0.0

    def is_cooling_down(self) -> bool:
        """Return True if this provider is currently in a rate-limit cooldown."""
        return time.time() < self._cooldown_until

    def remaining_cooldown(self) -> int:
        """Return the remaining cooldown in seconds, or 0 if active."""
        return max(0, int(self._cooldown_until - time.time()))

    def set_cooldown(self, seconds: float) -> None:
        """Set a cooldown duration in seconds."""
        self._cooldown_until = max(self._cooldown_until, time.time() + float(seconds))

    def reset_cooldown(self) -> None:
        """Clear active cooldown."""
        self._cooldown_until = 0.0

    def handle_rate_limit(
        self,
        response: Any | None = None,
        error_str: str = "",
        key_rotator: APIKeyRotator | None = None,
    ) -> int:
        """
        Handle a rate-limit event. If key_rotator has multiple keys, rotate to the next key.
        Calculate and activate the cooldown period.
        Returns the cooldown duration in seconds.
        """
        cooldown = parse_cooldown_duration(response, error_str=error_str)
        if key_rotator and key_rotator.has_multiple_keys:
            key_rotator.rotate()
        self.set_cooldown(cooldown)
        return cooldown

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
