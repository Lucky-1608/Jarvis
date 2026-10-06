from jarvis.events.bus import EventBus
from jarvis.tools.registry import ToolRegistry
from .plugin import VNexusApiCallTool

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(VNexusApiCallTool())
