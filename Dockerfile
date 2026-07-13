# ════════════════════════════════════════════════════════════
# MediClear AI - Dockerfile
# Multi-stage build. Choose which optional features to bake in with
# the EXTRAS build arg (default: the three cloud providers).
#
#   docker build -t mediclear-ai .
#   docker build --build-arg EXTRAS="openai,redis,metrics" -t mediclear-ai .
#   docker build --build-arg EXTRAS="all" -t mediclear-ai .
# ════════════════════════════════════════════════════════════

FROM python:3.12-slim AS builder

ARG EXTRAS="gemini,openai,anthropic,metrics"
WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml requirements.txt README.md ./
COPY app/ ./app/
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir ".[${EXTRAS}]"

# ── Runtime stage ─────────────────────────────────────────
FROM python:3.12-slim AS runtime

RUN addgroup --system --gid 1001 mediclear \
    && adduser --system --uid 1001 --gid 1001 --no-create-home mediclear

WORKDIR /app
COPY --from=builder /install /usr/local
COPY app/ ./app/
RUN chown -R mediclear:mediclear /app
USER mediclear

ENV HOST=0.0.0.0 \
    PORT=8000 \
    DEBUG=false \
    ENABLE_FRONTEND=true \
    ENVIRONMENT=production

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host $HOST --port $PORT"]
