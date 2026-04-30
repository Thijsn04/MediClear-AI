"""
Google Gemini provider.

Model is fully configurable via the GEMINI_MODEL environment variable.
Any model string accepted by the google-generativeai SDK can be used,
for example:
  - gemini-2.5-flash      (fast, cost-effective)
  - gemini-2.5-pro        (most capable)
  - gemini-1.5-pro        (stable alternative)
  - gemini-1.5-flash      (lightweight)
"""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

from app.core.exceptions import AIProviderError, AIProviderNotConfiguredError, UnsupportedModalityError
from app.core.logging import get_logger
from app.providers.base import AnalysisResult, BaseAIProvider, ConversationMessage, ProcessedDocument
from app.providers.prompts import ANALYSIS_SYSTEM_PROMPT, CHAT_SYSTEM_PROMPT

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class GeminiProvider(BaseAIProvider):
    """Google Gemini provider — supports text and vision models."""

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model(self) -> str:
        return self._model

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    @property
    def supports_images(self) -> bool:
        # All current Gemini Flash/Pro models are multimodal.
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_model(self):  # type: ignore[return]
        """Lazily import and configure the Gemini SDK."""
        try:
            import google.generativeai as genai  # type: ignore[import-untyped]
        except ImportError as exc:
            raise AIProviderError(
                "google-generativeai package is not installed. "
                "Run: pip install google-generativeai"
            ) from exc

        if not self.is_configured:
            raise AIProviderNotConfiguredError(self.name)

        genai.configure(api_key=self._api_key)
        return genai.GenerativeModel(self._model)

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    async def analyze_document(
        self,
        document: ProcessedDocument,
        language_name: str,
    ) -> AnalysisResult:
        if not self.is_configured:
            raise AIProviderNotConfiguredError(self.name)

        model_obj = self._get_model()

        system_prompt = ANALYSIS_SYSTEM_PROMPT.format(language_name=language_name)
        parts: list = [system_prompt]

        if document.type == "text":
            parts.append(f"MEDICAL DOCUMENT:\n{document.text}")
        elif document.type == "image":
            if not self.supports_images:
                raise UnsupportedModalityError(self.name, "image")
            try:
                import google.generativeai as genai  # type: ignore[import-untyped]

                image_data = base64.b64decode(document.image_bytes)  # type: ignore[arg-type]
                image_part = {
                    "mime_type": document.image_media_type or "image/jpeg",
                    "data": image_data,
                }
                parts.append("ANALYSE THIS MEDICAL IMAGE:")
                parts.append(image_part)
            except Exception as exc:
                raise AIProviderError(f"Failed to prepare image for Gemini: {exc}") from exc
        else:
            raise AIProviderError(f"Unknown document type: {document.type}")

        try:
            logger.info("gemini.analyze", model=self._model, doc_type=document.type)
            response = model_obj.generate_content(parts)
            result_text = response.text
        except Exception as exc:
            logger.error("gemini.analyze.error", error=str(exc))
            raise AIProviderError(f"Gemini API error: {exc}") from exc

        initial_history = [
            ConversationMessage(role="user", content=f"[Document analysed — {document.type}]"),
            ConversationMessage(role="assistant", content=result_text),
        ]

        return AnalysisResult(
            text=result_text,
            provider=self.name,
            model=self._model,
            initial_history=initial_history,
        )

    async def chat(
        self,
        message: str,
        document_summary: str,
        history: list[ConversationMessage],
        language_name: str,
    ) -> str:
        if not self.is_configured:
            raise AIProviderNotConfiguredError(self.name)

        model_obj = self._get_model()

        conversation_text = "\n".join(
            f"{msg.role.capitalize()}: {msg.content}" for msg in history
        )

        prompt = CHAT_SYSTEM_PROMPT.format(
            document_summary=document_summary,
            conversation_history=conversation_text or "(no previous messages)",
            language_name=language_name,
        )
        full_prompt = f"{prompt}\n\nPatient question: {message}"

        try:
            logger.info("gemini.chat", model=self._model)
            response = model_obj.generate_content(full_prompt)
            return response.text
        except Exception as exc:
            logger.error("gemini.chat.error", error=str(exc))
            raise AIProviderError(f"Gemini API error: {exc}") from exc
