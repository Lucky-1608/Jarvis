from jarvis.tools.registry import ToolRegistry
from jarvis.events.bus import EventBus
from .tools import SlackMessageTool, SlackReadTool

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(SlackMessageTool())
    registry.register(SlackReadTool())
