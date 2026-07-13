<div align="center">

# 💬 MediClear AI

**Turn dense medical documents into clear, patient-friendly explanations - cloud or on-prem, API-first.**

A free, open-source FastAPI service that translates complex clinical language
into simple explanations at a configurable reading level (A2/B1/B2), in 17
languages, using the AI model of your choice. Returns **structured JSON** for
integrations and a rendered view for humans.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![CI](https://img.shields.io/badge/CI-ruff%20%C2%B7%20mypy%20%C2%B7%20pytest-2ea44f.svg)](.github/workflows/ci.yml)

</div>

---

## Table of Contents

- [Highlights](#highlights)
- [Quick Start](#quick-start)
- [Deployment targets](#deployment-targets)
- [AI provider configuration](#ai-provider-configuration)
- [API](#api)
- [Configuration](#configuration)
- [Development](#development)
- [Architecture](#architecture)
- [Contributing](#contributing)
- [License](#license)

---

## Highlights

- **Structured output** - every analysis is a typed object (summary, explanation,
  key terms, action items, lab values, medications, readability) plus a rendered
  markdown view. Built for EHR/mobile integration, not just display.
- **Faithful, measured clarification** - flags key terms not found in the source
  document, scores readability (Flesch/CEFR), and can re-simplify to hit a target
  level (A2/B1/B2).
- **Provider-agnostic** - Google Gemini, OpenAI, Anthropic Claude, and any
  OpenAI-compatible server (Ollama, Azure, Groq, vLLM, LM Studio). Model names
  are free strings; add a fallback chain for resilience.
- **API-first platform** - API-key auth, rate limiting, SSE streaming chat,
  session management, result caching, Prometheus metrics, unified errors.
- **Privacy-conscious** - `ZERO_RETENTION` mode, audit logging (metadata only),
  a fully offline/air-gapped path, and document content never written to logs.
- **17 languages**, RTL-aware output, optional text-to-speech (cloud or offline).
- **Production-ready** - Docker, Redis-pluggable state, health/readiness,
  structured JSON logging, CI (ruff + mypy + pytest), typed throughout.

---

## Quick Start

### Docker

```bash
git clone https://github.com/Thijsn04/MediClear-AI.git && cd MediClear-AI
cp .env.example .env          # set AI_PROVIDER + key + model
docker compose up -d
open http://localhost:8000     # UI · API docs at /api/docs
```

### Without Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install '.[openai]'        # core + one provider (see extras below)
cp .env.example .env
uvicorn app.main:app --reload
```

**Install extras** (install only what you need):
`gemini` · `openai` · `anthropic` · `redis` · `ocr` · `tts-cloud` · `tts-local`
· `metrics` · `all` · `dev`. Example: `pip install '.[all,dev]'`.

---

## Deployment targets

Both are reachable by configuration alone - one codebase.

**☁️ Cloud, API-first**
```env
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
REQUIRE_API_KEY=true
API_KEYS=key-for-team-a,key-for-team-b
REDIS_URL=redis://redis:6379/0
ALLOWED_ORIGINS=["https://app.example.com"]
```

**🏥 On-prem / air-gapped (PHI never leaves your network)**
```env
AI_PROVIDER=openai
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_MODEL=llama3.2
TTS_BACKEND=local
ZERO_RETENTION=true
```
The built-in frontend ships with no CDN dependencies, so it works fully offline.

---

## AI provider configuration

Set `AI_PROVIDER` and the matching key/model. **The model name is a free string.**

```env
# Gemini
AI_PROVIDER=gemini
GOOGLE_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash

# OpenAI (or Ollama / Azure / Groq / vLLM / LM Studio via OPENAI_BASE_URL)
AI_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o

# Anthropic
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL=claude-sonnet-4-5

# Optional resilience: try these in order if the primary fails
AI_FALLBACK_PROVIDERS=anthropic,gemini
```

See [docs/configuration.md](docs/configuration.md) for OpenAI-compatible base URLs.

---

## API

Full reference: [docs/api.md](docs/api.md) · interactive: `/api/docs`.

```bash
# Analyse text → structured result
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "text=The patient presents with acute myocardial infarction." \
  -F "language=en" -F "reading_level=B1"

# Analyse a PDF / photo
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "file=@discharge_summary.pdf" -F "language=nl"

# Streamed follow-up (Server-Sent Events)
curl -N -X POST http://localhost:8000/api/v1/chat/$SESSION/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Should I be worried?", "language": "en"}'
```

The `/analyze` response contains a structured `analysis` object, a `markdown`
convenience string, a `session_id` for follow-ups, and provider/model metadata.

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/v1/health` | Provider + session-store status |
| `GET`  | `/api/v1/languages` | Supported languages |
| `POST` | `/api/v1/analyze` | Analyse text or file → structured result |
| `POST` | `/api/v1/chat/{session_id}` | Follow-up question (grounded) |
| `POST` | `/api/v1/chat/{session_id}/stream` | Streaming follow-up (SSE) |
| `GET`/`DELETE` | `/api/v1/sessions/{session_id}` | Inspect / purge session |
| `POST` | `/api/v1/audio` | Text-to-speech |
| `GET`  | `/metrics` | Prometheus metrics |

---

## Configuration

Everything is an environment variable - full table in
[docs/configuration.md](docs/configuration.md). Highlights: `AI_PROVIDER`,
`TARGET_READING_LEVEL`, `REQUIRE_API_KEY`/`API_KEYS`, `RATE_LIMIT_*`, `REDIS_URL`,
`ZERO_RETENTION`, `TTS_BACKEND`, `ENABLE_FRONTEND`, `ALLOWED_ORIGINS`.

---

## Development

```bash
pip install '.[all,ocr,tts-local,dev]'

ruff check app/ tests/       # lint
ruff format --check app/ tests/
mypy app/                    # type check
pytest -q                    # tests (no API keys needed - uses a MockProvider)
```

CI runs the same gate on Python 3.11 and 3.12 plus a Docker build.

---

## Architecture

Layered FastAPI app; providers are thin (one `_complete`/`_stream` primitive) and
the base class owns prompt-building, JSON parsing, and grounding. State (sessions,
cache, rate limit) is pluggable between in-memory and Redis. Full diagram and
request lifecycle in [docs/architecture.md](docs/architecture.md).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
Security reports: [SECURITY.md](SECURITY.md).

---

## License

MIT - see [LICENSE](LICENSE).

---

> **Medical disclaimer:** MediClear AI is an educational tool. It does not
> constitute medical advice and must not be used as a substitute for consultation
> with a qualified healthcare professional. Always refer medical decisions to a
> licensed clinician.

---

<div align="center">
<sub>Built by <a href="https://github.com/Thijsn04">Thijs Nannings</a> · Medical Informatics @ UvA · <a href="https://lythos.nl">Lythos</a></sub>
</div>
