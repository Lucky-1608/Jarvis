"""
Jarvis OS - WhatsApp Bridge Routes
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from jarvis.events.bus import get_event_bus, Event
import structlog

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])
logger = structlog.get_logger(__name__)

class WhatsAppEventRequest(BaseModel):
    type: str = Field(..., description="The type of event (e.g., whatsapp.qr or whatsapp.status)")
    data: str | None = Field(None, description="Event data (e.g., the base64 URI or status string)")

@router.post("/event")
async def receive_whatsapp_event(request: WhatsAppEventRequest):
    """Receive an event from the WhatsApp Node.js bridge and publish to the Event Bus."""
    bus = get_event_bus()
    
    # Publish to the global event bus
    await bus.publish(Event(
        type=request.type,
        data={"payload": request.data},
        source="whatsapp_bridge"
    ))
    
    logger.info("whatsapp.event_received", event_type=request.type)
    return {"status": "ok"}
