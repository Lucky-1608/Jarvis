"""
Jarvis OS — Desktop Tools.

Exposes PyAutoGUI desktop automation capabilities to the AI Planner.
"""

from __future__ import annotations

from typing import Any

import structlog

from jarvis.tools.base import (
    Tool,
    ToolCategory,
    ToolMetadata,
    ToolParameter,
    ToolResult,
)

logger = structlog.get_logger(__name__)


class MouseMoveTool(Tool):
    """Move the physical mouse cursor."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="desktop_mouse_move",
            description="Move the mouse cursor to specific coordinates.",
            category=ToolCategory.DESKTOP,
            parameters=[
                ToolParameter(name="x", type="integer", description="X coordinate"),
                ToolParameter(name="y", type="integer", description="Y coordinate"),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        x = params.get("x")
        y = params.get("y")
        if x is None or y is None:
            return ToolResult(success=False, error="x and y coordinates are required.")

        try:
            from jarvis.automation.desktop.mouse import MouseController
            result = await MouseController.move_to(x, y)
            return ToolResult(success=True, output=result)
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


class MouseClickTool(Tool):
    """Click the physical mouse."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="desktop_mouse_click",
            description="Click the mouse. Optionally move to coordinates first.",
            category=ToolCategory.DESKTOP,
            parameters=[
                ToolParameter(name="x", type="integer", description="Optional X coordinate", required=False),
                ToolParameter(name="y", type="integer", description="Optional Y coordinate", required=False),
                ToolParameter(name="button", type="string", description="'left', 'middle', or 'right'", required=False, default="left"),
                ToolParameter(name="clicks", type="integer", description="Number of clicks", required=False, default=1),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        try:
            from jarvis.automation.desktop.mouse import MouseController
            result = await MouseController.click(
                x=params.get("x"),
                y=params.get("y"),
                button=params.get("button", "left"),
                clicks=params.get("clicks", 1),
            )
            return ToolResult(success=True, output=result)
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


class KeyboardTypeTool(Tool):
    """Type text using the physical keyboard."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="desktop_keyboard_type",
            description="Type a string of text.",
            category=ToolCategory.DESKTOP,
            parameters=[
                ToolParameter(name="text", type="string", description="Text to type"),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        text = params.get("text")
        if not text:
            return ToolResult(success=False, error="Text is required.")

        try:
            from jarvis.automation.desktop.keyboard import KeyboardController
            result = await KeyboardController.type_text(text)
            return ToolResult(success=True, output=result)
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


class KeyboardHotkeyTool(Tool):
    """Press a keyboard hotkey combination."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="desktop_keyboard_hotkey",
            description="Press a combination of keys (e.g., ctrl, c).",
            category=ToolCategory.DESKTOP,
            parameters=[
                ToolParameter(name="keys", type="string", description="Comma-separated list of keys"),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        keys_str = params.get("keys")
        if not keys_str:
            return ToolResult(success=False, error="Keys are required.")

        keys = [k.strip() for k in keys_str.split(",")]

        try:
            from jarvis.automation.desktop.keyboard import KeyboardController
            result = await KeyboardController.hotkey(*keys)
            return ToolResult(success=True, output=result)
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


class WindowManagerTool(Tool):
    """Manage application windows."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="desktop_window_manager",
            description="Get information about open windows or activate a specific window.",
            category=ToolCategory.DESKTOP,
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="'list_all', 'get_active', or 'activate'",
                    enum=["list_all", "get_active", "activate"]
                ),
                ToolParameter(
                    name="title",
                    type="string",
                    description="Title of the window to activate (required if action is 'activate')",
                    required=False
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        action = params.get("action")

        try:
            from jarvis.automation.desktop.window import WindowManager

            if action == "list_all":
                return ToolResult(success=True, output={"windows": WindowManager.get_all_windows()})
            elif action == "get_active":
                return ToolResult(success=True, output=WindowManager.get_active_window())
            elif action == "activate":
                title = params.get("title")
                if not title:
                    return ToolResult(success=False, error="Title is required for activate action.")
                return ToolResult(success=True, output=WindowManager.activate_window(title))
            else:
                return ToolResult(success=False, error=f"Unknown action: {action}")

        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


def get_desktop_tools() -> list[Tool]:
    """Return instances of all built-in desktop tools."""
    return [
        MouseMoveTool(),
        MouseClickTool(),
        KeyboardTypeTool(),
        KeyboardHotkeyTool(),
        WindowManagerTool(),
    ]
