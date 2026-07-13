"""
Anthropic Claude provider (native async client).

Model is freely configurable via ANTHROPIC_MODEL. Vision is supported on
Claude 3 and later.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.core.exceptions import AIProviderError, AIProviderNotConfiguredError
from app.core.logging import get_logger
from app.providers.base import BaseAIProvider, Completion, Message

logger = get_logger(__name__)


class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude provider — text and vision."""

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model
        self._client = None

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
        return True

    @property
    def supports_streaming(self) -> bool:
        return True

    # ------------------------------------------------------------------

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import anthropic
        except ImportError as exc:
            raise AIProviderError(
                "anthropic package is not installed. Run: pip install 'mediclear-ai[anthropic]'"
            ) from exc
        if not self.is_configured:
            raise AIProviderNotConfiguredError(self.name)
        self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
        return self._client

    @staticmethod
    def _to_anthropic_messages(messages: list[Message]) -> list[dict]:
        out: list[dict] = []
        for m in messages:
            if m.image is not None:
                content: list[dict] = [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": m.image.media_type,
                            "data": m.image.b64_data,
                        },
                    }
                ]
                if m.text:
                    content.append({"type": "text", "text": m.text})
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
        # Anthropic has no JSON flag; the prompt instructs JSON. Pre-fill an
        # opening brace to nudge JSON-only output when json_mode is requested.
        anthropic_messages = self._to_anthropic_messages(messages)
        if json_mode:
            anthropic_messages.append({"role": "assistant", "content": "{"})
        try:
            resp = await client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=anthropic_messages,
            )
        except Exception as exc:  # noqa: BLE001
            raise AIProviderError(f"Anthropic API error: {exc}") from exc

        text = resp.content[0].text if resp.content else ""
        if json_mode:
            text = "{" + text  # restore the prefilled brace
        usage = getattr(resp, "usage", None)
        return Completion(
            text=text,
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
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
            async with client.messages.stream(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=self._to_anthropic_messages(messages),
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as exc:  # noqa: BLE001
            raise AIProviderError(f"Anthropic API error: {exc}") from exc
