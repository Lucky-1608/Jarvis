from typing import Any
from jarvis.plugins.sdk import Plugin, PluginMetadata
from jarvis.events.bus import EventBus
from jarvis.tools.base import Tool
from .tools import DocumentParserTool

class DocumentParserPlugin(Plugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="document_parser",
            version="1.0.0",
            description="Provides tools for document parser integration."
        )

    async def register(self, bus: EventBus) -> None:
        pass

    def tools(self) -> list[Tool]:
        return [
            DocumentParserTool()
        ]
