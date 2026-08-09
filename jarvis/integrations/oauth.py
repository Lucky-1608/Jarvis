"""
Jarvis OS - Native OAuth Integrations

Handles OAuth2 flows for third-party services like Google and Notion.
"""
import os

from authlib.integrations.starlette_client import OAuth
from fastapi import Request

oauth = OAuth()

# Google OAuth Setup
# All scopes requested upfront — Google only prompts for new scopes on re-consent
GOOGLE_SCOPES = " ".join([
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/contacts.readonly",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/youtube.readonly",
])

oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID", "stub_client_id"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "stub_client_secret"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': GOOGLE_SCOPES,
        'access_type': 'offline',
        'prompt': 'consent',
    }
)


# Notion OAuth Setup
oauth.register(
    name='notion',
    client_id=os.getenv("NOTION_CLIENT_ID", "stub_client_id"),
    client_secret=os.getenv("NOTION_CLIENT_SECRET", "stub_client_secret"),
    authorize_url='https://api.notion.com/v1/oauth/authorize',
    access_token_url='https://api.notion.com/v1/oauth/token',
    client_kwargs={'scope': ''} # Notion scopes are configured on the integration dashboard
)

# GitHub OAuth Setup
oauth.register(
    name='github',
    client_id=os.getenv("GITHUB_CLIENT_ID", "stub_client_id"),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET", "stub_client_secret"),
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email repo'}
)


async def get_google_auth_url(request: Request, redirect_uri: str):
    """Generates the Google OAuth authorization URL."""
    return await oauth.google.authorize_redirect(request, redirect_uri)

async def get_notion_auth_url(request: Request, redirect_uri: str):
    """Generates the Notion OAuth authorization URL."""
    return await oauth.notion.authorize_redirect(request, redirect_uri)

async def get_github_auth_url(request: Request, redirect_uri: str):
    """Generates the GitHub OAuth authorization URL."""
    return await oauth.github.authorize_redirect(request, redirect_uri)

