from typing import Any
from jarvis.plugins.sdk import Plugin, PluginMetadata
from jarvis.events.bus import EventBus
from jarvis.tools.base import Tool
from .tools import GraphQueryTool

class GraphQueryPlugin(Plugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="graph_query",
            version="1.0.0",
            description="Provides tools for graph query integration."
        )

    async def register(self, bus: EventBus) -> None:
        pass

    def tools(self) -> list[Tool]:
        return [
            GraphQueryTool()
        ]
