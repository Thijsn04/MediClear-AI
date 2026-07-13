"""Document analysis endpoints: structured, streaming, and idempotent."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.v1.deps import rate_limited_identity
from app.core import metrics
from app.core.exceptions import DocumentProcessingError
from app.core.logging import get_logger
from app.dependencies import get_ai_service, get_document_service, get_idempotency_store
from app.models.languages import is_supported
from app.models.schemas import SUPPORTED_LANGUAGES, AnalyzeResponse
from app.services.ai_service import AIService, AnalysisOutcome
from app.services.document_service import DocumentService
from app.services.idempotency import IdempotencyStore

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


def _validate_level(reading_level: str | None) -> None:
    if reading_level is not None and reading_level not in _LEVELS:
        raise HTTPException(status_code=422, detail="reading_level must be A2, B1, or B2.")


async def _build_document(
    document_service: DocumentService,
    text: str | None,
    file: UploadFile | None,
):
    if file is not None and (file.filename or file.size):
        content = await file.read()
        return document_service.process_upload(
            content=content,
            content_type=file.content_type or "application/octet-stream",
            filename=file.filename,
        )
    if text:
        return document_service.process_text(text)
    raise DocumentProcessingError(
        "No input provided. Submit either a 'text' field or a 'file' upload."
    )


def _to_response(outcome: AnalysisOutcome, language: str) -> AnalyzeResponse:
    return AnalyzeResponse(
        session_id=outcome.session_id,
        analysis=outcome.analysis,
        markdown=outcome.analysis.render_markdown(),
        language=language,
        provider=outcome.provider,
        model=outcome.model,
        cached=outcome.cached,
    )


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Analyse a medical document",
    description=(
        "Submit a medical document as plain text **or** an uploaded file (PDF, "
        "JPEG, PNG, WEBP). Returns a **structured** analysis (summary, "
        "explanation, key terms, action items, and - when present - lab values "
        "and medications) plus a rendered markdown view and a readability "
        "assessment. The `session_id` powers `/chat/{session_id}` follow-ups.\n\n"
        "Send an `Idempotency-Key` header to make retries safe: an identical key "
        "returns the first response instead of re-running the analysis."
    ),
    tags=["Analysis"],
)
async def analyze(
    request: Request,
    language: Annotated[str, Form()] = "en",
    text: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile | None, File()] = None,
    reading_level: Annotated[str | None, Form()] = None,
    ai_service: AIService = Depends(get_ai_service),
    document_service: DocumentService = Depends(get_document_service),
    idempotency: IdempotencyStore = Depends(get_idempotency_store),
    identity: str = Depends(rate_limited_identity),
) -> AnalyzeResponse | JSONResponse:
    language = _validate_language(language)
    _validate_level(reading_level)

    idem_key = request.headers.get("idempotency-key")
    if idem_key:
        prior = await idempotency.get(identity, idem_key)
        if prior is not None:
            return JSONResponse(content=json.loads(prior), headers={"Idempotency-Replayed": "true"})

    document = await _build_document(document_service, text, file)
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

    response = _to_response(outcome, language)
    if idem_key:
        await idempotency.set(identity, idem_key, response.model_dump_json())
    return response


@router.post(
    "/analyze/stream",
    summary="Analyse a medical document (streaming)",
    description=(
        "Same inputs as `/analyze`, but streams Server-Sent Events: "
        '`data: {"delta": "..."}` progressively renders the explanation as the '
        'model writes it, then a final `data: {"result": <AnalyzeResponse>}` '
        'carries the full structured object, followed by `data: {"done": true}`. '
        "Providers that cannot stream emit only the final result."
    ),
    tags=["Analysis"],
)
async def analyze_stream(
    request: Request,
    language: Annotated[str, Form()] = "en",
    text: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile | None, File()] = None,
    reading_level: Annotated[str | None, Form()] = None,
    ai_service: AIService = Depends(get_ai_service),
    document_service: DocumentService = Depends(get_document_service),
    identity: str = Depends(rate_limited_identity),
) -> StreamingResponse:
    language = _validate_language(language)
    _validate_level(reading_level)
    document = await _build_document(document_service, text, file)

    async def event_stream():
        try:
            async for kind, payload in ai_service.stream_analyze(
                document=document, language=language, target_level=reading_level
            ):
                if kind == "delta":
                    yield f"data: {json.dumps({'delta': payload})}\n\n"
                elif kind == "result":
                    response = _to_response(payload, language)  # type: ignore[arg-type]
                    body = json.loads(response.model_dump_json())
                    yield f"data: {json.dumps({'result': body})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as exc:  # noqa: BLE001 - surface errors within the stream
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    logger.info("audit.analyze_stream", identity=identity, language=language)
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
