"""
Jarvis OS - Monitoring Daemon

Background task for tracking system health (CPU, RAM, Disk).
"""
import asyncio
import psutil
import structlog

logger = structlog.get_logger(__name__)

class SystemMonitorDaemon:
    def __init__(self, interval_seconds: int = 60):
        self.interval = interval_seconds
        self._running = False
        self._task = None

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
        while self._running:
            try:
                cpu = psutil.cpu_percent(interval=1)
                ram = psutil.virtual_memory().percent
                disk = psutil.disk_usage('/').percent
                
                # In a real app, this would be published to an EventBus or WebSocket
                logger.debug("system_monitor.heartbeat", cpu=cpu, ram=ram, disk=disk)
                
                # Check for critical thresholds
                if cpu > 90.0:
                    logger.warning("system_monitor.alert", resource="cpu", value=cpu)
                    
            except Exception as e:
                logger.error("system_monitor.error", error=str(e))
                
            await asyncio.sleep(self.interval)
