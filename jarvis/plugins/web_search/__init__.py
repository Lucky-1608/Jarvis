from .plugin import WebSearchPlugin
from jarvis.events.bus import EventBus
from jarvis.tools.registry import ToolRegistry

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    """Register the web search tools."""
    plugin = WebSearchPlugin()
    for tool in plugin.tools():
        registry.register(tool)

__all__ = ["WebSearchPlugin", "setup"]
