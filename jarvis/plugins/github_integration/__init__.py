from jarvis.events.bus import EventBus
from jarvis.tools.registry import ToolRegistry

from .tools import GitHubPRTool, GitHubReviewTool


def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(GitHubPRTool())
    registry.register(GitHubReviewTool())
