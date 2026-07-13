"""Document analysis endpoint — plain text or file upload → structured result."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.v1.deps import rate_limited_identity
from app.core import metrics
from app.core.exceptions import DocumentProcessingError
from app.core.logging import get_logger
from app.dependencies import get_ai_service, get_document_service
from app.models.languages import is_supported
from app.models.schemas import AnalyzeResponse, SUPPORTED_LANGUAGES
from app.services.ai_service import AIService
from app.services.document_service import DocumentService

router = APIRouter()
logger = get_logger(__name__)

_LEVELS = {"A2", "B1", "B2"}


def _validate_language(language: str) -> str:
    if not is_supported(language):
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported language code '{language}'. "
            f"Supported codes: {', '.join(SUPPORTED_LANGUAGES)}.",
        )
    return language


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Analyse a medical document",
    description=(
        "Submit a medical document as plain text **or** an uploaded file (PDF, "
        "JPEG, PNG, WEBP). Returns a **structured** analysis (summary, "
        "explanation, key terms, action items, and — when present — lab values "
        "and medications) plus a rendered markdown view and a readability "
        "assessment. The `session_id` powers `/chat/{session_id}` follow-ups."
    ),
    tags=["Analysis"],
)
async def analyze(
    language: Annotated[str, Form()] = "en",
    text: Annotated[Optional[str], Form()] = None,
    file: Annotated[Optional[UploadFile], File()] = None,
    reading_level: Annotated[Optional[str], Form()] = None,
    ai_service: AIService = Depends(get_ai_service),
    document_service: DocumentService = Depends(get_document_service),
    identity: str = Depends(rate_limited_identity),
) -> AnalyzeResponse:
    language = _validate_language(language)
    if reading_level is not None and reading_level not in _LEVELS:
        raise HTTPException(status_code=422, detail="reading_level must be A2, B1, or B2.")

    if file is not None and (file.filename or file.size):
        content = await file.read()
        document = document_service.process_upload(
            content=content,
            content_type=file.content_type or "application/octet-stream",
            filename=file.filename,
        )
    elif text:
        document = document_service.process_text(text)
    else:
        raise DocumentProcessingError(
            "No input provided. Submit either a 'text' field or a 'file' upload."
        )

    outcome = await ai_service.analyze(
        document=document, language=language, target_level=reading_level
    )

    metrics.record_analysis(
        outcome.provider, outcome.cached, outcome.input_tokens, outcome.output_tokens
    )
    logger.info(
        "audit.analyze",
        identity=identity,
        provider=outcome.provider,
        model=outcome.model,
        language=language,
        cached=outcome.cached,
        doc_type=outcome.analysis.document_type.value,
    )

    return AnalyzeResponse(
        session_id=outcome.session_id,
        analysis=outcome.analysis,
        markdown=outcome.analysis.render_markdown(),
        language=language,
        provider=outcome.provider,
        model=outcome.model,
        cached=outcome.cached,
    )
