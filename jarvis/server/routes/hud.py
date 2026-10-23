import asyncio

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from jarvis.events.bus import EventTypes, get_event_bus

router = APIRouter(prefix="/hud", tags=["HUD"])
logger = structlog.get_logger(__name__)

@router.websocket("/ws")
async def hud_websocket(websocket: WebSocket):
    await websocket.accept()
    bus = get_event_bus()

    # Create a unique subscriber ID for this websocket
    subscriber_id = f"hud_ws_{id(websocket)}"
    queue = asyncio.Queue()

    # Subscribe to relevant HUD events
    # Including notifications and system readiness
    async def _queue_event(event):
        await queue.put(event)

    bus.subscribe("hud.notification", _queue_event)
    bus.subscribe(EventTypes.SYSTEM_READY, _queue_event)
    bus.subscribe(EventTypes.SYSTEM_STATS, _queue_event)
    bus.subscribe(EventTypes.VISION_STARTED, _queue_event)
    bus.subscribe(EventTypes.VISION_COMPLETED, _queue_event)
    bus.subscribe(EventTypes.TTS_STARTED, _queue_event)
    bus.subscribe(EventTypes.TTS_COMPLETED, _queue_event)
    bus.subscribe("whatsapp.qr", _queue_event)
    bus.subscribe("whatsapp.pairing_code", _queue_event)
    bus.subscribe("whatsapp.status", _queue_event)
    bus.subscribe("telegram.status", _queue_event)

    logger.info("hud.websocket_connected", id=subscriber_id)

    # Immediately push current system stats on connect
    from jarvis.monitoring.daemon import get_system_metrics
    await websocket.send_json({
        "type": EventTypes.SYSTEM_STATS,
        "data": get_system_metrics(),
        "source": "system_monitor"
    })

    # Replay the last known status for bridges so the UI isn't stuck on "Offline"
    for event_type in ["telegram.status", "whatsapp.status"]:
        history = bus.get_history(event_type=event_type, limit=1)
        if history:
            await queue.put(history[0])

    # Only replay QR or pairing code if WhatsApp is not already connected
    wa_status = bus.get_history(event_type="whatsapp.status", limit=1)
    is_wa_connected = wa_status and wa_status[0].data.get("payload") == "connected"

    if not is_wa_connected:
        qr_history = bus.get_history(event_type="whatsapp.qr", limit=1)
        if qr_history:
            await queue.put(qr_history[0])
        pair_history = bus.get_history(event_type="whatsapp.pairing_code", limit=1)
        if pair_history:
            await queue.put(pair_history[0])

    try:
        while True:
            # Wait for an event to be pushed to the queue
            event = await queue.get()

            # Send the event data as JSON to the HUD frontend
            payload = {
                "type": event.type,
                "data": event.data,
                "source": event.source
            }
            if event.type == EventTypes.TTS_STARTED:
                payload["type"] = "tts"
                payload["text"] = event.data.get("text", "")

            await websocket.send_json(payload)
            queue.task_done()
    except WebSocketDisconnect:
        logger.info("hud.websocket_disconnected", id=subscriber_id)
    except asyncio.CancelledError:
        logger.info("hud.websocket_cancelled", id=subscriber_id)
    except Exception as e:
        logger.error("hud.websocket_error", error=str(e))
    finally:
        bus.unsubscribe("hud.notification", _queue_event)
        bus.unsubscribe(EventTypes.SYSTEM_READY, _queue_event)
        bus.unsubscribe(EventTypes.SYSTEM_STATS, _queue_event)
        bus.unsubscribe(EventTypes.VISION_STARTED, _queue_event)
        bus.unsubscribe(EventTypes.VISION_COMPLETED, _queue_event)
        bus.unsubscribe(EventTypes.TTS_STARTED, _queue_event)
        bus.unsubscribe(EventTypes.TTS_COMPLETED, _queue_event)
        bus.unsubscribe("whatsapp.qr", _queue_event)
        bus.unsubscribe("whatsapp.pairing_code", _queue_event)
        bus.unsubscribe("whatsapp.status", _queue_event)
        bus.unsubscribe("telegram.status", _queue_event)
