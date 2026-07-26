"""
Jarvis OS — Desktop Mouse Automation.

Wrappers for PyAutoGUI mouse functions.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

class MouseController:
    """Controls the physical mouse via PyAutoGUI."""

    @classmethod
    async def move_to(cls, x: int, y: int, duration: float = 0.5) -> dict[str, Any]:
        """Move the mouse to absolute coordinates (x, y)."""
        try:
            import pyautogui
        except ImportError:
            raise RuntimeError("pyautogui is required for desktop automation.")

        # PyAutoGUI functions block, so run them in a separate thread
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: pyautogui.moveTo(x, y, duration))
        
        logger.info("mouse.moved", x=x, y=y)
        return {"action": "move", "x": x, "y": y, "status": "success"}

    @classmethod
    async def click(cls, x: int | None = None, y: int | None = None, button: str = "left", clicks: int = 1) -> dict[str, Any]:
        """Click the mouse. If x and y are provided, moves there first."""
        try:
            import pyautogui
        except ImportError:
            raise RuntimeError("pyautogui is required for desktop automation.")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: pyautogui.click(x=x, y=y, button=button, clicks=clicks))
        
        logger.info("mouse.clicked", x=x, y=y, button=button, clicks=clicks)
        return {"action": "click", "x": x, "y": y, "button": button, "clicks": clicks, "status": "success"}

    @classmethod
    async def drag_to(cls, x: int, y: int, duration: float = 0.5, button: str = "left") -> dict[str, Any]:
        """Drag the mouse to absolute coordinates (x, y)."""
        try:
            import pyautogui
        except ImportError:
            raise RuntimeError("pyautogui is required for desktop automation.")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: pyautogui.dragTo(x, y, duration, button=button))
        
        logger.info("mouse.dragged", x=x, y=y, button=button)
        return {"action": "drag", "x": x, "y": y, "button": button, "status": "success"}
