"""Session management - inspect and delete chat sessions."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response

from app.api.v1.deps import rate_limited_identity
from app.dependencies import get_ai_service
from app.models.schemas import SessionResponse
from app.services.ai_service import AIService

router = APIRouter()


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    summary="Get session metadata",
    tags=["Sessions"],
)
async def get_session(
    session_id: str,
    ai_service: AIService = Depends(get_ai_service),
    identity: str = Depends(rate_limited_identity),
) -> SessionResponse:
    session = await ai_service.get_session(session_id)
    return SessionResponse(
        session_id=session.id,
        provider=session.provider,
        model=session.model,
        language=session.language,
        message_count=len(session.history),
        created_at=datetime.fromtimestamp(session.created_at, tz=UTC),
    )


@router.delete(
    "/sessions/{session_id}",
    status_code=204,
    summary="Delete a session",
    description="Immediately purge a session and its stored document context.",
    tags=["Sessions"],
)
async def delete_session(
    session_id: str,
    ai_service: AIService = Depends(get_ai_service),
    identity: str = Depends(rate_limited_identity),
) -> Response:
    await ai_service.delete_session(session_id)
    return Response(status_code=204)
