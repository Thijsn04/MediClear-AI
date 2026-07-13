"""Pytest configuration and shared fixtures for MediClear AI tests."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.dependencies import (
    get_ai_service,
    get_document_service,
    get_session_store,
    get_tts_service,
)
from app.main import create_app
from app.providers.base import BaseAIProvider, Completion
from app.services.ai_service import AIService
from app.services.cache import InMemoryCache, ResultCache
from app.services.document_service import DocumentService
from app.services.session_store import InMemorySessionStore


class MockProvider(BaseAIProvider):
    """Deterministic provider for tests - returns valid StructuredAnalysis JSON."""

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

    @property
    def supports_streaming(self) -> bool:
        return True

    async def _complete(
        self, *, system, messages, max_tokens, temperature, json_mode
    ) -> Completion:
        if json_mode:
            payload = {
                "document_type": "other",
                "summary": "This is a simple summary.",
                "explanation": "This is a clear and simple explanation for the patient.",
                "key_terms": [{"term": "hypertension", "definition": "high blood pressure"}],
                "action_items": ["Talk to your doctor."],
            }
            return Completion(text=json.dumps(payload), input_tokens=10, output_tokens=20)
        last = messages[-1].text if messages else ""
        return Completion(text=f"Test answer to: {last}", input_tokens=5, output_tokens=8)

    async def _stream(self, *, system, messages, max_tokens, temperature) -> AsyncIterator[str]:
        last = messages[-1].text if messages else ""
        for token in f"Test answer to: {last}".split():
            yield token + " "


@pytest.fixture()
def mock_provider() -> MockProvider:
    return MockProvider()


@pytest.fixture()
def test_settings() -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        google_api_key="test",
        ai_provider="gemini",
        rate_limit_enabled=False,
        require_api_key=False,
        cache_enabled=False,
        metrics_enabled=False,
        enforce_reading_level=False,
    )


@pytest.fixture()
def session_store() -> InMemorySessionStore:
    return InMemorySessionStore(ttl_seconds=60, max_sessions=10)


@pytest.fixture()
def ai_service(mock_provider, session_store, test_settings) -> AIService:
    cache = ResultCache(InMemoryCache(), ttl_seconds=60, enabled=False)
    return AIService(
        provider=mock_provider,
        session_store=session_store,
        cache=cache,
        settings=test_settings,
    )


@pytest.fixture()
def client(ai_service, session_store, test_settings) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_ai_service] = lambda: ai_service
    app.dependency_overrides[get_session_store] = lambda: session_store
    app.dependency_overrides[get_document_service] = lambda: DocumentService()
    app.dependency_overrides[get_tts_service] = lambda: get_tts_service()
    return TestClient(app)
