"""
Jarvis OS - Monitoring Daemon

Background task for tracking system health (CPU, RAM, Disk).
"""
import asyncio

import psutil
import structlog

import datetime

logger = structlog.get_logger(__name__)

from jarvis.automation.briefing import MorningBriefingTask
from jarvis.automation.email_briefing import EmailBriefingTask
from jarvis.events.bus import Event, EventTypes, get_event_bus


def get_system_metrics() -> dict:
    """Returns current system metrics mapped to thematic labels."""
    try:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
    except Exception as exc:
        logger.warning("system_monitor.fetch_failed", error=str(exc))
        cpu, ram, disk = 0.0, 0.0, 0.0

    return {
        "brain_core": max(5, round(cpu)),
        "router": max(5, round(ram)),
        "vision_engine": 100,
        "voice_engine": 100,
        "disk": round(disk),
    }


class SystemMonitorDaemon:
    def __init__(self, interval_seconds: int = 3):
        self.interval = interval_seconds
        self._running = False
        self._task = None
        self._briefing_task = MorningBriefingTask(target_hour=8, target_minute=0)
        self._last_briefing_date = None
        self._email_briefing_task = EmailBriefingTask()
        self._last_email_briefing_time = None

    async def start(self):
        """Starts the background monitoring daemon."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("system_monitor.started", interval=self.interval)

    async def stop(self):
        """Stops the monitoring daemon."""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("system_monitor.stopped")

    async def _loop(self):
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            pass

        bus = get_event_bus()

        while self._running:
            try:
                stats = get_system_metrics()

                # Publish dynamic telemetry to EventBus for HUD WebSocket subscribers
                await bus.publish(
                    Event(
                        type=EventTypes.SYSTEM_STATS,
                        data=stats,
                        source="system_monitor",
                    )
                )

                logger.debug("system_monitor.heartbeat", **stats)

                # Check for critical thresholds
                if stats.get("brain_core", 0) > 90.0:
                    logger.warning("system_monitor.alert", resource="cpu", value=stats["brain_core"])

                # Check if it's time for Morning Briefing
                now = datetime.datetime.now()
                current_date = now.date()
                if (
                    now.hour == self._briefing_task.target_hour and 
                    now.minute >= self._briefing_task.target_minute and 
                    self._last_briefing_date != current_date
                ):
                    asyncio.create_task(self._briefing_task.execute())
                    self._last_briefing_date = current_date

                # Check if it's time for Email Briefing (every 4 hours)
                if (
                    self._last_email_briefing_time is None or 
                    (now - self._last_email_briefing_time).total_seconds() >= 4 * 3600
                ):
                    asyncio.create_task(self._email_briefing_task.execute())
                    self._last_email_briefing_time = now

            except Exception as e:
                logger.error("system_monitor.error", error=str(e))

            await asyncio.sleep(self.interval)


_monitor_instance: SystemMonitorDaemon | None = None


def get_system_monitor(interval_seconds: int = 3) -> SystemMonitorDaemon:
    """Get or create singleton SystemMonitorDaemon."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = SystemMonitorDaemon(interval_seconds=interval_seconds)
    return _monitor_instance
