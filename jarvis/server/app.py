"""
Jarvis OS — FastAPI Application.

Main application entry point with CORS, lifecycle hooks,
and all API routes mounted. Also serves the built frontend.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from jarvis.brain.jarvis_brain import JarvisBrain
from jarvis.server.dependencies import set_brain, get_brain
from jarvis.server.routes import chat, health, memory, tools, vision, voice, hud, agents, workflows, whatsapp, telegram

logger = structlog.get_logger(__name__)

# Path to the built frontend
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

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

    API_KEY = os.getenv("JARVIS_API_KEY", "JARVIS_DEV_KEY")

    @app.middleware("http")
    async def api_key_auth(request: Request, call_next):
        # Allow unrestricted access to docs, root, and static frontend assets
        if request.url.path in ["/", "/docs", "/openapi.json"]:
            return await call_next(request)

        # Allow CORS preflight requests
        if request.method == "OPTIONS":
            return await call_next(request)

        # Allow frontend static files without API key
        if request.url.path.startswith("/assets/") or request.url.path in ["/favicon.svg", "/robots.txt"]:
            return await call_next(request)

        # SPA catch-all: let index.html through (API key handled by the JS)
        if request.url.path == "/index.html":
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
    app.include_router(agents.router, prefix="/api", tags=["Agents"])
    app.include_router(workflows.router, prefix="/api", tags=["Workflows"])
    app.include_router(whatsapp.router, prefix="/api", tags=["WhatsApp"])
    app.include_router(telegram.router, prefix="/api", tags=["Telegram"])

    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": "Jarvis OS",
            "version": "0.1.0",
            "status": "online",
            "docs": "/docs",
        }

    # ---------------------------------------------------------------
    # Serve the built frontend (dist/) for production
    # ---------------------------------------------------------------
    if FRONTEND_DIST.is_dir():
        logger.info("frontend.serving", path=str(FRONTEND_DIST))

        # Serve static assets
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="frontend_assets")

        # Serve root-level static files (favicon.svg, robots.txt)
        @app.get("/favicon.svg", include_in_schema=False)
        async def favicon():
            return FileResponse(str(FRONTEND_DIST / "favicon.svg"))

        @app.get("/robots.txt", include_in_schema=False)
        async def robots():
            return FileResponse(str(FRONTEND_DIST / "robots.txt"))

        # SPA catch-all: any non-API, non-asset path → index.html
        @app.get("/{catchall:path}", include_in_schema=False)
        async def frontend_spa(catchall: str):
            # Don't interfere with API routes
            if catchall.startswith("api/") or catchall.startswith("docs") or catchall.startswith("openapi"):
                return JSONResponse(status_code=404, content={"detail": "Not found"})
            return FileResponse(str(FRONTEND_DIST / "index.html"))
    else:
        logger.warning("frontend.not_found", path=str(FRONTEND_DIST),
                       hint="Run 'cd jarvis/frontend && npm run build' to build the frontend.")

    return app


# Default app instance for ``uvicorn jarvis.server.app:app``
app = create_app()
