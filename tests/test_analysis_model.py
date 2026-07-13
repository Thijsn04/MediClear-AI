"""Tests for the StructuredAnalysis model, markdown rendering, and grounding."""

from __future__ import annotations

import pytest

from app.models.analysis import DocumentType, KeyTerm, LabValue, StructuredAnalysis
from app.providers.base import BaseAIProvider


def test_render_markdown_includes_sections() -> None:
    analysis = StructuredAnalysis(
        document_type=DocumentType.LAB_REPORT,
        summary="Your blood test is mostly normal.",
        explanation="Everything looks fine.",
        key_terms=[KeyTerm(term="glucose", definition="blood sugar")],
        action_items=["Ask your doctor about diet."],
        lab_values=[LabValue(name="Glucose", value="5.2", unit="mmol/L", flag="normal")],
    )
    md = analysis.render_markdown()
    assert "## Summary" in md
    assert "## Lab Values" in md
    assert "glucose" in md
    assert "Ask your doctor" in md


def test_not_medical_render() -> None:
    analysis = StructuredAnalysis(
        document_type=DocumentType.NOT_MEDICAL, summary="This is a recipe, not a medical document."
    )
    assert "not look like a medical document" in analysis.render_markdown()


def test_grounding_flags_absent_terms() -> None:
    analysis = StructuredAnalysis(
        key_terms=[
            KeyTerm(term="hypertension", definition="high blood pressure"),
            KeyTerm(term="diabetes", definition="high blood sugar"),
        ]
    )
    BaseAIProvider._apply_grounding(analysis, "The patient has hypertension.")
    grounded = {kt.term: kt.found_in_source for kt in analysis.key_terms}
    assert grounded["hypertension"] is True
    assert grounded["diabetes"] is False


def test_parse_analysis_from_fenced_json() -> None:
    text = '```json\n{"summary": "hi", "explanation": "there"}\n```'
    analysis = BaseAIProvider._parse_analysis(text)
    assert analysis.summary == "hi"


def test_parse_analysis_falls_back_to_prose() -> None:
    analysis = BaseAIProvider._parse_analysis("just some prose, not json")
    assert "prose" in analysis.explanation
