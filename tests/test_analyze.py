"""Tests for the /analyze endpoint."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient


def test_analyze_text_returns_200(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/analyze",
        data={"text": "Patient has hypertension and type 2 diabetes mellitus.", "language": "en"},
    )
    assert resp.status_code == 200


def test_analyze_text_response_schema(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/analyze",
        data={"text": "Patient has hypertension.", "language": "en"},
    )
    data = resp.json()
    assert "session_id" in data
    assert "analysis" in data
    assert "language" in data
    assert "provider" in data
    assert "model" in data
    assert data["language"] == "en"


def test_analyze_text_creates_session(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/analyze",
        data={"text": "Patient has hypertension.", "language": "nl"},
    )
    data = resp.json()
    assert len(data["session_id"]) == 36  # UUID format


def test_analyze_no_input_returns_422(client: TestClient) -> None:
    resp = client.post("/api/v1/analyze", data={"language": "en"})
    assert resp.status_code == 422


def test_analyze_invalid_language_returns_422(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/analyze",
        data={"text": "Some medical text here.", "language": "xx"},
    )
    assert resp.status_code == 422


def test_analyze_unsupported_file_type(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/analyze",
        data={"language": "en"},
        files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert resp.status_code == 415


def test_analyze_all_supported_languages(client: TestClient) -> None:
    supported = ["en", "nl", "de", "fr", "es", "tr", "ar", "pl"]
    for lang in supported:
        resp = client.post(
            "/api/v1/analyze",
            data={"text": "Patient diagnosed with pneumonia.", "language": lang},
        )
        assert resp.status_code == 200, f"Failed for language: {lang}"
