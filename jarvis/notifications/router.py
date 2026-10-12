"""
Jarvis OS - Notification Router

Centralized routing of alerts and notifications across channels.
"""
import asyncio
import os
from typing import Literal

import httpx
import structlog

logger = structlog.get_logger(__name__)

class NotificationRouter:
    """Routes messages based on priority and user preferences."""

    async def send(
        self,
        message: str,
        priority: Literal["low", "medium", "high", "critical"] = "low",
        user_id: int | None = None,
    ):
        """Sends a notification based on user preferences and priority."""
        # Send native push notification to Companion Apps for high or critical alerts
        if priority in ("high", "critical"):
            try:
                from jarvis.server.companion_manager import companion_manager
                if companion_manager.has_companions():
                    asyncio.create_task(
                        companion_manager.broadcast_command(
                            action="show_notification",
                            params={
                                "title": f"Jarvis Alert ({priority.upper()})",
                                "message": message,
                            },
                        )
                    )
            except Exception as e:
                logger.error("notification.companion_push_failed", error=str(e))

        if priority == "critical":
            # Route to urgent channels (WhatsApp / Telegram)
            logger.info(
                "notification.routed",
                channel="whatsapp_and_telegram",
                priority=priority,
                message=message,
            )

            async def send_to_bridge(candidate_urls: list[str]):
                last_err = None
                async with httpx.AsyncClient(timeout=10.0) as client:
                    for url in candidate_urls:
                        try:
                            resp = await client.post(url, json={"message": message})
                            if resp.status_code == 200:
                                return
                            last_err = f"Status {resp.status_code}: {resp.text}"
                        except Exception as e:
                            last_err = str(e)
                logger.error("notification.bridge_push_failed", urls=candidate_urls, error=last_err)

            wa_port = os.getenv("WHATSAPP_BRIDGE_PORT", "3002")
            tg_port = os.getenv("TELEGRAM_BRIDGE_PORT", "3003")
            wa_custom = os.getenv("WHATSAPP_BRIDGE_URL")
            tg_custom = os.getenv("TELEGRAM_BRIDGE_URL")

            wa_urls = [wa_custom] if wa_custom else [
                f"http://127.0.0.1:{wa_port}/send",
                f"http://localhost:{wa_port}/send",
                f"http://0.0.0.0:{wa_port}/send",
            ]
            tg_urls = [tg_custom] if tg_custom else [
                f"http://127.0.0.1:{tg_port}/send",
                f"http://localhost:{tg_port}/send",
                f"http://0.0.0.0:{tg_port}/send",
            ]

            # Send to both WhatsApp and Telegram
            asyncio.create_task(send_to_bridge(wa_urls))
            asyncio.create_task(send_to_bridge(tg_urls))
        elif priority == "high":
            # Route to Web UI + Email
            logger.info("notification.routed", channel="email", priority=priority, message=message)
        else:
            # Route strictly to Web UI Notification Center
            logger.info("notification.routed", channel="web_ui", priority=priority, message=message)

notification_router = NotificationRouter()

def setup_notifications():
    from jarvis.events.bus import Event, EventTypes, get_event_bus

    async def on_notification(event: Event):
        content = event.data.get("content", "")
        priority = event.data.get("priority", "low")
        if content:
            await notification_router.send(content, priority=priority)

    get_event_bus().subscribe(EventTypes.NOTIFICATION_SEND, on_notification)
