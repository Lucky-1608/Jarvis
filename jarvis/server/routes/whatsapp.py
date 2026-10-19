"""
Jarvis OS - WhatsApp Bridge Routes
"""

import os
import shutil
from pathlib import Path

import httpx
import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from jarvis.events.bus import Event, get_event_bus

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


@router.post("/reset")
async def reset_whatsapp_session():
    """Reset the WhatsApp session, delete credentials, and generate a fresh QR."""
    bus = get_event_bus()
    bridge_port = os.getenv("WHATSAPP_BRIDGE_PORT", "3002")
    bridge_url = f"http://127.0.0.1:{bridge_port}"

    # First attempt to notify bridge via HTTP
    bridge_notified = False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{bridge_url}/reset")
            if resp.status_code == 200:
                bridge_notified = True
    except Exception as e:
        logger.warning("whatsapp.bridge_reset_call_failed", error=str(e))

    # Also perform local filesystem cleanup if reachable
    auth_dir = os.getenv("WHATSAPP_AUTH_DIR")
    if not auth_dir:
        if os.getenv("WEBSITE_SITE_NAME"):
            auth_dir = "/home/site/auth_info_baileys"
        else:
            base_dir = Path(__file__).resolve().parent.parent.parent
            auth_dir = str(base_dir / "whatsapp-bridge" / "auth_info_baileys")

    if os.path.exists(auth_dir):
        try:
            shutil.rmtree(auth_dir, ignore_errors=True)
            logger.info("whatsapp.auth_dir_cleared", path=auth_dir)
        except Exception as e:
            logger.error("whatsapp.auth_dir_cleanup_error", error=str(e))

    await bus.publish(Event(
        type="whatsapp.status",
        data={"payload": "disconnected"},
        source="whatsapp_bridge"
    ))

    return {
        "status": "ok",
        "message": "WhatsApp session reset. Generating fresh QR code...",
        "bridge_notified": bridge_notified
    }


@router.post("/pairing-code")
async def request_pairing_code(payload: dict | None = None):
    """Request a pairing code to link WhatsApp by phone number instead of QR."""
    bridge_port = os.getenv("WHATSAPP_BRIDGE_PORT", "3002")
    bridge_url = f"http://127.0.0.1:{bridge_port}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{bridge_url}/pairing-code", json=payload or {})
            if resp.status_code == 200:
                return resp.json()
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("whatsapp.pairing_code_request_error", error=str(e))
        raise HTTPException(status_code=503, detail=f"WhatsApp bridge unreachable: {str(e)}")


