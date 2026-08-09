from jarvis.events.bus import EventBus
from jarvis.tools.registry import ToolRegistry

from .tools import DockerBuildTool, DockerRunTool


def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(DockerRunTool())
    registry.register(DockerBuildTool())
