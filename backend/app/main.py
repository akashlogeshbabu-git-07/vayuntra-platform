"""
Vayuntra Control Plane — FastAPI Application Entry Point
Serves the dashboard UI from /static/index.html
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from pathlib import Path

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import router as api_v1_router
from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.logging import configure_logging

log = structlog.get_logger(__name__)
STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log.info("vayuntra.startup", version=settings.APP_VERSION, env=settings.APP_ENV)
    await init_db()
    log.info("vayuntra.ready", message="Control plane operational")
    yield
    log.info("vayuntra.shutdown")
    await close_db()


def create_application() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="Vayuntra Control Plane API",
        description="Autonomous AI Cyber Defense Platform",
        version=settings.APP_VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_v1_router, prefix="/api/v1")

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.exception_handler(Exception)
    async def global_exc_handler(request: Request, exc: Exception) -> JSONResponse:
        log.error("unhandled_exception", path=request.url.path, error=str(exc))
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": str(exc)})

    @app.get("/health", include_in_schema=False)
    async def health_check():
        return {"status": "healthy", "version": settings.APP_VERSION}

    @app.get("/", include_in_schema=False)
    async def serve_dashboard():
        index = STATIC_DIR / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return JSONResponse(status_code=404, content={"detail": "Dashboard not found"})

    return app


app = create_application()
