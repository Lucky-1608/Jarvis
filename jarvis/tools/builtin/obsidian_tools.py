"""
Jarvis OS — Built-in Obsidian Sync Tools.

Tools to sync knowledge and read/write notes directly 
to a local Obsidian Markdown vault.
"""

import os
from pathlib import Path
from typing import Any

import structlog

from jarvis.config.settings import get_settings
from jarvis.tools.base import (
    Tool,
    ToolCategory,
    ToolMetadata,
    ToolParameter,
    ToolResult,
)

logger = structlog.get_logger(__name__)

class SyncObsidianNoteTool(Tool):
    """Write or update a note in the Obsidian vault."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="sync_obsidian_note",
            description="Create or update a markdown note in the user's Obsidian vault. It is idempotent.",
            category=ToolCategory.FILE,
            parameters=[
                ToolParameter(
                    name="title",
                    type="string",
                    description="The title of the note (without .md extension).",
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="The markdown content to write to the note.",
                ),
            ],
            dangerous=False,
        )

    async def execute(self, **params: Any) -> ToolResult:
        settings = get_settings()
        if not settings.obsidian.enabled:
            return ToolResult(success=False, error="Obsidian sync is disabled in settings.")

        vault_path = Path(settings.obsidian.vault_path)
        vault_path.mkdir(parents=True, exist_ok=True)

        title = params.get("title", "").strip()
        content = params.get("content", "").strip()

        if not title:
            return ToolResult(success=False, error="No title provided.")

        file_path = vault_path / f"{title}.md"

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            logger.info("obsidian.synced_note", title=title, path=str(file_path))
            return ToolResult(
                success=True, 
                output=f"Successfully synced note '{title}' to Obsidian vault."
            )
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


class ReadObsidianNoteTool(Tool):
    """Read a note from the Obsidian vault."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="read_obsidian_note",
            description="Read the contents of a markdown note from the user's Obsidian vault.",
            category=ToolCategory.FILE,
            parameters=[
                ToolParameter(
                    name="title",
                    type="string",
                    description="The title of the note (without .md extension).",
                ),
            ],
            dangerous=False,
        )

    async def execute(self, **params: Any) -> ToolResult:
        settings = get_settings()
        if not settings.obsidian.enabled:
            return ToolResult(success=False, error="Obsidian sync is disabled in settings.")

        vault_path = Path(settings.obsidian.vault_path)
        title = params.get("title", "").strip()

        if not title:
            return ToolResult(success=False, error="No title provided.")

        file_path = vault_path / f"{title}.md"

        if not file_path.exists():
            return ToolResult(success=False, error=f"Note '{title}' not found in Obsidian vault.")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            return ToolResult(
                success=True, 
                output={"title": title, "content": content}
            )
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

def get_obsidian_tools() -> list[Tool]:
    """Return instances of all built-in Obsidian tools."""
    return [
        SyncObsidianNoteTool(),
        ReadObsidianNoteTool(),
    ]
