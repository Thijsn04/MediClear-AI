"""
Asynchronous batch jobs.

Submit many documents at once and poll for the result, instead of blocking on a
long synchronous call. A job is created immediately (status ``queued``), a
background task processes each item sequentially (to respect provider limits),
and progress is written to a job store (in-memory or Redis) that any instance
can read.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import asdict, dataclass, field

from app.core.logging import get_logger
from app.providers.base import ProcessedDocument

logger = get_logger(__name__)


@dataclass
class JobItemResult:
    index: int
    status: str  # "succeeded" | "failed"
    markdown: str | None = None
    analysis: dict | None = None
    error: str | None = None


@dataclass
class Job:
    id: str
    status: str  # queued | processing | succeeded | failed | partial
    total: int
    completed: int = 0
    results: list[JobItemResult] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, raw: str) -> Job:
        data = json.loads(raw)
        data["results"] = [JobItemResult(**r) for r in data.get("results", [])]
        return cls(**data)


class JobStore(ABC):
    @abstractmethod
    async def save(self, job: Job) -> None: ...

    @abstractmethod
    async def get(self, job_id: str) -> Job | None: ...


class InMemoryJobStore(JobStore):
    def __init__(self, max_jobs: int = 1000) -> None:
        self._store: OrderedDict[str, Job] = OrderedDict()
        self._max = max_jobs

    async def save(self, job: Job) -> None:
        self._store[job.id] = job
        self._store.move_to_end(job.id)
        while len(self._store) > self._max:
            self._store.popitem(last=False)

    async def get(self, job_id: str) -> Job | None:
        return self._store.get(job_id)


class RedisJobStore(JobStore):
    _PREFIX = "mediclear:job:"

    def __init__(self, client, ttl_seconds: int = 86_400) -> None:
        self._redis = client
        self._ttl = ttl_seconds

    async def save(self, job: Job) -> None:
        await self._redis.set(f"{self._PREFIX}{job.id}", job.to_json(), ex=self._ttl)

    async def get(self, job_id: str) -> Job | None:
        raw = await self._redis.get(f"{self._PREFIX}{job_id}")
        if raw is None:
            return None
        return Job.from_json(raw.decode() if isinstance(raw, bytes) else raw)


# Keep references to running tasks so they are not garbage-collected.
_TASKS: set[asyncio.Task] = set()


class JobRunner:
    """Creates jobs and processes them in the background using the AI service."""

    def __init__(self, ai_service, store: JobStore) -> None:
        self._ai = ai_service
        self._store = store

    async def submit(self, items: list[dict]) -> Job:
        job = Job(id=str(uuid.uuid4()), status="queued", total=len(items))
        await self._store.save(job)
        task = asyncio.create_task(self._run(job.id, items))
        _TASKS.add(task)
        task.add_done_callback(_TASKS.discard)
        return job

    async def _run(self, job_id: str, items: list[dict]) -> None:
        job = await self._store.get(job_id)
        if job is None:
            return
        job.status = "processing"
        await self._store.save(job)

        failures = 0
        for idx, item in enumerate(items):
            try:
                document = ProcessedDocument(type="text", text=item["text"])
                outcome = await self._ai.analyze(
                    document=document,
                    language=item.get("language", "en"),
                    target_level=item.get("reading_level"),
                )
                job.results.append(
                    JobItemResult(
                        index=idx,
                        status="succeeded",
                        markdown=outcome.analysis.render_markdown(),
                        analysis=json.loads(outcome.analysis.model_dump_json()),
                    )
                )
            except Exception as exc:  # noqa: BLE001 - record per-item failure, keep going
                failures += 1
                job.results.append(JobItemResult(index=idx, status="failed", error=str(exc)))
                logger.warning("job.item_failed", job_id=job_id, index=idx, error=str(exc))
            job.completed += 1
            await self._store.save(job)

        if failures == 0:
            job.status = "succeeded"
        elif failures == len(items):
            job.status = "failed"
        else:
            job.status = "partial"
        await self._store.save(job)
        logger.info("job.finished", job_id=job_id, status=job.status)
