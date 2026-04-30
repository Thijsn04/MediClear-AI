"""Document analysis endpoint — supports plain text and file uploads."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.exceptions import DocumentProcessingError
from app.dependencies import get_ai_service, get_document_service
from app.models.schemas import AnalyzeResponse, SUPPORTED_LANGUAGES
from app.services.ai_service import AIService
from app.services.document_service import DocumentService

router = APIRouter()


def _validate_language(language: str) -> str:
    """Validate language code from Form data (Pydantic validators don't run on Form fields)."""
    if language not in SUPPORTED_LANGUAGES:
        from fastapi import HTTPException
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
        "Submit a medical document as plain text **or** as an uploaded file "
        "(PDF, JPEG, PNG). The AI provider configured by the operator will "
        "return a patient-friendly explanation structured with a Summary, "
        "Explanation, Key Medical Terms, and What This Means for You sections.\n\n"
        "The response includes a `session_id` that you must pass to the "
        "`/chat/{session_id}` endpoint for follow-up questions."
    ),
    tags=["Analysis"],
)
async def analyze(
    language: Annotated[
        str,
        Form(description="BCP 47 language code for the response, e.g. 'en', 'nl'."),
    ] = "en",
    text: Annotated[
        Optional[str],
        Form(description="Plain text to analyse. Provide either this or a file."),
    ] = None,
    file: Annotated[
        Optional[UploadFile],
        File(description="PDF, JPEG, or PNG file to analyse."),
    ] = None,
    ai_service: AIService = Depends(get_ai_service),
    document_service: DocumentService = Depends(get_document_service),
) -> AnalyzeResponse:
    language = _validate_language(language)

    if file is not None:
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

    session = await ai_service.analyze(document=document, language=language)

    return AnalyzeResponse(
        session_id=session.id,
        analysis=session.document_summary,
        language=session.language,
        provider=session.provider,
        model=session.model,
    )
