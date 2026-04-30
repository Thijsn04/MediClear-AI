"""
AI service — provider selection and orchestration.

This module is the single point of contact between the API layer and the
AI providers.  It reads configuration, instantiates the correct provider,
and delegates to it.
"""

from __future__ import annotations

from app.config import Settings
from app.core.exceptions import AIProviderError
from app.core.logging import get_logger
from app.models.schemas import SUPPORTED_LANGUAGES
from app.providers.base import BaseAIProvider, ProcessedDocument
from app.services.session_store import ChatSession, SessionStore

logger = get_logger(__name__)


def build_provider(settings: Settings) -> BaseAIProvider:
    """
    Instantiate the AI provider selected by AI_PROVIDER.

    The returned object is *not* validated here — configuration errors
    are surfaced lazily when the first request is made, so the server
    can still start (and return informative health-check responses) even
    when credentials are absent.
    """
    provider_name = settings.ai_provider

    if provider_name == "gemini":
        from app.providers.gemini import GeminiProvider
        return GeminiProvider(
            api_key=settings.google_api_key,
            model=settings.gemini_model,
        )

    if provider_name == "openai":
        from app.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url,
        )

    if provider_name == "anthropic":
        from app.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
        )

    raise AIProviderError(
        f"Unknown AI provider '{provider_name}'. "
        "Valid options: gemini, openai, anthropic."
    )


class AIService:
    """Orchestrates document analysis and chat across providers and sessions."""

    def __init__(
        self,
        provider: BaseAIProvider,
        session_store: SessionStore,
    ) -> None:
        self._provider = provider
        self._sessions = session_store

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def provider(self) -> BaseAIProvider:
        return self._provider

    @property
    def session_store(self) -> SessionStore:
        return self._sessions

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze(
        self,
        document: ProcessedDocument,
        language: str,
    ) -> ChatSession:
        """
        Analyse a document and create a chat session for follow-up questions.

        Parameters
        ----------
        document:
            Pre-processed document content.
        language:
            BCP 47 language code (e.g. 'en').

        Returns
        -------
        ChatSession
            The newly created session containing the analysis result.
        """
        language_name = SUPPORTED_LANGUAGES.get(language, "English")

        logger.info(
            "ai_service.analyze",
            provider=self._provider.name,
            model=self._provider.model,
            language=language,
        )

        result = await self._provider.analyze_document(document, language_name)

        session = self._sessions.create(
            provider=result.provider,
            model=result.model,
            language=language,
            language_name=language_name,
            document_summary=result.text,
            initial_history=result.initial_history,
        )
        return session

    async def chat(
        self,
        session_id: str,
        message: str,
        language: str,
    ) -> str:
        """
        Continue a conversation within an existing session.

        Parameters
        ----------
        session_id:
            Session identifier returned by a previous analyze call.
        message:
            The patient's question.
        language:
            BCP 47 language code for the response.

        Returns
        -------
        str
            The AI's answer.
        """
        session = self._sessions.get(session_id)
        language_name = SUPPORTED_LANGUAGES.get(language, session.language_name)

        logger.info(
            "ai_service.chat",
            session_id=session_id,
            provider=self._provider.name,
        )

        response_text = await self._provider.chat(
            message=message,
            document_summary=session.document_summary,
            history=session.history,
            language_name=language_name,
        )

        # Persist both turns in the session
        self._sessions.append_message(session_id, role="user", content=message)
        self._sessions.append_message(session_id, role="assistant", content=response_text)

        return response_text
