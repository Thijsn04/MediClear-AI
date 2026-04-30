"""
OpenAI provider — also covers every OpenAI-compatible API.

Set OPENAI_BASE_URL to redirect requests to any compatible server:

  | Service            | OPENAI_BASE_URL                           | Example model        |
  |--------------------|-------------------------------------------|----------------------|
  | OpenAI (default)   | (leave empty)                             | gpt-4o               |
  | Azure OpenAI       | https://<resource>.openai.azure.com/…     | gpt-4o               |
  | Ollama             | http://localhost:11434/v1                 | llama3.2             |
  | Groq               | https://api.groq.com/openai/v1            | llama-3.3-70b-versatile |
  | LM Studio          | http://localhost:1234/v1                  | <local model name>   |
  | Together AI        | https://api.together.xyz/v1               | meta-llama/…         |
  | vLLM               | http://localhost:8000/v1                  | <model path>         |
  | Mistral AI         | https://api.mistral.ai/v1                 | mistral-large-latest |

The model name is set freely via OPENAI_MODEL — whatever the target server
accepts.  No model names are hardcoded here.
"""

from __future__ import annotations

import base64

from app.core.exceptions import AIProviderError, AIProviderNotConfiguredError, UnsupportedModalityError
from app.core.logging import get_logger
from app.providers.base import AnalysisResult, BaseAIProvider, ConversationMessage, ProcessedDocument
from app.providers.prompts import ANALYSIS_SYSTEM_PROMPT, CHAT_SYSTEM_PROMPT

logger = get_logger(__name__)


class OpenAIProvider(BaseAIProvider):
    """
    OpenAI-compatible provider.

    Works with OpenAI, Azure OpenAI, Ollama, Groq, LM Studio, vLLM,
    Mistral, Together AI, and any other server that speaks the OpenAI
    Chat Completions API.
    """

    def __init__(self, api_key: str, model: str, base_url: str = "") -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url or None

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    @property
    def supports_images(self) -> bool:
        # Vision support depends on the chosen model, not the provider.
        # We optimistically return True; the API will reject unsupported models.
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_client(self):  # type: ignore[return]
        try:
            from openai import AsyncOpenAI  # type: ignore[import-untyped]
        except ImportError as exc:
            raise AIProviderError(
                "openai package is not installed. Run: pip install openai"
            ) from exc

        if not self.is_configured:
            raise AIProviderNotConfiguredError(self.name)

        kwargs: dict = {"api_key": self._api_key}
        if self._base_url:
            kwargs["base_url"] = self._base_url

        return AsyncOpenAI(**kwargs)

    def _build_image_content(self, document: ProcessedDocument) -> list[dict]:
        """Build the content list for a vision request."""
        b64 = base64.b64encode(document.image_bytes).decode()  # type: ignore[arg-type]
        media_type = document.image_media_type or "image/jpeg"
        return [
            {"type": "text", "text": "ANALYSE THIS MEDICAL IMAGE:"},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{media_type};base64,{b64}"},
            },
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
            user_content: list[dict] | str = (
                f"MEDICAL DOCUMENT:\n{document.text}"
            )
        elif document.type == "image":
            user_content = self._build_image_content(document)
        else:
            raise AIProviderError(f"Unknown document type: {document.type}")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        try:
            logger.info("openai.analyze", model=self._model, doc_type=document.type)
            response = await client.chat.completions.create(
                model=self._model,
                messages=messages,  # type: ignore[arg-type]
            )
            result_text = response.choices[0].message.content or ""
        except Exception as exc:
            logger.error("openai.analyze.error", error=str(exc))
            raise AIProviderError(f"OpenAI-compatible API error: {exc}") from exc

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

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ]

        try:
            logger.info("openai.chat", model=self._model)
            response = await client.chat.completions.create(
                model=self._model,
                messages=messages,  # type: ignore[arg-type]
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.error("openai.chat.error", error=str(exc))
            raise AIProviderError(f"OpenAI-compatible API error: {exc}") from exc
