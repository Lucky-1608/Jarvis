"""
Jarvis OS — Built-in Social Tools (Agent Reach Integration).

Tools for searching social media platforms via local CLI tools.
"""

from __future__ import annotations

import subprocess
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


class TwitterSearchTool(Tool):
    """Search Twitter using twitter-cli."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="twitter_search",
            description="Search Twitter for tweets matching a query (requires twitter-cli to be installed).",
            category=ToolCategory.WEB,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="The search query.",
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        query = params.get("query", "").strip()
        if not query:
            return ToolResult(success=False, error="Query cannot be empty.")

        try:
            # Using twitter-cli search
            result = subprocess.run(
                ["twitter-cli", "search", query, "--limit", "5"],
                capture_output=True,
                text=True,
                check=True
            )
            return ToolResult(
                success=True,
                output={
                    "query": query,
                    "content": result.stdout.strip()
                }
            )
        except FileNotFoundError:
            return ToolResult(
                success=False,
                error="twitter-cli is not installed. Please install it first (e.g., npm install -g twitter-cli or equivalent)."
            )
        except subprocess.CalledProcessError as e:
            return ToolResult(success=False, error=f"Twitter search failed: {e.stderr}")


class RedditSearchTool(Tool):
    """Search Reddit using rdt-cli."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="reddit_search",
            description="Search Reddit for posts matching a query (requires rdt-cli to be installed).",
            category=ToolCategory.WEB,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="The search query.",
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        query = params.get("query", "").strip()
        if not query:
            return ToolResult(success=False, error="Query cannot be empty.")

        try:
            result = subprocess.run(
                ["rdt-cli", "search", query],
                capture_output=True,
                text=True,
                check=True
            )
            return ToolResult(
                success=True,
                output={
                    "query": query,
                    "content": result.stdout.strip()
                }
            )
        except FileNotFoundError:
            return ToolResult(
                success=False,
                error="rdt-cli is not installed. Please install it first."
            )
        except subprocess.CalledProcessError as e:
            return ToolResult(success=False, error=f"Reddit search failed: {e.stderr}")


class YouTubeSearchTool(Tool):
    """Search YouTube using yt-dlp."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="youtube_search",
            description="Search YouTube for videos matching a query and return titles and descriptions (requires yt-dlp to be installed).",
            category=ToolCategory.WEB,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="The search query.",
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        query = params.get("query", "").strip()
        if not query:
            return ToolResult(success=False, error="Query cannot be empty.")

        try:
            search_query = f"ytsearch3:{query}"
            result = subprocess.run(
                ["yt-dlp", search_query, "--get-title", "--get-id"],
                capture_output=True,
                text=True,
                check=True
            )
            return ToolResult(
                success=True,
                output={
                    "query": query,
                    "content": result.stdout.strip()
                }
            )
        except FileNotFoundError:
            return ToolResult(
                success=False,
                error="yt-dlp is not installed. Please install it first (e.g., pip install yt-dlp)."
            )
        except subprocess.CalledProcessError as e:
            return ToolResult(success=False, error=f"YouTube search failed: {e.stderr}")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def get_social_tools() -> list[Tool]:
    """Return instances of all social tools."""
    return [
        TwitterSearchTool(),
        RedditSearchTool(),
        YouTubeSearchTool(),
    ]
