# =============================================================================
# ChainBoard UI - Development Dockerfile
# =============================================================================
# React + TypeScript + Vite frontend for ChainBridge operations.
# Port: 5173 (Vite dev server)
#
# Dan (GID-07) — DevOps & CI/CD Lead
# =============================================================================

FROM node:20-alpine

WORKDIR /app

# Install dependencies first (for layer caching)
COPY package*.json ./
RUN npm ci --legacy-peer-deps

# Copy source code
COPY . .

# Environment variables for Vite
ENV VITE_API_BASE_URL=http://localhost:8000
ENV VITE_CHAINIQ_BASE_URL=http://localhost:8102

EXPOSE 5173

# Health check (Vite dev server)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget -q --spider http://localhost:5173 || exit 1

# Start Vite dev server with host binding for Docker
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
