from jarvis.events.bus import EventBus
from jarvis.plugins.sdk import Plugin, PluginMetadata
from jarvis.tools.base import Tool

from .tools import WebScraperTool


class WebScraperPlugin(Plugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="web_scraper",
            version="1.0.0",
            description="Provides tools for web scraper integration."
        )

    async def register(self, bus: EventBus) -> None:
        pass

    def tools(self) -> list[Tool]:
        return [
            WebScraperTool()
        ]
