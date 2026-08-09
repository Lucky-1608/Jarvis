from jarvis.events.bus import EventBus
from jarvis.tools.registry import ToolRegistry

from .tools import (
    YouTubeGetTranscriptTool,
    YouTubeGetVideoInfoTool,
    YouTubeListPlaylistsTool,
    YouTubeSearchTool,
)


def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(YouTubeSearchTool())
    registry.register(YouTubeGetVideoInfoTool())
    registry.register(YouTubeGetTranscriptTool())
    registry.register(YouTubeListPlaylistsTool())
