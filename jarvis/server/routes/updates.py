"""
Jarvis OS — App Update Management API Routes.

Provides endpoints to:
- Check for mandatory/optional updates from desktop and web clients
- Retrieve the latest version, release notes, and installer download URLs
- Provide Tauri-compatible updater manifest (latest.json)
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import httpx
import structlog
from fastapi import APIRouter, Query
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

router = APIRouter()

VERSION_FILE = Path(__file__).resolve().parent.parent.parent / "version.json"
GITHUB_REPO = os.getenv("JARVIS_GITHUB_REPO", "Lucky-1608/Jarvis")

# In-memory cache for GitHub release checks (120 seconds TTL)
_release_cache: Dict[str, Any] = {
    "timestamp": 0.0,
    "data": None,
}


def _parse_version(v_str: str) -> Tuple[int, ...]:
    """Parse version string like '1.2.3' or 'v1.2.3' into a comparable tuple."""
    cleaned = re.sub(r"^[^\d]*", "", str(v_str).strip())
    parts = []
    for token in cleaned.split("."):
        num_match = re.match(r"^(\d+)", token)
        if num_match:
            parts.append(int(num_match.group(1)))
        else:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:4])


def _load_local_version_config() -> Dict[str, Any]:
    """Read local version.json metadata."""
    if VERSION_FILE.exists():
        try:
            with open(VERSION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("failed_reading_version_file", error=str(e))
    return {
        "version": "1.0.0",
        "min_required_version": "1.0.0",
        "latest_version": "1.0.0",
        "mandatory": True,
        "title": "Jarvis OS Mandatory Update",
        "release_notes": "Frontend and core system updates.",
        "download_url": f"https://github.com/{GITHUB_REPO}/releases/latest",
    }


async def _fetch_github_latest_release() -> Optional[Dict[str, Any]]:
    """Fetch the latest release info from GitHub API with caching."""
    now = time.time()
    if _release_cache["data"] and (now - _release_cache["timestamp"] < 120):
        return _release_cache["data"]

    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "Jarvis-OS-Updater"}
    try:
        async with httpx.AsyncClient(timeout=3.5) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                _release_cache["timestamp"] = now
                _release_cache["data"] = data
                return data
    except Exception as e:
        logger.debug("github_release_fetch_skipped", error=str(e))
    return _release_cache["data"]


class UpdateCheckResponse(BaseModel):
    update_available: bool
    mandatory: bool
    current_version: str
    latest_version: str
    title: str
    release_notes: str
    download_url: str
    published_at: Optional[str] = None


@router.get("/updates/check", response_model=UpdateCheckResponse)
async def check_for_updates(
    current_version: str = Query("1.0.0", description="Current client application version"),
    platform: str = Query("windows", description="Client OS platform (windows, macos, linux, android)"),
):
    """
    Check if a mandatory update is available for the given client version.
    Returns update status, latest version, changelog, and direct download URL.
    """
    local_cfg = _load_local_version_config()
    latest_ver_str = os.getenv("JARVIS_LATEST_VERSION", local_cfg.get("latest_version", "1.0.0"))
    release_notes = local_cfg.get("release_notes", "Important frontend and system updates.")
    download_url = local_cfg.get("download_url", f"https://github.com/{GITHUB_REPO}/releases/latest")
    title = local_cfg.get("title", f"Jarvis OS v{latest_ver_str} Update Required")
    published_at = None

    # Attempt to query GitHub Releases for dynamically published releases
    gh_release = await _fetch_github_latest_release()
    if gh_release and "tag_name" in gh_release:
        tag = gh_release["tag_name"]
        gh_ver = _parse_version(tag)
        if gh_ver > _parse_version(latest_ver_str):
            latest_ver_str = tag.lstrip("v")
            title = gh_release.get("name") or f"Jarvis OS v{latest_ver_str}"
            release_notes = gh_release.get("body") or release_notes
            published_at = gh_release.get("published_at")

            # Look for platform-specific asset in GitHub release
            assets = gh_release.get("assets", [])
            plat_lower = platform.lower()
            for asset in assets:
                name = asset.get("name", "").lower()
                if plat_lower == "windows" and (name.endswith(".exe") or name.endswith("-setup.exe") or name.endswith(".msi")):
                    download_url = asset.get("browser_download_url", download_url)
                    break
                elif plat_lower == "android" and name.endswith(".apk"):
                    download_url = asset.get("browser_download_url", download_url)
                    break
                elif plat_lower == "ios" and name.endswith(".ipa"):
                    download_url = asset.get("browser_download_url", download_url)
                    break
            else:
                download_url = gh_release.get("html_url", download_url)

    # Compare versions
    current_parsed = _parse_version(current_version)
    latest_parsed = _parse_version(latest_ver_str)
    update_available = latest_parsed > current_parsed

    # By default, updates are mandatory as requested by user
    mandatory = local_cfg.get("mandatory", True) if update_available else False

    return UpdateCheckResponse(
        update_available=update_available,
        mandatory=mandatory,
        current_version=current_version,
        latest_version=latest_ver_str,
        title=title,
        release_notes=release_notes,
        download_url=download_url,
        published_at=published_at,
    )


@router.get("/updates/version")
async def get_version():
    """Return the current local backend/system version."""
    local_cfg = _load_local_version_config()
    return {
        "status": "online",
        "system": "Jarvis OS",
        "version": local_cfg.get("version", "1.0.0"),
        "latest_version": local_cfg.get("latest_version", "1.0.0"),
        "mandatory_updates": local_cfg.get("mandatory", True),
    }


@router.get("/updates/latest.json")
async def get_tauri_updater_manifest(
    platform: str = Query("windows-x86_64", description="Target platform for Tauri updater"),
):
    """
    Tauri v2 updater schema endpoint.
    Used by Tauri's native auto-updater plugin.
    """
    local_cfg = _load_local_version_config()
    latest_ver = local_cfg.get("latest_version", "1.0.0")
    download_url = local_cfg.get("download_url", f"https://github.com/{GITHUB_REPO}/releases/latest")
    notes = local_cfg.get("release_notes", "Jarvis OS update available.")

    return {
        "version": latest_ver,
        "notes": notes,
        "pub_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "platforms": {
            platform: {
                "signature": "",
                "url": download_url,
            }
        },
    }

