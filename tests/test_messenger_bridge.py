import httpx
import pytest

from jarvis.plugins.messenger_bridge.tools import (
    TelegramSendMessageTool,
    WhatsAppSendMessageTool,
    _get_candidate_endpoints,
)


def test_candidate_endpoints():
    endpoints = _get_candidate_endpoints("NON_EXISTENT_URL", "WHATSAPP_BRIDGE_PORT", "3002")
    assert "http://127.0.0.1:3002/send" in endpoints
    assert "http://localhost:3002/send" in endpoints
    assert "http://0.0.0.0:3002/send" in endpoints


@pytest.mark.asyncio
async def test_whatsapp_tool_success(monkeypatch):
    tool = WhatsAppSendMessageTool()

    async def mock_post(self, url, **kwargs):
        req = httpx.Request("POST", url)
        return httpx.Response(200, json={"status": "ok"}, request=req)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    result = await tool.execute(message="Hello from test!")
    assert result.success is True
    assert "Message sent to WhatsApp." in result.output


@pytest.mark.asyncio
async def test_whatsapp_tool_missing_message():
    tool = WhatsAppSendMessageTool()
    result = await tool.execute(message="")
    assert result.success is False
    assert "'message' is required." in result.error


@pytest.mark.asyncio
async def test_telegram_tool_success(monkeypatch):
    tool = TelegramSendMessageTool()

    async def mock_post(self, url, **kwargs):
        req = httpx.Request("POST", url)
        return httpx.Response(200, json={"status": "ok"}, request=req)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    result = await tool.execute(message="Test telegram")
    assert result.success is True
    assert "Message sent to Telegram." in result.output
