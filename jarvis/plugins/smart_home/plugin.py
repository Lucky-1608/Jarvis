from typing import Any
from jarvis.plugins.sdk import Plugin, PluginMetadata
from jarvis.events.bus import EventBus
from jarvis.tools.base import Tool
from .tools import SmartHomeTool

class SmartHomePlugin(Plugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="smart_home",
            version="1.0.0",
            description="Provides tools for smart home integration."
        )

    async def register(self, bus: EventBus) -> None:
        pass

    def tools(self) -> list[Tool]:
        return [
            SmartHomeTool()
        ]
