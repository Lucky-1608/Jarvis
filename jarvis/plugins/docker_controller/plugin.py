from typing import Any
from jarvis.plugins.sdk import Plugin, PluginMetadata
from jarvis.events.bus import EventBus
from jarvis.tools.base import Tool
from .tools import DockerRunTool, DockerBuildTool

class DockerControllerPlugin(Plugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="docker_controller",
            version="1.0.0",
            description="Provides tools for docker controller integration."
        )

    async def register(self, bus: EventBus) -> None:
        pass

    def tools(self) -> list[Tool]:
        return [
            DockerRunTool(),
            DockerBuildTool()
        ]
