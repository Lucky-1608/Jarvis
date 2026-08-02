"""
Jarvis OS - OAuth Routes

API endpoints for initiating and handling OAuth2 callbacks.
"""
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from jarvis.database.core import get_db
from jarvis.database.models import OAuthAccount, User
from sqlalchemy import select
from jarvis.integrations.oauth import oauth, get_google_auth_url, get_notion_auth_url, get_github_auth_url

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
    try:
        token = await oauth.google.authorize_access_token(request)
        userinfo = token.get('userinfo')
        if userinfo:
            email = userinfo.get("email")
            logger.info("oauth.google.success", email=email)
            user_id = await get_or_create_default_user(db)
            
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
            if token.get("refresh_token"):
                account.refresh_token = token.get("refresh_token")
            await db.commit()

            return {"message": "Google Authentication Successful", "user": email}
    except Exception as e:
        logger.error("oauth.google.error", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google authentication failed")

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

        return {"message": "Notion Authentication Successful", "bot_id": bot_id}
    except Exception as e:
        logger.error("oauth.notion.error", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Notion authentication failed")

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

        return {"message": "GitHub Authentication Successful", "username": username}
    except Exception as e:
        logger.error("oauth.github.error", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GitHub authentication failed")


