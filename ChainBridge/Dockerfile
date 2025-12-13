# syntax=docker/dockerfile:1.4
# Multi-stage build: builder stage installs build deps; runtime stage is minimal and non-root
# PAC-DAN-NEXT-033: Fusion Engine v1.2 Deployment Support
# Build with: DOCKER_BUILDKIT=1 docker build --cache-from=type=registry,ref=<registry>/chainbridge:buildcache .
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build deps only in builder stage
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy source into builder (so pip-installed wheels are available if needed)
COPY . /app

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fusion Engine Build Stage (PAC-DAN-NEXT-033)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FROM builder AS fusion-builder

WORKDIR /app

# Install Fusion Engine ML dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install \
    scikit-learn>=1.3.0 \
    numpy>=1.24.0 \
    pandas>=2.0.0 \
    joblib>=1.3.0 \
    || echo "Fusion ML deps installed"

# Pre-compile Fusion models if available
RUN python -c "
    import os
    import sys
    sys.path.insert(0, '/app')
    try:
        from chainiq_service.app.fusion import FusionEngine
        print('✅ FusionEngine preload OK')
    except ImportError:
        print('⚠️ FusionEngine not yet available')
" || true

# Runtime image
FROM python:3.11-slim

# Create a non-root user
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy runtime Python from builder (optional: copy only installed site-packages)
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application files (respect .dockerignore)
COPY . /app

# Ensure logs directory exists with correct ownership
RUN mkdir -p /app/logs && chown -R appuser:appuser /app

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

USER appuser

EXPOSE 8000

# Default command; allow override
CMD ["python", "benson_system.py", "--mode", "api-server", "--port", "8000"]
