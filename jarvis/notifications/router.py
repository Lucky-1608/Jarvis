"""
Jarvis OS - Notification Router

Centralized routing of alerts and notifications across channels.
"""
import structlog
from typing import Literal

logger = structlog.get_logger(__name__)

class NotificationRouter:
    """Routes messages based on priority and user preferences."""
    
    async def send(self, message: str, priority: Literal["low", "medium", "high", "critical"] = "low", user_id: int | None = None):
        """
        Sends a notification. 
        In production, this checks user preferences (e.g., 'Only SMS for critical, otherwise push notification').
        """
        if priority == "critical":
            # Route to urgent channels (WhatsApp / Telegram)
            logger.info("notification.routed", channel="whatsapp", priority=priority, message=message)
            # await whatsapp_bridge.send_message(...)
        elif priority == "high":
            # Route to Web UI + Email
            logger.info("notification.routed", channel="email", priority=priority, message=message)
        else:
            # Route strictly to Web UI Notification Center
            logger.info("notification.routed", channel="web_ui", priority=priority, message=message)

notification_router = NotificationRouter()
