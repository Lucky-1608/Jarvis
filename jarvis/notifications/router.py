"""
Jarvis OS - Notification Router

Centralized routing of alerts and notifications across channels.
"""
from typing import Literal
import asyncio
import httpx

import structlog

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
            logger.info("notification.routed", channel="whatsapp_and_telegram", priority=priority, message=message)
            
            async def send_to_bridge(url: str):
                try:
                    async with httpx.AsyncClient() as client:
                        await client.post(url, json={"message": message}, timeout=10.0)
                except Exception as e:
                    logger.error("notification.bridge_push_failed", url=url, error=str(e))
            
            # Send to both WhatsApp and Telegram
            asyncio.create_task(send_to_bridge("http://127.0.0.1:3001/send"))
            asyncio.create_task(send_to_bridge("http://127.0.0.1:3002/send"))
        elif priority == "high":
            # Route to Web UI + Email
            logger.info("notification.routed", channel="email", priority=priority, message=message)
        else:
            # Route strictly to Web UI Notification Center
            logger.info("notification.routed", channel="web_ui", priority=priority, message=message)

notification_router = NotificationRouter()

def setup_notifications():
    from jarvis.events.bus import get_event_bus, EventTypes, Event
    
    async def on_notification(event: Event):
        content = event.data.get("content", "")
        priority = event.data.get("priority", "low")
        if content:
            await notification_router.send(content, priority=priority)
            
    get_event_bus().subscribe(EventTypes.NOTIFICATION_SEND, on_notification)
