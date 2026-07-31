from typing import Any
from jarvis.plugins.sdk import Plugin, PluginMetadata
from jarvis.events.bus import EventBus
from jarvis.tools.base import Tool
from .tools import StaticAnalysisTool, DependencyScannerTool, SecretsDetectorTool

class SecurityScannerPlugin(Plugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="security_scanner",
            version="1.0.0",
            description="Provides tools for security scanner integration."
        )

    async def register(self, bus: EventBus) -> None:
        pass

    def tools(self) -> list[Tool]:
        return [
            StaticAnalysisTool(),
            DependencyScannerTool(),
            SecretsDetectorTool()
        ]
