"""
Request / response schemas for the MediClear AI API.

The analysis response carries the full :class:`StructuredAnalysis` object
*and* a rendered markdown convenience field, so programmatic consumers read
structured fields while simple clients can display the markdown directly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.analysis import StructuredAnalysis
from app.models.languages import SUPPORTED_LANGUAGES, is_supported

__all__ = [
    "SUPPORTED_LANGUAGES",
    "AnalyzeTextRequest",
    "ChatRequest",
    "AudioRequest",
    "AnalyzeResponse",
    "ChatResponse",
    "HealthResponse",
    "LanguageInfo",
    "LanguagesResponse",
    "SessionResponse",
    "ErrorResponse",
]

_LEVELS = ("A2", "B1", "B2")


def _validate_language(v: str) -> str:
    if not is_supported(v):
        raise ValueError(
            f"Unsupported language code '{v}'. Supported: {', '.join(SUPPORTED_LANGUAGES)}."
        )
    return v


# ── Requests ───────────────────────────────────────────────────────────────


class AnalyzeTextRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=100_000)
    language: str = Field(default="en")
    reading_level: Literal["A2", "B1", "B2"] | None = Field(default=None)

    @field_validator("language")
    @classmethod
    def _check_language(cls, v: str) -> str:
        return _validate_language(v)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2_000)
    language: str = Field(default="en")

    @field_validator("language")
    @classmethod
    def _check_language(cls, v: str) -> str:
        return _validate_language(v)


class AudioRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10_000)
    language: str = Field(default="en")

    @field_validator("language")
    @classmethod
    def _check_language(cls, v: str) -> str:
        return _validate_language(v)


# ── Responses ──────────────────────────────────────────────────────────────


class AnalyzeResponse(BaseModel):
    session_id: str | None = Field(
        default=None,
        description="Session id for follow-up chat. Null in zero-retention mode.",
    )
    analysis: StructuredAnalysis = Field(..., description="Structured analysis.")
    markdown: str = Field(..., description="Rendered markdown view of the analysis.")
    language: str
    provider: str
    model: str
    cached: bool = False


class ChatResponse(BaseModel):
    session_id: str
    message: str
    response: str
    language: str


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    ai_provider: str
    ai_model: str
    ai_provider_configured: bool
    ai_provider_reachable: bool | None = None
    session_store: str
    active_sessions: int
    timestamp: datetime


class LanguageInfo(BaseModel):
    code: str
    name: str
    english_name: str
    rtl: bool


class LanguagesResponse(BaseModel):
    languages: list[LanguageInfo]


class SessionResponse(BaseModel):
    session_id: str
    provider: str
    model: str
    language: str
    message_count: int
    created_at: datetime


class ErrorResponse(BaseModel):
    error: str
    status_code: int
    request_id: str | None = None
