"""Tests for API-key auth, rate limiting, streaming, and zero-retention."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.core.rate_limit import InMemoryRateLimiter
from app.dependencies import (
    get_ai_service,
    get_document_service,
    get_rate_limiter,
    get_session_store,
)
from app.main import create_app
from app.services.document_service import DocumentService


def _client(settings: Settings, ai_service, session_store, limiter=None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_ai_service] = lambda: ai_service
    app.dependency_overrides[get_session_store] = lambda: session_store
    app.dependency_overrides[get_document_service] = lambda: DocumentService()
    if limiter is not None:
        app.dependency_overrides[get_rate_limiter] = lambda: limiter
    return TestClient(app, raise_server_exceptions=False)


def test_missing_api_key_rejected(ai_service, session_store) -> None:
    settings = Settings(
        _env_file=None,
        google_api_key="test",
        require_api_key=True,
        api_keys=["secret-key"],
        rate_limit_enabled=False,
    )
    client = _client(settings, ai_service, session_store)
    resp = client.post(
        "/api/v1/analyze",
        data={"text": "Patient has a fever today.", "language": "en"},
    )
    assert resp.status_code == 401


def test_valid_api_key_accepted(ai_service, session_store) -> None:
    settings = Settings(
        _env_file=None,
        google_api_key="test",
        require_api_key=True,
        api_keys=["secret-key"],
        rate_limit_enabled=False,
    )
    client = _client(settings, ai_service, session_store)
    resp = client.post(
        "/api/v1/analyze",
        data={"text": "Patient has a fever today.", "language": "en"},
        headers={"X-API-Key": "secret-key"},
    )
    assert resp.status_code == 200


def test_rate_limit_returns_429(ai_service, session_store) -> None:
    settings = Settings(
        _env_file=None,
        google_api_key="test",
        require_api_key=False,
        rate_limit_enabled=True,
    )
    limiter = InMemoryRateLimiter(limit=1, window_seconds=60)
    client = _client(settings, ai_service, session_store, limiter)
    payload = {"text": "Patient has a fever today.", "language": "en"}
    assert client.post("/api/v1/analyze", data=payload).status_code == 200
    resp = client.post("/api/v1/analyze", data=payload)
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


def test_zero_retention_no_session(mock_provider, session_store) -> None:
    from app.services.ai_service import AIService
    from app.services.cache import InMemoryCache, ResultCache

    settings = Settings(
        _env_file=None,
        google_api_key="test",
        zero_retention=True,
        rate_limit_enabled=False,
        cache_enabled=False,
        enforce_reading_level=False,
    )
    service = AIService(
        provider=mock_provider,
        session_store=session_store,
        cache=ResultCache(InMemoryCache(), ttl_seconds=60, enabled=False),
        settings=settings,
    )
    client = _client(settings, service, session_store)
    resp = client.post(
        "/api/v1/analyze", data={"text": "Patient has a fever today.", "language": "en"}
    )
    assert resp.status_code == 200
    assert resp.json()["session_id"] is None


def test_streaming_chat(client: TestClient) -> None:
    sid = client.post(
        "/api/v1/analyze",
        data={"text": "Patient has type 2 diabetes mellitus.", "language": "en"},
    ).json()["session_id"]
    with client.stream(
        "POST", f"/api/v1/chat/{sid}/stream", json={"message": "What is this?", "language": "en"}
    ) as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())
    assert "data:" in body
    assert "done" in body


def test_request_id_header(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert "X-Request-ID" in resp.headers
