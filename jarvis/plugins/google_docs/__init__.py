from jarvis.events.bus import EventBus
from jarvis.tools.registry import ToolRegistry

from .tools import DocsAppendTool, DocsCreateTool, DocsReadTool, DocsSearchTool


def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(DocsReadTool())
    registry.register(DocsCreateTool())
    registry.register(DocsAppendTool())
    registry.register(DocsSearchTool())
