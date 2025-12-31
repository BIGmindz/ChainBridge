# syntax=docker/dockerfile:1.4
# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Control Plane — Deterministic Docker Build
# PAC-JEFFREY-P01: SECTION 6.4 — Containerization
#
# INVARIANTS:
# - Deterministic reproducible build
# - Non-root user execution
# - Health check integration
# - FAIL_CLOSED governance
#
# Author: DAN (GID-07) — CI/CD Lane
# ═══════════════════════════════════════════════════════════════════════════════

# Build Arguments for reproducibility
ARG PYTHON_VERSION=3.11
ARG BUILD_DATE
ARG GIT_SHA

# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 1: Builder
# ═══════════════════════════════════════════════════════════════════════════════
FROM python:${PYTHON_VERSION}-slim AS builder

WORKDIR /build

# Install build dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements for better caching
COPY requirements.txt ./
COPY requirements-dev.txt ./

# Install Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-deps -r requirements.txt && \
    pip install pytest pytest-asyncio httpx

# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 2: Runtime
# ═══════════════════════════════════════════════════════════════════════════════
FROM python:${PYTHON_VERSION}-slim AS runtime

# Labels for governance traceability
LABEL org.chainbridge.pac="PAC-JEFFREY-P01" \
      org.chainbridge.component="control-plane" \
      org.chainbridge.lane="ci-cd" \
      org.chainbridge.agent="DAN-GID07" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${GIT_SHA}"

# Create non-root user (FAIL_CLOSED security)
RUN groupadd --gid 1000 chainbridge && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash chainbridge

WORKDIR /app

# Copy Python environment from builder
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=chainbridge:chainbridge . /app

# Create required directories
RUN mkdir -p /app/logs /app/proofpacks /app/cache && \
    chown -R chainbridge:chainbridge /app

# Environment configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    CONTROLPLANE_MODE=production \
    GOVERNANCE_FAIL_CLOSED=true

# Switch to non-root user
USER chainbridge

# Expose API port
EXPOSE 8000

# Health check (FAIL_CLOSED: unhealthy container restarts)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/oc/controlplane/health || exit 1

# Default command: Run API server with Control Plane endpoints
CMD ["python", "-m", "uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
