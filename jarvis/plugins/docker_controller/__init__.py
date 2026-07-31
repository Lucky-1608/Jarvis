from jarvis.tools.registry import ToolRegistry
from jarvis.events.bus import EventBus
from .tools import DockerRunTool, DockerBuildTool

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(DockerRunTool())
    registry.register(DockerBuildTool())
