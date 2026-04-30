"""
Anthropic Claude provider.

Model is freely configurable via ANTHROPIC_MODEL, for example:
  - claude-opus-4-5          (most capable)
  - claude-sonnet-4-5        (balanced)
  - claude-3-5-haiku-20241022 (fast and lightweight)
  - any future Claude model released by Anthropic
"""

from __future__ import annotations

import base64

from app.core.exceptions import AIProviderError, AIProviderNotConfiguredError
from app.core.logging import get_logger
from app.providers.base import AnalysisResult, BaseAIProvider, ConversationMessage, ProcessedDocument
from app.providers.prompts import ANALYSIS_SYSTEM_PROMPT, CHAT_SYSTEM_PROMPT

logger = get_logger(__name__)

# Anthropic's API enforces a hard cap on the system prompt + messages payload.
# 4096 output tokens is a safe, generous default.
_MAX_TOKENS = 4096


class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude provider — supports text and vision (Claude 3+)."""

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def model(self) -> str:
        return self._model

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    @property
    def supports_images(self) -> bool:
        # Claude 3 and later models support vision.
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_client(self):  # type: ignore[return]
        try:
            import anthropic  # type: ignore[import-untyped]
        except ImportError as exc:
            raise AIProviderError(
                "anthropic package is not installed. Run: pip install anthropic"
            ) from exc

        if not self.is_configured:
            raise AIProviderNotConfiguredError(self.name)

        return anthropic.AsyncAnthropic(api_key=self._api_key)

    def _build_image_content(self, document: ProcessedDocument) -> list[dict]:
        """Build the Anthropic vision content block for an image."""
        b64 = base64.b64encode(document.image_bytes).decode()  # type: ignore[arg-type]
        media_type = document.image_media_type or "image/jpeg"
        return [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": b64,
                },
            },
            {"type": "text", "text": "ANALYSE THIS MEDICAL IMAGE:"},
        ]

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

        client = self._get_client()
        system_prompt = ANALYSIS_SYSTEM_PROMPT.format(language_name=language_name)

        if document.type == "text":
            user_content: list[dict] | str = f"MEDICAL DOCUMENT:\n{document.text}"
        elif document.type == "image":
            user_content = self._build_image_content(document)
        else:
            raise AIProviderError(f"Unknown document type: {document.type}")

        try:
            logger.info("anthropic.analyze", model=self._model, doc_type=document.type)
            response = await client.messages.create(
                model=self._model,
                max_tokens=_MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            result_text = response.content[0].text if response.content else ""
        except Exception as exc:
            logger.error("anthropic.analyze.error", error=str(exc))
            raise AIProviderError(f"Anthropic API error: {exc}") from exc

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

        client = self._get_client()
        conversation_text = "\n".join(
            f"{msg.role.capitalize()}: {msg.content}" for msg in history
        )

        system_prompt = CHAT_SYSTEM_PROMPT.format(
            document_summary=document_summary,
            conversation_history=conversation_text or "(no previous messages)",
            language_name=language_name,
        )

        try:
            logger.info("anthropic.chat", model=self._model)
            response = await client.messages.create(
                model=self._model,
                max_tokens=_MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": message}],
            )
            return response.content[0].text if response.content else ""
        except Exception as exc:
            logger.error("anthropic.chat.error", error=str(exc))
            raise AIProviderError(f"Anthropic API error: {exc}") from exc
