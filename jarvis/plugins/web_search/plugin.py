from jarvis.events.bus import EventBus
from jarvis.plugins.sdk import Plugin, PluginMetadata
from jarvis.tools.base import Tool

from .tools import WebSearchTool


class WebSearchPlugin(Plugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="web_search",
            version="1.0.0",
            description="Provides tools for Jina Web Search integration."
        )

    async def register(self, bus: EventBus) -> None:
        pass

    def tools(self) -> list[Tool]:
        return [
            WebSearchTool()
        ]
