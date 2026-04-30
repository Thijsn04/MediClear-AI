"""
MediClear AI — FastAPI application factory.

Entry point:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import router as api_v1_router
from app.config import get_settings
from app.core.exceptions import MediClearException
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)
_STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup / shutdown lifecycle."""
    configure_logging()
    settings = get_settings()
    logger.info(
        "mediclear.startup",
        version=settings.app_version,
        provider=settings.ai_provider,
        debug=settings.debug,
    )
    yield
    logger.info("mediclear.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global exception handler ──────────────────────────────────────────────
    @app.exception_handler(MediClearException)
    async def mediclear_exception_handler(
        request: Request, exc: MediClearException
    ) -> JSONResponse:
        logger.warning(
            "mediclear.exception",
            status_code=exc.status_code,
            message=exc.message,
            path=str(request.url),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message, "status_code": exc.status_code},
        )

    # ── API routes ────────────────────────────────────────────────────────────
    app.include_router(api_v1_router)

    # ── i18n translations endpoint ────────────────────────────────────────────
    from app.i18n.translations import TRANSLATIONS
    from fastapi.responses import JSONResponse as _JSONResponse

    @app.get("/api/v1/translations", tags=["System"], include_in_schema=True)
    async def get_translations():
        """Return all UI string translations for the frontend."""
        return _JSONResponse(content=TRANSLATIONS)

    # ── Static frontend (only when ENABLE_FRONTEND=true) ─────────────────────
    if settings.enable_frontend and _STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")
    elif not settings.enable_frontend:
        logger.info("mediclear.frontend_disabled")

    return app


app = create_app()
