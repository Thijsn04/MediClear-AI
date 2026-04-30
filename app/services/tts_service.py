"""
Text-to-speech service using Google Text-to-Speech (gTTS).

gTTS requires an internet connection to Google's TTS API.
For fully on-premises deployments, replace this implementation with
a local TTS engine (e.g. Coqui TTS, Piper, or eSpeak).
"""

from __future__ import annotations

import io
import tempfile
import os

from app.core.exceptions import TTSError
from app.core.logging import get_logger
from app.models.schemas import SUPPORTED_LANGUAGES

logger = get_logger(__name__)

# Map from BCP 47 language codes to gTTS language tags.
# gTTS uses slightly different codes for some languages.
_GTTS_LANG_MAP: dict[str, str] = {
    "en": "en",
    "nl": "nl",
    "de": "de",
    "fr": "fr",
    "es": "es",
    "tr": "tr",
    "ar": "ar",
    "pl": "pl",
    "pt": "pt",
    "it": "it",
    "zh": "zh-CN",
    "ja": "ja",
    "ko": "ko",
    "ru": "ru",
    "hi": "hi",
}


class TTSService:
    """Converts text to MP3 audio using gTTS."""

    async def synthesize(self, text: str, language_code: str) -> bytes:
        """
        Synthesize text into MP3 audio bytes.

        Parameters
        ----------
        text:
            The text to synthesize.
        language_code:
            BCP 47 language code (e.g. 'en', 'nl').

        Returns
        -------
        bytes
            Raw MP3 audio data.
        """
        try:
            from gtts import gTTS  # type: ignore[import-untyped]
        except ImportError as exc:
            raise TTSError(
                "gTTS package is not installed. Run: pip install gTTS"
            ) from exc

        gtts_code = _GTTS_LANG_MAP.get(language_code, "en")

        try:
            logger.info("tts.synthesize", language=language_code, gtts_code=gtts_code)
            tts = gTTS(text=text, lang=gtts_code)
            buffer = io.BytesIO()
            tts.write_to_fp(buffer)
            buffer.seek(0)
            return buffer.read()
        except Exception as exc:
            logger.error("tts.error", error=str(exc))
            raise TTSError(str(exc)) from exc
