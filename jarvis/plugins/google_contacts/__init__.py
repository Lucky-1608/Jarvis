from jarvis.tools.registry import ToolRegistry
from jarvis.events.bus import EventBus
from .tools import ContactsSearchTool, ContactsGetDetailsTool, ContactsListAllTool

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(ContactsSearchTool())
    registry.register(ContactsGetDetailsTool())
    registry.register(ContactsListAllTool())
