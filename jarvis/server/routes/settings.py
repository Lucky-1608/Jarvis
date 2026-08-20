"""
Jarvis OS - Settings Routes

API endpoints for managing API keys and checking integration statuses.
"""
import os
from datetime import UTC

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.database.core import get_db
from jarvis.database.models import OAuthAccount

logger = structlog.get_logger(__name__)
router = APIRouter()

def mask_key(key: str, prefix: str = "sk-") -> str | None:
    if not key:
        return None
    # For very short keys just return the mask
    if len(key) < 8:
        return f"{prefix}***"
    return f"{prefix}...{key[-4:]}"

@router.get("/keys")
async def get_api_keys():
    """Returns the masked API keys for the current user/system."""

    opencode_key = os.getenv("OPENCODE_API_KEY", "")
    nvidia_key = os.getenv("NVIDIA_API_KEY", "")
    groq_key = os.getenv("GROQ_API_KEYS", os.getenv("GROQ_API_KEY", ""))
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    jina_key = os.getenv("JINA_API_KEY", "")

    return {
        "opencode": mask_key(opencode_key, "sk-"),
        "nvidia": mask_key(nvidia_key, "nvapi-"),
        "groq": mask_key(groq_key, "gsk_"),
        "gemini": mask_key(gemini_key, "AI-"),
        "jina": mask_key(jina_key, "jina_"),
        "ollama_cloud_url": os.getenv("OLLAMA_CLOUD_BASE_URL", "https://ollama.com")
    }

@router.get("/integrations")
async def get_integrations_status(db: AsyncSession = Depends(get_db)):
    """Returns the connection status of various integrations."""
    # Temporarily assume user_id 1 for local OS usage
    result = await db.execute(select(OAuthAccount).where(OAuthAccount.user_id == 1))
    accounts = result.scalars().all()

    def _account_info(acc: OAuthAccount) -> dict:
        info = {
            "id": acc.id,
            "account_id": acc.account_id,
            "label": getattr(acc, "label", None),
            "scopes": getattr(acc, "scopes", None),
        }
        expires = getattr(acc, "token_expires_at", None)
        if expires:
            info["token_expires_at"] = expires.isoformat()
            from datetime import datetime
            info["token_active"] = datetime.now(UTC) < expires.replace(
                tzinfo=UTC
            ) if expires.tzinfo is None else datetime.now(UTC) < expires
        else:
            info["token_expires_at"] = None
            info["token_active"] = None
        return info

    google_accounts = [_account_info(acc) for acc in accounts if acc.provider == "google"]
    notion_accounts = [_account_info(acc) for acc in accounts if acc.provider == "notion"]
    github_accounts = [_account_info(acc) for acc in accounts if acc.provider == "github"]

    return {
        "google": google_accounts,
        "notion": notion_accounts,
        "github": github_accounts,
        "whatsapp": bool(os.getenv("WHATSAPP_OWNER_NUMBER")),
        "telegram": bool(os.getenv("TELEGRAM_BOT_TOKEN"))
    }


@router.get("/plugins")
async def get_plugin_keys():
    return {
        "github_token": mask_key(os.getenv("GITHUB_TOKEN", ""), "ghp_"),
        "homeassistant_url": os.getenv("HOMEASSISTANT_URL", ""),
        "eth_rpc_url": mask_key(os.getenv("ETH_RPC_URL", ""), "https://"),
        "database_url": mask_key(os.getenv("DATABASE_URL", ""), "postgres://")
    }

@router.get("/system")
async def get_system_settings():
    """Returns core system settings."""
    from jarvis.config.settings import get_settings
    settings = get_settings()
    return {
        "ai_tool_selector_enabled": settings.ai_tool_selector_enabled
    }


from pydantic import BaseModel

from jarvis.utils.env_updater import update_env_file


class SystemSettingsUpdate(BaseModel):
    ai_tool_selector_enabled: bool

@router.post("/system")
async def update_system_settings(data: SystemSettingsUpdate):
    """Updates core system settings."""
    from jarvis.config.settings import get_settings
    settings = get_settings()
    settings.ai_tool_selector_enabled = data.ai_tool_selector_enabled

    # Persist to .env
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")
    update_env_file(env_path, {
        "AI_TOOL_SELECTOR_ENABLED": "true" if data.ai_tool_selector_enabled else "false"
    })

    return {"success": True, "ai_tool_selector_enabled": settings.ai_tool_selector_enabled}

@router.post("/plugins")
async def update_plugin_keys(keys: dict[str, str]):
    """Updates plugin API keys in .env and runtime environment."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")

    # Map frontend key names to .env variables
    key_mapping = {
        "github_token": "GITHUB_TOKEN",
        "homeassistant_url": "HOMEASSISTANT_URL",
        "eth_rpc_url": "ETH_RPC_URL",
        "database_url": "DATABASE_URL"
    }

    updates = {}
    for k, v in keys.items():
        if k in key_mapping and v:
            # Only update if it's not a masked string
            if '***' not in v and '...' not in v:
                updates[key_mapping[k]] = v

    if updates:
        update_env_file(env_path, updates)

    return {"success": True, "updated_keys": list(updates.keys())}

