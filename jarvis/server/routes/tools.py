"""
Jarvis OS — Tools API Routes.

GET  /api/tools           — List all registered tools
POST /api/tools/execute   — Execute a tool directly
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from jarvis.server.dependencies import get_brain

router = APIRouter()


class ExecuteToolRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the tool to execute")
    params: dict = Field(default_factory=dict, description="Tool parameters")


@router.get("/tools")
async def list_tools():
    """List all registered tools with their metadata."""
    brain = get_brain()
    tools = brain.tools.list_all()

    return {
        "count": len(tools),
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category.value,
                "dangerous": t.dangerous,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "description": p.description,
                        "required": p.required,
                    }
                    for p in t.parameters
                ],
            }
            for t in tools
        ],
    }


@router.post("/tools/execute")
async def execute_tool(request: ExecuteToolRequest):
    """Execute a specific tool with parameters."""
    brain = get_brain()

    # Check if the tool exists
    tool = brain.tools.get(request.tool_name)
    if tool is None:
        return {"success": False, "error": f"Tool '{request.tool_name}' not found."}

    # Warn about dangerous tools
    if tool.is_dangerous:
        # In production, this would require additional confirmation
        pass

    from jarvis.executor.executor import Executor
    from jarvis.verification.verifier import Verifier

    executor = Executor(brain.tools, Verifier())
    result = await executor.execute_single_tool(request.tool_name, request.params)

    return result.to_dict()
