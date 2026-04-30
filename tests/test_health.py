"""Tests for the health-check endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200


def test_health_schema(client: TestClient) -> None:
    data = client.get("/api/v1/health").json()
    assert "status" in data
    assert "version" in data
    assert "ai_provider" in data
    assert "ai_model" in data
    assert "ai_provider_configured" in data
    assert "active_sessions" in data
    assert "timestamp" in data


def test_health_provider_configured(client: TestClient) -> None:
    data = client.get("/api/v1/health").json()
    # MockProvider always returns is_configured=True
    assert data["ai_provider_configured"] is True
    assert data["status"] == "healthy"


def test_health_provider_name(client: TestClient) -> None:
    data = client.get("/api/v1/health").json()
    assert data["ai_provider"] == "mock"
    assert data["ai_model"] == "mock-model"
