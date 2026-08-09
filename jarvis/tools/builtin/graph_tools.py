"""
Jarvis OS — Built-in Graph Tools.

Tools for interacting with the knowledge graph.
"""

from __future__ import annotations

import json
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
# Graph Query Tool
# ---------------------------------------------------------------------------
class GraphQueryTool(Tool):
    """Search the knowledge graph for entities and concepts."""

    def __init__(self, graph_registry: Any) -> None:
        self._registry = graph_registry

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="graph_query",
            description="Search the knowledge graph for entities, concepts, and code structures matching a query",
            category=ToolCategory.MEMORY,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="The search query.",
                ),
                ToolParameter(
                    name="limit",
                    type="integer",
                    description="Maximum number of results (default: 10).",
                    required=False,
                    default=10,
                ),
                ToolParameter(
                    name="project_name",
                    type="string",
                    description="The project name to target.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        project_name = params.get("project_name")
        if not project_name:
            return ToolResult(success=False, error="Must provide project_name.")

        graph = self._registry.get_graph(project_name)
        if not graph:
            return ToolResult(success=False, error=f"Project '{project_name}' not found.")

        query = params.get("query", "").strip()
        limit = params.get("limit", 10)

        if not query:
            return ToolResult(success=False, error="No query provided.")

        try:
            results = graph.search_entities(query, limit)
            formatted = json.dumps(results, indent=2)
            return ToolResult(success=True, output=formatted)
        except Exception as exc:
            logger.warning("graph_query.error", query=query, error=str(exc))
            return ToolResult(success=False, error=str(exc))


# ---------------------------------------------------------------------------
# Graph Explain Tool
# ---------------------------------------------------------------------------
class GraphExplainTool(Tool):
    """Get detailed information about a specific entity."""

    def __init__(self, graph_registry: Any) -> None:
        self._registry = graph_registry

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="graph_explain",
            description="Get detailed information about a specific entity in the knowledge graph including its type, source file, community, and all connections",
            category=ToolCategory.MEMORY,
            parameters=[
                ToolParameter(
                    name="entity",
                    type="string",
                    description="The entity to explain.",
                ),
                ToolParameter(
                    name="project_name",
                    type="string",
                    description="The project name to target.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        project_name = params.get("project_name")
        if not project_name:
            return ToolResult(success=False, error="Must provide project_name.")

        graph = self._registry.get_graph(project_name)
        if not graph:
            return ToolResult(success=False, error=f"Project '{project_name}' not found.")

        entity = params.get("entity", "").strip()

        if not entity:
            return ToolResult(success=False, error="No entity provided.")

        try:
            explanation = graph.explain(entity)
            formatted = json.dumps(explanation, indent=2)
            return ToolResult(success=True, output=formatted)
        except Exception as exc:
            logger.warning("graph_explain.error", entity=entity, error=str(exc))
            return ToolResult(success=False, error=str(exc))


# ---------------------------------------------------------------------------
# Graph Path Tool
# ---------------------------------------------------------------------------
class GraphPathTool(Tool):
    """Find the shortest path between two entities."""

    def __init__(self, graph_registry: Any) -> None:
        self._registry = graph_registry

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="graph_path",
            description="Find how two entities are connected in the knowledge graph, showing the shortest path between them",
            category=ToolCategory.MEMORY,
            parameters=[
                ToolParameter(
                    name="source",
                    type="string",
                    description="The source entity.",
                ),
                ToolParameter(
                    name="target",
                    type="string",
                    description="The target entity.",
                ),
                ToolParameter(
                    name="project_name",
                    type="string",
                    description="The project name to target.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        project_name = params.get("project_name")
        if not project_name:
            return ToolResult(success=False, error="Must provide project_name.")

        graph = self._registry.get_graph(project_name)
        if not graph:
            return ToolResult(success=False, error=f"Project '{project_name}' not found.")

        source = params.get("source", "").strip()
        target = params.get("target", "").strip()

        if not source or not target:
            return ToolResult(success=False, error="Both source and target entities must be provided.")

        try:
            path = graph.find_path(source, target)
            formatted = json.dumps(path, indent=2)
            return ToolResult(success=True, output=formatted)
        except Exception as exc:
            logger.warning("graph_path.error", source=source, target=target, error=str(exc))
            return ToolResult(success=False, error=str(exc))


# ---------------------------------------------------------------------------
# Graph Build Tool
# ---------------------------------------------------------------------------
class GraphBuildTool(Tool):
    """Build or rebuild the knowledge graph."""

    def __init__(self, graph_registry: Any) -> None:
        self._registry = graph_registry

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="graph_build",
            description="Build or rebuild the knowledge graph from a project directory. This parses all code files using AST analysis and creates a queryable knowledge graph",
            category=ToolCategory.MEMORY,
            dangerous=True,
            parameters=[
                ToolParameter(
                    name="directory",
                    type="string",
                    description="Path to the project directory to analyze",
                ),
                ToolParameter(
                    name="project_name",
                    type="string",
                    description="The project name to target.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        project_name = params.get("project_name")
        if not project_name:
            return ToolResult(success=False, error="Must provide project_name.")

        graph = self._registry.get_graph(project_name)
        if not graph:
            return ToolResult(success=False, error=f"Project '{project_name}' not found.")

        directory = params.get("directory", "").strip()

        if not directory:
            return ToolResult(success=False, error="No directory provided.")

        try:
            stats = await graph.build(directory)
            formatted = json.dumps(stats, indent=2)
            return ToolResult(success=True, output=formatted)
        except Exception as exc:
            logger.warning("graph_build.error", directory=directory, error=str(exc))
            return ToolResult(success=False, error=str(exc))


class GraphAddProjectTool(Tool):
    """Add a new project to the knowledge graph registry."""

    def __init__(self, graph_registry: Any) -> None:
        self._registry = graph_registry

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="graph_add_project",
            description="Add a new project to the knowledge graph registry",
            category=ToolCategory.MEMORY,
            parameters=[
                ToolParameter(
                    name="project_name",
                    type="string",
                    description="Name of the project",
                ),
                ToolParameter(
                    name="directory",
                    type="string",
                    description="Path to the project directory",
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        project_name = params.get("project_name", "").strip()
        directory = params.get("directory", "").strip()

        if not project_name or not directory:
            return ToolResult(success=False, error="Both project_name and directory are required.")

        try:
            await self._registry.add_project(project_name, directory)
            return ToolResult(success=True, output=f"Project '{project_name}' added successfully.")
        except Exception as exc:
            logger.warning("graph_add_project.error", project_name=project_name, error=str(exc))
            return ToolResult(success=False, error=str(exc))


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def get_graph_tools(graph_registry: Any) -> list[Tool]:
    """Return knowledge graph tools wired to the given GraphifyRegistry instance."""
    return [
        GraphQueryTool(graph_registry),
        GraphExplainTool(graph_registry),
        GraphPathTool(graph_registry),
        GraphBuildTool(graph_registry),
        GraphAddProjectTool(graph_registry),
    ]
