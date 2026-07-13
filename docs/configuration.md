# Configuration

Every setting is an environment variable (or an entry in `.env`). Defaults are
sensible for local development; harden them for production. See
[`.env.example`](../.env.example) for a copy-paste starting point.

## Provider selection

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_PROVIDER` | `gemini` | `gemini` \| `openai` \| `anthropic` \| `demo` (canned, no key) |
| `AI_FALLBACK_PROVIDERS` | - | Ordered failover chain, e.g. `openai,anthropic` |
| `AI_REQUEST_TIMEOUT_SECONDS` | `60` | Per-call timeout |
| `AI_MAX_RETRIES` | `2` | Retries with exponential backoff before failover |
| `AI_MAX_OUTPUT_TOKENS` | `4096` | Max generated tokens |
| `AI_TEMPERATURE` | `0.2` | Sampling temperature |

Provider keys/models: `GOOGLE_API_KEY`/`GEMINI_MODEL`,
`OPENAI_API_KEY`/`OPENAI_MODEL`/`OPENAI_BASE_URL`,
`ANTHROPIC_API_KEY`/`ANTHROPIC_MODEL`. **Model names are free strings** - use any
model your key or server accepts.

### OpenAI-compatible servers

Set `AI_PROVIDER=openai` and `OPENAI_BASE_URL`:

| Server | `OPENAI_BASE_URL` |
|--------|-------------------|
| Ollama | `http://localhost:11434/v1` |
| Azure OpenAI | `https://<resource>.openai.azure.com/openai/deployments/<deployment>` |
| Groq | `https://api.groq.com/openai/v1` |
| vLLM / LM Studio | `http://localhost:8000/v1` / `http://localhost:1234/v1` |

## Clarification quality

| Variable | Default | Description |
|----------|---------|-------------|
| `TARGET_READING_LEVEL` | `B1` | `A2` \| `B1` \| `B2` |
| `ENFORCE_READING_LEVEL` | `true` | Re-simplify if output overshoots the target |
| `MAX_SIMPLIFICATION_PASSES` | `1` | Extra simplification attempts |

## Terminology grounding

| Variable | Default | Description |
|----------|---------|-------------|
| `TERMINOLOGY_ENABLED` | `true` | Back key-term definitions with a curated source |
| `TERMINOLOGY_ONLINE` | `false` | Also query MedlinePlus (needs internet; EN/ES) |
| `TERMINOLOGY_TIMEOUT_SECONDS` | `4.0` | Per-lookup timeout for the online source |

The bundled offline glossary (`app/data/glossary.json`) always applies and works
air-gapped. When a trusted definition is found, the key term's `source` becomes
`glossary` or `online` and a `source_url` is attached where available.

## Sessions, cache & Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSION_TTL_SECONDS` | `3600` | Chat session lifetime |
| `MAX_SESSIONS` | `1000` | In-memory session cap |
| `REDIS_URL` | - | Durable, multi-instance store (sessions, cache, rate limit) |
| `CACHE_ENABLED` | `true` | Reuse results for identical requests |
| `CACHE_TTL_SECONDS` | `86400` | Cached result lifetime |

## Privacy & security

| Variable | Default | Description |
|----------|---------|-------------|
| `ZERO_RETENTION` | `false` | Persist nothing derived from the document (disables chat) |
| `AUDIT_LOGGING` | `true` | Emit audit events (metadata only, never content) |
| `REQUIRE_API_KEY` | `false` | Require `X-API-Key` / `Bearer` on mutations |
| `API_KEYS` | - | Comma-separated keys |
| `RATE_LIMIT_ENABLED` | `true` | Fixed-window per-identity limiting |
| `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS` | `60` / `60` | Limit + window |
| `ALLOWED_ORIGINS` | `["*"]` | CORS origins; credentials auto-off while wildcard |

## Uploads, OCR & TTS

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_UPLOAD_SIZE_MB` | `10` | Upload size cap |
| `MAX_REQUEST_BODY_BYTES` | `12582912` | Hard body-size guard (pre-buffer) |
| `ENABLE_OCR` | `true` | OCR scanned PDFs (needs `[ocr]` extra + tesseract/poppler) |
| `TTS_BACKEND` | `gtts` | `gtts` (cloud) \| `local` (offline) \| `disabled` |

## Server & observability

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` / `PORT` | `0.0.0.0` / `8000` | Bind address |
| `ENVIRONMENT` | `production` | `development` \| `staging` \| `production` |
| `DEBUG` | `false` | Verbose, human-readable logs |
| `ENABLE_FRONTEND` | `true` | Serve the built-in UI |
| `METRICS_ENABLED` | `true` | Expose `/metrics` (needs `[metrics]` extra) |
