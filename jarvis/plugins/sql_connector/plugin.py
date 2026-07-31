from typing import Any
from jarvis.plugins.sdk import Plugin, PluginMetadata
from jarvis.events.bus import EventBus
from jarvis.tools.base import Tool
from .tools import SQLQueryTool

class SqlConnectorPlugin(Plugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="sql_connector",
            version="1.0.0",
            description="Provides tools for sql connector integration."
        )

    async def register(self, bus: EventBus) -> None:
        pass

    def tools(self) -> list[Tool]:
        return [
            SQLQueryTool()
        ]
