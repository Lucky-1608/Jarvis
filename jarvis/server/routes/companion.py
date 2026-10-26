import json

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from jarvis.server.companion_manager import companion_manager

logger = structlog.get_logger(__name__)

router = APIRouter()

@router.websocket("/ws/companion")
async def companion_websocket(websocket: WebSocket):
    """WebSocket endpoint for local companion apps to connect."""
    connection_id = await companion_manager.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("companion.invalid_json", connection_id=connection_id)
                continue

            # Respond to heartbeat pings to keep the connection alive
            if data.get("type") == "ping":
                try:
                    await websocket.send_json({"type": "pong"})
                except Exception:
                    break  # Connection is dead
                continue

            # Registration payload: {"type": "register", "device": "pc"}
            if data.get("type") == "register":
                device = data.get("device", "unknown")
                companion_manager.register_device(connection_id, device)
                continue

            # Response payload: {"task_id": "...", "status": "success/error", "output": "..."}
            task_id = data.get("task_id")
            if task_id:
                await companion_manager.handle_response(task_id, data)
            else:
                logger.debug(
                    "companion.received_unsolicited",
                    connection_id=connection_id,
                    data=data,
                )

    except WebSocketDisconnect:
        companion_manager.disconnect(connection_id)
    except Exception as e:
        logger.error("companion.websocket_error", error=str(e), connection_id=connection_id)
        companion_manager.disconnect(connection_id)

