from jarvis.tools.registry import ToolRegistry
from jarvis.events.bus import EventBus
from .tools import StripeMetricsTool

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(StripeMetricsTool())
