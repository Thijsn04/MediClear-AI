"""
Resilience wrapper.

Wraps a primary provider plus an optional ordered list of fallback providers
and adds, transparently, to every low-level call:

* a per-attempt timeout,
* bounded retries with exponential backoff on transient errors,
* failover to the next provider when the primary is exhausted.

Because all the high-level logic (analyze/chat/simplify) lives in
:class:`BaseAIProvider` and only ever calls ``_complete`` / ``_stream``,
wrapping those two primitives makes the whole pipeline resilient.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from app.core.exceptions import AIProviderError
from app.core.logging import get_logger
from app.providers.base import BaseAIProvider, Completion

logger = get_logger(__name__)


class ResilientProvider(BaseAIProvider):
    def __init__(
        self,
        providers: list[BaseAIProvider],
        *,
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        if not providers:
            raise ValueError("ResilientProvider requires at least one provider")
        self._providers = providers
        self._primary = providers[0]
        self._timeout = timeout_seconds
        self._max_retries = max_retries

    # Identity delegates to the primary provider.
    @property
    def name(self) -> str:
        return self._primary.name

    @property
    def model(self) -> str:
        return self._primary.model

    @property
    def is_configured(self) -> bool:
        return self._primary.is_configured

    @property
    def supports_images(self) -> bool:
        return self._primary.supports_images

    @property
    def supports_streaming(self) -> bool:
        return self._primary.supports_streaming

    @property
    def inner(self) -> BaseAIProvider:
        return self._primary

    # ------------------------------------------------------------------

    async def _complete(self, **kwargs) -> Completion:  # type: ignore[override]
        last_exc: Exception | None = None
        for provider in self._providers:
            for attempt in range(self._max_retries + 1):
                try:
                    return await asyncio.wait_for(
                        provider._complete(**kwargs), timeout=self._timeout
                    )
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    logger.warning(
                        "provider.attempt_failed",
                        provider=provider.name,
                        attempt=attempt,
                        error=str(exc),
                    )
                    if attempt < self._max_retries:
                        await asyncio.sleep(min(2**attempt, 8))
            logger.warning("provider.failover", exhausted=provider.name)
        raise AIProviderError(f"All providers failed. Last error: {last_exc}") from last_exc

    async def _stream(self, **kwargs) -> AsyncIterator[str]:  # type: ignore[override]
        # Streaming failover is best-effort: try providers in order, but once a
        # provider has emitted its first chunk we commit to it.
        last_exc: Exception | None = None
        for provider in self._providers:
            if not provider.supports_streaming:
                continue
            try:
                emitted = False
                async for chunk in provider._stream(**kwargs):
                    emitted = True
                    yield chunk
                if emitted:
                    return
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                logger.warning("provider.stream_failed", provider=provider.name, error=str(exc))
        if last_exc is not None:
            raise AIProviderError(f"All streaming providers failed: {last_exc}") from last_exc
