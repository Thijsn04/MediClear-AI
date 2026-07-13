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
| `POST` | `/analyze` | Analyse text or a file → structured result |
| `POST` | `/chat/{session_id}` | Follow-up question (grounded) |
| `POST` | `/chat/{session_id}/stream` | Same, streamed as SSE |
| `GET` | `/sessions/{session_id}` | Session metadata |
| `DELETE` | `/sessions/{session_id}` | Purge a session |
| `POST` | `/audio` | Text-to-speech |
| `GET` | `/metrics` | Prometheus metrics (top-level, not under `/api/v1`) |

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
       "found_in_source": true}
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
