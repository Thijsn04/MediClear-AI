"""Text-to-speech endpoint — converts analysis text to MP3 audio."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.dependencies import get_tts_service
from app.models.schemas import AudioRequest
from app.services.tts_service import TTSService

router = APIRouter()


@router.post(
    "/audio",
    response_class=Response,
    responses={
        200: {
            "content": {"audio/mpeg": {}},
            "description": "MP3 audio stream of the synthesized speech.",
        }
    },
    summary="Text-to-speech synthesis",
    description=(
        "Convert text to MP3 audio. Typically called with the `analysis` "
        "field from an `/analyze` response so the patient can listen to "
        "their explanation."
    ),
    tags=["Audio"],
)
async def audio(
    body: AudioRequest,
    tts_service: TTSService = Depends(get_tts_service),
) -> Response:
    audio_bytes = await tts_service.synthesize(
        text=body.text,
        language_code=body.language,
    )
    return Response(content=audio_bytes, media_type="audio/mpeg")
