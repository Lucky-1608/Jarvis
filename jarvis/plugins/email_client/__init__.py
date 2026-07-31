from jarvis.tools.registry import ToolRegistry
from jarvis.events.bus import EventBus
from .tools import EmailSendTool, EmailReadTool

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(EmailSendTool())
    registry.register(EmailReadTool())
