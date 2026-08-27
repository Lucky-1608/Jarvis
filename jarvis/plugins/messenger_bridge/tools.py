import httpx
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

class WhatsAppSendMessageTool(Tool):
    """Send a message via the local WhatsApp bridge."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="whatsapp_send_message",
            description="Send a message directly to the user's WhatsApp using the local bridge (port 3001).",
            category=ToolCategory.COMMUNICATION,
            dangerous=False,
            parameters=[
                ToolParameter(name="message", type="string", description="The text message to send."),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        message = kwargs.get("message")
        if not message:
            return ToolResult(success=False, error="'message' is required.")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post("http://127.0.0.1:3001/send", json={"message": message}, timeout=10.0)
                if resp.status_code == 200:
                    return ToolResult(success=True, output="Message successfully sent to WhatsApp.")
                else:
                    return ToolResult(success=False, error=f"Bridge returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to connect to WhatsApp bridge: {str(e)}")


class TelegramSendMessageTool(Tool):
    """Send a message via the local Telegram bridge."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="telegram_send_message",
            description="Send a message directly to the user's Telegram using the local bridge (port 3002).",
            category=ToolCategory.COMMUNICATION,
            dangerous=False,
            parameters=[
                ToolParameter(name="message", type="string", description="The text message to send."),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        message = kwargs.get("message")
        if not message:
            return ToolResult(success=False, error="'message' is required.")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post("http://127.0.0.1:3002/send", json={"message": message}, timeout=10.0)
                if resp.status_code == 200:
                    return ToolResult(success=True, output="Message successfully sent to Telegram.")
                else:
                    return ToolResult(success=False, error=f"Bridge returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to connect to Telegram bridge: {str(e)}")
