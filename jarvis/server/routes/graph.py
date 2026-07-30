"""Jarvis OS — Knowledge Graph API routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/graph", tags=["graph"])

# Reference to brain — set during app startup
_brain = None


def set_brain(brain):
    global _brain
    _brain = brain


def _get_graph(project_name: str):
    if not _brain or not hasattr(_brain, '_graph_registry') or not _brain._graph_registry:
        raise HTTPException(status_code=503, detail="Knowledge graph registry not available")
    graph = _brain._graph_registry.get_graph(project_name)
    if not graph:
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")
    return graph


class BuildRequest(BaseModel):
    project_name: str
    directory: str = "."


@router.post("/build")
async def build_graph(req: BuildRequest):
    graph = _get_graph(req.project_name)
    result = await graph.build(req.directory)
    return {"status": "ok", **result}


@router.get("/query")
async def query_graph(project_name: str = Query(...), q: str = Query(...), limit: int = Query(10)):
    graph = _get_graph(project_name)
    results = graph.search_entities(q, limit=limit)
    return {"query": q, "results": results}


@router.get("/explain/{entity}")
async def explain_entity(entity: str, project_name: str = Query(...)):
    graph = _get_graph(project_name)
    result = graph.explain(entity)
    if not result:
        raise HTTPException(status_code=404, detail=f"Entity '{entity}' not found")
    return result


@router.get("/path")
async def find_path(project_name: str = Query(...), source: str = Query(...), target: str = Query(...)):
    graph = _get_graph(project_name)
    result = graph.find_path(source, target)
    if not result:
        raise HTTPException(status_code=404, detail="No path found")
    return {"source": source, "target": target, "path": result}


@router.get("/stats")
async def graph_stats(project_name: str = Query(...)):
    graph = _get_graph(project_name)
    return graph.get_stats()


class AddProjectRequest(BaseModel):
    project_name: str
    directory: str


@router.post("/project")
async def add_project(req: AddProjectRequest):
    if not _brain or not hasattr(_brain, '_graph_registry') or not _brain._graph_registry:
        raise HTTPException(status_code=503, detail="Knowledge graph registry not available")
    await _brain._graph_registry.add_project(req.project_name, req.directory)
    return {"status": "ok", "project_name": req.project_name}


@router.get("/projects")
async def list_projects():
    if not _brain or not hasattr(_brain, '_graph_registry') or not _brain._graph_registry:
        raise HTTPException(status_code=503, detail="Knowledge graph registry not available")
    
    # Try multiple ways to get projects depending on registry implementation
    registry = _brain._graph_registry
    if hasattr(registry, 'list_projects'):
        projects = registry.list_projects()
    elif hasattr(registry, 'projects'):
        projects = list(registry.projects.keys())
    elif hasattr(registry, '_projects'):
        projects = list(registry._projects.keys())
    else:
        projects = []
    
    return {"projects": projects}
