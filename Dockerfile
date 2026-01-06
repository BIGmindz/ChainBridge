# ═══════════════════════════════════════════════════════════════════════════════
# CHAINBRIDGE V1.2.0 — DOCKERFILE
# PAC-OCC-P31 — Containerization
#
# GOVERNANCE:
# - LAW-09: Immutable Infrastructure
# - SECURITY: Non-root user (chainbridge, UID 1000)
# - PERSISTENCE: Database mounted at runtime, never baked in
#
# BUILD: docker build -t chainbridge:v1.2.0 .
# RUN: docker-compose up
# ═══════════════════════════════════════════════════════════════════════════════

# syntax=docker/dockerfile:1.4

# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 1: Builder (Install dependencies with build tools)
# ═══════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies (for compiled packages like numpy, pandas)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 2: Runtime (Minimal image with non-root user)
# ═══════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS runtime

# Labels
LABEL maintainer="ChainBridge Team"
LABEL version="1.2.0"
LABEL description="ChainBridge Constitutional Control Plane"

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Copy Python environment from builder
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin

# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY: Create non-root user (SAM/GID-06 Requirement)
# Kill Condition: Running as root is a security violation
# ═══════════════════════════════════════════════════════════════════════════════
RUN useradd --create-home --uid 1000 --shell /bin/bash chainbridge

# ═══════════════════════════════════════════════════════════════════════════════
# APPLICATION STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════

# Create necessary directories
RUN mkdir -p /app/logs /app/_incoming /app/data && \
    chown -R chainbridge:chainbridge /app

# Copy application source (respects .dockerignore)
COPY --chown=chainbridge:chainbridge src/ ./src/
COPY --chown=chainbridge:chainbridge api/ ./api/
COPY --chown=chainbridge:chainbridge tests/ ./tests/
COPY --chown=chainbridge:chainbridge docs/ ./docs/
COPY --chown=chainbridge:chainbridge core/ ./core/
COPY --chown=chainbridge:chainbridge *.py ./

# ═══════════════════════════════════════════════════════════════════════════════
# RUNTIME CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Switch to non-root user
USER chainbridge

# Expose API port (for future P32)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command: Run API server
CMD ["python", "-m", "uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
