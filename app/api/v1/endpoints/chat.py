"""Chat endpoint — follow-up questions about an analysed document."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_ai_service
from app.models.schemas import ChatRequest, ChatResponse
from app.services.ai_service import AIService

router = APIRouter()


@router.post(
    "/chat/{session_id}",
    response_model=ChatResponse,
    summary="Ask a follow-up question",
    description=(
        "Send a follow-up question about a previously analysed document. "
        "The `session_id` is obtained from the `/analyze` response and is "
        "valid for the duration configured by `SESSION_TTL_SECONDS` "
        "(default: 1 hour)."
    ),
    tags=["Chat"],
)
async def chat(
    session_id: str,
    body: ChatRequest,
    ai_service: AIService = Depends(get_ai_service),
) -> ChatResponse:
    response_text = await ai_service.chat(
        session_id=session_id,
        message=body.message,
        language=body.language,
    )
    return ChatResponse(
        session_id=session_id,
        message=body.message,
        response=response_text,
        language=body.language,
    )
