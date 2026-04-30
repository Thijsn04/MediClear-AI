"""
In-memory chat session store with automatic TTL expiry.

For single-instance deployments this is sufficient.
For multi-instance / HA deployments, replace this with a Redis-backed
implementation that satisfies the same interface.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from app.core.exceptions import SessionNotFoundError
from app.core.logging import get_logger
from app.providers.base import ConversationMessage

logger = get_logger(__name__)


@dataclass
class ChatSession:
    """All state required to continue a conversation about an analysed document."""

    id: str
    provider: str
    model: str
    language: str
    language_name: str
    document_summary: str
    history: list[ConversationMessage] = field(default_factory=list)
    created_at: float = field(default_factory=time.monotonic)
    last_accessed: float = field(default_factory=time.monotonic)

    def touch(self) -> None:
        """Update the last-accessed timestamp."""
        self.last_accessed = time.monotonic()

    def is_expired(self, ttl_seconds: int) -> bool:
        return (time.monotonic() - self.last_accessed) > ttl_seconds


class SessionStore:
    """Thread-safe (GIL-protected) in-memory session store."""

    def __init__(self, ttl_seconds: int = 3600, max_sessions: int = 1000) -> None:
        self._store: dict[str, ChatSession] = {}
        self._ttl = ttl_seconds
        self._max_sessions = max_sessions

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(
        self,
        provider: str,
        model: str,
        language: str,
        language_name: str,
        document_summary: str,
        initial_history: Optional[list[ConversationMessage]] = None,
    ) -> ChatSession:
        """Create and store a new session, returning it."""
        self._evict_expired()

        if len(self._store) >= self._max_sessions:
            self._evict_oldest()

        session_id = str(uuid.uuid4())
        session = ChatSession(
            id=session_id,
            provider=provider,
            model=model,
            language=language,
            language_name=language_name,
            document_summary=document_summary,
            history=list(initial_history or []),
        )
        self._store[session_id] = session
        logger.info("session.created", session_id=session_id, provider=provider)
        return session

    def get(self, session_id: str) -> ChatSession:
        """Retrieve a session or raise SessionNotFoundError."""
        session = self._store.get(session_id)
        if session is None or session.is_expired(self._ttl):
            self._store.pop(session_id, None)
            raise SessionNotFoundError(session_id)
        session.touch()
        return session

    def append_message(self, session_id: str, role: str, content: str) -> None:
        """Append a message to an existing session's history."""
        session = self.get(session_id)
        session.history.append(ConversationMessage(role=role, content=content))

    def count(self) -> int:
        """Return the number of active (non-expired) sessions."""
        self._evict_expired()
        return len(self._store)

    # ------------------------------------------------------------------
    # Eviction
    # ------------------------------------------------------------------

    def _evict_expired(self) -> None:
        expired = [sid for sid, s in self._store.items() if s.is_expired(self._ttl)]
        for sid in expired:
            del self._store[sid]
        if expired:
            logger.debug("session.evicted", count=len(expired))

    def _evict_oldest(self) -> None:
        if not self._store:
            return
        oldest_id = min(self._store, key=lambda sid: self._store[sid].last_accessed)
        del self._store[oldest_id]
        logger.warning("session.evicted_oldest", session_id=oldest_id)
