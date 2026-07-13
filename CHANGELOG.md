# Changelog

All notable changes to MediClear AI are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [3.0.0] — 2026-07-13

State-of-the-art overhaul: structured output, an API-first platform, clarification
quality tooling, resilience, privacy controls, and full CI.

### Added

- **Structured analysis output** — `/analyze` returns a typed `StructuredAnalysis`
  (document type, summary, explanation, key terms, action items, lab values,
  medications, readability) **plus** a rendered markdown convenience field.
- **Faithfulness grounding** — key terms not present in the source document are
  flagged (`found_in_source`).
- **Readability scoring & enforcement** — Flesch/CEFR estimate with an optional
  re-simplification pass toward a configurable target level (A2/B1/B2).
- **SSE streaming chat** at `/chat/{session_id}/stream`; grounded follow-ups now
  use the *source document*, not just the AI summary.
- **API-key authentication** and **per-identity rate limiting** (memory or Redis)
  with `Retry-After`.
- **Pluggable Redis backends** for sessions, result cache, and rate limiting.
- **Result caching** to avoid re-billing identical requests.
- **Provider resilience** — per-call timeout, retries with backoff, ordered
  failover (`AI_FALLBACK_PROVIDERS`).
- **Privacy controls** — `ZERO_RETENTION` mode and audit logging (metadata only).
- **Session endpoints** — `GET`/`DELETE /sessions/{id}`.
- **Observability** — Prometheus `/metrics`, request IDs, unified error envelope.
- **OCR fallback** for scanned PDFs; WEBP support; two more languages (uk, fa).
- **Text-to-speech backends** — cloud (gTTS) and offline (`local`), selectable.
- **CI** (ruff + ruff format + mypy + pytest/coverage + Docker build), install
  extras, `.dockerignore`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue/PR templates,
  and `docs/` (configuration, architecture, API).

### Changed

- **Thin provider contract** — providers implement one `_complete`/`_stream`
  primitive; prompt-building, JSON parsing, and grounding live once in the base.
- **Non-blocking Gemini** — synchronous SDK calls now run in a worker thread
  instead of blocking the event loop.
- **Frontend renders structured data directly** (no markdown parser, no CDNs) —
  works offline/air-gapped and closes the XSS vector.
- **Corrected CORS** — credentials disabled while origins are the wildcard.
- **Single-source version** (`app/version.py`); AI SDKs are now optional extras.

### Fixed

- Upload size is enforced **before** the body is buffered (memory-DoS hole).
- Health check now reports `unhealthy` when the session store is unreachable.
- Broken `pyproject.toml` build backend (`setuptools.build_meta`).

---

## [2.0.0] — 2026-04-30

Complete rewrite from a Streamlit prototype to an enterprise-grade FastAPI application.

### Added

- **FastAPI backend** replacing Streamlit — clean REST API, versioned at `/api/v1/`
- **Multi-provider AI support**: Google Gemini, OpenAI (and all OpenAI-compatible APIs), Anthropic Claude
- **Free model selection** — model name is a plain env var; no model names hardcoded
- **OpenAI-compatible API support** — Ollama (on-premises), Azure OpenAI, Groq, LM Studio, vLLM, Mistral, Together AI
- **`ENABLE_FRONTEND` toggle** — set to `false` for a pure REST API server
- **Interactive API documentation** at `/api/docs` (Swagger UI) and `/api/redoc` (ReDoc)
- **Proper session management** — in-memory `SessionStore` with configurable TTL and eviction
- **Document processing service** — PDF text extraction (pypdf), image handling (Pillow)
- **Abstract provider interface** — `BaseAIProvider` makes it trivial to add new providers
- **Structured logging** with structlog (JSON in production, coloured console in debug mode)
- **Health-check endpoint** (`GET /api/v1/health`) with provider status and active session count
- **Languages endpoint** (`GET /api/v1/languages`) — frontend fetches supported languages dynamically
- **Translations endpoint** (`GET /api/v1/translations`) — 8 languages for UI strings
- **15 language codes** supported for AI output (en, nl, de, fr, es, tr, ar, pl, pt, it, zh, ja, ko, ru, hi)
- **Professional frontend** — NHS-design-system colours, WCAG 2.1 AA accessible, responsive, RTL support for Arabic
- **Docker support** — multi-stage Dockerfile + docker-compose.yml
- **pytest test suite** — 20 tests covering all endpoints with a `MockProvider`
- **`pyproject.toml`** — proper Python packaging metadata
- **`.env.example`** with fully-annotated configuration

### Changed

- Complete project structure overhaul (layered architecture)
- System prompts improved — structured Markdown output with clear patient-friendly sections
- Language list expanded from 8 to 15 languages

### Removed

- Streamlit dependency and `main.py` Streamlit app
- `translations.py` (moved to `app/i18n/translations.py` and frontend JS)
- `check_models.py` debug script

---

## [1.0.0] — 2025 (initial prototype)

- Single-file Streamlit application
- Google Gemini integration
- Basic document analysis and chat
- Dutch/English/Turkish/Arabic/Polish/German/French/Spanish support
