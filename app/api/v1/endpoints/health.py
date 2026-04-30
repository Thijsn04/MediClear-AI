"""Health-check endpoint."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.dependencies import get_ai_service
from app.models.schemas import HealthResponse
from app.services.ai_service import AIService

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description=(
        "Returns the current health status of the API, including which AI "
        "provider is active, whether it is configured, and how many chat "
        "sessions are currently held in memory."
    ),
    tags=["System"],
)
async def health_check(
    ai_service: AIService = Depends(get_ai_service),
) -> HealthResponse:
    provider = ai_service.provider
    configured = provider.is_configured
    active = ai_service.session_store.count()

    status = "healthy" if configured else "degraded"

    return HealthResponse(
        status=status,
        version="2.0.0",
        ai_provider=provider.name,
        ai_model=provider.model,
        ai_provider_configured=configured,
        active_sessions=active,
        timestamp=datetime.now(timezone.utc),
    )
