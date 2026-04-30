"""
Application configuration — driven entirely by environment variables.

Developers set AI_PROVIDER to select the backend, then supply the matching
API key and freely choose any model string supported by that provider.
No model names are hardcoded; every default is just a sensible suggestion
that can be overridden without touching source code.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_name: str = "MediClear AI"
    app_version: str = "2.0.0"
    app_description: str = (
        "Enterprise-grade medical document simplification for hospitals and clinics."
    )
    debug: bool = False

    # ── Server ────────────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000

    # ── AI Provider selection ─────────────────────────────────────────────────
    # Set AI_PROVIDER to one of: gemini | openai | anthropic
    # For OpenAI-compatible APIs (Ollama, Azure OpenAI, Groq, LM Studio, vLLM…)
    # set AI_PROVIDER=openai and provide OPENAI_BASE_URL.
    ai_provider: Literal["gemini", "openai", "anthropic"] = Field(
        default="gemini", alias="AI_PROVIDER"
    )

    # ── Google Gemini ─────────────────────────────────────────────────────────
    # Any model available to your API key, e.g.:
    #   gemini-2.5-flash | gemini-2.5-pro | gemini-1.5-pro | gemini-1.5-flash
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")

    # ── OpenAI / OpenAI-compatible ────────────────────────────────────────────
    # Any model string accepted by the target API, e.g.:
    #   gpt-4o | gpt-4.1 | o3 | gpt-4o-mini         (OpenAI)
    #   llama3.2 | mistral | phi4 | qwen2.5           (Ollama)
    #   meta-llama/Llama-3-70b-chat-hf                (Groq / Together)
    #   …any model your Azure deployment or compatible server exposes
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")
    # Override to point at Ollama, Azure OpenAI, Groq, LM Studio, vLLM, etc.
    # Leave empty to use the official OpenAI API.
    openai_base_url: str = Field(default="", alias="OPENAI_BASE_URL")

    # ── Anthropic Claude ──────────────────────────────────────────────────────
    # Any model available to your API key, e.g.:
    #   claude-opus-4-5 | claude-sonnet-4-5 | claude-3-5-haiku-20241022
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(
        default="claude-opus-4-5", alias="ANTHROPIC_MODEL"
    )

    # ── Session management ────────────────────────────────────────────────────
    # Seconds of inactivity before a chat session is purged from memory.
    session_ttl_seconds: int = Field(default=3600, alias="SESSION_TTL_SECONDS")
    # Maximum concurrent sessions held in memory.
    max_sessions: int = Field(default=1000, alias="MAX_SESSIONS")

    # ── Upload limits ─────────────────────────────────────────────────────────
    max_upload_size_mb: int = Field(default=10, alias="MAX_UPLOAD_SIZE_MB")

    # ── CORS ──────────────────────────────────────────────────────────────────
    # In production, restrict to your frontend origin, e.g. "https://mediclear.example.com"
    allowed_origins: list[str] = Field(default=["*"], alias="ALLOWED_ORIGINS")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton for the process lifetime)."""
    return Settings()
