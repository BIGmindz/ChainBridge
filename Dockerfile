# ══════════════════════════════════════════════════════════════════════════════
# CHAINBRIDGE SOVEREIGN NODE v2.0.0 - CONTAINERIZATION
# PAC-OPS-P220-CONTAINER-V2
# ══════════════════════════════════════════════════════════════════════════════
# CAPABILITIES:
#   - Trinity Gates (P85/P65/P75): Biometric, AML, Customs
#   - Invisible Bank (P200-P203): Ledger, Settlement, Fees, Currency
#   - Sovereign API v2.0 (P211): Financial Transparency
# INVARIANTS:
#   INV-OPS-001 (Portability): System must not depend on host OS
#   INV-OPS-002 (Isolation): Dependencies locked within image
#   INV-OPS-005 (Version Alignment): Container == API == Controller
# ══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1: BUILDER - Install dependencies in isolated layer
# PAC-OPS-P251: Runtime upgraded to Python 3.14.2 (vulnerability-free)
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.14.2-slim AS builder

WORKDIR /build

# Install build dependencies (temporary, not in final image)
# PAC-OPS-P251: Added gfortran for scipy/numpy compilation on Python 3.14
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gfortran \
    pkg-config \
    libopenblas-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (layer caching optimization)
# PAC-P251: Using runtime requirements (TensorFlow excluded for Python 3.14.2 compatibility)
COPY requirements-runtime.txt ./

# Install Python dependencies (lean runtime without TensorFlow)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-runtime.txt && \
    pip install --no-cache-dir fastapi uvicorn pydantic

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2: RUNTIME - Minimal production image
# PAC-OPS-P251: Runtime upgraded to Python 3.14.2 (vulnerability-free)
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.14.2-slim AS runtime

# Security: Create non-root user for container execution
RUN useradd --create-home --shell /bin/bash --uid 1000 sovereign && \
    mkdir -p /app/logs /app/data && \
    chown -R sovereign:sovereign /app

WORKDIR /app

# Copy Python environment from builder
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code (respects .dockerignore)
COPY --chown=sovereign:sovereign . /app

# Ensure critical directories exist with correct permissions
RUN mkdir -p /app/logs/core /app/logs/ops /app/logs/sim && \
    chown -R sovereign:sovereign /app/logs

# Environment configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=8000

# Security: Run as non-root user
USER sovereign

# Expose only the API port
EXPOSE 8000

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default: Launch Sovereign Server
CMD ["uvicorn", "sovereign_server:app", "--host", "0.0.0.0", "--port", "8000"]

# ══════════════════════════════════════════════════════════════════════════════
# LABELS - Container Metadata
# ══════════════════════════════════════════════════════════════════════════════
LABEL org.opencontainers.image.title="ChainBridge Sovereign Node" \
      org.opencontainers.image.description="Trinity Gates + Invisible Bank Transaction Processor" \
      org.opencontainers.image.version="2.0.0" \
      org.opencontainers.image.vendor="ChainBridge" \
      org.opencontainers.image.authors="Benson (GID-00)" \
      com.chainbridge.pac="PAC-OPS-P220-CONTAINER-V2" \
      com.chainbridge.capabilities="Trinity Gates, Invisible Bank, Financial Transparency"
