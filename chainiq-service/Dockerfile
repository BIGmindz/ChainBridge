# =============================================================================
# ChainIQ Risk Scoring Service - Development Dockerfile
# =============================================================================
# FastAPI ML service providing risk scoring, simulation, and health endpoints.
# Port: 8102 (as per Maggie spec)
#
# Dan (GID-07) — DevOps & CI/CD Lead
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pytest pytest-asyncio httpx

# Copy application code
COPY . /app

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8102

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8102/health || exit 1

# Default command - run ChainIQ service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8102", "--reload"]
