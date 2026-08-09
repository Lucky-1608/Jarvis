from jarvis.events.bus import EventBus
from jarvis.tools.registry import ToolRegistry

from .tools import ContactsGetDetailsTool, ContactsListAllTool, ContactsSearchTool


def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(ContactsSearchTool())
    registry.register(ContactsGetDetailsTool())
    registry.register(ContactsListAllTool())
