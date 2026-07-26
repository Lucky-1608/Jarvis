"""
Jarvis OS — Async Event Bus.

The nervous system of Jarvis.  Every module publishes and subscribes to
typed events so components stay decoupled.

Usage::

    from jarvis.events.bus import get_event_bus, Event

    bus = get_event_bus()

    # Subscribe
    async def on_chat(event: Event):
        print(event.data)

    bus.subscribe("chat.message", on_chat)

    # Publish
    await bus.publish(Event(type="chat.message", data={"text": "Hello"}))
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

import structlog

logger = structlog.get_logger(__name__)

# Type alias for event handler callbacks
EventHandler = Callable[["Event"], Coroutine[Any, Any, None]]


# ---------------------------------------------------------------------------
# Event data class
# ---------------------------------------------------------------------------
@dataclass
class Event:
    """A single event flowing through the bus."""

    type: str
    data: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    source: str = "system"


# ---------------------------------------------------------------------------
# Core event types used across Jarvis
# ---------------------------------------------------------------------------
class EventTypes:
    """Constants for well-known event types."""

    # Voice
    WAKE_WORD_DETECTED = "voice.wake_word"
    SPEECH_STARTED = "voice.speech_started"
    SPEECH_COMPLETED = "voice.speech_completed"
    STT_RESULT = "voice.stt_result"
    TTS_STARTED = "voice.tts_started"
    TTS_COMPLETED = "voice.tts_completed"

    # Chat
    CHAT_MESSAGE = "chat.message"
    CHAT_RESPONSE = "chat.response"
    CHAT_STREAM_CHUNK = "chat.stream_chunk"

    # Intent / routing
    INTENT_DETECTED = "router.intent_detected"
    PROVIDER_SELECTED = "router.provider_selected"

    # Planning
    PLAN_CREATED = "planner.plan_created"
    PLAN_STEP_STARTED = "planner.step_started"
    PLAN_STEP_COMPLETED = "planner.step_completed"

    # Execution
    TOOL_STARTED = "executor.tool_started"
    TOOL_COMPLETED = "executor.tool_completed"
    TOOL_FAILED = "executor.tool_failed"

    # Memory
    MEMORY_STORED = "memory.stored"
    MEMORY_RETRIEVED = "memory.retrieved"
    MEMORY_UPDATED = "memory.updated"

    # Vision
    VISION_STARTED = "vision.started"
    VISION_COMPLETED = "vision.completed"

    # System
    SYSTEM_READY = "system.ready"
    SYSTEM_ERROR = "system.error"
    SYSTEM_SHUTDOWN = "system.shutdown"
    HEALTH_CHECK = "system.health_check"


# ---------------------------------------------------------------------------
# Event Bus
# ---------------------------------------------------------------------------
class EventBus:
    """
    Async publish/subscribe event bus.

    Supports:
    - Typed event subscriptions
    - Wildcard listeners (subscribe to ``"*"`` for all events)
    - Event history (last N events for debugging)
    """

    def __init__(self, history_size: int = 200) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: list[Event] = []
        self._history_size = history_size
        self._lock = asyncio.Lock()

    # -- Subscribe / Unsubscribe --------------------------------------------

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register *handler* for events of *event_type* (or ``"*"`` for all)."""
        self._handlers[event_type].append(handler)
        logger.debug("event_bus.subscribe", event_type=event_type, handler=handler.__name__)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove *handler* from *event_type*."""
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)
            logger.debug("event_bus.unsubscribe", event_type=event_type, handler=handler.__name__)

    # -- Publish ------------------------------------------------------------

    async def publish(self, event: Event) -> None:
        """
        Dispatch *event* to all matching handlers **and** wildcard listeners.

        Handlers run concurrently via ``asyncio.gather``.
        """
        async with self._lock:
            self._history.append(event)
            if len(self._history) > self._history_size:
                self._history = self._history[-self._history_size :]

        # Collect specific + wildcard handlers
        handlers = list(self._handlers.get(event.type, []))
        handlers.extend(self._handlers.get("*", []))

        if not handlers:
            return

        logger.debug(
            "event_bus.publish",
            event_type=event.type,
            event_id=event.id,
            handler_count=len(handlers),
        )

        # Fire all handlers concurrently; isolate failures
        results = await asyncio.gather(
            *(h(event) for h in handlers),
            return_exceptions=True,
        )
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "event_bus.handler_error",
                    event_type=event.type,
                    handler=handlers[i].__name__,
                    error=str(result),
                )

    # -- Emit (sync convenience) -------------------------------------------

    def emit(self, event_type: str, data: dict[str, Any] | None = None, source: str = "system"):
        """
        Fire-and-forget helper for sync code.

        Schedules ``publish`` on the running event loop.
        """
        event = Event(type=event_type, data=data or {}, source=source)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.publish(event))
        except RuntimeError:
            # No running loop — skip silently (e.g. during import or tests)
            pass

    # -- Query history ------------------------------------------------------

    def get_history(self, event_type: str | None = None, limit: int = 50) -> list[Event]:
        """Return recent events, optionally filtered by *event_type*."""
        events = self._history
        if event_type:
            events = [e for e in events if e.type == event_type]
        return events[-limit:]

    def clear_history(self) -> None:
        """Wipe the event history."""
        self._history.clear()


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------
_bus_instance: EventBus | None = None


def get_event_bus() -> EventBus:
    """Return the global ``EventBus`` singleton."""
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = EventBus()
    return _bus_instance
