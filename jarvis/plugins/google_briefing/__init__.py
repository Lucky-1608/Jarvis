from jarvis.events.bus import EventBus
from jarvis.tools.registry import ToolRegistry

from .tools import DailyBriefingTool, MeetingPrepTool


def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(DailyBriefingTool())
    registry.register(MeetingPrepTool())
