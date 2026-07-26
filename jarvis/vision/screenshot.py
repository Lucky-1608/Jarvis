"""
Jarvis OS — Screenshot Capture Pipeline.

Captures screenshots of the desktop or specific windows for
the vision system to analyze.

Spec Volume 6 Safety:
  - Never continuously monitor the screen
  - Never capture screenshots without user intent
  - Always discard temporary images after processing
"""

from __future__ import annotations

import base64
import io
import tempfile
import time
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class ScreenCapture:
    """
    Cross-platform screenshot capture.

    Uses PIL/Pillow for capture on all platforms.
    Screenshots are always captured on explicit user request only.
    """

    @staticmethod
    async def capture_full_screen() -> dict[str, Any]:
        """
        Capture the entire screen.

        Returns a dict with the image as base64 PNG and metadata.
        """
        try:
            from PIL import ImageGrab
        except ImportError:
            raise RuntimeError(
                "Pillow is required for screenshots. "
                "Install with: pip install 'jarvis-os[vision]'"
            )

        import asyncio
        loop = asyncio.get_event_loop()

        # Capture (CPU-bound, run in executor)
        screenshot = await loop.run_in_executor(None, ImageGrab.grab)

        # Convert to base64 PNG
        buffer = io.BytesIO()
        screenshot.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        result = {
            "type": "full_screen",
            "width": screenshot.width,
            "height": screenshot.height,
            "format": "png",
            "size_bytes": len(image_bytes),
            "base64": image_b64,
            "timestamp": time.time(),
        }

        logger.info(
            "screenshot.captured",
            type="full_screen",
            width=screenshot.width,
            height=screenshot.height,
            size_kb=round(len(image_bytes) / 1024, 1),
        )

        return result

    @staticmethod
    async def capture_region(
        left: int, top: int, right: int, bottom: int
    ) -> dict[str, Any]:
        """Capture a specific region of the screen."""
        try:
            from PIL import ImageGrab
        except ImportError:
            raise RuntimeError("Pillow is required for screenshots.")

        import asyncio
        loop = asyncio.get_event_loop()

        screenshot = await loop.run_in_executor(
            None,
            lambda: ImageGrab.grab(bbox=(left, top, right, bottom)),
        )

        buffer = io.BytesIO()
        screenshot.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        return {
            "type": "region",
            "region": {"left": left, "top": top, "right": right, "bottom": bottom},
            "width": screenshot.width,
            "height": screenshot.height,
            "format": "png",
            "size_bytes": len(image_bytes),
            "base64": image_b64,
            "timestamp": time.time(),
        }

    @staticmethod
    async def capture_to_file(
        output_path: str | Path | None = None,
    ) -> Path:
        """Capture screenshot and save to file. Returns the file path."""
        try:
            from PIL import ImageGrab
        except ImportError:
            raise RuntimeError("Pillow is required for screenshots.")

        import asyncio
        loop = asyncio.get_event_loop()
        screenshot = await loop.run_in_executor(None, ImageGrab.grab)

        if output_path is None:
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            output_path = tmp.name
            tmp.close()

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        await loop.run_in_executor(
            None,
            lambda: screenshot.save(str(output_path), format="PNG"),
        )

        logger.info("screenshot.saved", path=str(output_path))
        return output_path

    @staticmethod
    async def capture_active_window() -> dict[str, Any]:
        """
        Capture only the currently active/focused window.

        Falls back to full screen if window detection fails.
        """
        import platform

        if platform.system() == "Windows":
            try:
                import ctypes
                from ctypes import wintypes

                user32 = ctypes.windll.user32
                hwnd = user32.GetForegroundWindow()

                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))

                return await ScreenCapture.capture_region(
                    rect.left, rect.top, rect.right, rect.bottom
                )
            except Exception as exc:
                logger.warning("screenshot.active_window_failed", error=str(exc))

        # Fallback to full screen
        return await ScreenCapture.capture_full_screen()
