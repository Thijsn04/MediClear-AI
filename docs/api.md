# API Reference

Interactive docs live at `/api/docs` (Swagger) and `/api/redoc`. The OpenAPI
schema is at `/api/openapi.json`.

Base path: `/api/v1`. When `REQUIRE_API_KEY=true`, send
`X-API-Key: <key>` (or `Authorization: Bearer <key>`) on every request.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Status, provider, session-store liveness |
| `GET` | `/languages` | Supported languages (code, names, RTL) |
| `POST` | `/analyze` | Analyse text or a file into a structured result |
| `POST` | `/analyze/stream` | Same, streamed as SSE (progressive explanation + final result) |
| `POST` | `/analyze/batch` | Queue up to 50 documents; returns a job id (202) |
| `GET` | `/jobs/{job_id}` | Batch job status and results |
| `POST` | `/chat/{session_id}` | Follow-up question (grounded) |
| `POST` | `/chat/{session_id}/stream` | Same, streamed as SSE |
| `GET` | `/sessions/{session_id}` | Session metadata |
| `DELETE` | `/sessions/{session_id}` | Purge a session |
| `POST` | `/audio` | Text-to-speech |
| `GET` | `/metrics` | Prometheus metrics (top-level, not under `/api/v1`) |

**Idempotency:** send an `Idempotency-Key` header on `POST /analyze` to make
retries safe. A repeated key within the cache TTL returns the first response
(with `Idempotency-Replayed: true`) instead of re-running the analysis.

**Rate-limit headers:** responses include `X-RateLimit-Limit` and
`X-RateLimit-Remaining`; a `429` adds `Retry-After`.

## Analyse a document

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "text=The patient presents with acute myocardial infarction." \
  -F "language=en" -F "reading_level=B1"
```

```jsonc
{
  "session_id": "a1b2c3d4-…",           // null in zero-retention mode
  "analysis": {
    "document_type": "consultation_note",
    "summary": "This note describes a heart attack…",
    "explanation": "…",
    "key_terms": [
      {"term": "myocardial infarction", "definition": "a heart attack",
       "found_in_source": true, "source": "glossary", "source_url": null}
    ],
    "action_items": ["Ask your doctor whether…"],
    "lab_values": [],
    "medications": [],
    "readability": {"flesch_reading_ease": 68.2, "estimated_cefr": "B1",
                    "target_cefr": "B1", "meets_target": true},
    "disclaimer": "…"
  },
  "markdown": "## Summary\n…",
  "language": "en",
  "provider": "openai",
  "model": "gpt-4o",
  "cached": false
}
```

Upload a file instead:

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "file=@discharge_summary.pdf" -F "language=nl"
```

## Streaming analyse

Same inputs as `/analyze`. Streams the explanation progressively, then the full
structured result:

```bash
curl -N -X POST http://localhost:8000/api/v1/analyze/stream \
  -F "text=..." -F "language=en"
```

```
data: {"delta": "You came to hospital with "}
data: {"delta": "a fever and a cough..."}
data: {"result": { ...full AnalyzeResponse... }}
data: {"done": true}
```

## Batch analyse (async jobs)

```bash
# Submit (returns 202 + job_id)
curl -X POST http://localhost:8000/api/v1/analyze/batch \
  -H "Content-Type: application/json" \
  -d '{"items": [{"text": "...", "language": "en"},
                 {"text": "...", "language": "nl", "reading_level": "A2"}]}'

# Poll
curl http://localhost:8000/api/v1/jobs/$JOB_ID
```

The job response reports `status` (`queued` / `processing` / `succeeded` /
`partial` / `failed`), `completed` / `total`, and a `results` array where each
item is a structured `analysis` or an `error`.

## Follow-up chat (streaming)

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/$SESSION/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Should I be worried?", "language": "en"}'
```

Server-Sent Events:

```
data: {"delta": "It's understandable "}
data: {"delta": "to feel worried…"}
data: {"done": true}
```

## Errors

All errors share one envelope:

```json
{ "error": "human-readable message", "status_code": 429, "request_id": "…" }
```

`429` responses include a `Retry-After` header. Validation errors (`422`) add a
`detail` array. The `X-Request-ID` header is echoed on every response.
