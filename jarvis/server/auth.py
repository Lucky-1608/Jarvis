"""Authentication helpers shared by HTTP and WebSocket endpoints."""

from __future__ import annotations

import hmac
import os
import secrets
import time

from fastapi import WebSocket

from jarvis.config.settings import get_settings

_WS_TICKET_TTL_SECONDS = 60
_ws_tickets: dict[str, float] = {}
_PLACEHOLDER_SECRETS = {
    "",
    "change-this-to-a-random-secret",
    "replace-with-a-long-random-secret",
    "JARVIS_DEV_KEY",
}


def authentication_required() -> bool:
    """Return whether the configured server must authenticate clients."""
    server = get_settings().server
    if server.require_auth:
        return True
    bind_host = os.getenv("JARVIS_BIND_HOST") or server.host
    if not bind_host:
        return False
    bind_host = bind_host.lower()
    return server.require_auth or bind_host not in {
        "127.0.0.1",
        "localhost",
        "::1",
    }


def secret_is_configured(secret: str) -> bool:
    """Reject empty and documented development secrets."""
    return bool(secret) and secret not in _PLACEHOLDER_SECRETS


def issue_websocket_ticket() -> dict[str, int | str]:
    """Issue a short-lived, single-use credential for a WebSocket handshake."""
    now = time.monotonic()
    for existing_ticket, expires_at in list(_ws_tickets.items()):
        if expires_at < now:
            _ws_tickets.pop(existing_ticket, None)
    ticket = secrets.token_urlsafe(32)
    _ws_tickets[ticket] = now + _WS_TICKET_TTL_SECONDS
    return {"ticket": ticket, "expires_in": _WS_TICKET_TTL_SECONDS}


def consume_websocket_ticket(ticket: str) -> bool:
    """Consume a WebSocket ticket exactly once if it is still valid."""
    expires_at = _ws_tickets.pop(ticket, None)
    return expires_at is not None and expires_at >= time.monotonic()


async def authenticate_websocket(websocket: WebSocket) -> bool:
    """Authenticate a WebSocket handshake using the same API key as HTTP.

    Browsers cannot set arbitrary handshake headers, so they use a short-lived
    one-time ticket. The connection is rejected before ``accept`` when
    authentication is enabled.
    """
    settings = get_settings().server
    client_host = websocket.client.host if websocket.client else None
    is_local = client_host in ("127.0.0.1", "localhost", "::1")

    if not authentication_required() or (is_local and not settings.require_auth):
        return True

    ticket = websocket.query_params.get("ticket")
    if ticket and consume_websocket_ticket(ticket):
        return True

    # Native clients may send the key as a handshake header. Browser clients
    # should use the short-lived ticket above; never put the API key in a URL.
    client_key = websocket.headers.get("x-api-key") or ""
    expected_key = settings.secret_key or ""
    if (is_local and client_key == "JARVIS_DEV_KEY") or (
        secret_is_configured(expected_key) and hmac.compare_digest(client_key, expected_key)
    ):
        return True
