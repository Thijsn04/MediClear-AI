"""Tests for terminology grounding (glossary + enrichment)."""

from __future__ import annotations

import pytest

from app.models.analysis import KeyTerm
from app.services.terminology import GlossaryLookup, TerminologyService


@pytest.mark.asyncio
async def test_glossary_lookup_hits_known_term() -> None:
    lookup = GlossaryLookup()
    assert lookup.size > 0
    result = await lookup.lookup("Hypertension", "en")
    assert result is not None
    assert result.source == "glossary"
    assert "blood pressure" in result.definition.lower()


@pytest.mark.asyncio
async def test_glossary_lookup_plural_fallback() -> None:
    lookup = GlossaryLookup()
    # "tumors" should loosely match "tumor" via the trailing-s fallback.
    result = await lookup.lookup("tumors", "en")
    assert result is not None


@pytest.mark.asyncio
async def test_glossary_lookup_misses_unknown_and_non_english() -> None:
    lookup = GlossaryLookup()
    assert await lookup.lookup("floopglorbin", "en") is None
    assert await lookup.lookup("hypertension", "nl") is None  # glossary is English-only


@pytest.mark.asyncio
async def test_enrich_overrides_definition_and_records_source() -> None:
    service = TerminologyService(enabled=True, online=False)
    terms = [
        KeyTerm(term="hypertension", definition="a made-up definition"),
        KeyTerm(term="floopglorbin", definition="untouched"),
    ]
    enriched = await service.enrich(terms, "en")
    assert enriched[0].source == "glossary"
    assert "blood pressure" in enriched[0].definition.lower()
    assert enriched[1].source == "model"
    assert enriched[1].definition == "untouched"


@pytest.mark.asyncio
async def test_enrich_disabled_is_noop() -> None:
    service = TerminologyService(enabled=False)
    terms = [KeyTerm(term="hypertension", definition="kept")]
    enriched = await service.enrich(terms, "en")
    assert enriched[0].definition == "kept"
    assert enriched[0].source == "model"
