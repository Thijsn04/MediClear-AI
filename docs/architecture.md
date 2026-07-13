# Architecture

MediClear is a layered FastAPI application. Each layer has one job and depends
only on the layer below it.

```
HTTP request
    │
    ▼
Middleware            request-id · body-size guard · CORS · metrics
    │
    ▼
Endpoint              app/api/v1/endpoints/*      (validation, auth, rate limit)
    │
    ▼
AIService             app/services/ai_service.py  (orchestration)
    │   ┌──────────────┬───────────────┬─────────────────┐
    ▼   ▼              ▼               ▼                 ▼
ResultCache   SessionStore    Readability      DocumentService
(mem/redis)   (mem/redis)     (scoring)        (PDF/img/OCR)
    │
    ▼
BaseAIProvider        app/providers/base.py
    │   builds prompts, parses JSON → StructuredAnalysis, grounds terms
    ▼
ResilientProvider     timeout · retries · failover
    │
    ▼
Concrete provider     Gemini / OpenAI-compatible / Anthropic
    │
    ▼
AI API
```

## Key design decisions

**Thin providers.** A provider implements just `_complete` (and optionally
`_stream`). All domain logic - prompt construction, JSON parsing into
`StructuredAnalysis`, faithfulness grounding, readability - lives once in
`BaseAIProvider`. Adding a provider is ~40 lines.

**Structured output.** The provider asks the model for JSON matching the
`StructuredAnalysis` schema. The API returns that object *and* a rendered
markdown view, so programmatic consumers read fields while simple clients
display markdown. A prose fallback keeps things working if a model ignores the
JSON instruction.

**Resilience by composition.** `ResilientProvider` wraps a list of providers and
adds timeout, retries, and failover around the two primitives - so the whole
pipeline inherits resilience without touching provider code.

**Pluggable state.** `SessionStore`, the cache backend, and the rate limiter
each have an in-memory and a Redis implementation behind one interface. The
choice is made once, in `app/dependencies.py`, from `REDIS_URL`.

**Two deployment targets, one codebase.** Cloud API-first (hosted model + auth +
rate limit + Redis) and on-prem/air-gapped (local OpenAI-compatible server +
local TTS + bundled frontend assets + zero-retention) are both reachable by
configuration alone.

## Request lifecycle (analyze)

1. Middleware assigns a request ID and rejects oversized bodies pre-buffer.
2. The endpoint authenticates, rate-limits, and validates input.
3. `DocumentService` normalises text / image / PDF (OCR fallback for scans).
4. `AIService` checks the result cache; on miss it calls the provider.
5. `BaseAIProvider` prompts the model, parses JSON, and grounds key terms.
6. Optional readability pass re-simplifies if the output overshoots the target.
7. The result is cached, a session is created (unless zero-retention), and the
   structured response + markdown is returned.
