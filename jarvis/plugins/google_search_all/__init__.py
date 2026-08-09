from jarvis.events.bus import EventBus
from jarvis.tools.registry import ToolRegistry

from .tools import GlobalSearchTool


def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(GlobalSearchTool())
