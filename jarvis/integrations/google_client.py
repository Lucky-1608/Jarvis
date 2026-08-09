"""
Jarvis OS — Google API Client.

Shared authenticated HTTP client for all Google service plugins.
Handles:
  - Bearer token injection
  - Automatic token refresh on 401
  - Account selection (multi-account support)
  - Rate limiting with exponential backoff
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.database.models import OAuthAccount

logger = structlog.get_logger(__name__)

# Google's token endpoint for refreshing access tokens
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class GoogleAuthError(Exception):
    """Raised when Google authentication fails irrecoverably."""
    pass


class GoogleClient:
    """
    Authenticated async HTTP client for Google APIs.

    Usage::

        async with GoogleClient(db, account) as client:
            resp = await client.get("https://gmail.googleapis.com/gmail/v1/users/me/messages")
            data = resp.json()
    """

    def __init__(
        self,
        db: AsyncSession,
        account: OAuthAccount,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._db = db
        self._account = account
        self._timeout = timeout
        self._max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> GoogleClient:
        self._client = httpx.AsyncClient(timeout=self._timeout)
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # -- Public request methods -----------------------------------------------

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self._request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self._request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self._request("PUT", url, **kwargs)

    async def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self._request("PATCH", url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self._request("DELETE", url, **kwargs)

    # -- Core request with auto-refresh & retry -------------------------------

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Execute an authenticated request with automatic token refresh and retry."""
        assert self._client is not None, "Client not initialized. Use `async with GoogleClient(...):`"

        # Proactively refresh if token is known to be expired
        if self._is_token_expired():
            await self._refresh_access_token()

        for attempt in range(self._max_retries):
            headers = kwargs.pop("headers", {})
            headers["Authorization"] = f"Bearer {self._account.access_token}"
            kwargs["headers"] = headers

            response = await self._client.request(method, url, **kwargs)

            if response.status_code == 401:
                # Token expired — refresh and retry
                logger.info(
                    "google_client.token_expired",
                    account=self._account.account_id,
                    attempt=attempt + 1,
                )
                refreshed = await self._refresh_access_token()
                if not refreshed:
                    raise GoogleAuthError(
                        f"Failed to refresh token for {self._account.account_id}. "
                        "User may need to re-authenticate."
                    )
                continue

            if response.status_code == 429:
                # Rate limited — exponential backoff
                wait = min(2 ** attempt * 1.0, 30.0)
                logger.warning(
                    "google_client.rate_limited",
                    account=self._account.account_id,
                    wait_seconds=wait,
                )
                await asyncio.sleep(wait)
                continue

            return response

        # Exhausted retries
        return response  # type: ignore[possibly-undefined]

    # -- Token refresh --------------------------------------------------------

    def _is_token_expired(self) -> bool:
        """Check if the access token is known to be expired."""
        if self._account.token_expires_at is None:
            return False  # Unknown expiry — try the request
        # Add 60-second buffer to avoid race conditions
        now = datetime.now(UTC)
        expires = self._account.token_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return now >= (expires - timedelta(seconds=60))

    async def _refresh_access_token(self) -> bool:
        """
        Use the refresh_token to get a new access_token from Google.
        Updates the DB and in-memory account object.
        """
        import os

        if not self._account.refresh_token:
            logger.error(
                "google_client.no_refresh_token",
                account=self._account.account_id,
            )
            return False

        client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")

        if not client_id or not client_secret:
            logger.error("google_client.missing_credentials")
            return False

        try:
            async with httpx.AsyncClient() as http:
                resp = await http.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "refresh_token": self._account.refresh_token,
                        "grant_type": "refresh_token",
                    },
                )

            if resp.status_code != 200:
                logger.error(
                    "google_client.refresh_failed",
                    status=resp.status_code,
                    body=resp.text,
                )
                return False

            data = resp.json()
            new_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)

            # Update in-memory
            self._account.access_token = new_token
            self._account.token_expires_at = datetime.now(UTC) + timedelta(
                seconds=expires_in
            )

            # Google sometimes issues a new refresh token
            if data.get("refresh_token"):
                self._account.refresh_token = data["refresh_token"]

            # Persist to database
            await self._db.commit()

            logger.info(
                "google_client.token_refreshed",
                account=self._account.account_id,
                expires_in=expires_in,
            )
            return True

        except Exception as exc:
            logger.error(
                "google_client.refresh_error",
                account=self._account.account_id,
                error=str(exc),
            )
            return False


# ---------------------------------------------------------------------------
# Account helpers
# ---------------------------------------------------------------------------

async def get_google_account(
    db: AsyncSession,
    user_id: int = 1,
    account_email: str | None = None,
    label: str | None = None,
) -> OAuthAccount | None:
    """
    Retrieve a Google OAuth account from the database.

    Priority:
      1. If ``account_email`` is given, return that exact account.
      2. If ``label`` is given (e.g., "Work"), return the first matching account.
      3. Otherwise, return the first (oldest) connected Google account.
    """
    query = select(OAuthAccount).where(
        OAuthAccount.user_id == user_id,
        OAuthAccount.provider == "google",
    )

    if account_email:
        query = query.where(OAuthAccount.account_id == account_email)
    elif label:
        query = query.where(OAuthAccount.label == label)

    query = query.order_by(OAuthAccount.created_at.asc())

    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_all_google_accounts(
    db: AsyncSession,
    user_id: int = 1,
) -> list[OAuthAccount]:
    """Return all connected Google accounts for a user."""
    result = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.user_id == user_id,
            OAuthAccount.provider == "google",
        ).order_by(OAuthAccount.created_at.asc())
    )
    return list(result.scalars().all())
