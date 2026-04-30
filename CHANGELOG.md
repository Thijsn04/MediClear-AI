# Changelog

All notable changes to MediClear AI are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
