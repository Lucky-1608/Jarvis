"""
Jarvis OS — Built-in Web Tools.

Tools for searching the web and fetching URL content.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import structlog

from jarvis.security.network import fetch_public_url
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
            resp = await fetch_public_url(
                "https://html.duckduckgo.com/html/?" + urlencode({"q": query}),
                timeout=15,
                headers={"User-Agent": "Jarvis-OS/0.1 (AI Assistant)"},
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
                    from urllib.parse import parse_qs, unquote, urlparse

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
        try:
            max_length = max(1, min(int(params.get("max_length", 5000)), 100_000))
        except (TypeError, ValueError):
            max_length = 5000

        if not url:
            return ToolResult(success=False, error="No URL provided.")

        try:
            resp = await fetch_public_url(
                url,
                timeout=15,
                headers={"User-Agent": "Jarvis-OS/0.1 (AI Assistant)"},
            )
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
# Image Search (DuckDuckGo + Wikimedia Commons fallback)
# ---------------------------------------------------------------------------
class ImageSearchTool(Tool):
    """Search for images on the web."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="image_search",
            description=(
                "Search the web for images matching a query. Returns direct image URLs. "
                "CRITICAL: Always include the retrieved image URLs in markdown format "
                "![title](url) in your final response so companion apps, WhatsApp, and "
                "Telegram can display and render the images for the user."
            ),
            category=ToolCategory.WEB,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="The image search query (e.g. 'iron man suit', 'golden retriever puppy').",
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="Maximum number of images to return (default: 5).",
                    required=False,
                    default=5,
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        import json
        import re
        from urllib.parse import quote

        query = params.get("query", "").strip()
        try:
            max_results = max(1, min(int(params.get("max_results", 5)), 20))
        except (TypeError, ValueError):
            max_results = 5

        if not query:
            return ToolResult(success=False, error="No search query provided.")

        results: list[dict[str, str]] = []
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        # Strategy 1: DuckDuckGo image search
        try:
            ddg_init_url = f"https://duckduckgo.com/?q={quote(query)}"
            init_resp = await fetch_public_url(ddg_init_url, timeout=12, headers={"User-Agent": ua})
            if init_resp.status_code == 200:
                html = init_resp.text
                vqd_match = re.search(r'vqd=([0-9-]+)', html) or re.search(r'vqd="([^"]+)"', html)
                if vqd_match:
                    vqd = vqd_match.group(1)
                    api_url = f"https://duckduckgo.com/i.js?l=us-en&o=json&q={quote(query)}&vqd={vqd}&f=,,,"
                    img_resp = await fetch_public_url(api_url, timeout=12, headers={"User-Agent": ua})
                    if img_resp.status_code == 200:
                        data = json.loads(img_resp.text)
                        for item in data.get("results", []):
                            img_url = item.get("image")
                            title = item.get("title", query)
                            if img_url and img_url.startswith("http"):
                                results.append({
                                    "title": title,
                                    "url": img_url,
                                    "thumbnail": item.get("thumbnail") or img_url,
                                })
                            if len(results) >= max_results:
                                break
        except Exception as exc:
            logger.debug("image_search.ddg_error", query=query, error=str(exc))

        # Strategy 2: Wikimedia Commons / Wikipedia API fallback
        if len(results) < max_results:
            try:
                wiki_limit = max_results - len(results)
                wiki_url = (
                    f"https://en.wikipedia.org/w/api.php?action=query&generator=search"
                    f"&gsrsearch={quote(query)}&gsrlimit={wiki_limit * 2}&prop=pageimages"
                    f"&piprop=original|thumbnail&pithumbsize=1000&format=json"
                )
                wiki_resp = await fetch_public_url(wiki_url, timeout=12, headers={"User-Agent": "Jarvis-OS/0.1 (AI Assistant)"})
                if wiki_resp.status_code == 200:
                    wiki_data = json.loads(wiki_resp.text)
                    pages = wiki_data.get("query", {}).get("pages", {}).values()
                    for page in pages:
                        img_info = page.get("original") or page.get("thumbnail")
                        if img_info and img_info.get("source"):
                            results.append({
                                "title": page.get("title", query),
                                "url": img_info["source"],
                                "thumbnail": (page.get("thumbnail") or {}).get("source", img_info["source"]),
                            })
                        if len(results) >= max_results:
                            break
            except Exception as exc:
                logger.debug("image_search.wiki_error", query=query, error=str(exc))

        if not results:
            return ToolResult(
                success=False,
                error=f"No images found on the web for query: '{query}'. Try a broader search term.",
            )

        markdown = "\n".join([f"![{r['title']}]({r['url']})" for r in results])
        return ToolResult(
            success=True,
            output={
                "query": query,
                "count": len(results),
                "images": results,
                "markdown": markdown,
            },
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def get_web_tools() -> list[Tool]:
    """Return instances of all built-in web tools."""
    return [
        WebSearchTool(),
        FetchURLTool(),
        ImageSearchTool(),
    ]
