"""
Jarvis OS — Memory API Routes.

GET  /api/memory/search  — Semantic search across memories
POST /api/memory         — Store a new memory
GET  /api/memory/stats   — Memory statistics
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from jarvis.memory.memory_manager import MemoryType
from jarvis.server.dependencies import get_brain

router = APIRouter()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class StoreMemoryRequest(BaseModel):
    content: str = Field(..., description="Content to store")
    memory_type: str = Field("conversations", description="Memory type")
    importance: float = Field(0.5, ge=0.0, le=1.0, description="Importance score")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class MemorySearchResult(BaseModel):
    id: str
    content: str
    memory_type: str
    score: float
    importance: float
    timestamp: float


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/memory/search")
async def search_memory(
    query: str = Query(..., description="Search query"),
    memory_type: str | None = Query(None, description="Filter by memory type"),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
):
    """Search memories by semantic similarity."""
    brain = get_brain()
    mem_type = MemoryType(memory_type) if memory_type else None

    results = await brain.memory.search(
        query=query,
        memory_type=mem_type,
        limit=limit,
    )

    return {
        "query": query,
        "results": [
            MemorySearchResult(
                id=r.entry.id,
                content=r.entry.content,
                memory_type=r.entry.memory_type.value,
                score=round(r.score, 4),
                importance=r.entry.importance,
                timestamp=r.entry.timestamp,
            ).model_dump()
            for r in results
        ],
    }


@router.get("/memory/recent")
async def recent_memory(
    memory_type: str | None = Query(None, description="Filter by memory type"),
    limit: int = Query(20, ge=1, le=50, description="Max results"),
):
    """Fetch recent memories."""
    brain = get_brain()
    mem_type = MemoryType(memory_type) if memory_type else None

    entries = await brain.memory.get_recent(
        memory_type=mem_type,
        limit=limit,
    )

    return {
        "results": [
            {
                "id": entry.id,
                "content": entry.content,
                "memory_type": entry.memory_type.value,
                "score": 1.0,  # Max score for recent fetch
                "importance": entry.importance,
                "timestamp": entry.timestamp,
            }
            for entry in entries
        ],
    }


@router.post("/memory")
async def store_memory(request: StoreMemoryRequest):
    """Store a new memory entry."""
    brain = get_brain()

    try:
        mem_type = MemoryType(request.memory_type)
    except ValueError:
        mem_type = MemoryType.CONVERSATION

    ids = await brain.memory.store(
        content=request.content,
        memory_type=mem_type,
        metadata=request.metadata,
        importance=request.importance,
    )

    return {"stored": True, "ids": ids, "memory_type": mem_type.value}


class UpdateMemoryRequest(BaseModel):
    content: str | None = Field(None, description="Updated content")
    metadata: dict | None = Field(None, description="Updated metadata")


@router.put("/memory/{entry_id}")
async def update_memory(entry_id: str, request: UpdateMemoryRequest):
    """Update a specific memory entry."""
    brain = get_brain()
    success = await brain.memory.update_entry(
        entry_id=entry_id, 
        content=request.content, 
        metadata=request.metadata
    )
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"success": True, "id": entry_id}


@router.delete("/memory/{entry_id}")
async def delete_memory(entry_id: str):
    """Delete a specific memory entry."""
    brain = get_brain()
    success = await brain.memory.delete_entry(entry_id)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"success": True, "id": entry_id}


@router.get("/memory/stats")
async def memory_stats():
    """Return memory system statistics."""
    brain = get_brain()
    return await brain.memory.get_stats()
