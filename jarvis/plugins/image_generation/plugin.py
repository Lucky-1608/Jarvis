from jarvis.events.bus import EventBus
from jarvis.plugins.sdk import Plugin, PluginMetadata
from jarvis.tools.base import Tool

from .tools import GenerateImageTool


class ImageGenerationPlugin(Plugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="image_generation",
            version="1.0.0",
            description="Provides tools for image generation integration."
        )

    async def register(self, bus: EventBus) -> None:
        pass

    def tools(self) -> list[Tool]:
        return [
            GenerateImageTool()
        ]
