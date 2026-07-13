"""
Idempotency store.

Lets clients safely retry POST requests: send the same ``Idempotency-Key``
header and, within the TTL, get back the exact response the first call produced
instead of triggering (and paying for) a second analysis. Backed by the same
in-memory or Redis backend as the result cache.
"""

from __future__ import annotations

from app.services.cache import CacheBackend


class IdempotencyStore:
    def __init__(self, backend: CacheBackend, ttl_seconds: int = 86_400) -> None:
        self._backend = backend
        self._ttl = ttl_seconds

    @staticmethod
    def _key(identity: str, idempotency_key: str) -> str:
        return f"mediclear:idem:{identity}:{idempotency_key}"

    async def get(self, identity: str, idempotency_key: str) -> str | None:
        return await self._backend.get(self._key(identity, idempotency_key))

    async def set(self, identity: str, idempotency_key: str, body: str) -> None:
        await self._backend.set(self._key(identity, idempotency_key), body, self._ttl)
