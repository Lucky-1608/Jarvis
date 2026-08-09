from jarvis.events.bus import EventBus
from jarvis.tools.registry import ToolRegistry

from .tools import (
    GmailDraftMessageTool,
    GmailGetLabelsTool,
    GmailGetUnreadCountTool,
    GmailListMessagesTool,
    GmailModifyLabelsTool,
    GmailReadMessageTool,
    GmailReplyToMessageTool,
    GmailSendMessageTool,
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
