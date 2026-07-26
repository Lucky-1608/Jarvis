"""
Jarvis OS — FastAPI Application.

Main application entry point with CORS, lifecycle hooks,
and all API routes mounted.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from jarvis.brain.jarvis_brain import JarvisBrain
from jarvis.server.dependencies import set_brain, get_brain
from jarvis.server.routes import chat, health, memory, tools, vision, voice, hud

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle for the FastAPI server."""
    logger.info("server.starting")

    brain = JarvisBrain()
    await brain.initialize()
    set_brain(brain)

    logger.info("server.ready", docs="/docs")
    yield

    # Shutdown
    if brain:
        await brain.shutdown()
    logger.info("server.stopped")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Jarvis OS",
        description="AI Operating System — API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — allow the frontend (and any local dev tools)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # tighten in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    import os
    from fastapi import Request
    from fastapi.responses import JSONResponse
    
    API_KEY = os.getenv("JARVIS_API_KEY", "JARVIS_DEV_KEY")
    
    @app.middleware("http")
    async def api_key_auth(request: Request, call_next):
        # Allow unrestricted access to docs and root
        if request.url.path in ["/", "/docs", "/openapi.json"]:
            return await call_next(request)
            
        # Check header or query param
        client_key = request.headers.get("X-API-Key") or request.query_params.get("token")
        
        if client_key != API_KEY:
            return JSONResponse(status_code=403, content={"detail": "Forbidden: Invalid API Key"})
            
        return await call_next(request)

    # Mount route modules
    app.include_router(chat.router, prefix="/api", tags=["Chat"])
    app.include_router(memory.router, prefix="/api", tags=["Memory"])
    app.include_router(tools.router, prefix="/api", tags=["Tools"])
    app.include_router(voice.router, prefix="/api", tags=["Voice"])
    app.include_router(vision.router, prefix="/api", tags=["Vision"])
    app.include_router(health.router, prefix="/api", tags=["Health"])
    app.include_router(hud.router, prefix="/api", tags=["HUD"])

    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": "Jarvis OS",
            "version": "0.1.0",
            "status": "online",
            "docs": "/docs",
        }

    return app


# Default app instance for ``uvicorn jarvis.server.app:app``
app = create_app()
