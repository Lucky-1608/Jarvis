from jarvis.tools.registry import ToolRegistry
from jarvis.events.bus import EventBus
from .tools import SmartHomeTool

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(SmartHomeTool())
