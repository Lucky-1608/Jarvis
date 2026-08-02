"""
Jarvis OS — Health API Routes.

GET /api/health — Full system health check
"""

from __future__ import annotations

from fastapi import APIRouter

from jarvis.server.dependencies import get_brain

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Check the health of all Jarvis subsystems.

    Returns status for:
    - Brain (core orchestrator)
    - AI providers (OpenCode, Ollama)
    - Memory system (ChromaDB)
    - Tool registry
    """
    brain = get_brain()
    health = await brain.get_health()

    # Determine overall status
    overall = "healthy"
    if not health.get("initialized"):
        overall = "not_initialized"
    elif any(
        not p.get("available", False)
        for p in health.get("providers", {}).values()
    ):
        overall = "degraded"

    return {
        "status": overall,
        **health,
    }
