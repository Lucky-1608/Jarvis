import os

import httpx

from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult


def _get_candidate_endpoints(env_url_key: str, env_port_key: str, default_port: str) -> list[str]:
    """Return an ordered list of candidate URLs to attempt connecting to a bridge."""
    custom_url = os.getenv(env_url_key)
    if custom_url:
        return [custom_url.rstrip("/")]

    port = os.getenv(env_port_key, default_port)
    return [
        f"http://127.0.0.1:{port}/send",
        f"http://localhost:{port}/send",
        f"http://0.0.0.0:{port}/send",
    ]


class WhatsAppSendMessageTool(Tool):
    """Send a message via the WhatsApp bridge."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="whatsapp_send_message",
            description="Send a message to WhatsApp via local bridge (port 3002).",
            category=ToolCategory.COMMUNICATION,
            dangerous=False,
            parameters=[
                ToolParameter(
                    name="message",
                    type="string",
                    description="The text message to send.",
                    required=True,
                ),
                ToolParameter(
                    name="to",
                    type="string",
                    description="Optional recipient phone number. Defaults to owner.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        message = kwargs.get("message")
        if not message:
            return ToolResult(success=False, error="'message' is required.")

        payload = {"message": message}
        recipient = kwargs.get("to") or kwargs.get("recipient") or kwargs.get("phone_number")
        if recipient:
            payload["to"] = recipient

        endpoints = _get_candidate_endpoints("WHATSAPP_BRIDGE_URL", "WHATSAPP_BRIDGE_PORT", "3002")
        last_error = None

        async with httpx.AsyncClient(timeout=10.0) as client:
            for url in endpoints:
                try:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        return ToolResult(success=True, output="Message sent to WhatsApp.")
                    try:
                        err_msg = resp.json().get("error", resp.text)
                    except Exception:
                        err_msg = resp.text
                    return ToolResult(
                        success=False,
                        error=f"WhatsApp bridge returned status {resp.status_code}: {err_msg}",
                    )
                except (httpx.ConnectError, httpx.ConnectTimeout) as conn_err:
                    last_error = conn_err
                    continue
                except Exception as e:
                    return ToolResult(success=False, error=f"Error sending WhatsApp message: {e}")

        candidates = ", ".join(endpoints)
        return ToolResult(
            success=False,
            error=f"Failed to connect to WhatsApp bridge ({candidates}): {last_error}",
        )


class TelegramSendMessageTool(Tool):
    """Send a message via the Telegram bridge."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="telegram_send_message",
            description="Send a message to Telegram via local bridge (port 3003).",
            category=ToolCategory.COMMUNICATION,
            dangerous=False,
            parameters=[
                ToolParameter(
                    name="message",
                    type="string",
                    description="The text message to send.",
                    required=True,
                ),
                ToolParameter(
                    name="to",
                    type="string",
                    description="Optional recipient chat ID. Defaults to owner.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        message = kwargs.get("message")
        if not message:
            return ToolResult(success=False, error="'message' is required.")

        payload = {"message": message}
        recipient = kwargs.get("to") or kwargs.get("chat_id")
        if recipient:
            payload["to"] = recipient

        endpoints = _get_candidate_endpoints("TELEGRAM_BRIDGE_URL", "TELEGRAM_BRIDGE_PORT", "3003")
        last_error = None

        async with httpx.AsyncClient(timeout=10.0) as client:
            for url in endpoints:
                try:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        return ToolResult(success=True, output="Message sent to Telegram.")
                    try:
                        err_msg = resp.json().get("error", resp.text)
                    except Exception:
                        err_msg = resp.text
                    return ToolResult(
                        success=False,
                        error=f"Telegram bridge returned status {resp.status_code}: {err_msg}",
                    )
                except (httpx.ConnectError, httpx.ConnectTimeout) as conn_err:
                    last_error = conn_err
                    continue
                except Exception as e:
                    return ToolResult(success=False, error=f"Error sending Telegram message: {e}")

        candidates = ", ".join(endpoints)
        return ToolResult(
            success=False,
            error=f"Failed to connect to Telegram bridge ({candidates}): {last_error}",
        )
