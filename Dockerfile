# ════════════════════════════════════════════════════════════
# MediClear AI — Dockerfile
# Multi-stage build: slim production image (~200 MB)
# ════════════════════════════════════════════════════════════

# ── Build stage ───────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt

# ── Runtime stage ─────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Non-root user for security
RUN addgroup --system --gid 1001 mediclear \
    && adduser --system --uid 1001 --gid 1001 --no-create-home mediclear

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY app/ ./app/

# Set ownership
RUN chown -R mediclear:mediclear /app

USER mediclear

# Runtime environment defaults (override via docker run -e or docker-compose)
ENV HOST=0.0.0.0 \
    PORT=8000 \
    DEBUG=false \
    ENABLE_FRONTEND=true

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host $HOST --port $PORT"]
