import asyncio
import uuid
import structlog
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect

logger = structlog.get_logger(__name__)

class CompanionManager:
    """Manages WebSocket connections from local companion apps (Desktop/Mobile)."""

    def __init__(self):
        # Maps connection_id to WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # Maps task_id to asyncio.Future waiting for a response
        self.pending_tasks: Dict[str, asyncio.Future] = {}

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = websocket
        logger.info("companion.connected", connection_id=connection_id, total_connected=len(self.active_connections))
        return connection_id

    def disconnect(self, connection_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            logger.info("companion.disconnected", connection_id=connection_id, total_connected=len(self.active_connections))

    def has_companions(self) -> bool:
        """Returns True if there is at least one active companion connected."""
        return len(self.active_connections) > 0

    async def send_command_and_wait(self, action: str, params: Dict[str, Any], timeout: int = 15) -> Dict[str, Any]:
        """
        Sends a command to the first available companion and waits for the response.
        Raises TimeoutError if it takes too long.
        Raises ConnectionError if no companions are connected.
        """
        if not self.has_companions():
            raise ConnectionError("No local companions are currently connected.")

        # For now, just pick the first connected companion.
        connection_id = list(self.active_connections.keys())[0]
        websocket = self.active_connections[connection_id]

        task_id = str(uuid.uuid4())
        future = asyncio.Future()
        self.pending_tasks[task_id] = future

        payload = {
            "action": action,
            "task_id": task_id,
            "params": params
        }

        try:
            await websocket.send_json(payload)
            logger.debug("companion.command_sent", action=action, task_id=task_id, connection_id=connection_id)
            
            # Wait for the companion to reply
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
            
        except asyncio.TimeoutError:
            logger.warning("companion.command_timeout", action=action, task_id=task_id)
            if task_id in self.pending_tasks:
                del self.pending_tasks[task_id]
            raise
        except Exception as e:
            logger.error("companion.command_error", error=str(e), action=action, task_id=task_id)
            if task_id in self.pending_tasks:
                del self.pending_tasks[task_id]
            raise

    async def handle_response(self, task_id: str, payload: Dict[str, Any]):
        """Called when the WebSocket receives a response from the companion."""
        if task_id in self.pending_tasks:
            future = self.pending_tasks[task_id]
            if not future.done():
                future.set_result(payload)
            del self.pending_tasks[task_id]
            logger.debug("companion.response_received", task_id=task_id)
        else:
            logger.warning("companion.unknown_task", task_id=task_id)

# Global singleton
companion_manager = CompanionManager()
