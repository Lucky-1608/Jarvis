from typing import Any
from jarvis.plugins.sdk import Plugin, PluginMetadata
from jarvis.events.bus import EventBus
from jarvis.tools.base import Tool
from .tools import SlackMessageTool, SlackReadTool

class SlackBridgePlugin(Plugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="slack_bridge",
            version="1.0.0",
            description="Provides tools for slack bridge integration."
        )

    async def register(self, bus: EventBus) -> None:
        pass

    def tools(self) -> list[Tool]:
        return [
            SlackMessageTool(),
            SlackReadTool()
        ]
