"""Text-to-speech endpoint — converts text to audio."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.v1.deps import rate_limited_identity
from app.core.exceptions import FeatureDisabledError
from app.dependencies import get_tts_service
from app.models.schemas import AudioRequest
from app.services.tts_service import TTSService

router = APIRouter()


@router.post(
    "/audio",
    response_class=Response,
    responses={200: {"content": {"audio/mpeg": {}}, "description": "Synthesized audio."}},
    summary="Text-to-speech synthesis",
    description=(
        "Convert text (typically an analysis explanation) to audio. The backend "
        "(cloud gTTS or offline local) is chosen by the `TTS_BACKEND` setting."
    ),
    tags=["Audio"],
)
async def audio(
    body: AudioRequest,
    tts_service: TTSService = Depends(get_tts_service),
    identity: str = Depends(rate_limited_identity),
) -> Response:
    if not tts_service.enabled:
        raise FeatureDisabledError("text-to-speech")
    audio_bytes = await tts_service.synthesize(text=body.text, language_code=body.language)
    return Response(content=audio_bytes, media_type=tts_service.media_type)
