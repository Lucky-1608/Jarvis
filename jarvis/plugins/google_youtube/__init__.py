from jarvis.tools.registry import ToolRegistry
from jarvis.events.bus import EventBus
from .tools import (
    YouTubeSearchTool,
    YouTubeGetVideoInfoTool,
    YouTubeGetTranscriptTool,
    YouTubeListPlaylistsTool,
)

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(YouTubeSearchTool())
    registry.register(YouTubeGetVideoInfoTool())
    registry.register(YouTubeGetTranscriptTool())
    registry.register(YouTubeListPlaylistsTool())
