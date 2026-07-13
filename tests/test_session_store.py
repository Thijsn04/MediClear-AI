"""Tests for the in-memory session store."""

from __future__ import annotations

import pytest

from app.core.exceptions import SessionNotFoundError
from app.services.session_store import InMemorySessionStore


async def _make(store: InMemorySessionStore) -> str:
    session = await store.create(
        provider="mock",
        model="mock-model",
        language="en",
        language_name="English",
        document_context="source document text",
    )
    return session.id


@pytest.mark.asyncio
async def test_create_and_get() -> None:
    store = InMemorySessionStore()
    sid = await _make(store)
    session = await store.get(sid)
    assert session.document_context == "source document text"
    assert await store.count() == 1


@pytest.mark.asyncio
async def test_append_and_delete() -> None:
    store = InMemorySessionStore()
    sid = await _make(store)
    await store.append_message(sid, "user", "hello")
    await store.append_message(sid, "assistant", "hi")
    assert len((await store.get(sid)).history) == 2
    await store.delete(sid)
    with pytest.raises(SessionNotFoundError):
        await store.get(sid)


@pytest.mark.asyncio
async def test_expiry() -> None:
    store = InMemorySessionStore(ttl_seconds=0)
    sid = await _make(store)
    with pytest.raises(SessionNotFoundError):
        await store.get(sid)


@pytest.mark.asyncio
async def test_lru_eviction() -> None:
    store = InMemorySessionStore(max_sessions=2)
    await _make(store)
    await _make(store)
    await _make(store)
    assert await store.count() <= 2
