"""
Chat session storage.

An abstract, async interface with two implementations:

* :class:`InMemorySessionStore` — TTL + LRU eviction, single-instance.
* :class:`RedisSessionStore`   — durable, multi-instance, TTL via Redis.

Unlike the previous version, a session stores the **document context** used to
ground follow-up answers (the source text or, for images, the rendered
analysis) — not merely the AI's own summary — so chat can be faithful to the
original document.
"""

from __future__ import annotations

import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Optional

from app.core.exceptions import SessionNotFoundError
from app.core.logging import get_logger
from app.providers.base import ConversationMessage

logger = get_logger(__name__)


@dataclass
class ChatSession:
    id: str
    provider: str
    model: str
    language: str
    language_name: str
    document_context: str  # grounding context for follow-up chat
    history: list[ConversationMessage] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)

    def touch(self) -> None:
        self.last_accessed = time.time()

    def is_expired(self, ttl_seconds: int) -> bool:
        return (time.time() - self.last_accessed) > ttl_seconds

    def to_json(self) -> str:
        data = asdict(self)
        return json.dumps(data)

    @classmethod
    def from_json(cls, raw: str) -> "ChatSession":
        data = json.loads(raw)
        data["history"] = [ConversationMessage(**m) for m in data.get("history", [])]
        return cls(**data)


class SessionStore(ABC):
    """Async session storage interface."""

    @abstractmethod
    async def create(
        self,
        *,
        provider: str,
        model: str,
        language: str,
        language_name: str,
        document_context: str,
        initial_history: Optional[list[ConversationMessage]] = None,
    ) -> ChatSession: ...

    @abstractmethod
    async def get(self, session_id: str) -> ChatSession: ...

    @abstractmethod
    async def append_message(self, session_id: str, role: str, content: str) -> None: ...

    @abstractmethod
    async def delete(self, session_id: str) -> None: ...

    @abstractmethod
    async def count(self) -> int: ...

    async def health_ok(self) -> bool:
        return True


class InMemorySessionStore(SessionStore):
    def __init__(self, ttl_seconds: int = 3600, max_sessions: int = 1000) -> None:
        self._store: dict[str, ChatSession] = {}
        self._ttl = ttl_seconds
        self._max_sessions = max_sessions

    async def create(
        self,
        *,
        provider: str,
        model: str,
        language: str,
        language_name: str,
        document_context: str,
        initial_history: Optional[list[ConversationMessage]] = None,
    ) -> ChatSession:
        self._evict_expired()
        if len(self._store) >= self._max_sessions:
            self._evict_oldest()
        session = ChatSession(
            id=str(uuid.uuid4()),
            provider=provider,
            model=model,
            language=language,
            language_name=language_name,
            document_context=document_context,
            history=list(initial_history or []),
        )
        self._store[session.id] = session
        logger.info("session.created", session_id=session.id, provider=provider)
        return session

    async def get(self, session_id: str) -> ChatSession:
        session = self._store.get(session_id)
        if session is None or session.is_expired(self._ttl):
            self._store.pop(session_id, None)
            raise SessionNotFoundError(session_id)
        session.touch()
        return session

    async def append_message(self, session_id: str, role: str, content: str) -> None:
        session = await self.get(session_id)
        session.history.append(ConversationMessage(role=role, content=content))

    async def delete(self, session_id: str) -> None:
        self._store.pop(session_id, None)

    async def count(self) -> int:
        self._evict_expired()
        return len(self._store)

    def _evict_expired(self) -> None:
        expired = [sid for sid, s in self._store.items() if s.is_expired(self._ttl)]
        for sid in expired:
            del self._store[sid]

    def _evict_oldest(self) -> None:
        if not self._store:
            return
        oldest = min(self._store, key=lambda sid: self._store[sid].last_accessed)
        del self._store[oldest]
        logger.warning("session.evicted_oldest", session_id=oldest)


class RedisSessionStore(SessionStore):
    """Durable, multi-instance session store backed by Redis."""

    _PREFIX = "mediclear:session:"

    def __init__(self, client, ttl_seconds: int = 3600) -> None:
        self._redis = client
        self._ttl = ttl_seconds

    def _key(self, session_id: str) -> str:
        return f"{self._PREFIX}{session_id}"

    async def create(
        self,
        *,
        provider: str,
        model: str,
        language: str,
        language_name: str,
        document_context: str,
        initial_history: Optional[list[ConversationMessage]] = None,
    ) -> ChatSession:
        session = ChatSession(
            id=str(uuid.uuid4()),
            provider=provider,
            model=model,
            language=language,
            language_name=language_name,
            document_context=document_context,
            history=list(initial_history or []),
        )
        await self._redis.set(self._key(session.id), session.to_json(), ex=self._ttl)
        return session

    async def get(self, session_id: str) -> ChatSession:
        raw = await self._redis.get(self._key(session_id))
        if raw is None:
            raise SessionNotFoundError(session_id)
        session = ChatSession.from_json(raw.decode() if isinstance(raw, bytes) else raw)
        session.touch()
        await self._redis.set(self._key(session_id), session.to_json(), ex=self._ttl)
        return session

    async def append_message(self, session_id: str, role: str, content: str) -> None:
        session = await self.get(session_id)
        session.history.append(ConversationMessage(role=role, content=content))
        await self._redis.set(self._key(session_id), session.to_json(), ex=self._ttl)

    async def delete(self, session_id: str) -> None:
        await self._redis.delete(self._key(session_id))

    async def count(self) -> int:
        count = 0
        async for _ in self._redis.scan_iter(match=f"{self._PREFIX}*"):
            count += 1
        return count

    async def health_ok(self) -> bool:
        try:
            return bool(await self._redis.ping())
        except Exception:  # noqa: BLE001
            return False
