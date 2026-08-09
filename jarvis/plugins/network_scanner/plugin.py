from jarvis.events.bus import EventBus
from jarvis.plugins.sdk import Plugin, PluginMetadata
from jarvis.tools.base import Tool

from .tools import NetworkScannerTool


class NetworkScannerPlugin(Plugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="network_scanner",
            version="1.0.0",
            description="Provides tools for network scanner integration."
        )

    async def register(self, bus: EventBus) -> None:
        pass

    def tools(self) -> list[Tool]:
        return [
            NetworkScannerTool()
        ]
