"""
Terminology grounding.

Backs key-term definitions with a curated source so they are not simply invented
by the model:

* :class:`GlossaryLookup` - a bundled, offline glossary (English). Always on.
* :class:`MedlinePlusLookup` - an opt-in online lookup against the U.S. National
  Library of Medicine's MedlinePlus web service (English/Spanish), used only
  when ``TERMINOLOGY_ONLINE`` is enabled and internet egress is allowed.

:class:`TerminologyService.enrich` walks a list of :class:`KeyTerm` and, when a
trusted definition is found *in the output language*, replaces the model's
definition and records the provenance (``source`` / ``source_url``). Lookups are
best-effort: any failure leaves the model's definition untouched.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.logging import get_logger
from app.models.analysis import KeyTerm

logger = get_logger(__name__)

_GLOSSARY_PATH = Path(__file__).parent.parent / "data" / "glossary.json"
# MedlinePlus web service supports English and Spanish health-topic databases.
_MEDLINEPLUS_DB = {"en": "healthTopics", "es": "healthTopicsSpanish"}


@dataclass
class TermDefinition:
    term: str
    definition: str
    source: str  # "glossary" | "online"
    language: str
    url: str | None = None


def _normalise(term: str) -> str:
    return re.sub(r"\s+", " ", term.strip().lower())


class TermLookup(ABC):
    @abstractmethod
    async def lookup(self, term: str, language: str) -> TermDefinition | None: ...


@lru_cache
def _load_glossary() -> dict[str, str]:
    try:
        data = json.loads(_GLOSSARY_PATH.read_text(encoding="utf-8"))
        return {_normalise(k): v for k, v in data.get("terms", {}).items()}
    except Exception as exc:  # noqa: BLE001
        logger.warning("glossary.load_failed", error=str(exc))
        return {}


class GlossaryLookup(TermLookup):
    """Offline glossary lookup (English definitions only)."""

    def __init__(self) -> None:
        self._terms = _load_glossary()

    async def lookup(self, term: str, language: str) -> TermDefinition | None:
        if language != "en":
            return None
        key = _normalise(term)
        definition = self._terms.get(key)
        if definition is None:
            # Try dropping a trailing plural 's' for a loose match.
            definition = self._terms.get(key.rstrip("s"))
        if definition is None:
            return None
        return TermDefinition(term=term, definition=definition, source="glossary", language="en")

    @property
    def size(self) -> int:
        return len(self._terms)


class MedlinePlusLookup(TermLookup):
    """Online lookup against the MedlinePlus web service (English/Spanish)."""

    _ENDPOINT = "https://wsearch.nlm.nih.gov/ws/query"

    def __init__(self, timeout_seconds: float = 4.0) -> None:
        self._timeout = timeout_seconds

    async def lookup(self, term: str, language: str) -> TermDefinition | None:
        db = _MEDLINEPLUS_DB.get(language)
        if db is None:
            return None
        try:
            import httpx

            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    self._ENDPOINT,
                    params={"db": db, "term": term, "retmax": "1"},
                )
                resp.raise_for_status()
                return self._parse(resp.text, term, language)
        except Exception as exc:  # noqa: BLE001 - online lookup is best-effort
            logger.info("terminology.online_failed", term=term, error=str(exc))
            return None

    @staticmethod
    def _parse(xml_text: str, term: str, language: str) -> TermDefinition | None:
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return None
        doc = root.find(".//document")
        if doc is None:
            return None
        fields = {c.get("name"): c for c in doc.findall("content")}
        summary_el = fields.get("FullSummary") or fields.get("snippet")
        if summary_el is None or not summary_el.text:
            return None
        # Strip highlight markup and tags, keep the first two sentences.
        text = re.sub(r"<[^>]+>", "", summary_el.text)
        text = re.sub(r"\s+", " ", text).strip()
        sentences = re.split(r"(?<=[.!?])\s+", text)
        definition = " ".join(sentences[:2]).strip()
        if not definition:
            return None
        url = doc.get("url")
        return TermDefinition(
            term=term, definition=definition, source="online", language=language, url=url
        )


class TerminologyService:
    def __init__(
        self,
        *,
        enabled: bool = True,
        online: bool = False,
        timeout_seconds: float = 4.0,
    ) -> None:
        self._enabled = enabled
        self._lookups: list[TermLookup] = []
        if enabled:
            # Prefer the online (language-aware, citable) source, then glossary.
            if online:
                self._lookups.append(MedlinePlusLookup(timeout_seconds))
            self._lookups.append(GlossaryLookup())

    async def enrich(self, key_terms: list[KeyTerm], language: str) -> list[KeyTerm]:
        if not self._enabled or not self._lookups:
            return key_terms
        for kt in key_terms:
            for lookup in self._lookups:
                try:
                    found = await lookup.lookup(kt.term, language)
                except Exception:  # noqa: BLE001
                    found = None
                if found is not None:
                    kt.definition = found.definition
                    kt.source = found.source  # type: ignore[assignment]
                    kt.source_url = found.url
                    break
        return key_terms
