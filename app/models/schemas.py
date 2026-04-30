"""
Pydantic request / response schemas for the MediClear AI API.

Language codes follow IETF BCP 47 short codes (e.g. "en", "nl").
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Supported languages
# ---------------------------------------------------------------------------

SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "nl": "Nederlands",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "tr": "Türkçe",
    "ar": "العربية",
    "pl": "Polski",
    "pt": "Português",
    "it": "Italiano",
    "zh": "中文",
    "ja": "日本語",
    "ko": "한국어",
    "ru": "Русский",
    "hi": "हिन्दी",
}

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class AnalyzeTextRequest(BaseModel):
    """Request body for plain-text document analysis."""

    text: str = Field(
        ...,
        min_length=10,
        max_length=50_000,
        description="Medical text to be simplified.",
        examples=["Patient has been diagnosed with type 2 diabetes mellitus…"],
    )
    language: str = Field(
        default="en",
        description=(
            "Target language code for the simplified output "
            f"(one of: {', '.join(SUPPORTED_LANGUAGES)})."
        ),
        examples=["en"],
    )

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        if v not in SUPPORTED_LANGUAGES:
            supported = ", ".join(SUPPORTED_LANGUAGES)
            raise ValueError(
                f"Unsupported language code '{v}'. Supported codes: {supported}."
            )
        return v


class ChatRequest(BaseModel):
    """Request body for a follow-up chat message."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=2_000,
        description="Patient's follow-up question about the analysed document.",
        examples=["Should I be worried about this result?"],
    )
    language: str = Field(
        default="en",
        description="Target language code for the response.",
        examples=["en"],
    )

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        if v not in SUPPORTED_LANGUAGES:
            supported = ", ".join(SUPPORTED_LANGUAGES)
            raise ValueError(
                f"Unsupported language code '{v}'. Supported codes: {supported}."
            )
        return v


class AudioRequest(BaseModel):
    """Request body for text-to-speech synthesis."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=10_000,
        description="Text to convert to speech.",
    )
    language: str = Field(
        default="en",
        description="Language code for TTS voice selection.",
        examples=["en"],
    )

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        if v not in SUPPORTED_LANGUAGES:
            supported = ", ".join(SUPPORTED_LANGUAGES)
            raise ValueError(
                f"Unsupported language code '{v}'. Supported codes: {supported}."
            )
        return v


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class AnalyzeResponse(BaseModel):
    """Response from a document analysis request."""

    session_id: str = Field(
        ..., description="Unique session identifier for follow-up chat."
    )
    analysis: str = Field(
        ..., description="Simplified medical explanation in the requested language."
    )
    language: str = Field(..., description="Language code of the response.")
    provider: str = Field(..., description="AI provider used for this analysis.")
    model: str = Field(..., description="Exact model name used for this analysis.")


class ChatResponse(BaseModel):
    """Response from a chat message."""

    session_id: str
    message: str = Field(..., description="The patient's original question.")
    response: str = Field(..., description="AI response in the requested language.")
    language: str


class HealthResponse(BaseModel):
    """API health-check response."""

    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    ai_provider: str
    ai_model: str
    ai_provider_configured: bool
    active_sessions: int
    timestamp: datetime


class LanguageInfo(BaseModel):
    """A supported language entry."""

    code: str
    name: str


class LanguagesResponse(BaseModel):
    """All languages supported by the API."""

    languages: list[LanguageInfo]


class ErrorResponse(BaseModel):
    """Standard error payload."""

    error: str
    detail: Optional[str] = None
    status_code: int
