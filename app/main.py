"""
MediClear AI — FastAPI application factory.

Entry point:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.endpoints.metrics import router as metrics_router
from app.api.v1.router import router as api_v1_router
from app.config import get_settings
from app.core import metrics
from app.core.exceptions import MediClearException, RateLimitError
from app.core.logging import configure_logging, get_logger
from app.core.middleware import BodySizeLimitMiddleware, RequestContextMiddleware
from app.version import __version__

logger = get_logger(__name__)
_STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    logger.info(
        "mediclear.startup",
        version=__version__,
        provider=settings.ai_provider,
        environment=settings.environment,
        redis=settings.use_redis,
        zero_retention=settings.zero_retention,
    )
    yield
    logger.info("mediclear.shutdown")


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=__version__,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware (outermost first) ──────────────────────────────────────────
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_body_bytes)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Metrics timing ────────────────────────────────────────────────────────
    if settings.metrics_enabled and metrics.is_available():

        @app.middleware("http")
        async def _metrics_mw(request: Request, call_next):
            start = time.perf_counter()
            response = await call_next(request)
            route = request.scope.get("route")
            path = getattr(route, "path", None) or request.url.path
            metrics.record_request(
                request.method, path, response.status_code, time.perf_counter() - start
            )
            return response

    # ── Exception handlers (unified envelope) ─────────────────────────────────
    @app.exception_handler(MediClearException)
    async def _mediclear_handler(request: Request, exc: MediClearException) -> JSONResponse:
        logger.warning("mediclear.exception", status_code=exc.status_code, message=exc.message)
        headers = {}
        if isinstance(exc, RateLimitError):
            headers["Retry-After"] = str(exc.retry_after)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "status_code": exc.status_code,
                "request_id": _request_id(request),
            },
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation error",
                "status_code": 422,
                "detail": exc.errors(),
                "request_id": _request_id(request),
            },
        )

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(api_v1_router)
    app.include_router(metrics_router)

    from app.i18n.translations import TRANSLATIONS

    @app.get("/api/v1/translations", tags=["System"])
    async def get_translations():
        return JSONResponse(content=TRANSLATIONS)

    # ── Static frontend (optional) ────────────────────────────────────────────
    if settings.enable_frontend and _STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")
    elif not settings.enable_frontend:
        logger.info("mediclear.frontend_disabled")

    return app


app = create_app()
