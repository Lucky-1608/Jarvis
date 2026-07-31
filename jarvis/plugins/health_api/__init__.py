from jarvis.tools.registry import ToolRegistry
from jarvis.events.bus import EventBus
from .tools import HealthSyncTool

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(HealthSyncTool())
