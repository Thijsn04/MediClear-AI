"""
FastAPI dependency providers.

Using module-level singletons (lazily initialised on first request)
keeps construction cheap and ensures providers/services are shared
across requests without needing a DI framework.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.services.ai_service import AIService, build_provider
from app.services.document_service import DocumentService
from app.services.session_store import SessionStore
from app.services.tts_service import TTSService


@lru_cache
def get_session_store() -> SessionStore:
    settings = get_settings()
    return SessionStore(
        ttl_seconds=settings.session_ttl_seconds,
        max_sessions=settings.max_sessions,
    )


@lru_cache
def get_ai_service() -> AIService:
    settings = get_settings()
    provider = build_provider(settings)
    return AIService(provider=provider, session_store=get_session_store())


@lru_cache
def get_document_service() -> DocumentService:
    settings = get_settings()
    return DocumentService(max_upload_size_mb=settings.max_upload_size_mb)


@lru_cache
def get_tts_service() -> TTSService:
    return TTSService()
