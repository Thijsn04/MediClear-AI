"""Tests for streaming analyze, idempotency, and batch jobs (demo provider)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.dependencies import get_ai_service, get_job_runner, get_job_store
from app.main import create_app
from app.providers.registry import build_provider
from app.services.ai_service import AIService
from app.services.cache import InMemoryCache, ResultCache
from app.services.jobs import InMemoryJobStore, JobRunner
from app.services.session_store import InMemorySessionStore
from app.services.terminology import TerminologyService


def _demo_client() -> TestClient:
    settings = Settings(
        _env_file=None,
        ai_provider="demo",
        rate_limit_enabled=False,
        cache_enabled=False,
        enforce_reading_level=False,
    )
    service = AIService(
        provider=build_provider(settings),
        session_store=InMemorySessionStore(),
        cache=ResultCache(InMemoryCache(), 60, enabled=False),
        settings=settings,
        terminology=TerminologyService(enabled=True, online=False),
    )
    store = InMemoryJobStore()
    runner = JobRunner(service, store)
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_ai_service] = lambda: service
    app.dependency_overrides[get_job_store] = lambda: store
    app.dependency_overrides[get_job_runner] = lambda: runner
    return TestClient(app, raise_server_exceptions=False)


def test_streaming_analyze_emits_deltas_and_result() -> None:
    client = _demo_client()
    with client.stream(
        "POST",
        "/api/v1/analyze/stream",
        data={"text": "discharge summary pneumonia", "language": "en"},
    ) as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())
    assert '"delta"' in body  # progressive explanation streamed
    assert '"result"' in body  # final structured object
    assert '"done"' in body
    assert "pneumonia" in body


def test_idempotency_replays_response() -> None:
    client = _demo_client()
    headers = {"Idempotency-Key": "abc-123"}
    r1 = client.post(
        "/api/v1/analyze",
        data={"text": "some medical text here", "language": "en"},
        headers=headers,
    )
    r2 = client.post(
        "/api/v1/analyze",
        data={"text": "some medical text here", "language": "en"},
        headers=headers,
    )
    assert r1.status_code == 200 and r2.status_code == 200
    assert r2.headers.get("Idempotency-Replayed") == "true"
    assert r1.json()["session_id"] == r2.json()["session_id"]  # identical replay


def _demo_service() -> AIService:
    settings = Settings(
        _env_file=None,
        ai_provider="demo",
        rate_limit_enabled=False,
        cache_enabled=False,
        enforce_reading_level=False,
    )
    return AIService(
        provider=build_provider(settings),
        session_store=InMemorySessionStore(),
        cache=ResultCache(InMemoryCache(), 60, enabled=False),
        settings=settings,
        terminology=TerminologyService(enabled=True, online=False),
    )


@pytest.mark.asyncio
async def test_batch_job_runner_processes_all_items() -> None:
    import asyncio

    store = InMemoryJobStore()
    runner = JobRunner(_demo_service(), store)
    job = await runner.submit(
        [
            {"text": "first medical document text", "language": "en"},
            {"text": "second medical document text", "language": "nl"},
        ]
    )
    for _ in range(100):
        current = await store.get(job.id)
        if current and current.status in {"succeeded", "failed", "partial"}:
            break
        await asyncio.sleep(0.02)
    current = await store.get(job.id)
    assert current is not None
    assert current.status == "succeeded"
    assert current.completed == 2
    assert all(r.status == "succeeded" for r in current.results)
    assert current.results[0].analysis["document_type"] == "discharge_summary"


def test_batch_submit_returns_202_and_job() -> None:
    client = _demo_client()
    submit = client.post(
        "/api/v1/analyze/batch",
        json={"items": [{"text": "first medical document text", "language": "en"}]},
    )
    assert submit.status_code == 202
    body = submit.json()
    assert body["total"] == 1
    got = client.get(f"/api/v1/jobs/{body['job_id']}")
    assert got.status_code == 200
    assert got.json()["status"] in {"queued", "processing", "succeeded", "partial", "failed"}


def test_batch_job_missing_returns_404() -> None:
    client = _demo_client()
    assert client.get("/api/v1/jobs/does-not-exist").status_code == 404


def test_rate_limit_headers_present() -> None:
    from app.core.rate_limit import InMemoryRateLimiter
    from app.dependencies import get_rate_limiter

    settings = Settings(
        _env_file=None,
        ai_provider="demo",
        rate_limit_enabled=True,
        rate_limit_requests=10,
        cache_enabled=False,
    )
    service = AIService(
        provider=build_provider(settings),
        session_store=InMemorySessionStore(),
        cache=ResultCache(InMemoryCache(), 60, enabled=False),
        settings=settings,
        terminology=TerminologyService(enabled=False),
    )
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_ai_service] = lambda: service
    app.dependency_overrides[get_rate_limiter] = lambda: InMemoryRateLimiter(
        limit=10, window_seconds=60
    )
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/v1/analyze", data={"text": "some medical text here", "language": "en"})
    assert resp.status_code == 200
    assert resp.headers.get("X-RateLimit-Limit") == "10"
    assert int(resp.headers.get("X-RateLimit-Remaining")) == 9
