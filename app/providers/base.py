"""Abstract base class that every AI provider must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProcessedDocument:
    """
    Normalised representation of user-submitted content, produced by
    DocumentService before being handed to a provider.
    """

    type: str  # "text" | "image"
    text: Optional[str] = None
    image_bytes: Optional[bytes] = None
    image_media_type: Optional[str] = None  # e.g. "image/jpeg"
    filename: Optional[str] = None


@dataclass
class ConversationMessage:
    """A single turn in a chat conversation."""

    role: str  # "user" | "assistant"
    content: str


@dataclass
class AnalysisResult:
    """Returned by a provider after analysing a document."""

    text: str
    provider: str
    model: str
    initial_history: list[ConversationMessage] = field(default_factory=list)


class BaseAIProvider(ABC):
    """
    Abstract interface that every MediClear AI provider must satisfy.

    Providers are intentionally kept thin — they receive already-processed
    content and return plain strings.  All session/history management lives
    in the service layer.
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier, e.g. 'gemini', 'openai', 'anthropic'."""

    @property
    @abstractmethod
    def model(self) -> str:
        """The exact model string being used (comes from configuration)."""

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Return True when the required credentials are present."""

    @property
    def supports_images(self) -> bool:  # noqa: D401
        """
        Whether this provider+model combination can process image inputs.
        Defaults to False; override in subclasses that support vision.
        """
        return False

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    @abstractmethod
    async def analyze_document(
        self,
        document: ProcessedDocument,
        language_name: str,
    ) -> AnalysisResult:
        """
        Analyse a medical document and return a simplified explanation.

        Parameters
        ----------
        document:
            Pre-processed document content.
        language_name:
            Full language name to instruct the model (e.g. 'English').

        Returns
        -------
        AnalysisResult
            The simplified explanation and metadata.
        """

    @abstractmethod
    async def chat(
        self,
        message: str,
        document_summary: str,
        history: list[ConversationMessage],
        language_name: str,
    ) -> str:
        """
        Answer a patient's follow-up question in context.

        Parameters
        ----------
        message:
            The patient's question.
        document_summary:
            The initial AI analysis (used as grounding context).
        history:
            Previous conversation turns in this session.
        language_name:
            Full language name for the response.

        Returns
        -------
        str
            The AI's answer.
        """
