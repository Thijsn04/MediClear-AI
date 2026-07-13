"""
Supported languages catalogue.

A single source of truth for every language the tool can produce output in,
with the metadata each subsystem needs: the display name (native), the English
name (used to instruct the model), a right-to-left flag (for correct rendering
of the *response*, not just the UI), and the TTS engine's language tag.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    code: str  # BCP 47 short code, e.g. "en"
    native_name: str  # endonym shown in UI, e.g. "Nederlands"
    english_name: str  # used in prompts, e.g. "Dutch"
    rtl: bool  # right-to-left script
    tts_code: str  # language tag for the TTS backend


_LANGUAGES: tuple[Language, ...] = (
    Language("en", "English", "English", False, "en"),
    Language("nl", "Nederlands", "Dutch", False, "nl"),
    Language("de", "Deutsch", "German", False, "de"),
    Language("fr", "Français", "French", False, "fr"),
    Language("es", "Español", "Spanish", False, "es"),
    Language("tr", "Türkçe", "Turkish", False, "tr"),
    Language("ar", "العربية", "Arabic", True, "ar"),
    Language("pl", "Polski", "Polish", False, "pl"),
    Language("pt", "Português", "Portuguese", False, "pt"),
    Language("it", "Italiano", "Italian", False, "it"),
    Language("zh", "中文", "Chinese", False, "zh-CN"),
    Language("ja", "日本語", "Japanese", False, "ja"),
    Language("ko", "한국어", "Korean", False, "ko"),
    Language("ru", "Русский", "Russian", False, "ru"),
    Language("hi", "हिन्दी", "Hindi", False, "hi"),
    Language("uk", "Українська", "Ukrainian", False, "uk"),
    Language("fa", "فارسی", "Persian", True, "fa"),
)

LANGUAGES: dict[str, Language] = {lang.code: lang for lang in _LANGUAGES}

# Backwards-compatible mapping used throughout the app: code -> native name.
SUPPORTED_LANGUAGES: dict[str, str] = {lang.code: lang.native_name for lang in _LANGUAGES}


def get_language(code: str) -> Language:
    """Return the Language for ``code``, defaulting to English."""
    return LANGUAGES.get(code, LANGUAGES["en"])


def is_supported(code: str) -> bool:
    return code in LANGUAGES
