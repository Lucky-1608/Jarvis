"""
Jarvis OS — Browser Tools.

Exposes Playwright browser automation capabilities to the AI Planner.
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


class NavigateTool(Tool):
    """Navigate the browser to a specific URL."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="browser_navigate",
            description="Open a browser and navigate to a URL.",
            category=ToolCategory.WEB,
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="The URL to navigate to (e.g., 'https://google.com').",
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        url = params.get("url")
        if not url:
            return ToolResult(success=False, error="URL is required.")

        try:
            from jarvis.automation.browser.engine import BrowserEngine
            result = await BrowserEngine.navigate(url)
            return ToolResult(success=True, output=result)
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


class ClickElementTool(Tool):
    """Click on an element in the browser."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="browser_click",
            description="Click on a web element using a CSS or XPath selector.",
            category=ToolCategory.WEB,
            parameters=[
                ToolParameter(
                    name="selector",
                    type="string",
                    description="Playwright selector (e.g., 'button#submit', 'text=\"Login\"').",
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        selector = params.get("selector")
        if not selector:
            return ToolResult(success=False, error="Selector is required.")

        try:
            from jarvis.automation.browser.engine import BrowserEngine
            result = await BrowserEngine.click(selector)
            return ToolResult(success=True, output=result)
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


class FillFormTool(Tool):
    """Type text into an input field in the browser."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="browser_fill",
            description="Type text into a form input or text area in the browser.",
            category=ToolCategory.WEB,
            parameters=[
                ToolParameter(
                    name="selector",
                    type="string",
                    description="Playwright selector for the input field.",
                ),
                ToolParameter(
                    name="text",
                    type="string",
                    description="The text to type into the field.",
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        selector = params.get("selector")
        text = params.get("text", "")
        if not selector:
            return ToolResult(success=False, error="Selector is required.")

        try:
            from jarvis.automation.browser.engine import BrowserEngine
            result = await BrowserEngine.type_text(selector, text)
            return ToolResult(success=True, output=result)
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


class ExtractContentTool(Tool):
    """Extract text or HTML from the current page."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="browser_extract",
            description="Extract the current page's content as text or HTML.",
            category=ToolCategory.WEB,
            parameters=[
                ToolParameter(
                    name="format",
                    type="string",
                    description="Format to extract: 'text' or 'html'. Default is 'text'.",
                    required=False,
                    default="text",
                    enum=["text", "html"],
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        format_str = params.get("format", "text")

        try:
            from jarvis.automation.browser.engine import BrowserEngine
            result = await BrowserEngine.extract_content(format=format_str)
            return ToolResult(success=True, output=result)
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


def get_browser_tools() -> list[Tool]:
    """Return instances of all built-in browser tools."""
    return [
        NavigateTool(),
        ClickElementTool(),
        FillFormTool(),
        ExtractContentTool(),
    ]
