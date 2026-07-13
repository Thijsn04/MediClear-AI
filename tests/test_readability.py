"""Tests for readability scoring."""

from __future__ import annotations

from app.services import readability


def test_simple_text_scores_easier_than_complex() -> None:
    simple = "The cat sat on the mat. The dog ran. We can go now."
    complex_ = (
        "The patient presents with an idiopathic thrombocytopenic condition "
        "necessitating comprehensive haematological reassessment."
    )
    assert readability.flesch_reading_ease(simple) > readability.flesch_reading_ease(complex_)


def test_ease_to_cefr_bands() -> None:
    assert readability.ease_to_cefr(90) == "A2"
    assert readability.ease_to_cefr(65) == "B1"
    assert readability.ease_to_cefr(10) == "C2"


def test_meets_target() -> None:
    assert readability.meets_target("A2", "B1") is True
    assert readability.meets_target("B1", "B1") is True
    assert readability.meets_target("C1", "B1") is False


def test_assess_populates_fields() -> None:
    result = readability.assess("This is a short and simple sentence.", "B1")
    assert result.flesch_reading_ease is not None
    assert result.estimated_cefr is not None
    assert result.target_cefr == "B1"


def test_assess_empty_text_is_safe() -> None:
    result = readability.assess("", "B1")
    assert result.target_cefr == "B1"
