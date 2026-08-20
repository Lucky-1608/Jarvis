import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Dict, Any, Optional

from jarvis.server.companion_manager import companion_manager

logger = structlog.get_logger(__name__)

router = APIRouter()

@router.websocket("/ws/companion")
async def companion_websocket(websocket: WebSocket):
    """WebSocket endpoint for local companion apps to connect."""
    connection_id = await companion_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            
            # Expecting response payload: {"task_id": "...", "status": "success/error", "output": "..."}
            task_id = data.get("task_id")
            if task_id:
                await companion_manager.handle_response(task_id, data)
            else:
                logger.debug("companion.received_unsolicited", connection_id=connection_id, data=data)
                
    except WebSocketDisconnect:
        companion_manager.disconnect(connection_id)
    except Exception as e:
        logger.error("companion.websocket_error", error=str(e), connection_id=connection_id)
        companion_manager.disconnect(connection_id)
