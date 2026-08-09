"""
Jarvis OS - OAuth Routes

API endpoints for initiating and handling OAuth2 callbacks.
Includes account management (disconnect, label, refresh).
"""
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.database.core import get_db
from jarvis.database.models import OAuthAccount, User
from jarvis.integrations.oauth import (
    get_github_auth_url,
    get_google_auth_url,
    get_notion_auth_url,
    oauth,
)

logger = structlog.get_logger(__name__)
router = APIRouter()

async def get_or_create_default_user(db: AsyncSession) -> int:
    # Get or create a default user for linking accounts
    result = await db.execute(select(User).where(User.username == "default"))
    user = result.scalar_one_or_none()
    if not user:
        user = User(username="default")
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user.id

# Note: In a real environment, session middleware is required for authlib Starlette clients
# app.add_middleware(SessionMiddleware, secret_key="...") would be in app.py

@router.get("/login/google")
async def login_google(request: Request):
    """Initiates the Google OAuth flow."""
    import os
    if os.getenv("GOOGLE_CLIENT_ID", "stub_client_id") == "stub_client_id":
        return {"error": "Not Configured", "message": "Please configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env file."}

    redirect_uri = str(request.url_for('auth_google_callback'))
    return await get_google_auth_url(request, redirect_uri)

@router.get("/auth/google/callback")
async def auth_google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Handles the Google OAuth callback."""
    import os
    try:
        token = await oauth.google.authorize_access_token(request)
        userinfo = token.get('userinfo')
        if userinfo:
            email = userinfo.get("email")
            logger.info("oauth.google.success", email=email)
            user_id = await get_or_create_default_user(db)

            # Calculate token expiry
            expires_in = token.get("expires_in", 3600)
            token_expires_at = datetime.now(UTC) + timedelta(seconds=int(expires_in))

            # Get granted scopes
            granted_scopes = token.get("scope", "")

            # Save or update token
            result = await db.execute(select(OAuthAccount).where(
                OAuthAccount.user_id == user_id,
                OAuthAccount.provider == "google",
                OAuthAccount.account_id == email
            ))
            account = result.scalar_one_or_none()
            if not account:
                account = OAuthAccount(user_id=user_id, provider="google", account_id=email)
                db.add(account)

            account.access_token = token.get("access_token")
            account.token_expires_at = token_expires_at
            account.scopes = granted_scopes
            if token.get("refresh_token"):
                account.refresh_token = token.get("refresh_token")
            await db.commit()

            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
            return RedirectResponse(url=f"{frontend_url}/settings")
    except Exception as e:
        logger.error("oauth.google.error", error=str(e))
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        return RedirectResponse(url=f"{frontend_url}/settings?error=Google_Auth_Failed")

# ---------------------------------------------------------------------------
# Google Account Management Endpoints
# ---------------------------------------------------------------------------

@router.delete("/google/{account_id}")
async def disconnect_google_account(account_id: str, db: AsyncSession = Depends(get_db)):
    """Disconnect (delete) a Google account by email."""
    result = await db.execute(select(OAuthAccount).where(
        OAuthAccount.provider == "google",
        OAuthAccount.account_id == account_id
    ))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail=f"Google account '{account_id}' not found")

    await db.delete(account)
    await db.commit()
    logger.info("oauth.google.disconnected", account=account_id)
    return {"message": f"Disconnected Google account: {account_id}"}


class LabelUpdate(BaseModel):
    label: str


@router.patch("/google/{account_id}")
async def update_google_account_label(
    account_id: str,
    data: LabelUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update the label (e.g., 'Work', 'Personal') for a Google account."""
    result = await db.execute(select(OAuthAccount).where(
        OAuthAccount.provider == "google",
        OAuthAccount.account_id == account_id
    ))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail=f"Google account '{account_id}' not found")

    account.label = data.label
    await db.commit()
    logger.info("oauth.google.label_updated", account=account_id, label=data.label)
    return {"message": f"Label updated to '{data.label}'", "account_id": account_id}


