"""
Application configuration — driven entirely by environment variables.

Every subsystem (AI providers, auth, rate limiting, sessions, caching,
privacy, TTS, observability) is configured here. Nothing is hardcoded in
source: operators set ``AI_PROVIDER`` to select a backend, then supply the
matching key and freely choose any model string that backend accepts.

The two headline deployment targets are supported by configuration alone:

* **Cloud API-first** — set provider to a hosted model, enable API-key auth
  and rate limiting, optionally point ``REDIS_URL`` at a shared store.
* **On-prem / air-gapped** — set the provider to a local OpenAI-compatible
  server (Ollama, vLLM, LM Studio), use the local TTS backend, and enable
  ``ZERO_RETENTION`` so no document content is ever persisted.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.version import __version__


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_name: str = "MediClear AI"
    app_version: str = __version__
    app_description: str = (
        "State-of-the-art medical document simplification — cloud or on-prem, "
        "API-first, provider-agnostic."
    )
    environment: Literal["development", "staging", "production"] = Field(
        default="production", alias="ENVIRONMENT"
    )
    debug: bool = False

    # ── Server ────────────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    # Maximum accepted request body in bytes (defends the event loop / memory
    # before the upload is ever buffered). Applies to multipart uploads too.
    max_request_body_bytes: int = Field(
        default=12 * 1024 * 1024, alias="MAX_REQUEST_BODY_BYTES"
    )

    # ── AI Provider selection ─────────────────────────────────────────────────
    # gemini | openai | anthropic. For OpenAI-compatible servers (Ollama, Azure,
    # Groq, vLLM, LM Studio) use AI_PROVIDER=openai + OPENAI_BASE_URL.
    ai_provider: Literal["gemini", "openai", "anthropic"] = Field(
        default="gemini", alias="AI_PROVIDER"
    )
    # Optional ordered fallback chain, e.g. "openai,anthropic". If the primary
    # provider fails after retries, these are tried in order. Empty = no fallback.
    ai_fallback_providers: list[str] = Field(
        default_factory=list, alias="AI_FALLBACK_PROVIDERS"
    )
    # Per-call resilience.
    ai_request_timeout_seconds: float = Field(
        default=60.0, alias="AI_REQUEST_TIMEOUT_SECONDS"
    )
    ai_max_retries: int = Field(default=2, alias="AI_MAX_RETRIES")
    ai_max_output_tokens: int = Field(default=4096, alias="AI_MAX_OUTPUT_TOKENS")
    ai_temperature: float = Field(default=0.2, alias="AI_TEMPERATURE")

    # ── Google Gemini ─────────────────────────────────────────────────────────
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")

    # ── OpenAI / OpenAI-compatible ────────────────────────────────────────────
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")
    openai_base_url: str = Field(default="", alias="OPENAI_BASE_URL")

    # ── Anthropic Claude ──────────────────────────────────────────────────────
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-sonnet-4-5", alias="ANTHROPIC_MODEL")

    # ── Clarification quality ─────────────────────────────────────────────────
    # Target CEFR reading level for output. The service estimates readability and
    # (when enforcement is on) asks the model to simplify further if it overshoots.
    target_reading_level: Literal["A2", "B1", "B2"] = Field(
        default="B1", alias="TARGET_READING_LEVEL"
    )
    enforce_reading_level: bool = Field(default=True, alias="ENFORCE_READING_LEVEL")
    max_simplification_passes: int = Field(
        default=1, alias="MAX_SIMPLIFICATION_PASSES"
    )

    # ── Result cache ──────────────────────────────────────────────────────────
    # Identical (document, language, level, model) requests reuse a cached result
    # instead of re-billing the provider. Uses Redis when REDIS_URL is set,
    # otherwise an in-process LRU.
    cache_enabled: bool = Field(default=True, alias="CACHE_ENABLED")
    cache_ttl_seconds: int = Field(default=86_400, alias="CACHE_TTL_SECONDS")
    cache_max_entries: int = Field(default=1024, alias="CACHE_MAX_ENTRIES")

    # ── Sessions ──────────────────────────────────────────────────────────────
    session_ttl_seconds: int = Field(default=3600, alias="SESSION_TTL_SECONDS")
    max_sessions: int = Field(default=1000, alias="MAX_SESSIONS")
    # When set, sessions and cache live in Redis (durable, multi-instance).
    # e.g. redis://localhost:6379/0. Empty = in-memory single-instance.
    redis_url: str = Field(default="", alias="REDIS_URL")

    # ── Privacy & retention ───────────────────────────────────────────────────
    # In zero-retention mode nothing derived from the document (source text,
    # summary, chat history) is stored server-side; follow-up chat is disabled
    # unless the client re-supplies context. Ideal for PHI-sensitive on-prem use.
    zero_retention: bool = Field(default=False, alias="ZERO_RETENTION")
    # Redact detected PII/PHI patterns from logs (document content is never
    # logged regardless; this covers metadata like filenames).
    redact_logs: bool = Field(default=True, alias="REDACT_LOGS")
    # Emit an audit event for every analysis/chat (who, when, sizes — never
    # content). Written through the structured logger under the "audit" channel.
    audit_logging: bool = Field(default=True, alias="AUDIT_LOGGING")

    # ── Uploads ───────────────────────────────────────────────────────────────
    max_upload_size_mb: int = Field(default=10, alias="MAX_UPLOAD_SIZE_MB")
    # Attempt OCR on image-only PDFs / images when the provider is text-only.
    enable_ocr: bool = Field(default=True, alias="ENABLE_OCR")

    # ── Text-to-speech ────────────────────────────────────────────────────────
    # gtts (cloud, Google) | local (offline, pyttsx3/espeak) | disabled
    tts_backend: Literal["gtts", "local", "disabled"] = Field(
        default="gtts", alias="TTS_BACKEND"
    )

    # ── Authentication ────────────────────────────────────────────────────────
    # When true, every /api/v1 mutation requires a valid key in the
    # `X-API-Key` header (or `Authorization: Bearer <key>`). Keys are supplied
    # as a comma-separated list; keep them out of source and logs.
    require_api_key: bool = Field(default=False, alias="REQUIRE_API_KEY")
    api_keys: list[str] = Field(default_factory=list, alias="API_KEYS")

    # ── Rate limiting ─────────────────────────────────────────────────────────
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    # Requests allowed per window, keyed by API key (or client IP when anon).
    rate_limit_requests: int = Field(default=60, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(
        default=60, alias="RATE_LIMIT_WINDOW_SECONDS"
    )

    # ── Frontend ──────────────────────────────────────────────────────────────
    enable_frontend: bool = Field(default=True, alias="ENABLE_FRONTEND")

    # ── Observability ─────────────────────────────────────────────────────────
    # Expose Prometheus metrics at /metrics.
    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Restrict to your frontend origin(s) in production, e.g.
    # ALLOWED_ORIGINS=["https://mediclear.example.com"].
    allowed_origins: list[str] = Field(default=["*"], alias="ALLOWED_ORIGINS")

    # ------------------------------------------------------------------
    # Validators / derived helpers
    # ------------------------------------------------------------------

    @field_validator("ai_fallback_providers", "api_keys", mode="before")
    @classmethod
    def _split_csv(cls, v: object) -> object:
        """Allow comma-separated strings as well as JSON lists in env vars."""
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped or stripped.startswith("["):
                return v  # empty or JSON list — let pydantic handle it
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return v

    @property
    def cors_allow_credentials(self) -> bool:
        """Credentials must be disabled when origins are the wildcard, per the
        CORS spec (browsers reject `Access-Control-Allow-Credentials: true`
        alongside `Access-Control-Allow-Origin: *`)."""
        return self.allowed_origins != ["*"]

    @property
    def use_redis(self) -> bool:
        return bool(self.redis_url)


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton for the process lifetime)."""
    return Settings()
