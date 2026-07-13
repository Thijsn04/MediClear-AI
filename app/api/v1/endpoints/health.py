"""Health & readiness endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.dependencies import get_ai_service, get_session_store
from app.models.schemas import HealthResponse
from app.services.ai_service import AIService
from app.services.session_store import RedisSessionStore, SessionStore
from app.version import __version__

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description=(
        "Reports the active provider, whether it is configured, the session "
        "store backend and its liveness, and the active session count. Returns "
        "`unhealthy` if the session store (e.g. Redis) is unreachable, "
        "`degraded` if the provider is not configured."
    ),
    tags=["System"],
)
async def health_check(
    settings: Settings = Depends(get_settings),
    ai_service: AIService = Depends(get_ai_service),
    session_store: SessionStore = Depends(get_session_store),
) -> HealthResponse:
    provider = ai_service.provider
    configured = provider.is_configured

    store_ok = await session_store.health_ok()
    store_kind = "redis" if isinstance(session_store, RedisSessionStore) else "memory"
    active = await session_store.count() if store_ok else 0

    if not store_ok:
        status = "unhealthy"
    elif not configured:
        status = "degraded"
    else:
        status = "healthy"

    return HealthResponse(
        status=status,
        version=__version__,
        ai_provider=provider.name,
        ai_model=provider.model,
        ai_provider_configured=configured,
        ai_provider_reachable=None,
        session_store=store_kind,
        active_sessions=active,
        timestamp=datetime.now(timezone.utc),
    )
