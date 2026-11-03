"""
Jarvis OS — Workflows API Routes.

GET /api/workflows       — List all execution plans/workflows
GET /api/workflows/stats — Workflow statistics
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from jarvis.server.dependencies import get_brain

router = APIRouter()


@router.get("/workflows")
async def list_workflows():
    """List all tracked execution plans."""
    brain = get_brain()
    workflows = brain.workflow_history
    return {
        "count": len(workflows),
        "workflows": workflows,
    }


@router.get("/workflows/stats")
async def workflow_stats():
    """Return workflow statistics."""
    brain = get_brain()
    workflows = brain.workflow_history
    completed = sum(1 for w in workflows if w.get("status") == "completed")
    running = sum(1 for w in workflows if w.get("status") == "running")
    failed = sum(1 for w in workflows if w.get("status") == "failed")
    return {
        "total": len(workflows),
        "completed": completed,
        "running": running,
        "failed": failed,
    }


@router.post("/workflows/{workflow_id}/approve")
async def approve_workflow(workflow_id: str):
    """Approve and resume one blocked workflow."""
    brain = get_brain()
    try:
        return await brain.approve_workflow(workflow_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Workflow not found or no longer pending")


@router.post("/workflows/{workflow_id}/cancel")
async def cancel_workflow(workflow_id: str):
    """Cancel one blocked workflow without executing it."""
    brain = get_brain()
    try:
        return brain.cancel_workflow(workflow_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Workflow not found or no longer pending")
