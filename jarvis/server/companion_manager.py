import asyncio
import uuid
from typing import Any

import structlog
from fastapi import WebSocket

logger = structlog.get_logger(__name__)

class CompanionManager:
    """Manages WebSocket connections from local companion apps (Desktop/Mobile)."""

    def __init__(self):
        # Maps connection_id to WebSocket
        self.active_connections: dict[str, WebSocket] = {}
        # Maps connection_id to device type ("pc", "mobile", "web")
        self.device_types: dict[str, str] = {}
        # Maps task_id to asyncio.Future waiting for a response
        self.pending_tasks: dict[str, asyncio.Future] = {}

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = websocket
        logger.info(
            "companion.connected",
            connection_id=connection_id,
            total_connected=len(self.active_connections),
        )
        return connection_id

    def disconnect(self, connection_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.device_types:
            del self.device_types[connection_id]
        logger.info(
            "companion.disconnected",
            connection_id=connection_id,
            total_connected=len(self.active_connections),
        )

    def register_device(self, connection_id: str, device: str):
        self.device_types[connection_id] = device
        logger.info("companion.registered", connection_id=connection_id, device=device)

    def has_companions(self) -> bool:
        """Returns True if there is at least one active companion connected."""
        return len(self.active_connections) > 0

    async def broadcast_command(
        self,
        action: str,
        params: dict[str, Any],
        target_device: str | None = None,
    ):
        """Broadcasts a command to all matching companions without waiting for a response."""
        if not self.has_companions():
            return
        payload = {
            "action": action,
            "task_id": str(uuid.uuid4()),
            "params": params,
        }
        for cid, ws in list(self.active_connections.items()):
            if target_device is None or self.device_types.get(cid) == target_device:
                try:
                    await ws.send_json(payload)
                    logger.debug("companion.broadcast_sent", action=action, connection_id=cid)
                except Exception as e:
                    logger.warning("companion.broadcast_failed", connection_id=cid, error=str(e))

    async def send_command_and_wait(
        self,
        action: str,
        params: dict[str, Any],
        timeout: int = 15,
        target_device: str = "pc",
    ) -> dict[str, Any]:
        """
        Sends a command to the specified companion (or first available) and waits for the response.
        Prioritizes the most recently connected companion and automatically prunes broken sockets.
        Raises TimeoutError if it takes too long.
        Raises ConnectionError if no companions are connected.
        """
        if not self.has_companions():
            raise ConnectionError("No local companions are currently connected.")

        # Find all connections matching the target device, newest first
        matching_cids = [
            cid for cid in self.active_connections.keys()
            if self.device_types.get(cid) == target_device
        ]
        matching_cids.reverse()

        # Fallback to any active connection if specific target isn't found
        if not matching_cids:
            matching_cids = list(self.active_connections.keys())
            matching_cids.reverse()

        task_id = str(uuid.uuid4())
        future = asyncio.Future()
        self.pending_tasks[task_id] = future

        payload = {
            "action": action,
            "task_id": task_id,
            "params": params
        }

        sent = False
        last_error = None

        for cid in matching_cids:
            websocket = self.active_connections.get(cid)
            if not websocket:
                continue
            try:
                await websocket.send_json(payload)
                logger.debug(
                    "companion.command_sent",
                    action=action,
                    task_id=task_id,
                    connection_id=cid,
                )
                sent = True
                break
            except Exception as e:
                logger.warning(
                    "companion.send_failed_pruning",
                    action=action,
                    connection_id=cid,
                    error=str(e),
                )
                self.disconnect(cid)
                last_error = e

        if not sent:
            if task_id in self.pending_tasks:
                del self.pending_tasks[task_id]
            err_msg = f"Failed to deliver command to {target_device} companion: {str(last_error)}"
            raise ConnectionError(err_msg)


        try:
            # Wait for the companion to reply
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except TimeoutError:
            logger.warning("companion.command_timeout", action=action, task_id=task_id)
            if task_id in self.pending_tasks:
                del self.pending_tasks[task_id]
            raise
        except Exception as e:
            logger.error("companion.command_error", error=str(e), action=action, task_id=task_id)
            if task_id in self.pending_tasks:
                del self.pending_tasks[task_id]
            raise


    async def handle_response(self, task_id: str, payload: dict[str, Any]):
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
