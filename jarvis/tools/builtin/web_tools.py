"""
Jarvis OS — Built-in Web Tools.

Tools for searching the web and fetching URL content.
"""

from __future__ import annotations

from typing import Any

import httpx
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
# Web Search (via DuckDuckGo HTML — no API key needed)
# ---------------------------------------------------------------------------
class WebSearchTool(Tool):
    """Search the web using DuckDuckGo."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="web_search",
            description="Search the web for information using DuckDuckGo. Returns relevant results.",
            category=ToolCategory.WEB,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="The search query.",
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="Maximum number of results (default: 5).",
                    required=False,
                    default=5,
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        query = params.get("query", "").strip()
        max_results = params.get("max_results", 5)

        if not query:
            return ToolResult(success=False, error="No search query provided.")

        try:
            # Use DuckDuckGo HTML lite — no API key required
            async with httpx.AsyncClient(
                timeout=15,
                follow_redirects=True,
                headers={"User-Agent": "Jarvis-OS/0.1 (AI Assistant)"},
            ) as client:
                resp = await client.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": query},
                )
                resp.raise_for_status()
                html = resp.text

            # Simple extraction of result titles and URLs from DDG HTML
            results = self._parse_ddg_html(html, max_results)

            return ToolResult(
                success=True,
                output={
                    "query": query,
                    "results_count": len(results),
                    "results": results,
                },
            )
        except Exception as exc:
            logger.warning("web_search.error", query=query, error=str(exc))
            return ToolResult(success=False, error=f"Search failed: {exc}")

    @staticmethod
    def _parse_ddg_html(html: str, max_results: int) -> list[dict[str, str]]:
        """Extract search results from DuckDuckGo HTML lite page."""
        results = []
        # Look for result links — they appear in <a class="result__a"> tags
        import re

        # Pattern to find result blocks
        pattern = re.compile(
            r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?'
            r'class="result__snippet"[^>]*>(.*?)</(?:a|td|span)',
            re.DOTALL | re.IGNORECASE,
        )

        for match in pattern.finditer(html):
            if len(results) >= max_results:
                break
            url = match.group(1)
            title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            snippet = re.sub(r"<[^>]+>", "", match.group(3)).strip()

            if url and title:
                # DDG wraps URLs in a redirect; extract the real URL
                if "uddg=" in url:
                    from urllib.parse import unquote, parse_qs, urlparse

                    parsed = urlparse(url)
                    qs = parse_qs(parsed.query)
                    url = unquote(qs.get("uddg", [url])[0])

                results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                })

        return results


# ---------------------------------------------------------------------------
# Fetch URL
# ---------------------------------------------------------------------------
class FetchURLTool(Tool):
    """Fetch and read content from a URL."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="fetch_url",
            description="Fetch content from a URL and return the text. Useful for reading web pages and APIs.",
            category=ToolCategory.WEB,
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="The URL to fetch.",
                ),
                ToolParameter(
                    name="max_length",
                    type="integer",
                    description="Maximum content length in chars (default: 5000).",
                    required=False,
                    default=5000,
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        url = params.get("url", "").strip()
        max_length = params.get("max_length", 5000)

        if not url:
            return ToolResult(success=False, error="No URL provided.")

        try:
            async with httpx.AsyncClient(
                timeout=15,
                follow_redirects=True,
                headers={"User-Agent": "Jarvis-OS/0.1 (AI Assistant)"},
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()

            content_type = resp.headers.get("content-type", "")
            text = resp.text

            # Basic HTML to text stripping
            if "html" in content_type.lower():
                import re

                text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
                text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()

            # Truncate if needed
            truncated = len(text) > max_length
            text = text[:max_length]

            return ToolResult(
                success=True,
                output={
                    "url": url,
                    "status_code": resp.status_code,
                    "content_type": content_type,
                    "length": len(text),
                    "truncated": truncated,
                    "content": text,
                },
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"Fetch failed: {exc}")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def get_web_tools() -> list[Tool]:
    """Return instances of all built-in web tools."""
    return [
        WebSearchTool(),
        FetchURLTool(),
    ]
