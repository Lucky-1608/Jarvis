from jarvis.tools.registry import ToolRegistry
from jarvis.events.bus import EventBus
from .tools import DailyBriefingTool, MeetingPrepTool

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(DailyBriefingTool())
    registry.register(MeetingPrepTool())
