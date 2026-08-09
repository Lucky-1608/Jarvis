from jarvis.events.bus import EventBus
from jarvis.tools.registry import ToolRegistry

from .tools import NetworkScannerTool


def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(NetworkScannerTool())
