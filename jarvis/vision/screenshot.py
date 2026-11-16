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
    async def capture_full_screen(target_device: str | None = None) -> dict[str, Any]:
        """
        Capture the entire screen.

        Returns a dict with the image as base64 PNG and metadata.
        """
        # 1. Forward to connected desktop/mobile companion (prioritized for cloud or remote setups)
        companion_attempted = False
        companion_error: str | None = None
        try:
            from jarvis.server.companion_manager import companion_manager

            if companion_manager.has_companions():
                companion_attempted = True

                chosen_target = target_device
                if not chosen_target:
                    pc_cids = [cid for cid, dev in companion_manager.device_types.items() if dev == "pc"]
                    mobile_cids = [cid for cid, dev in companion_manager.device_types.items() if dev == "mobile"]
                    if not pc_cids and mobile_cids:
                        chosen_target = "mobile"
                    else:
                        chosen_target = "pc"

                res = await companion_manager.send_command_and_wait(
                    action="capture_screen",
                    params={},
                    target_device=chosen_target,
                    timeout=12,
                )
                if res.get("status") == "success" and res.get("image_base64"):
                    img_data = res["image_base64"]
                    raw_b64 = img_data.split(",", 1)[1] if "," in img_data else img_data
                    default_width = 1080 if chosen_target == "mobile" else 1920
                    default_height = 2400 if chosen_target == "mobile" else 1080
                    return {
                        "type": "full_screen",
                        "width": res.get("width", default_width),
                        "height": res.get("height", default_height),
                        "format": "png",
                        "size_bytes": len(raw_b64),
                        "base64": raw_b64,
                        "timestamp": time.time(),
                    }
                else:
                    companion_error = res.get("error") or res.get("message") or "Companion returned non-success response"
                    logger.warning("companion.screenshot_delegation_failed", error=companion_error)
        except Exception as e:
            companion_error = str(e)
            logger.debug("companion.screenshot_delegation_skipped", error=str(e))

        # Check for headless Linux environment without display server
        import os
        import sys

        is_headless_linux = sys.platform.startswith("linux") and not os.environ.get("DISPLAY")
        if is_headless_linux:
            if companion_attempted:
                msg = f"Screen capture failed: Desktop companion error ({companion_error}). Backend server is running headless (no DISPLAY) and cannot capture local screen."
            else:
                msg = "Screen capture requires a connected desktop companion when backend is running in a headless environment (no DISPLAY found)."
            logger.error("screenshot.headless_unsupported", error=msg)
            raise RuntimeError(msg)

        try:
            from PIL import ImageGrab
        except ImportError:
            raise RuntimeError(
                "Pillow is required for screenshots. "
                "Install with: pip install 'jarvis-os[vision]'"
            )

        # Capture screen (direct call preferred on Windows to avoid GDI thread affinity blocks)
        try:
            screenshot = ImageGrab.grab()
        except Exception:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                screenshot = await loop.run_in_executor(None, ImageGrab.grab)
            except Exception as e:
                err_str = str(e)
                if "X connection failed" in err_str or "DISPLAY" in err_str:
                    err_str = (
                        f"Screen capture failed (no X11 display available: {e}). "
                        "Please ensure the Jarvis desktop companion is running and connected."
                    )
                logger.error("screenshot.grab_failed", error=err_str)
                raise RuntimeError(err_str) from e

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
        import os
        import sys

        if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
            raise RuntimeError(
                "Region capture is not supported on a headless Linux server without a display server."
            )

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
        capture = await ScreenCapture.capture_full_screen()
        image_bytes = base64.b64decode(capture["base64"])

        if output_path is None:
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            output_path = tmp.name
            tmp.close()

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)

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
