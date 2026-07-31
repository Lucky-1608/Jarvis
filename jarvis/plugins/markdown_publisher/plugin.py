from typing import Any
from jarvis.plugins.sdk import Plugin, PluginMetadata
from jarvis.events.bus import EventBus
from jarvis.tools.base import Tool
from .tools import PublishMarkdownTool

class MarkdownPublisherPlugin(Plugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="markdown_publisher",
            version="1.0.0",
            description="Provides tools for markdown publisher integration."
        )

    async def register(self, bus: EventBus) -> None:
        pass

    def tools(self) -> list[Tool]:
        return [
            PublishMarkdownTool()
        ]
