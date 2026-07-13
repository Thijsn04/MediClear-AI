"""
Readability scoring.

The tool claims to write at a target CEFR level; this module *measures* it so
the claim can be verified and enforced. We compute a Flesch Reading Ease score
(a well-known, dependency-free heuristic) and map it to an approximate CEFR
band. It is a signal, not a certification — most reliable for Latin-script
languages, and used to decide whether a simplification pass is worthwhile.
"""

from __future__ import annotations

import re

from app.models.analysis import Readability

_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
_SENTENCE_RE = re.compile(r"[.!?…]+")
_VOWEL_GROUPS = re.compile(r"[aeiouyàâäéèêëïîôöùûüáíóúñãõ]+", re.IGNORECASE)


def _count_syllables(word: str) -> int:
    groups = _VOWEL_GROUPS.findall(word.lower())
    count = len(groups)
    if word.lower().endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def flesch_reading_ease(text: str) -> float | None:
    """Return the Flesch Reading Ease score (0–100, higher = easier)."""
    words = _WORD_RE.findall(text)
    sentences = [s for s in _SENTENCE_RE.split(text) if s.strip()]
    if not words or not sentences:
        return None
    num_words = len(words)
    num_sentences = max(1, len(sentences))
    num_syllables = sum(_count_syllables(w) for w in words)
    score = 206.835 - 1.015 * (num_words / num_sentences) - 84.6 * (num_syllables / num_words)
    return round(max(0.0, min(100.0, score)), 1)


def ease_to_cefr(score: float) -> str:
    """Map a Flesch Reading Ease score to an approximate CEFR level."""
    if score >= 80:
        return "A2"
    if score >= 60:
        return "B1"
    if score >= 50:
        return "B2"
    if score >= 30:
        return "C1"
    return "C2"


_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]


def meets_target(estimated: str, target: str) -> bool:
    """True when the estimated level is at or below (easier than) the target."""
    try:
        return _ORDER.index(estimated) <= _ORDER.index(target)
    except ValueError:
        return True


def assess(text: str, target_level: str) -> Readability:
    score = flesch_reading_ease(text)
    if score is None:
        return Readability(target_cefr=target_level)
    estimated = ease_to_cefr(score)
    return Readability(
        flesch_reading_ease=score,
        estimated_cefr=estimated,
        target_cefr=target_level,
        meets_target=meets_target(estimated, target_level),
    )
