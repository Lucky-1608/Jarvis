"""
Jarvis OS — Built-in Vision Tools.

Tools for screenshot capture and screen analysis.
These integrate with the tool registry so the Planner
and Executor can invoke vision capabilities.
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


# ---------------------------------------------------------------------------
# Take Screenshot
# ---------------------------------------------------------------------------
class TakeScreenshotTool(Tool):
    """Capture a screenshot of the screen."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="take_screenshot",
            description="Capture a screenshot of the entire screen or the active window.",
            category=ToolCategory.DESKTOP,
            parameters=[
                ToolParameter(
                    name="target",
                    type="string",
                    description="What to capture: 'full_screen' or 'active_window'.",
                    required=False,
                    default="full_screen",
                    enum=["full_screen", "active_window"],
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        target = params.get("target", "full_screen")

        try:
            from jarvis.vision.screenshot import ScreenCapture

            if target == "active_window":
                capture = await ScreenCapture.capture_active_window()
            else:
                capture = await ScreenCapture.capture_full_screen()

            return ToolResult(
                success=True,
                output={
                    "type": capture["type"],
                    "width": capture["width"],
                    "height": capture["height"],
                    "size_kb": round(capture["size_bytes"] / 1024, 1),
                    "base64_preview": capture["base64"][:100] + "...",
                },
                metadata={"base64": capture["base64"]},
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"Screenshot failed: {exc}")


# ---------------------------------------------------------------------------
# Analyze Screen
# ---------------------------------------------------------------------------
class AnalyzeScreenTool(Tool):
    """Analyze what's currently visible on screen."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="analyze_screen",
            description="Take a screenshot and analyze it with AI vision to understand what's on screen.",
            category=ToolCategory.DESKTOP,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Specific question about the screen (e.g., 'What error is shown?').",
                    required=False,
                    default="Describe what's on screen.",
                ),
                ToolParameter(
                    name="target",
                    type="string",
                    description="What device to read: 'pc' or 'phone'.",
                    required=False,
                    default="pc",
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        query = params.get("query", "Describe what's on screen.")
        target = params.get("target", "pc").strip().lower()

        try:
            from jarvis.vision.analyzer import VisionAnalyzer

            analyzer = VisionAnalyzer()
            result = await analyzer.read_screen(target=target)

            return ToolResult(
                success=True,
                output=result.to_dict(),
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"Screen analysis failed: {exc}")


# ---------------------------------------------------------------------------
# Find UI Element
# ---------------------------------------------------------------------------
class FindElementTool(Tool):
    """Find a specific UI element on screen."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="find_element",
            description="Find a specific button, text, menu, or UI element on screen.",
            category=ToolCategory.DESKTOP,
            parameters=[
                ToolParameter(
                    name="description",
                    type="string",
                    description="Description of the element to find (e.g., 'the Submit button', 'the search bar').",
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        description = params.get("description", "")
        if not description:
            return ToolResult(success=False, error="No element description provided.")

        try:
            from jarvis.vision.analyzer import VisionAnalyzer

            analyzer = VisionAnalyzer()
            result = await analyzer.find_element(description)

            return ToolResult(
                success=True,
                output=result.to_dict(),
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"Element search failed: {exc}")


# ---------------------------------------------------------------------------
# Read Screen Errors
# ---------------------------------------------------------------------------
class ReadErrorTool(Tool):
    """Read any error messages visible on screen."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="read_screen_error",
            description="Capture the screen and check for any error messages, warnings, or issues.",
            category=ToolCategory.DESKTOP,
        )

    async def execute(self, **params: Any) -> ToolResult:
        try:
            from jarvis.vision.analyzer import VisionAnalyzer

            analyzer = VisionAnalyzer()
            result = await analyzer.read_error()

            return ToolResult(
                success=True,
                output={
                    "errors_found": len(result.errors_detected) > 0,
                    "errors": result.errors_detected,
                    "summary": result.summary,
                    "recommended_actions": result.recommended_actions,
                    "confidence": result.confidence,
                },
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"Error detection failed: {exc}")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def get_vision_tools() -> list[Tool]:
    """Return instances of all built-in vision tools."""
    return [
        TakeScreenshotTool(),
        AnalyzeScreenTool(),
        FindElementTool(),
        ReadErrorTool(),
    ]
