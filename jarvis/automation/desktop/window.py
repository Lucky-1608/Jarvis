"""
Jarvis OS — Desktop Window Manager.

Manage application windows on the desktop (Windows specific for now).
"""

from __future__ import annotations

import sys
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

class WindowManager:
    """Manage application windows."""

    @classmethod
    def get_active_window(cls) -> dict[str, Any]:
        """Get information about the currently active window."""
        if sys.platform != "win32":
            return {"error": "Window management is currently only supported on Windows."}

        try:
            import pygetwindow as gw
        except ImportError:
            raise RuntimeError("pygetwindow is required for window management.")

        window = gw.getActiveWindow()
        if not window:
            return {"title": None}

        return {
            "title": window.title,
            "left": window.left,
            "top": window.top,
            "width": window.width,
            "height": window.height,
            "is_maximized": window.isMaximized,
            "is_minimized": window.isMinimized,
        }

    @classmethod
    def get_all_windows(cls) -> list[str]:
        """Get titles of all visible windows."""
        if sys.platform != "win32":
            return []

        try:
            import pygetwindow as gw
        except ImportError:
            raise RuntimeError("pygetwindow is required for window management.")

        windows = gw.getAllTitles()
        return [w for w in windows if w.strip()]

    @classmethod
    def activate_window(cls, title: str) -> dict[str, Any]:
        """Activate and bring a window to the foreground."""
        if sys.platform != "win32":
            return {"error": "Window management is currently only supported on Windows."}

        try:
            import pygetwindow as gw
        except ImportError:
            raise RuntimeError("pygetwindow is required for window management.")

        windows = gw.getWindowsWithTitle(title)
        if not windows:
            return {"error": f"No window found with title '{title}'"}

        window = windows[0]
        if window.isMinimized:
            window.restore()
        window.activate()

        logger.info("window.activated", title=window.title)
        return {"action": "activate", "title": window.title, "status": "success"}
