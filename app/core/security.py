"""
API-key authentication.

When ``REQUIRE_API_KEY`` is on, every mutating ``/api/v1`` endpoint requires a
valid key supplied either as ``X-API-Key: <key>`` or
``Authorization: Bearer <key>``. Keys are compared in constant time. The
identity of the caller (the key, or the client IP when auth is disabled) is
returned so the rate limiter can key on it.
"""

from __future__ import annotations

import hashlib
import hmac

from fastapi import Request

from app.config import Settings, get_settings
from app.core.exceptions import AuthenticationError


def _extract_key(request: Request) -> str | None:
    header = request.headers.get("x-api-key")
    if header:
        return header.strip()
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


def _matches_any(candidate: str, keys: list[str]) -> bool:
    cand_hash = hashlib.sha256(candidate.encode()).digest()
    for key in keys:
        if hmac.compare_digest(cand_hash, hashlib.sha256(key.encode()).digest()):
            return True
    return False


def _client_ip(request: Request) -> str:
    # Trust the left-most X-Forwarded-For entry when behind a proxy, else peer.
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def authenticate(request: Request, settings: Settings | None = None) -> str:
    """Validate the caller and return a stable identity string for rate-limiting.

    Raises :class:`AuthenticationError` when a key is required but absent/invalid.
    """
    settings = settings or get_settings()
    if not settings.require_api_key:
        return f"ip:{_client_ip(request)}"

    key = _extract_key(request)
    if not key or not settings.api_keys or not _matches_any(key, settings.api_keys):
        raise AuthenticationError()
    # Identify by a short hash of the key so logs never contain the secret.
    return "key:" + hashlib.sha256(key.encode()).hexdigest()[:16]
