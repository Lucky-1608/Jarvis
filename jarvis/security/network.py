"""Network safety helpers for user- and model-supplied URLs."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx


def validate_public_url(url: str) -> str:
    """Validate an HTTP(S) URL and reject private or local destinations."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only public http:// and https:// URLs are allowed")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing credentials are not allowed")

    hostname = parsed.hostname.rstrip(".")
    if hostname.lower() in {"localhost", "localhost.localdomain", "metadata.google.internal"}:
        raise ValueError("Local and cloud metadata hosts are not allowed")

    try:
        addresses = [ipaddress.ip_address(hostname)]
    except ValueError:
        try:
            addresses = [
                ipaddress.ip_address(result[4][0])
                for result in socket.getaddrinfo(
                    hostname,
                    parsed.port or (443 if parsed.scheme == "https" else 80),
                    type=socket.SOCK_STREAM,
                )
            ]
        except (OSError, ValueError) as exc:
            raise ValueError("Could not resolve URL host") from exc

    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("Private, link-local, loopback, or metadata destinations are not allowed")
    return url


async def fetch_public_url(
    url: str,
    *,
    timeout: float = 15.0,
    max_redirects: int = 5,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Fetch a URL while validating every redirect destination."""
    current_url = validate_public_url(url)
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=False,
        headers=headers,
    ) as client:
        for _ in range(max_redirects + 1):
            await asyncio.to_thread(validate_public_url, current_url)
            response = await client.get(current_url)
            if response.status_code not in {301, 302, 303, 307, 308}:
                return response
            location = response.headers.get("location")
            if not location:
                return response
            current_url = validate_public_url(urljoin(current_url, location))
    raise ValueError("Too many redirects")


def fetch_public_url_sync(
    url: str,
    *,
    timeout: float = 30.0,
    max_redirects: int = 5,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Synchronous counterpart used by legacy scraper tools."""
    current_url = validate_public_url(url)
    with httpx.Client(timeout=timeout, follow_redirects=False, headers=headers) as client:
        for _ in range(max_redirects + 1):
            validate_public_url(current_url)
            response = client.get(current_url)
            if response.status_code not in {301, 302, 303, 307, 308}:
                return response
            location = response.headers.get("location")
            if not location:
                return response
            current_url = validate_public_url(urljoin(current_url, location))
    raise ValueError("Too many redirects")
