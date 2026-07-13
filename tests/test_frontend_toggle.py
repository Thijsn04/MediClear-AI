"""Tests for the ENABLE_FRONTEND configuration toggle."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.dependencies import get_ai_service, get_document_service
from app.main import create_app


def _make_client(enable_frontend: bool, ai_service, document_service) -> TestClient:
    """Build a TestClient with a specific ENABLE_FRONTEND setting."""
    from app.config import Settings, get_settings

    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        google_api_key="test",
        ai_provider="gemini",
        enable_frontend=enable_frontend,
    )
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_ai_service] = lambda: ai_service
    app.dependency_overrides[get_document_service] = lambda: document_service
    return TestClient(app, raise_server_exceptions=False)


def test_frontend_enabled_serves_html(ai_service, client: TestClient) -> None:
    """When ENABLE_FRONTEND=true the root path serves the HTML application."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


def test_api_docs_always_available(client: TestClient) -> None:
    """The OpenAPI docs are always available regardless of frontend setting."""
    assert client.get("/api/docs").status_code == 200
    assert client.get("/api/openapi.json").status_code == 200


def test_api_endpoints_work_with_frontend_disabled(ai_service) -> None:
    """All API routes work correctly when the frontend is disabled."""
    from app.services.document_service import DocumentService

    doc_service = DocumentService()
    c = _make_client(False, ai_service, doc_service)

    # API endpoints must still work
    assert c.get("/api/v1/health").status_code == 200
    assert c.get("/api/v1/languages").status_code == 200
    resp = c.post(
        "/api/v1/analyze",
        data={"text": "Patient has hypertension.", "language": "en"},
    )
    assert resp.status_code == 200
