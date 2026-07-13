"""
Provider contract.

Providers are deliberately *thin*: each one implements a single low-level
primitive - :meth:`BaseAIProvider._complete` (and optionally
:meth:`BaseAIProvider._stream`) - that turns a normalised message list into
text. All the domain logic (prompt construction, JSON parsing into a
:class:`StructuredAnalysis`, faithfulness grounding, readability) lives once in
this base class, so adding a provider means writing ~40 lines, not duplicating
the whole pipeline.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from app.models.analysis import StructuredAnalysis
from app.providers.prompts import build_analysis_prompt, build_chat_prompt

# ---------------------------------------------------------------------------
# Transport-level data structures shared by every provider
# ---------------------------------------------------------------------------


@dataclass
class ImagePart:
    """An image attached to a message (base64-encoded bytes + media type)."""

    b64_data: str
    media_type: str  # e.g. "image/png"


@dataclass
class Message:
    """A normalised chat message. ``image`` is set only for multimodal turns."""

    role: str  # "system" | "user" | "assistant"
    text: str = ""
    image: ImagePart | None = None


@dataclass
class ProcessedDocument:
    """Normalised user content produced by DocumentService."""

    type: str  # "text" | "image"
    text: str | None = None
    image: ImagePart | None = None
    filename: str | None = None


@dataclass
class ConversationMessage:
    """A single stored turn in a chat conversation."""

    role: str  # "user" | "assistant"
    content: str


@dataclass
class Completion:
    """A provider's raw text completion plus usage metadata."""

    text: str
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class AnalysisResult:
    """Parsed, structured analysis plus provenance."""

    analysis: StructuredAnalysis
    provider: str
    model: str
    raw_text: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    initial_history: list[ConversationMessage] = field(default_factory=list)


