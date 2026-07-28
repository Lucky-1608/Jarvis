"""
Jarvis OS - Telegram Bridge Routes
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from jarvis.events.bus import get_event_bus, Event
import structlog

router = APIRouter(prefix="/telegram", tags=["Telegram"])
logger = structlog.get_logger(__name__)

class TelegramEventRequest(BaseModel):
    type: str = Field(..., description="The type of event (e.g., telegram.status)")
    data: str | None = Field(None, description="Event data (e.g., status string)")

@router.post("/event")
async def receive_telegram_event(request: TelegramEventRequest):
    """Receive an event from the Telegram Node.js bridge and publish to the Event Bus."""
    bus = get_event_bus()
    
    # Publish to the global event bus
    await bus.publish(Event(
        type=request.type,
        data={"payload": request.data},
        source="telegram_bridge"
    ))
    
    logger.info("telegram.event_received", event_type=request.type)
    return {"status": "ok"}
