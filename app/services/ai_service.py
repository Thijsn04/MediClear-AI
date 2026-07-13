"""
AI service — orchestration.

The single point of contact between the API layer and everything below it.
It owns the end-to-end analysis pipeline:

    cache lookup → provider analysis → readability enforcement →
    cache store → session creation (unless zero-retention)

and the follow-up chat pipeline (grounded in the stored document context).
"""

from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator
from dataclasses import dataclass

from app.config import Settings
from app.core.exceptions import ChatDisabledError
from app.core.logging import get_logger
from app.models.analysis import StructuredAnalysis
from app.models.languages import get_language
from app.providers.base import BaseAIProvider, ProcessedDocument
from app.services import readability as readability_mod
from app.services.cache import ResultCache, make_key
from app.services.session_store import ChatSession, SessionStore
from app.services.terminology import TerminologyService

logger = get_logger(__name__)


@dataclass
class AnalysisOutcome:
    analysis: StructuredAnalysis
    session_id: str | None
    provider: str
    model: str
    cached: bool
    input_tokens: int
    output_tokens: int


class AIService:
    def __init__(
        self,
        provider: BaseAIProvider,
        session_store: SessionStore,
        cache: ResultCache,
        settings: Settings,
        terminology: TerminologyService | None = None,
    ) -> None:
        self._provider = provider
        self._sessions = session_store
        self._cache = cache
        self._settings = settings
        self._terminology = terminology

    @property
    def provider(self) -> BaseAIProvider:
        return self._provider

    @property
    def session_store(self) -> SessionStore:
        return self._sessions

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    async def analyze(
        self,
        document: ProcessedDocument,
        language: str,
        target_level: str | None = None,
    ) -> AnalysisOutcome:
        target_level = target_level or self._settings.target_reading_level
        language_name = get_language(language).english_name

        cache_key = self._cache_key(document, language, target_level)
        cached = await self._cache.get(cache_key) if cache_key else None

        if cached is not None:
            logger.info("ai_service.cache_hit", provider=self._provider.name)
            analysis = cached
            input_tokens = output_tokens = 0
            was_cached = True
        else:
            result = await self._provider.analyze_document(
                document,
                language_name=language_name,
                target_level=target_level,
                max_tokens=self._settings.ai_max_output_tokens,
                temperature=self._settings.ai_temperature,
            )
            analysis = result.analysis
            input_tokens, output_tokens = result.input_tokens, result.output_tokens
            was_cached = False

            analysis = await self._enforce_readability(
                analysis, document, language_name, target_level
            )
            if self._terminology is not None:
                analysis.key_terms = await self._terminology.enrich(analysis.key_terms, language)
            if cache_key:
                await self._cache.set(cache_key, analysis)

        # Attach a fresh readability assessment for the response.
        analysis.readability = readability_mod.assess(
            analysis.explanation or analysis.summary, target_level
        )

        session_id = await self._maybe_create_session(document, analysis, language, language_name)
        return AnalysisOutcome(
            analysis=analysis,
            session_id=session_id,
            provider=self._provider.name,
            model=self._provider.model,
            cached=was_cached,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    async def _enforce_readability(
        self,
        analysis: StructuredAnalysis,
        document: ProcessedDocument,
        language_name: str,
        target_level: str,
    ) -> StructuredAnalysis:
        if not self._settings.enforce_reading_level:
            return analysis
        passes = self._settings.max_simplification_passes
        for _ in range(max(0, passes)):
            score = readability_mod.assess(analysis.explanation or analysis.summary, target_level)
            if score.meets_target is not False:
                break
            logger.info(
                "ai_service.simplify_pass",
                estimated=score.estimated_cefr,
                target=target_level,
            )
            analysis = await self._provider.simplify(
                analysis,
                language_name=language_name,
                target_level=target_level,
                max_tokens=self._settings.ai_max_output_tokens,
                temperature=self._settings.ai_temperature,
                source_text=document.text,
            )
        return analysis

    async def _maybe_create_session(
        self,
        document: ProcessedDocument,
        analysis: StructuredAnalysis,
        language: str,
        language_name: str,
    ) -> str | None:
        if self._settings.zero_retention:
            return None
        # Ground follow-up chat in the source text when we have it, else the
        # rendered analysis (best available for image-only inputs).
        document_context = document.text or analysis.render_markdown()
        session = await self._sessions.create(
            provider=self._provider.name,
            model=self._provider.model,
            language=language,
            language_name=language_name,
            document_context=document_context,
            initial_history=[],
        )
        return session.id

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    async def chat(self, session_id: str, message: str, language: str) -> str:
        if self._settings.zero_retention:
            raise ChatDisabledError()
        session = await self._sessions.get(session_id)
        language_name = get_language(language).english_name if language else session.language_name

        response_text = await self._provider.chat(
            message=message,
            document_context=session.document_context,
            history=session.history,
            language_name=language_name,
            max_tokens=self._settings.ai_max_output_tokens,
            temperature=self._settings.ai_temperature,
        )
        await self._sessions.append_message(session_id, "user", message)
        await self._sessions.append_message(session_id, "assistant", response_text)
        return response_text

    async def stream_chat(self, session_id: str, message: str, language: str) -> AsyncIterator[str]:
        if self._settings.zero_retention:
            raise ChatDisabledError()
        session = await self._sessions.get(session_id)
        language_name = get_language(language).english_name if language else session.language_name

        collected: list[str] = []
        async for chunk in self._provider.stream_chat(
            message=message,
            document_context=session.document_context,
            history=session.history,
            language_name=language_name,
            max_tokens=self._settings.ai_max_output_tokens,
            temperature=self._settings.ai_temperature,
        ):
            collected.append(chunk)
            yield chunk

        await self._sessions.append_message(session_id, "user", message)
        await self._sessions.append_message(session_id, "assistant", "".join(collected))

    async def get_session(self, session_id: str) -> ChatSession:
        return await self._sessions.get(session_id)

    async def delete_session(self, session_id: str) -> None:
        await self._sessions.delete(session_id)

    # ------------------------------------------------------------------

    def _cache_key(
        self, document: ProcessedDocument, language: str, target_level: str
    ) -> str | None:
        if not self._settings.cache_enabled:
            return None
        if document.type == "text" and document.text:
            content_hash = hashlib.sha256(document.text.encode()).hexdigest()
        elif document.type == "image" and document.image:
            content_hash = hashlib.sha256(document.image.b64_data.encode()).hexdigest()
        else:
            return None
        return make_key(content_hash, language, target_level, self._provider.model)
