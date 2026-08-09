"""
Jarvis OS - Background Agents

Base class for proactive tasks that run in the background.
"""

import asyncio
from typing import Any

import structlog

from jarvis.events.bus import Event, EventBus

logger = structlog.get_logger(__name__)


class BackgroundAgent:
    """
    Base class for background polling/monitoring agents.
    
    Subclasses must implement `run_loop()`.
    """

    def __init__(self, name: str, bus: EventBus, interval_seconds: int = 60) -> None:
        self.name = name
        self._bus = bus
        self._interval = interval_seconds
        self._task: asyncio.Task | None = None
        self._running = False

    def start(self) -> None:
        """Start the agent's background task."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._main_loop())
        logger.info("background_agent.started", agent=self.name, interval=self._interval)

    def stop(self) -> None:
        """Stop the background task."""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("background_agent.stopped", agent=self.name)

    async def _main_loop(self) -> None:
        """Internal loop that calls run_loop on an interval."""
        try:
            while self._running:
                await self.run_loop()
                await asyncio.sleep(self._interval)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("background_agent.crashed", agent=self.name, error=str(e))

    async def run_loop(self) -> None:
        """
        To be implemented by subclasses.
        Called periodically based on `interval_seconds`.
        """
        raise NotImplementedError

    async def notify_hud(self, title: str, message: str, level: str = "info", data: dict[str, Any] | None = None) -> None:
        """
        Emit a notification event intended for the HUD.
        """
        payload = {
            "title": title,
            "message": message,
            "level": level,  # info, warning, error, success
        }
        if data:
            payload["data"] = data

        await self._bus.publish(Event(
            type="hud.notification",
            data=payload,
            source=self.name,
        ))
        logger.info("background_agent.notified", agent=self.name, title=title)
