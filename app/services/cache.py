"""
Result cache.

Identical analysis requests (same document content, language, target level, and
model) reuse a cached structured result instead of re-billing the provider.
Backed by Redis when configured (shared across instances) or an in-process
TTL-LRU otherwise. Cache keys are salted hashes of content - the raw document
is never used as a key and never leaves the process for the in-memory backend.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from typing import Protocol

from app.core.logging import get_logger
from app.models.analysis import StructuredAnalysis

logger = get_logger(__name__)


def make_key(*parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
    return f"mediclear:analysis:{digest}"


class CacheBackend(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, ttl_seconds: int) -> None: ...


class InMemoryCache:
    """TTL-bounded LRU cache for single-instance deployments."""

    def __init__(self, max_entries: int = 1024) -> None:
        self._store: OrderedDict[str, tuple[float, str]] = OrderedDict()
        self._max = max_entries

    async def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            self._store.pop(key, None)
            return None
        self._store.move_to_end(key)
        return value

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self._store[key] = (time.monotonic() + ttl_seconds, value)
        self._store.move_to_end(key)
        while len(self._store) > self._max:
            self._store.popitem(last=False)


class RedisCache:
    """Redis-backed cache for multi-instance deployments."""

    def __init__(self, client) -> None:
        self._redis = client

    async def get(self, key: str) -> str | None:
        value = await self._redis.get(key)
        return value.decode() if isinstance(value, bytes) else value

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        await self._redis.set(key, value, ex=ttl_seconds)


class ResultCache:
    """Serialises/deserialises StructuredAnalysis through a CacheBackend."""

    def __init__(self, backend: CacheBackend, ttl_seconds: int, enabled: bool = True) -> None:
        self._backend = backend
        self._ttl = ttl_seconds
        self._enabled = enabled

    async def get(self, key: str) -> StructuredAnalysis | None:
        if not self._enabled:
            return None
        raw = await self._backend.get(key)
        if raw is None:
            return None
        try:
            return StructuredAnalysis.model_validate(json.loads(raw))
        except Exception:  # noqa: BLE001
            return None

    async def set(self, key: str, analysis: StructuredAnalysis) -> None:
        if not self._enabled:
            return
        try:
            await self._backend.set(key, analysis.model_dump_json(), self._ttl)
        except Exception as exc:  # noqa: BLE001 - caching must never break a request
            logger.warning("cache.set_failed", error=str(exc))
