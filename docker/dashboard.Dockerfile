# ===== STREAMLIT DASHBOARD - OPTIMIZED BUILD =====
# Versão: 2.3.0
# Target: < 1GB final image

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
COPY interfaces/ ./interfaces/
COPY core/ ./core/

# Health check
HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=8 \
  CMD wget -qO- http://localhost:8501/ || exit 1

EXPOSE 8501

CMD ["streamlit", "run", "interfaces/web/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
