# Multi-stage build: builder stage installs build deps; runtime stage is minimal and non-root
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build deps only in builder stage
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source into builder (so pip-installed wheels are available if needed)
COPY . /app

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
