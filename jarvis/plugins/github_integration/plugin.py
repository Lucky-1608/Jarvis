from typing import Any
from jarvis.plugins.sdk import Plugin, PluginMetadata
from jarvis.events.bus import EventBus
from jarvis.tools.base import Tool
from .tools import GitHubPRTool, GitHubReviewTool

class GithubIntegrationPlugin(Plugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="github_integration",
            version="1.0.0",
            description="Provides tools for github integration integration."
        )

    async def register(self, bus: EventBus) -> None:
        pass

    def tools(self) -> list[Tool]:
        return [
            GitHubPRTool(),
            GitHubReviewTool()
        ]
