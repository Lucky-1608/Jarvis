from jarvis.tools.registry import ToolRegistry
from jarvis.events.bus import EventBus
from .tools import DocsReadTool, DocsCreateTool, DocsAppendTool, DocsSearchTool

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(DocsReadTool())
    registry.register(DocsCreateTool())
    registry.register(DocsAppendTool())
    registry.register(DocsSearchTool())
