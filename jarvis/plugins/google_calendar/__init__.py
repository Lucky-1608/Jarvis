from jarvis.events.bus import EventBus
from jarvis.tools.registry import ToolRegistry

from .tools import (
    CalendarCheckAvailabilityTool,
    CalendarCreateEventTool,
    CalendarDeleteEventTool,
    CalendarGetAgendaTool,
    CalendarGetEventTool,
    CalendarListCalendarsTool,
    CalendarListEventsTool,
    CalendarUpdateEventTool,
)


def setup(registry: ToolRegistry, bus: EventBus) -> None:
    """Register all Google Calendar tools."""
    registry.register(CalendarListEventsTool())
    registry.register(CalendarGetEventTool())
    registry.register(CalendarCreateEventTool())
    registry.register(CalendarUpdateEventTool())
    registry.register(CalendarDeleteEventTool())
    registry.register(CalendarCheckAvailabilityTool())
    registry.register(CalendarListCalendarsTool())
    registry.register(CalendarGetAgendaTool())
