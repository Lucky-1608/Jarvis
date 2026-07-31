from jarvis.tools.registry import ToolRegistry
from jarvis.events.bus import EventBus
from .tools import WalletTool, SmartContractTool

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(WalletTool())
    registry.register(SmartContractTool())
