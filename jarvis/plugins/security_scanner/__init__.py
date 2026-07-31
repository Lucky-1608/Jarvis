from jarvis.tools.registry import ToolRegistry
from jarvis.events.bus import EventBus
from .tools import StaticAnalysisTool, DependencyScannerTool, SecretsDetectorTool

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(StaticAnalysisTool())
    registry.register(DependencyScannerTool())
    registry.register(SecretsDetectorTool())
