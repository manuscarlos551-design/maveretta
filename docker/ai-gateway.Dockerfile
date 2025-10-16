# ===== AI GATEWAY - OPTIMIZED MULTI-STAGE BUILD =====
# Versão: 2.3.1
# Target: < 800MB final image

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

# Set PYTHONPATH
ENV PYTHONPATH=/app

# Copy application files
COPY ai_gateway_main.py ./ai_gateway_main.py
COPY ai_gateway/ ./ai_gateway/
COPY core/ ./core/
COPY ai/ ./ai/
COPY config/ ./config/
COPY plugins/ ./plugins/
COPY risk/ ./risk/

# Health check with proper retries and timeout
HEALTHCHECK --interval=5s --timeout=2s --start-period=10s --retries=20 \
  CMD wget -qO- http://localhost:8080/health || exit 1

EXPOSE 8080

# Run using uvicorn directly
CMD ["python", "-m", "uvicorn", "ai_gateway_main:app", "--host", "0.0.0.0", "--port", "8080"]
