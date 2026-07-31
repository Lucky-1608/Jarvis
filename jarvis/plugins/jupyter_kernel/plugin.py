from typing import Any
from jarvis.plugins.sdk import Plugin, PluginMetadata
from jarvis.events.bus import EventBus
from jarvis.tools.base import Tool
from .tools import JupyterExecutionTool

class JupyterKernelPlugin(Plugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="jupyter_kernel",
            version="1.0.0",
            description="Provides tools for jupyter kernel integration."
        )

    async def register(self, bus: EventBus) -> None:
        pass

    def tools(self) -> list[Tool]:
        return [
            JupyterExecutionTool()
        ]
