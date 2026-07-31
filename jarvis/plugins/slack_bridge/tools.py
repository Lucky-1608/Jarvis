import os
from typing import Any
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

class SlackMessageTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="SlackMessageTool",
            description="Send a message to a Slack channel.",
            category=ToolCategory.COMMUNICATION,
            dangerous=False,
            parameters=[
                ToolParameter(name="channel", type="string", description="Channel name or ID"),
                ToolParameter(name="text", type="string", description="Message content")
            ]
        )
        
    async def execute(self, **kwargs) -> ToolResult:
        token = os.getenv("SLACK_BOT_TOKEN")
        if not token:
            return ToolResult(success=False, error="SLACK_BOT_TOKEN environment variable not set.")
            
        channel = kwargs.get("channel")
        text = kwargs.get("text")
        
        try:
            from slack_sdk import WebClient
            client = WebClient(token=token)
            res = client.chat_postMessage(channel=channel, text=text)
            return ToolResult(success=True, output={"ts": res["ts"]})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class SlackReadTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="SlackReadTool",
            description="Read recent messages from a Slack channel.",
            category=ToolCategory.COMMUNICATION,
            dangerous=False,
            parameters=[
                ToolParameter(name="channel", type="string", description="Channel name or ID"),
                ToolParameter(name="limit", type="integer", description="Number of messages to fetch")
            ]
        )
        
    async def execute(self, **kwargs) -> ToolResult:
        token = os.getenv("SLACK_BOT_TOKEN")
        if not token:
            return ToolResult(success=False, error="SLACK_BOT_TOKEN environment variable not set.")
            
        channel = kwargs.get("channel")
        limit = kwargs.get("limit", 10)
        
        try:
            from slack_sdk import WebClient
            client = WebClient(token=token)
            res = client.conversations_history(channel=channel, limit=limit)
            messages = [{"user": m.get("user"), "text": m.get("text")} for m in res.get("messages", [])]
            return ToolResult(success=True, output={"messages": messages})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