@router.post("/google/{account_id}/refresh")
async def force_refresh_google_token(
    account_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Force-refresh the access token for a Google account."""
    from jarvis.integrations.google_client import GoogleClient

    result = await db.execute(select(OAuthAccount).where(
        OAuthAccount.provider == "google",
        OAuthAccount.account_id == account_id
    ))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail=f"Google account '{account_id}' not found")

    if not account.refresh_token:
        raise HTTPException(
            status_code=400,
            detail="No refresh token available. Please disconnect and reconnect this account."
        )

    client = GoogleClient(db, account)
    success = await client._refresh_access_token()
    if not success:
        raise HTTPException(status_code=500, detail="Token refresh failed")

    return {
        "message": "Token refreshed successfully",
        "account_id": account_id,
        "expires_at": account.token_expires_at.isoformat() if account.token_expires_at else None,
    }


# ---------------------------------------------------------------------------
# Notion OAuth
# ---------------------------------------------------------------------------

@router.get("/login/notion")
async def login_notion(request: Request):
    """Initiates the Notion OAuth flow."""
    import os
    if os.getenv("NOTION_CLIENT_ID", "stub_client_id") == "stub_client_id":
        return {"error": "Not Configured", "message": "Please configure NOTION_CLIENT_ID and NOTION_CLIENT_SECRET in your .env file."}

    redirect_uri = str(request.url_for('auth_notion_callback'))
    return await get_notion_auth_url(request, redirect_uri)

@router.get("/auth/notion/callback")
async def auth_notion_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Handles the Notion OAuth callback."""
    import os
    try:
        token = await oauth.notion.authorize_access_token(request)
        logger.info("oauth.notion.success")

        bot_id = token.get("bot_id", "default_notion_bot")
        user_id = await get_or_create_default_user(db)

        # Save or update token
        result = await db.execute(select(OAuthAccount).where(
            OAuthAccount.user_id == user_id,
            OAuthAccount.provider == "notion",
            OAuthAccount.account_id == bot_id
        ))
        account = result.scalar_one_or_none()
        if not account:
            account = OAuthAccount(user_id=user_id, provider="notion", account_id=bot_id)
            db.add(account)

        account.access_token = token.get("access_token")
        await db.commit()

        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        return RedirectResponse(url=f"{frontend_url}/settings")
    except Exception as e:
        logger.error("oauth.notion.error", error=str(e))
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        return RedirectResponse(url=f"{frontend_url}/settings?error=Notion_Auth_Failed")

# ---------------------------------------------------------------------------
# GitHub OAuth
# ---------------------------------------------------------------------------

@router.get("/login/github")
async def login_github(request: Request):
    """Initiates the GitHub OAuth flow."""
    import os
    if os.getenv("GITHUB_CLIENT_ID", "stub_client_id") == "stub_client_id":
        return {"error": "Not Configured", "message": "Please configure GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in your .env file."}

    redirect_uri = str(request.url_for('auth_github_callback'))
    return await get_github_auth_url(request, redirect_uri)

@router.get("/auth/github/callback")
async def auth_github_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Handles the GitHub OAuth callback."""
    import os
    try:
        token = await oauth.github.authorize_access_token(request)
        resp = await oauth.github.get('user', token=token)
        profile = resp.json()

        username = profile.get("login")
        logger.info("oauth.github.success", username=username)
        user_id = await get_or_create_default_user(db)

        # Save or update token
        result = await db.execute(select(OAuthAccount).where(
            OAuthAccount.user_id == user_id,
            OAuthAccount.provider == "github",
            OAuthAccount.account_id == username
        ))
        account = result.scalar_one_or_none()
        if not account:
            account = OAuthAccount(user_id=user_id, provider="github", account_id=username)
            db.add(account)

        account.access_token = token.get("access_token")
        await db.commit()

        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        return RedirectResponse(url=f"{frontend_url}/settings")
    except Exception as e:
        logger.error("oauth.github.error", error=str(e))
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        return RedirectResponse(url=f"{frontend_url}/settings?error=GitHub_Auth_Failed")
