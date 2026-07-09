<div align="center">

# 💬 MediClear AI

**Enterprise-grade medical document simplification for hospitals and clinics**

A free, open-source FastAPI application that translates complex clinical language into simple, patient-friendly explanations (B1 level). Deployable on any infrastructure — from a hospital's private on-premises server to a public cloud — with full support for the AI model of your choice.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Google Gemini](https://img.shields.io/badge/AI-Gemini%202.5-8E75B2.svg?logo=googlegemini&logoColor=white)](https://ai.google.dev/)

</div>

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [AI Provider Configuration](#ai-provider-configuration)
- [Frontend Toggle](#frontend-toggle)
- [API Reference](#api-reference)
- [Docker Deployment](#docker-deployment)
- [Configuration Reference](#configuration-reference)
- [Development](#development)
- [Architecture](#architecture)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **Provider-agnostic AI** — bring your own model. Works with Google Gemini, OpenAI, Anthropic Claude, Ollama (local/on-premises), Azure OpenAI, Groq, Mistral, LM Studio, vLLM, and any other OpenAI-compatible API.
- **Free model selection** — the model name is a plain string in your `.env` file. No hardcoded names, no code changes required when you upgrade models.
- **Multi-language output** — 15 languages supported out of the box (English, Dutch, German, French, Spanish, Turkish, Arabic, Polish, Portuguese, Italian, Chinese, Japanese, Korean, Russian, Hindi).
- **Multiple input types** — plain text paste, PDF upload, JPEG/PNG image upload.
- **Chat follow-up** — after receiving an explanation, patients can ask follow-up questions in a conversation session.
- **Text-to-speech** — listen to the explanation in any supported language.
- **Optional frontend** — set `ENABLE_FRONTEND=false` for a pure REST API server; embed the UI elsewhere or build your own.
- **OpenAPI documentation** — full interactive Swagger UI at `/api/docs`.
- **Production-ready** — Docker support, structured JSON logging, CORS configuration, health-check endpoint, session TTL management.

---

## Quick Start

### With Docker (recommended)

```bash
# 1. Clone
git clone https://github.com/Thijsn04/MediClear-AI.git
cd MediClear-AI

# 2. Configure
cp .env.example .env
# Edit .env — set AI_PROVIDER and the matching API key + model name

# 3. Run
docker compose up -d

# 4. Open
open http://localhost:8000
```

### Without Docker

```bash
# Requires Python 3.11+
git clone https://github.com/Thijsn04/MediClear-AI.git
cd MediClear-AI

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env — set AI_PROVIDER and the matching API key + model name

uvicorn app.main:app --reload
# open http://localhost:8000
```

The interactive API documentation is available at **`http://localhost:8000/api/docs`**.

---

## AI Provider Configuration

MediClear AI supports three providers. Set `AI_PROVIDER` to select one, then supply the corresponding key and model. **The model name is a free string — use any model your API key or server supports.**

### Google Gemini

```env
AI_PROVIDER=gemini
GOOGLE_API_KEY=your-key-here
GEMINI_MODEL=gemini-2.5-flash       # or gemini-2.5-pro, gemini-1.5-pro, ...
```

### OpenAI

```env
AI_PROVIDER=openai
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4o                 # or gpt-4.1, o3, gpt-4o-mini, ...
```

### Anthropic Claude

```env
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-key-here
ANTHROPIC_MODEL=claude-opus-4-5     # or claude-sonnet-4-5, claude-3-5-haiku-20241022, ...
```

### Ollama (local / on-premises)

Hospitals and clinics that cannot send patient data to external APIs can run MediClear AI entirely on-premises using [Ollama](https://ollama.com):

```env
AI_PROVIDER=openai
OPENAI_API_KEY=ollama               # Ollama ignores the key value
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_MODEL=llama3.2               # or mistral, phi4, qwen2.5, meditron, ...
```

Start Ollama and pull a model before starting MediClear AI:
```bash
ollama serve
ollama pull llama3.2
```

### Azure OpenAI

```env
AI_PROVIDER=openai
OPENAI_API_KEY=your-azure-key
OPENAI_BASE_URL=https://<resource>.openai.azure.com/openai/deployments/<deployment>
OPENAI_MODEL=gpt-4o
```

### Other OpenAI-compatible servers

Any server that implements the OpenAI Chat Completions API works with `AI_PROVIDER=openai` + `OPENAI_BASE_URL`. Examples: Groq, Together AI, Mistral AI, LM Studio, vLLM.

---

## Frontend Toggle

By default MediClear AI serves a built-in web UI at `/`. To run as a **pure REST API** (no HTML served), set:

```env
ENABLE_FRONTEND=false
```

This is useful when:
- You are building a custom frontend or embedding MediClear in an existing hospital portal.
- You are consuming the API programmatically (EHR integration, mobile app, etc.).
- You want to serve the frontend from a CDN or separate Nginx instance.

When the frontend is disabled, all `/api/v1/*` endpoints continue to work normally. The OpenAPI documentation at `/api/docs` is always available regardless of this setting.

---

## API Reference

The full interactive API documentation is at **`/api/docs`** (Swagger UI) and **`/api/redoc`** (ReDoc).

### Key endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/v1/health` | Health check — provider status, active sessions |
| `GET`  | `/api/v1/languages` | List all supported language codes |
| `POST` | `/api/v1/analyze` | Analyse a document (text or file upload) |
| `POST` | `/api/v1/chat/{session_id}` | Follow-up question in a session |
| `POST` | `/api/v1/audio` | Text-to-speech synthesis (returns MP3) |

### Example: Analyse text

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "text=The patient presents with acute myocardial infarction." \
  -F "language=en"
```

Response:
```json
{
  "session_id": "a1b2c3d4-...",
  "analysis": "## Summary\nThis document describes a heart attack...",
  "language": "en",
  "provider": "gemini",
  "model": "gemini-2.5-flash"
}
```

### Example: Follow-up chat

```bash
curl -X POST http://localhost:8000/api/v1/chat/a1b2c3d4-... \
  -H "Content-Type: application/json" \
  -d '{"message": "Should I be worried?", "language": "en"}'
```

### Example: Upload a PDF

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "file=@discharge_summary.pdf" \
  -F "language=nl"
```

---

## Docker Deployment

```bash
cp .env.example .env   # configure your provider
docker compose up -d
```

For a pure API-only deployment:

```bash
docker run -d \
  -p 8000:8000 \
  -e AI_PROVIDER=openai \
  -e OPENAI_API_KEY=sk-... \
  -e OPENAI_MODEL=gpt-4o \
  -e ENABLE_FRONTEND=false \
  mediclear-ai:latest
```

---

## Configuration Reference

All settings are environment variables (or entries in `.env`).

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_PROVIDER` | `gemini` | Active provider: `gemini`, `openai`, or `anthropic` |
| `GOOGLE_API_KEY` | — | Google AI Studio API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Any Gemini model name |
| `OPENAI_API_KEY` | — | OpenAI API key (or `ollama` for Ollama) |
| `OPENAI_MODEL` | `gpt-4o` | Any model accepted by the target API |
| `OPENAI_BASE_URL` | — | Override for compatible APIs (Ollama, Azure, Groq...) |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-opus-4-5` | Any Anthropic model name |
| `ENABLE_FRONTEND` | `true` | Set `false` for pure REST API mode |
| `SESSION_TTL_SECONDS` | `3600` | Chat session expiry (seconds) |
| `MAX_SESSIONS` | `1000` | Maximum concurrent in-memory sessions |
| `MAX_UPLOAD_SIZE_MB` | `10` | Maximum file upload size |
| `ALLOWED_ORIGINS` | `["*"]` | CORS allowed origins (restrict in production) |
| `DEBUG` | `false` | Enable debug logging |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |

---

## Development

### Setup

```bash
git clone https://github.com/Thijsn04/MediClear-AI.git
cd MediClear-AI
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Running tests

```bash
pytest tests/ -v
```

Tests use a `MockProvider` that returns deterministic responses without requiring any API keys.

### Project structure

```
app/
├── main.py                   # FastAPI application factory
├── config.py                 # All configuration (env vars)
├── dependencies.py           # Dependency injection
├── api/v1/endpoints/         # HTTP endpoints
├── core/                     # Exceptions, logging
├── models/schemas.py         # Pydantic models
├── providers/                # AI provider implementations
├── services/                 # Business logic
├── i18n/translations.py      # UI translations
└── static/                   # Optional HTML/CSS/JS frontend
tests/                        # pytest test suite
```

### Adding a new AI provider

1. Create `app/providers/my_provider.py` extending `BaseAIProvider`.
2. Register it in `build_provider()` in `app/services/ai_service.py`.
3. Add the new literal to the `ai_provider` field in `app/config.py`.
4. Document the configuration in `.env.example` and this README.

---

## Architecture

```
HTTP Request
    │
    ▼
FastAPI Endpoint  (app/api/v1/endpoints/)
    │
    ▼
AIService         (app/services/ai_service.py)
    │  manages sessions, selects provider
    ▼
BaseAIProvider    (app/providers/)
    │  formats prompt, calls AI API
    ▼
AI API            (Gemini / OpenAI / Anthropic / Ollama / ...)
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

MIT — see [LICENSE](LICENSE).

---

> **Medical disclaimer:** MediClear AI is an educational tool. It does not constitute medical advice and must not be used as a substitute for consultation with a qualified healthcare professional. Always refer medical decisions to a licensed clinician.


---

<div align="center">
<sub>Built by <a href="https://github.com/Thijsn04">Thijs Nannings</a> · Medical Informatics @ UvA · <a href="https://lythos.nl">Lythos</a></sub>
</div>
