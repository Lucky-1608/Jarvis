from __future__ import annotations

import json
from pathlib import Path

import structlog

from jarvis.memory.graphify_memory import GraphifyMemory

logger = structlog.get_logger(__name__)


class GraphifyRegistry:
    """Registry for managing multiple Graphify knowledge graphs."""

    def __init__(self, base_data_dir: str):
        self.base_dir = Path(base_data_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.projects_file = self.base_dir / "projects.json"
        
        self.projects: dict[str, str] = {}
        self.graphs: dict[str, GraphifyMemory] = {}
        
        if self.projects_file.exists():
            try:
                with open(self.projects_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.projects = data.get("projects", {})
            except Exception as e:
                logger.error("Failed to load projects.json", error=str(e), exc_info=True)

    async def _load_registry(self) -> None:
        """Instantiate and initialize GraphifyMemory for loaded projects."""
        for project_name, target_dir in self.projects.items():
            project_dir = self.base_dir / project_name
            memory = GraphifyMemory(str(project_dir))
            await memory.initialize()
            self.graphs[project_name] = memory

    def get_graph(self, project_name: str) -> GraphifyMemory | None:
        """Get the graph memory for a specific project."""
        return self.graphs.get(project_name)

    def get_projects(self) -> dict:
        """Return the dictionary of loaded projects."""
        return self.projects

    async def add_project(self, project_name: str, target_dir: str) -> dict:
        """Add a new project, build its graph, and save to registry."""
        project_dir = self.base_dir / project_name
        memory = GraphifyMemory(str(project_dir))
        
        stats = await memory.build(target_dir)
        
        self.projects[project_name] = target_dir
        self.graphs[project_name] = memory
        
        try:
            with open(self.projects_file, "w", encoding="utf-8") as f:
                json.dump({"projects": self.projects}, f, indent=2)
        except Exception as e:
            logger.error("Failed to save projects.json", error=str(e), exc_info=True)
            
        return stats
