"""
Text-to-speech with pluggable backends.

* ``gtts``     — Google Text-to-Speech (cloud; requires internet).
* ``local``    — offline synthesis via pyttsx3/espeak (for air-gapped use).
* ``disabled`` — audio endpoint returns 404.

Selected by the ``TTS_BACKEND`` setting so the same code serves both the cloud
and on-prem deployment targets.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from app.core.exceptions import TTSError
from app.core.logging import get_logger
from app.models.languages import get_language

logger = get_logger(__name__)


class TTSBackend(ABC):
    media_type: str = "audio/mpeg"

    @abstractmethod
    async def synthesize(self, text: str, language_code: str) -> bytes: ...


class GTTSBackend(TTSBackend):
    media_type = "audio/mpeg"

    async def synthesize(self, text: str, language_code: str) -> bytes:
        try:
            from gtts import gTTS
        except ImportError as exc:
            raise TTSError("gTTS is not installed. Run: pip install gTTS") from exc

        tts_code = get_language(language_code).tts_code

        def _run() -> bytes:
            import io

            tts = gTTS(text=text, lang=tts_code)
            buffer = io.BytesIO()
            tts.write_to_fp(buffer)
            return buffer.getvalue()

        try:
            logger.info("tts.synthesize", backend="gtts", language=language_code)
            return await asyncio.to_thread(_run)
        except Exception as exc:  # noqa: BLE001
            raise TTSError(str(exc)) from exc


class LocalTTSBackend(TTSBackend):
    """Offline synthesis via pyttsx3 (espeak/nsss/sapi5). Produces WAV."""

    media_type = "audio/wav"

    async def synthesize(self, text: str, language_code: str) -> bytes:
        try:
            import pyttsx3  # noqa: F401
        except ImportError as exc:
            raise TTSError(
                "Local TTS requires pyttsx3. Run: pip install pyttsx3 "
                "(and install espeak on the host)."
            ) from exc

        def _run() -> bytes:
            import os
            import tempfile

            import pyttsx3

            engine = pyttsx3.init()
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                path = tmp.name
            try:
                engine.save_to_file(text, path)
                engine.runAndWait()
                with open(path, "rb") as fh:
                    return fh.read()
            finally:
                if os.path.exists(path):
                    os.unlink(path)

        try:
            logger.info("tts.synthesize", backend="local", language=language_code)
            return await asyncio.to_thread(_run)
        except Exception as exc:  # noqa: BLE001
            raise TTSError(str(exc)) from exc


class TTSService:
    def __init__(self, backend: str = "gtts") -> None:
        self._backend_name = backend
        self._backend: TTSBackend | None = None
        if backend == "gtts":
            self._backend = GTTSBackend()
        elif backend == "local":
            self._backend = LocalTTSBackend()
        elif backend == "disabled":
            self._backend = None
        else:
            raise TTSError(f"Unknown TTS backend '{backend}'.")

    @property
    def enabled(self) -> bool:
        return self._backend is not None

    @property
    def media_type(self) -> str:
        return self._backend.media_type if self._backend else "audio/mpeg"

    async def synthesize(self, text: str, language_code: str) -> bytes:
        if self._backend is None:
            raise TTSError("Text-to-speech is disabled on this server.")
        return await self._backend.synthesize(text, language_code)
