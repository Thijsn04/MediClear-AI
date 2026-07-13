"""
Endpoint-level dependencies: authentication + rate limiting.

A single ``Depends(rate_limited_identity)`` on a route enforces (in order) the
API-key check and the per-identity rate limit, and returns the caller identity
for downstream use (audit logging).
"""

from __future__ import annotations

from fastapi import Depends, Request

from app.config import Settings, get_settings
from app.core.exceptions import RateLimitError
from app.core.rate_limit import RateLimiter
from app.core.security import authenticate
from app.dependencies import get_rate_limiter


async def rate_limited_identity(
    request: Request,
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> str:
    identity = authenticate(request, settings)
    if not settings.rate_limit_enabled:
        return identity
    allowed, retry_after = await limiter.check(identity)
    if not allowed:
        raise RateLimitError(retry_after)
    return identity
