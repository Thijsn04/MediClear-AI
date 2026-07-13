"""Tests for the progressive explanation extractor."""

from __future__ import annotations

from app.services.streaming import ExplanationStreamExtractor


def _feed_incrementally(full: str, step: int = 7) -> tuple[str, bool]:
    ext = ExplanationStreamExtractor()
    out = ""
    for i in range(step, len(full) + step, step):
        out += ext.feed(full[:i])
    return out, ext.done


def test_extracts_explanation_progressively() -> None:
    payload = '{"summary": "s", "explanation": "Hello world, this is clear.", "x": 1}'
    text, done = _feed_incrementally(payload)
    assert text == "Hello world, this is clear."
    assert done is True


def test_handles_escaped_characters() -> None:
    payload = '{"explanation": "line one\\nline two with a \\"quote\\"."}'
    text, done = _feed_incrementally(payload, step=5)
    assert text == 'line one\nline two with a "quote".'
    assert done is True


def test_no_explanation_field_yields_nothing() -> None:
    ext = ExplanationStreamExtractor()
    assert ext.feed('{"summary": "only summary"}') == ""
    assert ext.done is False


def test_partial_then_complete() -> None:
    ext = ExplanationStreamExtractor()
    assert ext.feed('{"explanation": "Hel') == "Hel"
    assert ext.feed('{"explanation": "Hello') == "lo"
    assert ext.feed('{"explanation": "Hello."}') == "."
    assert ext.done is True
