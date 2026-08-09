"""
Jarvis OS — Wake Word Detection.

Always-on listener that waits for the wake word "Jarvis".
(Local Wake Word model has been removed/disabled per user request)
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

import structlog

from jarvis.events.bus import get_event_bus

logger = structlog.get_logger(__name__)


class WakeWordDetector:
    """
    Detects the wake word "Jarvis" from a continuous audio stream.
    (Disabled)
    """

    WAKE_WORDS = {"jarvis", "hey jarvis", "ok jarvis", "hello jarvis"}

    def __init__(
        self,
        wake_words: set[str] | None = None,
        cooldown_seconds: float = 2.0,
    ) -> None:
        self._wake_words = wake_words or self.WAKE_WORDS
        self._cooldown = cooldown_seconds
        self._active = False
        self._bus = get_event_bus()
        self._on_wake: Callable[[], Coroutine[Any, Any, None]] | None = None

    def on_wake(self, callback: Callable[[], Coroutine[Any, Any, None]]) -> None:
        """Register an async callback to invoke when the wake word is detected."""
        self._on_wake = callback

    async def start(self) -> None:
        """Disabled Wake Word Detection."""
        self._active = True
        logger.warning("wake_word.disabled", msg="Wake Word detection is disabled.")

        import asyncio
        while self._active:
            await asyncio.sleep(1.0)

    def stop(self) -> None:
        """Stop the wake word listener."""
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active
