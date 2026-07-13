"""
Google Gemini provider.

The google-generativeai SDK is synchronous, so every call is dispatched to a
worker thread via ``asyncio.to_thread`` — this keeps the async event loop free
and lets the server handle concurrent requests (the previous implementation
blocked the loop on every Gemini call).

Model is configurable via GEMINI_MODEL (e.g. gemini-2.5-flash, gemini-2.5-pro).
"""

from __future__ import annotations

import asyncio
import base64

from app.core.exceptions import AIProviderError, AIProviderNotConfiguredError
from app.core.logging import get_logger
from app.providers.base import BaseAIProvider, Completion, Message

logger = get_logger(__name__)


class GeminiProvider(BaseAIProvider):
    """Google Gemini provider — multimodal, non-blocking."""

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

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
        return True

    # ------------------------------------------------------------------

    def _build_model(self, system: str, json_mode: bool, max_tokens: int, temperature: float):
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise AIProviderError(
                "google-generativeai package is not installed. "
                "Run: pip install 'mediclear-ai[gemini]'"
            ) from exc
        if not self.is_configured:
            raise AIProviderNotConfiguredError(self.name)

        genai.configure(api_key=self._api_key)
        generation_config: dict = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_mode:
            generation_config["response_mime_type"] = "application/json"
        return genai.GenerativeModel(
            self._model,
            system_instruction=system,
            generation_config=generation_config,
        )

    @staticmethod
    def _to_gemini_contents(messages: list[Message]) -> list[dict]:
        contents: list[dict] = []
        for m in messages:
            role = "model" if m.role == "assistant" else "user"
            parts: list = []
            if m.text:
                parts.append(m.text)
            if m.image is not None:
                parts.append(
                    {
                        "mime_type": m.image.media_type,
                        "data": base64.b64decode(m.image.b64_data),
                    }
                )
            contents.append({"role": role, "parts": parts})
        return contents

    async def _complete(
        self,
        *,
        system: str,
        messages: list[Message],
        max_tokens: int,
        temperature: float,
        json_mode: bool,
    ) -> Completion:
        def _run() -> Completion:
            model_obj = self._build_model(system, json_mode, max_tokens, temperature)
            resp = model_obj.generate_content(self._to_gemini_contents(messages))
            usage = getattr(resp, "usage_metadata", None)
            return Completion(
                text=resp.text,
                input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
                output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            )

        try:
            return await asyncio.to_thread(_run)
        except (AIProviderError, AIProviderNotConfiguredError):
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("gemini.error", error=str(exc))
            raise AIProviderError(f"Gemini API error: {exc}") from exc
