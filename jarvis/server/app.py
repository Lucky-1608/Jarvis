"""
Jarvis OS — FastAPI Application.

Main application entry point with CORS, lifecycle hooks,
and all API routes mounted. Also serves the built frontend.
"""

from __future__ import annotations

import os

import traceroot
from dotenv import load_dotenv

load_dotenv()
traceroot.initialize()

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from jarvis.brain.jarvis_brain import JarvisBrain
from jarvis.server.dependencies import set_brain
from jarvis.server.routes import (
    agents,
    chat,
    health,
    hud,
    memory,
    oauth,
    settings,
    telegram,
    tools,
    vision,
    voice,
    whatsapp,
    workflows,
    companion,
)

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

    from jarvis.database.core import Base, engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    brain = JarvisBrain()
    await brain.initialize()
    set_brain(brain)

    # Start Node.js bridges automatically
    import subprocess
    
    base_dir = Path(__file__).resolve().parent.parent
    whatsapp_dir = base_dir / "whatsapp-bridge"
    telegram_dir = base_dir / "telegram-bridge"

    whatsapp_proc = None
    telegram_proc = None

    if (whatsapp_dir / "index.js").exists():
        logger.info("Starting WhatsApp bridge...")
        try:
            whatsapp_proc = subprocess.Popen(
                ["node", "index.js"],
                cwd=str(whatsapp_dir),
            )
        except Exception as e:
            logger.error("Failed to start WhatsApp bridge", error=str(e))

    if (telegram_dir / "index.js").exists():
        logger.info("Starting Telegram bridge...")
        try:
            telegram_proc = subprocess.Popen(
                ["node", "index.js"],
                cwd=str(telegram_dir),
            )
        except Exception as e:
            logger.error("Failed to start Telegram bridge", error=str(e))

    logger.info("server.ready", docs="/docs")
    yield

    # Shutdown
    if whatsapp_proc:
        logger.info("Stopping WhatsApp bridge...")
        whatsapp_proc.terminate()
    if telegram_proc:
        logger.info("Stopping Telegram bridge...")
        telegram_proc.terminate()

    if brain:
        await brain.shutdown()
    logger.info("server.stopped")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
from starlette.middleware.sessions import SessionMiddleware


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

    # Session Middleware is required for Authlib OAuth
    app.add_middleware(SessionMiddleware, secret_key=os.getenv("JARVIS_SECRET_KEY", "fallback-secret-for-oauth"))

    # --- Security Middleware ---

    @app.middleware("http")
    async def api_key_auth(request: Request, call_next):
        path = request.url.path

        # Allow CORS preflight requests
        if request.method == "OPTIONS":
            return await call_next(request)

        # Only enforce API key authentication on /api/ routes
        # This allows SPA frontend routes (e.g. /settings) to load without an API key
        if not path.startswith("/api/"):
            return await call_next(request)

        # Whitelist public API routes
        if path == "/api/health" or path.startswith("/api/oauth"):
            return await call_next(request)

        # Check header or query param
        client_key = request.headers.get("X-API-Key") or request.query_params.get("token")

        from jarvis.config.settings import get_settings
        settings = get_settings()

        # Actively enforce authentication if enabled
        if settings.server.require_auth:
            if not client_key or client_key != settings.server.secret_key:
                return JSONResponse(status_code=403, content={"detail": "Forbidden: Invalid or missing API Key"})

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
    app.include_router(companion.router, prefix="/api", tags=["Companion"])
    app.include_router(oauth.router, prefix="/api/oauth", tags=["OAuth"])
    app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])

    @app.get("/", tags=["Root"])
    async def root():
        if FRONTEND_DIST.is_dir():
            return FileResponse(str(FRONTEND_DIST / "index.html"))
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
