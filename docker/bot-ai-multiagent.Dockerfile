# ===== BOT AI MULTIAGENT - OPTIMIZED MULTI-STAGE BUILD =====
# Versão: 2.3.0
# Target: < 900MB final image

# ===== STAGE 1: BUILDER =====
FROM python:3.11-bookworm AS builder

WORKDIR /build

# Install build dependencies with retry logic
RUN set -eux; \
    for i in 1 2 3; do \
      apt-get update && \
      apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        build-essential \
        ca-certificates && \
      break || sleep 3; \
    done; \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and build wheels with cache mount
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --wheel-dir /wheels -r requirements.txt

# ===== STAGE 2: RUNTIME =====
FROM python:3.11-slim-bookworm

WORKDIR /app

ARG DEBIAN_FRONTEND=noninteractive

# Install minimal runtime dependencies with retry logic
RUN set -eux; \
    for i in 1 2 3; do \
      apt-get update && \
      apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        wget && \
      break || sleep 3; \
    done; \
    rm -rf /var/lib/apt/lists/*; \
    apt-get clean

# Copy wheels and install with cache mount
COPY --from=builder /wheels /wheels
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --no-index --find-links=/wheels /wheels/* && \
    rm -rf /wheels

# Copy application
COPY bot_runner.py .
COPY core/ ./core/
COPY ai/ ./ai/
COPY config/ ./config/

# Health check
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=6 \
  CMD curl -fsS http://localhost:9200/health || exit 1

EXPOSE 9200

CMD ["python", "bot_runner.py"]
