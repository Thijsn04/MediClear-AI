"""
Provider registry / factory.

Builds a single provider by name, and assembles the resilient primary+fallback
chain from settings. Kept separate from the service layer so providers can be
instantiated (and unit-tested) without pulling in orchestration.
"""

from __future__ import annotations

from app.config import Settings
from app.core.exceptions import AIProviderError
from app.providers.base import BaseAIProvider
from app.providers.resilient import ResilientProvider


def build_single_provider(name: str, settings: Settings) -> BaseAIProvider:
    if name == "gemini":
        from app.providers.gemini import GeminiProvider

        return GeminiProvider(api_key=settings.google_api_key, model=settings.gemini_model)
    if name == "openai":
        from app.providers.openai_provider import OpenAIProvider

        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url,
        )
    if name == "anthropic":
        from app.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(
            api_key=settings.anthropic_api_key, model=settings.anthropic_model
        )
    raise AIProviderError(
        f"Unknown AI provider '{name}'. Valid options: gemini, openai, anthropic."
    )


def build_provider(settings: Settings) -> BaseAIProvider:
    """Build the primary provider wrapped with retries/timeout/fallback."""
    chain: list[BaseAIProvider] = [build_single_provider(settings.ai_provider, settings)]
    for fallback in settings.ai_fallback_providers:
        if fallback and fallback != settings.ai_provider:
            chain.append(build_single_provider(fallback, settings))
    return ResilientProvider(
        chain,
        timeout_seconds=settings.ai_request_timeout_seconds,
        max_retries=settings.ai_max_retries,
    )
