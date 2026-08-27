from jarvis.events.bus import EventBus
from jarvis.tools.registry import ToolRegistry

from .tools import WhatsAppSendMessageTool, TelegramSendMessageTool

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    """Register messaging bridge tools."""
    registry.register(WhatsAppSendMessageTool())
    registry.register(TelegramSendMessageTool())
