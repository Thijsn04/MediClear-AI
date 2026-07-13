"""
Rate limiting — fixed-window counters keyed by caller identity.

Uses Redis (atomic INCR + EXPIRE) when configured so limits hold across
instances; otherwise an in-process counter. Simple, predictable, and good
enough to protect an operator's AI budget from runaway callers.
"""

from __future__ import annotations

import time
from collections import defaultdict

from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Abstract fixed-window limiter. Returns (allowed, retry_after_seconds)."""

    async def check(self, identity: str) -> tuple[bool, int]:  # pragma: no cover
        raise NotImplementedError


class InMemoryRateLimiter(RateLimiter):
    def __init__(self, limit: int, window_seconds: int) -> None:
        self._limit = limit
        self._window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def check(self, identity: str) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - self._window
        hits = [t for t in self._hits[identity] if t > cutoff]
        if len(hits) >= self._limit:
            retry_after = int(self._window - (now - hits[0])) + 1
            self._hits[identity] = hits
            return False, max(1, retry_after)
        hits.append(now)
        self._hits[identity] = hits
        return True, 0


class RedisRateLimiter(RateLimiter):
    def __init__(self, client, limit: int, window_seconds: int) -> None:
        self._redis = client
        self._limit = limit
        self._window = window_seconds

    async def check(self, identity: str) -> tuple[bool, int]:
        key = f"mediclear:ratelimit:{identity}:{int(time.time()) // self._window}"
        try:
            count = await self._redis.incr(key)
            if count == 1:
                await self._redis.expire(key, self._window)
            if count > self._limit:
                ttl = await self._redis.ttl(key)
                return False, max(1, int(ttl))
            return True, 0
        except Exception as exc:  # noqa: BLE001 — fail open, never block on limiter errors
            logger.warning("ratelimit.backend_error", error=str(exc))
            return True, 0


class NullRateLimiter(RateLimiter):
    async def check(self, identity: str) -> tuple[bool, int]:
        return True, 0
