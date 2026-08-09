from jarvis.events.bus import EventBus
from jarvis.tools.registry import ToolRegistry

from .tools import DependencyScannerTool, SecretsDetectorTool, StaticAnalysisTool


def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(StaticAnalysisTool())
    registry.register(DependencyScannerTool())
    registry.register(SecretsDetectorTool())
