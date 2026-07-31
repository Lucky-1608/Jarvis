from typing import Any
from jarvis.plugins.sdk import Plugin, PluginMetadata
from jarvis.events.bus import EventBus
from jarvis.tools.base import Tool
from .tools import VectorSearchTool

class VectorMemoryPlugin(Plugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="vector_memory",
            version="1.0.0",
            description="Provides tools for vector memory integration."
        )

    async def register(self, bus: EventBus) -> None:
        pass

    def tools(self) -> list[Tool]:
        return [
            VectorSearchTool()
        ]
