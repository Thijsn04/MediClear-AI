"""
Pytest configuration and shared fixtures for MediClear AI tests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.dependencies import get_ai_service, get_document_service, get_tts_service
from app.main import create_app
from app.providers.base import AnalysisResult, BaseAIProvider, ConversationMessage, ProcessedDocument
from app.services.ai_service import AIService
from app.services.session_store import SessionStore


class MockProvider(BaseAIProvider):
    """Minimal AI provider for unit tests — returns deterministic responses."""

    @property
    def name(self) -> str:
        return "mock"

    @property
    def model(self) -> str:
        return "mock-model"

    @property
    def is_configured(self) -> bool:
        return True

    @property
    def supports_images(self) -> bool:
        return True

    async def analyze_document(
        self, document: ProcessedDocument, language_name: str
    ) -> AnalysisResult:
        text = "## Summary\nTest summary.\n\n## Explanation\nTest explanation."
        return AnalysisResult(
            text=text,
            provider=self.name,
            model=self.model,
            initial_history=[
                ConversationMessage(role="user", content="[test document]"),
                ConversationMessage(role="assistant", content=text),
            ],
        )

    async def chat(
        self,
        message: str,
        document_summary: str,
        history: list[ConversationMessage],
        language_name: str,
    ) -> str:
        return f"Test answer to: {message}"


@pytest.fixture()
def mock_provider() -> MockProvider:
    return MockProvider()


@pytest.fixture()
def session_store() -> SessionStore:
    return SessionStore(ttl_seconds=60, max_sessions=10)


@pytest.fixture()
def ai_service(mock_provider, session_store) -> AIService:
    return AIService(provider=mock_provider, session_store=session_store)


@pytest.fixture()
def client(ai_service) -> TestClient:
    """Test client with dependencies overridden to use MockProvider."""
    app = create_app()

    # Override settings to avoid needing real API keys
    test_settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        google_api_key="test",
        ai_provider="gemini",
    )
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_ai_service] = lambda: ai_service
    app.dependency_overrides[get_document_service] = lambda: __import__(
        "app.services.document_service", fromlist=["DocumentService"]
    ).DocumentService()

    return TestClient(app)
