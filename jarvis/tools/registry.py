"""
Jarvis OS — Tool Registry.

Central registry that discovers, registers, and provides tools
to the Planner and Executor.
"""

from __future__ import annotations

from typing import Any

import structlog

from jarvis.tools.base import Tool, ToolCategory, ToolMetadata

logger = structlog.get_logger(__name__)


class ToolRegistry:
    """
    Central registry for all Jarvis tools.

    Tools are registered at startup and looked up by name
    when the Planner or Executor needs them.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    # -- Registration -------------------------------------------------------

    def register(self, tool: Tool) -> None:
        """Register a tool instance."""
        name = tool.metadata.name
        if name in self._tools:
            logger.warning("tool_registry.duplicate", name=name)
        self._tools[name] = tool
        logger.info(
            "tool_registry.registered",
            name=name,
            category=tool.metadata.category.value,
            dangerous=tool.metadata.dangerous,
        )

    def register_many(self, tools: list[Tool]) -> None:
        """Register multiple tools at once."""
        for tool in tools:
            self.register(tool)

    # -- Lookup -------------------------------------------------------------

    def get(self, name: str) -> Tool | None:
        """Return a tool by exact name, or ``None``."""
        return self._tools.get(name)

    def get_by_category(self, category: ToolCategory) -> list[Tool]:
        """Return all tools in a category."""
        return [t for t in self._tools.values() if t.metadata.category == category]

    def list_all(self) -> list[ToolMetadata]:
        """Return metadata for every registered tool."""
        return [t.metadata for t in self._tools.values()]

    def list_names(self) -> list[str]:
        """Return just the tool names."""
        return list(self._tools.keys())

    # -- OpenAI schema export -----------------------------------------------

    def to_openai_tools(self, category: ToolCategory | None = None) -> list[dict[str, Any]]:
        """
        Export all tools as OpenAI function-calling schemas.

        Optionally filter by *category*.
        """
        tools = self._tools.values()
        if category:
            tools = [t for t in tools if t.metadata.category == category]
        return [t.metadata.to_openai_schema() for t in tools]

    # -- Info ---------------------------------------------------------------

    @property
    def count(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __repr__(self) -> str:
        return f"ToolRegistry({self.count} tools)"
