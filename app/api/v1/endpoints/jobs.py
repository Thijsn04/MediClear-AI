"""Batch analysis jobs: submit many documents, poll for results."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.deps import rate_limited_identity
from app.core.logging import get_logger
from app.dependencies import get_job_runner, get_job_store
from app.models.schemas import BatchAnalyzeRequest, JobResponse
from app.services.jobs import Job, JobRunner, JobStore

router = APIRouter()
logger = get_logger(__name__)


def _to_response(job: Job) -> JobResponse:
    return JobResponse.model_validate(
        {
            "job_id": job.id,
            "status": job.status,
            "total": job.total,
            "completed": job.completed,
            "results": [
                {
                    "index": r.index,
                    "status": r.status,
                    "markdown": r.markdown,
                    "analysis": r.analysis,
                    "error": r.error,
                }
                for r in job.results
            ],
            "created_at": datetime.fromtimestamp(job.created_at, tz=UTC),
        }
    )


@router.post(
    "/analyze/batch",
    response_model=JobResponse,
    status_code=202,
    summary="Submit a batch of documents for analysis",
    description=(
        "Queue up to 50 text documents for asynchronous analysis. Returns a "
        "`job_id` immediately; poll `GET /jobs/{job_id}` for progress and "
        "results. Each item is processed sequentially to respect provider limits."
    ),
    tags=["Jobs"],
)
async def submit_batch(
    body: BatchAnalyzeRequest,
    runner: JobRunner = Depends(get_job_runner),
    identity: str = Depends(rate_limited_identity),
) -> JobResponse:
    items = [item.model_dump() for item in body.items]
    job = await runner.submit(items)
    logger.info("audit.batch_submit", identity=identity, job_id=job.id, total=job.total)
    return _to_response(job)


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Get batch job status and results",
    tags=["Jobs"],
)
async def get_job(
    job_id: str,
    store: JobStore = Depends(get_job_store),
    identity: str = Depends(rate_limited_identity),
) -> JobResponse:
    job = await store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found or expired.")
    return _to_response(job)
