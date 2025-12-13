# Local Development Guide

> **Author:** Dan (GID-07) — DevOps & CI/CD Lead
> **Last Updated:** 2024-12-07
> **Purpose:** Reproduce CI steps locally for fast iteration

This document describes how to run the same build/test commands locally that CI runs on every PR. Use this to catch issues before pushing.

---

## Prerequisites

| Tool | Version | Check Command |
|------|---------|---------------|
| Python | 3.11+ | `python --version` |
| Node.js | 20+ | `node --version` |
| npm | 10+ | `npm --version` |
| pip | Latest | `pip --version` |

---

## Quick Start (All Services)

```bash
# From repo root, run all tests:
make test          # If Makefile is configured
# OR manually:
python benson_rsi_bot.py --test
pytest tests/ -v
```

---

## Service-by-Service Instructions

### 1. Backend API (`api/`, `core/`, `tests/`)

```bash
# Setup
cd /path/to/ChainBridge-local-repo
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Optional dev tools

# Test
python benson_rsi_bot.py --test        # Legacy RSI tests
pytest tests/ -v --tb=short            # Full pytest suite

# Lint (optional)
pip install ruff black
ruff check .
black --check .
```

---

### 2. ChainPay Service (`ChainBridge/chainpay-service/`)

```bash
# Setup
cd ChainBridge/chainpay-service
python -m venv .venv
source .venv/bin/activate

# Install
pip install --upgrade pip
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio

# Test
pytest tests/ -v --tb=short --cov=chainpay_service --cov=app

# Run service (dev mode)
uvicorn app.main:app --reload --port 8001
```

---

### 3. ChainIQ ML Service (`ChainBridge/chainiq-service/`)

```bash
# Setup
cd ChainBridge/chainiq-service
python -m venv .venv
source .venv/bin/activate

# Install
pip install --upgrade pip
pip install -r requirements.txt
pip install pytest

# Sanity check (compiles all Python)
python -m compileall app/ -q

# Test (when tests exist)
pytest tests/ -v --tb=short

# Run service (dev mode)
uvicorn app.main:app --reload --port 8002
```

> ⚠️ **Note:** ChainIQ tests are currently stubbed. Full test suite coming with Maggie's ML implementation.

---

### 4. ChainFreight Service (`ChainBridge/chainfreight-service/`)

```bash
# Setup
cd ChainBridge/chainfreight-service
python -m venv .venv
source .venv/bin/activate

# Install
pip install --upgrade pip
pip install -r requirements.txt

# Sanity check
python -m compileall app/ -q

# Test (when tests exist)
pytest tests/ -v --tb=short
```

> ⚠️ **Note:** ChainFreight is a skeleton service. Tests will be added when implemented.

---

### 5. ChainBoard UI (`ChainBridge/chainboard-ui/`)

```bash
# Setup
cd ChainBridge/chainboard-ui

# Install
npm ci                    # Clean install (uses package-lock.json)
# OR
npm install               # If no package-lock.json

# Type check
npm run type-check

# Lint
npm run lint

# Build (production)
npm run build

# Test
npm test -- --run         # Single run
npm test                  # Watch mode
npm run test:coverage     # With coverage

# Dev server
npm run dev               # Starts Vite dev server at http://localhost:5173
```

---

## Option B: Docker Compose Dev Stack

For a one-command development environment with all services:

### Quick Start

```bash
# From repo root
cd /path/to/ChainBridge-local-repo

# 1. Copy environment template
cp .env.dev.example .env.dev

# 2. Build and start all services
docker compose -f docker-compose.dev.yml up --build

# Wait for all services to be healthy (~60 seconds first time)
```

### Services & Ports

| Service | URL | Description |
|---------|-----|-------------|
| **API Gateway** | http://localhost:8000 | ChainBridge FastAPI (governance, OC, risk proxy) |
| **ChainIQ** | http://localhost:8102 | ML risk scoring service |
| **ChainBoard UI** | http://localhost:5173 | React frontend (The OC) |
| **PostgreSQL** | localhost:5432 | Database (user: `chainbridge`) |

### Verify Services

```bash
# API health check
curl http://localhost:8000/health

# ChainIQ health check
curl http://localhost:8102/health

# UI - open in browser
open http://localhost:5173
```

### Common Commands

```bash
# Start stack (detached)
docker compose -f docker-compose.dev.yml up -d

# View logs
docker compose -f docker-compose.dev.yml logs -f

# View specific service logs
docker compose -f docker-compose.dev.yml logs -f api
docker compose -f docker-compose.dev.yml logs -f chainiq
docker compose -f docker-compose.dev.yml logs -f ui

# Stop stack
docker compose -f docker-compose.dev.yml down

# Reset database (destroys data)
docker compose -f docker-compose.dev.yml down -v

# Rebuild specific service
docker compose -f docker-compose.dev.yml build api --no-cache
docker compose -f docker-compose.dev.yml up -d api
```

### Hot Reload

All services support hot-reload in dev mode:

- **API/ChainIQ**: Code changes in `ChainBridge/api/`, `chainiq-service/app/` auto-reload
- **UI**: Vite HMR enabled for `ChainBridge/chainboard-ui/src/`

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Network: chainbridge-net               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐               │
│  │    UI    │─────▶│   API    │─────▶│ ChainIQ  │               │
│  │  :5173   │      │  :8000   │      │  :8102   │               │
│  └──────────┘      └────┬─────┘      └──────────┘               │
│                         │                                        │
│                         ▼                                        │
│                    ┌──────────┐                                  │
│                    │ Postgres │                                  │
│                    │  :5432   │                                  │
│                    └──────────┘                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### Python version mismatch
```bash
# Use pyenv to manage Python versions
pyenv install 3.11.0
pyenv local 3.11.0
```

### Node version mismatch
```bash
# Use nvm to manage Node versions
nvm install 20
nvm use 20
```

### Virtual environment issues
```bash
# Delete and recreate
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### npm ci fails
```bash
# Clear npm cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

---

## CI/Local Parity Checklist

Before pushing, ensure:

- [ ] `python benson_rsi_bot.py --test` — passes
- [ ] `pytest tests/ -v` — passes (or no regressions)
- [ ] `cd ChainBridge/chainpay-service && pytest tests/ -v` — passes
- [ ] `cd ChainBridge/chainboard-ui && npm run build && npm test -- --run` — passes
- [ ] `ruff check .` — no errors (warnings OK)
- [ ] `black --check .` — formatted

---

## Related Documentation

- [CI Pipeline](.github/workflows/chainbridge-ci.yml) — Full CI workflow
- [RSI Threshold Policy](docs/RSI_THRESHOLD_POLICY.md) — Trading thresholds governance
- [Architecture](docs/architecture/) — System design docs

---

*Generated by Dan (GID-07) — DevOps & CI/CD Lead*
