"""
Jarvis OS — Desktop Keyboard Automation.

Wrappers for PyAutoGUI keyboard functions.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

class KeyboardController:
    """Controls the physical keyboard via PyAutoGUI."""

    @classmethod
    async def type_text(cls, text: str, interval: float = 0.05) -> dict[str, Any]:
        """Type a string of text with a small delay between keystrokes."""
        try:
            import pyautogui
        except ImportError:
            raise RuntimeError("pyautogui is required for desktop automation.")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: pyautogui.typewrite(text, interval=interval))

        logger.info("keyboard.typed", text_length=len(text))
        return {"action": "type", "length": len(text), "status": "success"}

    @classmethod
    async def press_key(cls, key: str) -> dict[str, Any]:
        """Press a single key."""
        try:
            import pyautogui
        except ImportError:
            raise RuntimeError("pyautogui is required for desktop automation.")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: pyautogui.press(key))

        logger.info("keyboard.pressed", key=key)
        return {"action": "press", "key": key, "status": "success"}

    @classmethod
    async def hotkey(cls, *keys: str) -> dict[str, Any]:
        """Press a combination of keys (e.g., 'ctrl', 'c')."""
        try:
            import pyautogui
        except ImportError:
            raise RuntimeError("pyautogui is required for desktop automation.")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: pyautogui.hotkey(*keys))

        logger.info("keyboard.hotkey", keys=keys)
        return {"action": "hotkey", "keys": keys, "status": "success"}
