"""
OpenAI provider - also covers every OpenAI-compatible API.

Set OPENAI_BASE_URL to redirect requests to any compatible server (Azure
OpenAI, Ollama, Groq, LM Studio, vLLM, Together, Mistral). The model name is
set freely via OPENAI_MODEL - nothing is hardcoded.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from app.core.exceptions import AIProviderError, AIProviderNotConfiguredError
from app.core.logging import get_logger
from app.providers.base import BaseAIProvider, Completion, Message

logger = get_logger(__name__)


class OpenAIProvider(BaseAIProvider):
    """OpenAI-compatible chat provider (native async client)."""

    def __init__(self, api_key: str, model: str, base_url: str = "") -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url or None
        self._client: Any = None

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
        return True

    @property
    def supports_streaming(self) -> bool:
        return True

    # ------------------------------------------------------------------

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise AIProviderError(
                "openai package is not installed. Run: pip install 'mediclear-ai[openai]'"
            ) from exc
        if not self.is_configured:
            raise AIProviderNotConfiguredError(self.name)
        kwargs: dict = {"api_key": self._api_key}
        if self._base_url:
            kwargs["base_url"] = self._base_url
        self._client = AsyncOpenAI(**kwargs)
        return self._client

    @staticmethod
    def _to_openai_messages(system: str, messages: list[Message]) -> list[dict]:
        out: list[dict] = [{"role": "system", "content": system}]
        for m in messages:
            if m.image is not None:
                content: list[dict] = []
                if m.text:
                    content.append({"type": "text", "text": m.text})
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{m.image.media_type};base64,{m.image.b64_data}"
                        },
                    }
                )
                out.append({"role": m.role, "content": content})
            else:
                out.append({"role": m.role, "content": m.text})
        return out

    async def _complete(
        self,
        *,
        system: str,
        messages: list[Message],
        max_tokens: int,
        temperature: float,
        json_mode: bool,
    ) -> Completion:
        client = self._get_client()
        kwargs: dict = {
            "model": self._model,
            "messages": self._to_openai_messages(system, messages),
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            resp = await client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            # Some compatible servers reject response_format - retry without it.
            if json_mode:
                kwargs.pop("response_format", None)
                try:
                    resp = await client.chat.completions.create(**kwargs)
                except Exception as exc2:  # noqa: BLE001
                    raise AIProviderError(f"OpenAI-compatible API error: {exc2}") from exc2
            else:
                raise AIProviderError(f"OpenAI-compatible API error: {exc}") from exc

        usage = getattr(resp, "usage", None)
        return Completion(
            text=resp.choices[0].message.content or "",
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
        )

    async def _stream(
        self,
        *,
        system: str,
        messages: list[Message],
        max_tokens: int,
        temperature: float,
    ) -> AsyncIterator[str]:
        client = self._get_client()
        try:
            stream = await client.chat.completions.create(
                model=self._model,
                messages=self._to_openai_messages(system, messages),
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
        except Exception as exc:  # noqa: BLE001
            raise AIProviderError(f"OpenAI-compatible API error: {exc}") from exc
