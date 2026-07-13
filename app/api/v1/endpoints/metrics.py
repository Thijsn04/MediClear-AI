"""Prometheus metrics endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.config import Settings, get_settings
from app.core import metrics
from app.core.exceptions import FeatureDisabledError

router = APIRouter()


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Exposes request and token-usage metrics in Prometheus text format.",
    tags=["System"],
    include_in_schema=False,
)
async def prometheus_metrics(settings: Settings = Depends(get_settings)) -> Response:
    if not settings.metrics_enabled or not metrics.is_available():
        raise FeatureDisabledError("metrics")
    payload, content_type = metrics.render()
    return Response(content=payload, media_type=content_type)
