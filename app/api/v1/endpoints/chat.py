"""Chat endpoints — follow-up questions, with optional SSE streaming."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.v1.deps import rate_limited_identity
from app.core.logging import get_logger
from app.dependencies import get_ai_service
from app.models.schemas import ChatRequest, ChatResponse
from app.services.ai_service import AIService

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/chat/{session_id}",
    response_model=ChatResponse,
    summary="Ask a follow-up question",
    description=(
        "Send a follow-up question about a previously analysed document. The "
        "answer is grounded in the original document context stored with the "
        "session. Requires a `session_id` from `/analyze`."
    ),
    tags=["Chat"],
)
async def chat(
    session_id: str,
    body: ChatRequest,
    ai_service: AIService = Depends(get_ai_service),
    identity: str = Depends(rate_limited_identity),
) -> ChatResponse:
    response_text = await ai_service.chat(
        session_id=session_id, message=body.message, language=body.language
    )
    logger.info("audit.chat", identity=identity, session_id=session_id)
    return ChatResponse(
        session_id=session_id,
        message=body.message,
        response=response_text,
        language=body.language,
    )


@router.post(
    "/chat/{session_id}/stream",
    summary="Ask a follow-up question (streaming)",
    description=(
        "Same as `/chat/{session_id}` but streams the answer as Server-Sent "
        "Events. Each event is `data: {\"delta\": \"...\"}`; the stream ends "
        "with `data: {\"done\": true}`."
    ),
    tags=["Chat"],
)
async def chat_stream(
    session_id: str,
    body: ChatRequest,
    ai_service: AIService = Depends(get_ai_service),
    identity: str = Depends(rate_limited_identity),
) -> StreamingResponse:
    async def event_stream():
        try:
            async for delta in ai_service.stream_chat(
                session_id=session_id, message=body.message, language=body.language
            ):
                yield f"data: {json.dumps({'delta': delta})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as exc:  # noqa: BLE001 — surface errors within the stream
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    logger.info("audit.chat_stream", identity=identity, session_id=session_id)
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
