from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
from jarvis.events.bus import get_event_bus, EventTypes
import structlog

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
    
    logger.info("hud.websocket_connected", id=subscriber_id)
    
    try:
        while True:
            # Wait for an event to be pushed to the queue
            event = await queue.get()
            
            # Send the event data as JSON to the HUD frontend
            await websocket.send_json({
                "type": event.type,
                "data": event.data,
                "source": event.source
            })
            queue.task_done()
    except WebSocketDisconnect:
        logger.info("hud.websocket_disconnected", id=subscriber_id)
    except Exception as e:
        logger.error("hud.websocket_error", error=str(e))
    finally:
        bus.unsubscribe("hud.notification", _queue_event)
        bus.unsubscribe(EventTypes.SYSTEM_READY, _queue_event)
