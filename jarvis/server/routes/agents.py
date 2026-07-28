"""
Jarvis OS — Agents API Routes.

GET  /api/agents              — List all tracked agents (system + spawned)
GET  /api/agents/stats        — Agent statistics
POST /api/agents/spawn        — Spawn a new sub-agent
POST /api/agents/{id}/wake    — Wake a sleeping agent
POST /api/agents/{id}/terminate — Terminate an agent
"""

from __future__ import annotations
import time
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from jarvis.server.dependencies import get_brain
from jarvis.team.sub_agent import SubAgent
from jarvis.tools.builtin.team_tools import get_agent_history, _agent_history

router = APIRouter()


def _get_system_agents() -> list[dict]:
    """Return the built-in system agents that are always present."""
    brain = get_brain()
    tool_count = brain.tools.count if brain.tools else 0

    system_agents = [
        {
            "id": "sys_planner",
            "name": "Planner",
            "type": "SystemAgent",
            "persona": "Decomposes complex user requests into structured, multi-step execution plans using LLM reasoning.",
            "status": "running",
            "created_at": None,
            "task": f"Watching for complex requests to decompose",
        },
        {
            "id": "sys_executor",
            "name": "Executor",
            "type": "SystemAgent",
            "persona": "Executes tool-calling steps from the Planner's execution plans, with verification and error handling.",
            "status": "running",
            "created_at": None,
            "task": f"Ready to execute {tool_count} registered tools",
        },
        {
            "id": "sys_memory",
            "name": "MemoryManager",
            "type": "SystemAgent",
            "persona": "Manages long-term semantic memory, conversation context, and knowledge retrieval using vector embeddings.",
            "status": "running",
            "created_at": None,
            "task": "Storing and retrieving memories",
        },
        {
            "id": "sys_vision",
            "name": "VisionAnalyzer",
            "type": "SystemAgent",
            "persona": "Real-time environmental perception — captures screenshots, reads screens, detects UI elements and errors.",
            "status": "idle",
            "created_at": None,
            "task": "Waiting for vision requests",
        },
        {
            "id": "sys_voice",
            "name": "VoiceEngine",
            "type": "SystemAgent",
            "persona": "Handles speech-to-text transcription and text-to-speech synthesis using neural TTS voices.",
            "status": "idle",
            "created_at": None,
            "task": "Waiting for audio input/output",
        },
        {
            "id": "sys_browser",
            "name": "BrowserAutomation",
            "type": "BackgroundAgent",
            "persona": "Controls headless and visible browsers — navigates pages, extracts content, fills forms, clicks elements.",
            "status": "idle",
            "created_at": None,
            "task": "No active browser sessions",
        },
        {
            "id": "sys_desktop",
            "name": "DesktopAutomation",
            "type": "BackgroundAgent",
            "persona": "Controls the desktop environment — launches apps, types text, moves mouse, manages windows.",
            "status": "idle",
            "created_at": None,
            "task": "No active desktop tasks",
        },
        {
            "id": "sys_router",
            "name": "AIRouter",
            "type": "SystemAgent",
            "persona": "Intelligent model router — selects the best AI provider (OpenAI, Gemini, Ollama, etc.) based on task complexity and availability.",
            "status": "running",
            "created_at": None,
            "task": "Routing AI requests to optimal provider",
        },
    ]
    return system_agents


def _is_system_agent(agent_id: str) -> bool:
    return any(agent["id"] == agent_id for agent in _get_system_agents())


class SpawnAgentRequest(BaseModel):
    name: str = "DelegatedExpert"
    persona: str = "You are a helpful AI assistant."
    task: str = ""


@router.post("/agents/spawn")
async def spawn_agent(req: SpawnAgentRequest):
    """Spawn a new sub-agent with a given persona and task."""
    brain = get_brain()
    router = brain._router

    agent = SubAgent(name=req.name, persona=req.persona, router=router)

    agent_entry = {
        "id": f"agent_{int(time.time())}_{len(_agent_history)}",
        "name": req.name,
        "type": "SubAgent",
        "persona": req.persona[:200],
        "status": "running",
        "created_at": time.time(),
        "task": req.task[:200] if req.task else "No task assigned",
    }
    _agent_history.insert(0, agent_entry)

    if req.task:
        result = await agent.execute_task(req.task)
        agent_entry["status"] = "completed"
        agent_entry["completed_at"] = time.time()
        return {"success": True, "agent": agent_entry, "result": result}

    return {"success": True, "agent": agent_entry}


@router.post("/agents/{agent_id}/wake")
async def wake_agent(agent_id: str):
    """Wake a sleeping agent."""
    for agent in _agent_history:
        if agent["id"] == agent_id:
            agent["status"] = "running"
            agent["task"] = "Woken by user request"
            return {"success": True, "agent": agent}

    if _is_system_agent(agent_id):
        raise HTTPException(
            status_code=409,
            detail="Built-in agents are managed by Jarvis and cannot be woken manually.",
        )

    raise HTTPException(status_code=404, detail="Agent not found")


@router.post("/agents/{agent_id}/terminate")
async def terminate_agent(agent_id: str):
    """Terminate a spawned agent."""
    for i, agent in enumerate(_agent_history):
        if agent["id"] == agent_id:
            agent["status"] = "completed"
            agent["completed_at"] = time.time()
            agent["task"] = "Terminated by user"
            return {"success": True, "agent": agent}

    if _is_system_agent(agent_id):
        raise HTTPException(
            status_code=409,
            detail="Built-in agents are managed by Jarvis and cannot be terminated manually.",
        )

    raise HTTPException(status_code=404, detail="Agent not found")


@router.get("/agents")
async def list_agents():
    """List all agents — built-in system agents + dynamically spawned sub-agents."""
    system_agents = _get_system_agents()
    spawned_agents = get_agent_history()

    all_agents = system_agents + spawned_agents
    return {
        "count": len(all_agents),
        "agents": all_agents,
    }


@router.get("/agents/stats")
async def agent_stats():
    """Return agent statistics."""
    system_agents = _get_system_agents()
    spawned_agents = get_agent_history()
    all_agents = system_agents + spawned_agents

    running = sum(1 for a in all_agents if a.get("status") == "running")
    completed = sum(1 for a in all_agents if a.get("status") == "completed")
    idle = sum(1 for a in all_agents if a.get("status") == "idle")
    return {
        "total": len(all_agents),
        "running": running,
        "completed": completed,
        "idle": idle,
    }