class BaseAIProvider(ABC):
    """Abstract interface every MediClear AI provider must satisfy."""

    # ------------------------------------------------------------------
    # Identity (implement in subclasses)
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier, e.g. 'gemini', 'openai', 'anthropic'."""

    @property
    @abstractmethod
    def model(self) -> str:
        """The exact model string being used (from configuration)."""

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """True when the required credentials are present."""

    @property
    def supports_images(self) -> bool:
        """Whether this provider+model can accept image input."""
        return False

    @property
    def supports_streaming(self) -> bool:
        """Whether :meth:`_stream` is implemented."""
        return False

    # ------------------------------------------------------------------
    # Low-level primitives (implement in subclasses)
    # ------------------------------------------------------------------

    @abstractmethod
    async def _complete(
        self,
        *,
        system: str,
        messages: list[Message],
        max_tokens: int,
        temperature: float,
        json_mode: bool,
    ) -> Completion:
        """Return a single completion for the given system prompt + messages."""

    async def _stream(
        self,
        *,
        system: str,
        messages: list[Message],
        max_tokens: int,
        temperature: float,
    ) -> AsyncIterator[str]:
        """Yield text chunks. Default: not supported."""
        raise NotImplementedError(f"{self.name} does not support streaming")
        yield  # pragma: no cover  (makes this an async generator)

    # ------------------------------------------------------------------
    # High-level operations (shared logic - do not override)
    # ------------------------------------------------------------------

    async def analyze_document(
        self,
        document: ProcessedDocument,
        *,
        language_name: str,
        target_level: str,
        max_tokens: int,
        temperature: float,
    ) -> AnalysisResult:
        """Analyse a document and return a structured, grounded result."""
        system = build_analysis_prompt(language_name=language_name, target_level=target_level)
        user = self._document_message(document)

        completion = await self._complete(
            system=system,
            messages=[user],
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=True,
        )

        analysis = self._parse_analysis(completion.text)
        if document.type == "text" and document.text:
            self._apply_grounding(analysis, document.text)

        initial_history = [
            ConversationMessage(role="user", content="[Document submitted for analysis]"),
            ConversationMessage(role="assistant", content=analysis.render_markdown()),
        ]
        return AnalysisResult(
            analysis=analysis,
            provider=self.name,
            model=self.model,
            raw_text=completion.text,
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
            initial_history=initial_history,
        )

    async def stream_analysis(
        self,
        document: ProcessedDocument,
        *,
        language_name: str,
        target_level: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncIterator[str]:
        """Stream the raw model output (JSON) for an analysis, chunk by chunk.

        The caller accumulates the chunks, extracts a progressive explanation for
        display, and parses the final text via :meth:`parse_analysis_text`.
        """
        system = build_analysis_prompt(language_name=language_name, target_level=target_level)
        user = self._document_message(document)
        async for chunk in self._stream(
            system=system, messages=[user], max_tokens=max_tokens, temperature=temperature
        ):
            yield chunk

    def parse_analysis_text(
        self, text: str, *, source_text: str | None = None
    ) -> StructuredAnalysis:
        """Parse accumulated model text into a grounded StructuredAnalysis."""
        analysis = self._parse_analysis(text)
        if source_text:
            self._apply_grounding(analysis, source_text)
        return analysis

    async def simplify(
        self,
        analysis: StructuredAnalysis,
        *,
        language_name: str,
        target_level: str,
        max_tokens: int,
        temperature: float,
        source_text: str | None = None,
    ) -> StructuredAnalysis:
        """Ask the model to rewrite an over-complex explanation more simply."""
        system = build_analysis_prompt(
            language_name=language_name, target_level=target_level, simplify_pass=True
        )
        user = Message(
            role="user",
            text=(
                "Rewrite the following explanation so it is easier to read at the "
                f"target level, keeping all facts. Return the same JSON structure.\n\n"
                f"{analysis.model_dump_json()}"
            ),
        )
        completion = await self._complete(
            system=system,
            messages=[user],
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=True,
        )
        rewritten = self._parse_analysis(completion.text)
        if source_text:
            self._apply_grounding(rewritten, source_text)
        return rewritten

    async def chat(
        self,
        *,
        message: str,
        document_context: str,
        history: list[ConversationMessage],
        language_name: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Answer a follow-up question grounded in the original document."""
        system = build_chat_prompt(document_context=document_context, language_name=language_name)
        messages = [Message(role=m.role, text=m.content) for m in history]
        messages.append(Message(role="user", text=message))

        completion = await self._complete(
            system=system,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=False,
        )
        return completion.text

    async def stream_chat(
        self,
        *,
        message: str,
        document_context: str,
        history: list[ConversationMessage],
        language_name: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncIterator[str]:
        """Stream a follow-up answer token-by-token."""
        system = build_chat_prompt(document_context=document_context, language_name=language_name)
        messages = [Message(role=m.role, text=m.content) for m in history]
        messages.append(Message(role="user", text=message))

        async for chunk in self._stream(
            system=system,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        ):
            yield chunk

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _document_message(document: ProcessedDocument) -> Message:
        if document.type == "text":
            return Message(role="user", text=f"MEDICAL DOCUMENT:\n{document.text}")
        if document.type == "image":
            return Message(
                role="user",
                text="Analyse this medical document image.",
                image=document.image,
            )
        raise ValueError(f"Unknown document type: {document.type}")

    @staticmethod
    def _parse_analysis(text: str) -> StructuredAnalysis:
        """Parse model output into a StructuredAnalysis, tolerating stray prose
        or ```json fences around the JSON object."""
        payload = _extract_json_object(text)
        if payload is not None:
            try:
                return StructuredAnalysis.model_validate(payload)
            except Exception:  # noqa: BLE001 - fall through to text fallback
                pass
        # Fallback: the model returned prose, not JSON. Preserve it as the
        # explanation so the caller still gets a usable result.
        return StructuredAnalysis(summary="", explanation=text.strip())

    @staticmethod
    def _apply_grounding(analysis: StructuredAnalysis, source_text: str) -> None:
        """Faithfulness check: flag key terms not present in the source."""
        haystack = source_text.lower()
        for term in analysis.key_terms:
            term.found_in_source = term.term.lower() in haystack


def _extract_json_object(text: str) -> dict | None:
    """Best-effort extraction of a single JSON object from model output."""
    text = text.strip()
    if text.startswith("```"):
        # Strip a ```json ... ``` fence.
        text = text.split("```", 2)[1] if text.count("```") >= 2 else text
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        result = json.loads(text[start : end + 1])
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError:
        return None
