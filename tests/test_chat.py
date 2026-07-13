"""Tests for the /chat endpoint and session management."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_session(client: TestClient) -> str:
    resp = client.post(
        "/api/v1/analyze",
        data={"text": "Patient has been diagnosed with type 2 diabetes.", "language": "en"},
    )
    assert resp.status_code == 200
    return resp.json()["session_id"]


def test_chat_returns_200(client: TestClient) -> None:
    session_id = _create_session(client)
    resp = client.post(
        f"/api/v1/chat/{session_id}",
        json={"message": "Should I be worried?", "language": "en"},
    )
    assert resp.status_code == 200


def test_chat_response_schema(client: TestClient) -> None:
    session_id = _create_session(client)
    resp = client.post(
        f"/api/v1/chat/{session_id}",
        json={"message": "What does this mean?", "language": "en"},
    )
    data = resp.json()
    assert "session_id" in data
    assert "message" in data
    assert "response" in data
    assert "language" in data
    assert data["session_id"] == session_id
    assert data["message"] == "What does this mean?"


def test_chat_invalid_session_returns_404(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/chat/00000000-0000-0000-0000-000000000000",
        json={"message": "Hello?", "language": "en"},
    )
    assert resp.status_code == 404


def test_chat_empty_message_returns_422(client: TestClient) -> None:
    session_id = _create_session(client)
    resp = client.post(
        f"/api/v1/chat/{session_id}",
        json={"message": "", "language": "en"},
    )
    assert resp.status_code == 422


def test_chat_multiple_turns(client: TestClient) -> None:
    session_id = _create_session(client)
    questions = [
        "What is diabetes?",
        "Is this serious?",
        "What should I eat?",
    ]
    for q in questions:
        resp = client.post(
            f"/api/v1/chat/{session_id}",
            json={"message": q, "language": "en"},
        )
        assert resp.status_code == 200
        assert resp.json()["response"] != ""


def test_chat_language_selection(client: TestClient) -> None:
    session_id = _create_session(client)
    resp = client.post(
        f"/api/v1/chat/{session_id}",
        json={"message": "Wat betekent dit?", "language": "nl"},
    )
    assert resp.status_code == 200
    assert resp.json()["language"] == "nl"
