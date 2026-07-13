"""
Dependency providers.

Module-level singletons (lazily built, process-lifetime cached) wire the whole
object graph from settings: the Redis client (when configured), the session
store, the result cache, the rate limiter, and the orchestration service.
Choosing Redis vs. in-memory happens here and nowhere else.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.core.logging import get_logger
from app.core.rate_limit import (
    InMemoryRateLimiter,
    NullRateLimiter,
    RateLimiter,
    RedisRateLimiter,
)
from app.providers.registry import build_provider
from app.services.ai_service import AIService
from app.services.cache import InMemoryCache, RedisCache, ResultCache
from app.services.document_service import DocumentService
from app.services.session_store import (
    InMemorySessionStore,
    RedisSessionStore,
    SessionStore,
)
from app.services.terminology import TerminologyService
from app.services.tts_service import TTSService

logger = get_logger(__name__)


@lru_cache
def get_redis():
    """Return an async Redis client, or None if not configured/available."""
    settings = get_settings()
    if not settings.use_redis:
        return None
    try:
        from redis.asyncio import Redis

        return Redis.from_url(settings.redis_url)
    except ImportError:
        logger.warning("redis.unavailable", detail="redis not installed; using in-memory")
        return None


@lru_cache
def get_session_store() -> SessionStore:
    settings = get_settings()
    redis = get_redis()
    if redis is not None:
        return RedisSessionStore(redis, ttl_seconds=settings.session_ttl_seconds)
    return InMemorySessionStore(
        ttl_seconds=settings.session_ttl_seconds,
        max_sessions=settings.max_sessions,
    )


@lru_cache
def get_result_cache() -> ResultCache:
    settings = get_settings()
    redis = get_redis()
    backend = RedisCache(redis) if redis is not None else InMemoryCache(settings.cache_max_entries)
    return ResultCache(
        backend, ttl_seconds=settings.cache_ttl_seconds, enabled=settings.cache_enabled
    )


@lru_cache
def get_rate_limiter() -> RateLimiter:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return NullRateLimiter()
    redis = get_redis()
    if redis is not None:
        return RedisRateLimiter(
            redis, settings.rate_limit_requests, settings.rate_limit_window_seconds
        )
    return InMemoryRateLimiter(settings.rate_limit_requests, settings.rate_limit_window_seconds)


@lru_cache
def get_terminology_service() -> TerminologyService:
    settings = get_settings()
    return TerminologyService(
        enabled=settings.terminology_enabled,
        online=settings.terminology_online,
        timeout_seconds=settings.terminology_timeout_seconds,
    )


@lru_cache
def get_ai_service() -> AIService:
    settings = get_settings()
    provider = build_provider(settings)
    return AIService(
        provider=provider,
        terminology=get_terminology_service(),
        session_store=get_session_store(),
        cache=get_result_cache(),
        settings=settings,
    )


@lru_cache
def get_document_service() -> DocumentService:
    settings = get_settings()
    return DocumentService(
        max_upload_size_mb=settings.max_upload_size_mb, enable_ocr=settings.enable_ocr
    )


@lru_cache
def get_tts_service() -> TTSService:
    settings = get_settings()
    return TTSService(backend=settings.tts_backend)
