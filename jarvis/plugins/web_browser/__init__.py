import re
from typing import Any

import httpx

from jarvis.events.bus import EventBus
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult
from jarvis.tools.registry import ToolRegistry


class FetchUrlTool(Tool):
    """Fetches the text content of a given URL."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="fetch_url_content",
            description="Fetch the text content of a given URL.",
            category=ToolCategory.WEB,
            dangerous=False,
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="The full URL to fetch, e.g. https://example.com"
                )
            ]
        )

    async def execute(self, **kwargs) -> ToolResult:
        url = kwargs.get("url")
        if not url:
            return ToolResult(success=False, error="No URL provided.")

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "").lower()
                text = response.text

                if "text/html" in content_type:
                    # Strip basic HTML tags if it's HTML
                    text = re.sub(r'<style.*?>.*?</style>', '', text, flags=re.DOTALL)
                    text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.DOTALL)
                    text = re.sub(r'<[^>]+>', ' ', text)
                    text = re.sub(r'\s+', ' ', text).strip()

                # Truncate to avoid massive outputs overloading context
                limit = 4000
                if len(text) > limit:
                    text = text[:limit] + "\n... (truncated)"

                return ToolResult(success=True, output=text)
        except Exception as e:
            return ToolResult(success=False, error=f"Error fetching URL: {str(e)}")

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    """Register the web browser tools."""
    registry.register(FetchUrlTool())
