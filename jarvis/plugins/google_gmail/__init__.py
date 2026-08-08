from jarvis.tools.registry import ToolRegistry
from jarvis.events.bus import EventBus
from .tools import (
    GmailListMessagesTool,
    GmailReadMessageTool,
    GmailSendMessageTool,
    GmailDraftMessageTool,
    GmailReplyToMessageTool,
    GmailGetLabelsTool,
    GmailModifyLabelsTool,
    GmailGetUnreadCountTool,
)

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    """Register all Gmail tools."""
    registry.register(GmailListMessagesTool())
    registry.register(GmailReadMessageTool())
    registry.register(GmailSendMessageTool())
    registry.register(GmailDraftMessageTool())
    registry.register(GmailReplyToMessageTool())
    registry.register(GmailGetLabelsTool())
    registry.register(GmailModifyLabelsTool())
    registry.register(GmailGetUnreadCountTool())
