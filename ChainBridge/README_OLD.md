# ChainBridge — Sense. Think. Act.

![Tests](https://github.com/BIGmindz/ChainBridge/actions/workflows/tests.yml/badge.svg)
![ALEX Governance Gate](https://github.com/BIGmindz/ChainBridge/actions/workflows/tests.yml/badge.svg?job=alex-governance)

**ChainBridge** is a logistics & financial OS for **tokenized supply chains**.

It helps operators and financiers:
- **Sense** what's happening in the network (loads, lanes, assets, risk).
- **Think** with AI-driven risk, performance, and credit scoring.
- **Act** automatically through programmable payments and tokenized incentives.

---

## The Sense → Think → Act Loop

### Sense
Capture ground truth from the real world.

- **ChainSense** — IoT, telematics, EDI, API, and event streams (TMS/WMS/ERP, ports, carriers).
- **ChainBoard – The OC** — Operator Console for a 360° view of shipments, lanes, risk, and cash.
- Normalized shipment + event model mapped to canonical IDs for freight, counterparties, and contracts.

> **Goal:** One reality layer for freight, risk, and money.

---

### Think
Turn noisy signals into decisions.

- **ChainIQ** — scoring engine for:
  - Shipment & lane risk
  - Counterparty reliability
  - Terms / creditworthiness
  - Fraud & anomaly flags
- **Maggie (ML/AI Lead) & agent stack** — interpretable ("glass box") models:
  - Inputs: IoT events, milestones, carrier performance, claims history, macro/logistics data.
  - Outputs: risk_score, confidence, recommended action (release, hold, reprice, inspect).

> **Goal:** Every shipment and counterpart gets a live, explainable score.

---

### Act
Wire decisions into money and workflows.

- **ChainPay** — programmable payment rails for logistics:
  - Milestone-based payouts (e.g. **20% pickup / 70% delivery / 10% claim window**).
  - Dynamic terms driven by **ChainIQ risk_score** (safer lanes → earlier pay, risky lanes → holds/escrow).
- **CB-USDx** — ChainBridge settlement token (design target):
  - Bridges traditional invoices with on-chain proofs.
  - Ready for XRPL-based settlement and Chainlink-powered actuation.
- Hooks into:
  - **XRPL** for fast cross-border settlement.
  - **Chainlink** for on-chain triggers and interoperability.

> **Goal:** "Decisions" aren't just reports — they move money.

---

## Core Platform Components

- **ChainBoard (The OC)**
  Operator console for:
  - Shipment timeline & event stream
  - Risk overlays (ChainIQ scores)
  - Payment state (ChainPay milestones, holds, releases)
  - IoT & exception views (ChainSense signals)

- **ChainSense**
  Data ingestion + normalization layer:
  - IoT / telematics
  - EDI/TMS/WMS/ERP feeds
  - External data (ports, marine traffic, macro/logistics indices)

- **ChainIQ**
  AI & rules engine:
  - Risk scoring
  - Exception detection
  - "What should we do next?" recommendations

- **ChainPay**
  Financial execution:
  - Tokenized invoices
  - Milestone-based payouts
  - Dynamic terms and incentives

---

## Why ChainBridge Now?

Global freight has moved from **"temporary disruption"** to **"permanent volatility."**

Shippers, brokers, and carriers need:
- Real-time **visibility** (what's happening).
- **Decision intelligence** (what it means).
- **Executable rails** (pay, pause, re-route, incentivize) tied to proof, not gut feel.

**ChainBridge** exists to connect those three:

> **Sense. Think. Act.**
> From shipment to payment to proof — in one OS.

---

## Developer Overview

> _Internal dev notes — adjust as your setup evolves._

- Monorepo layout:
  - `ChainBridge/chainboard-ui` – React/Vite frontend (ChainBoard / The OC).
  - `ChainBridge/chainiq-service` – FastAPI-based AI/risk service.
  - `ChainBridge/chainpay-service` – payment & settlement service.
  - `docs/` – product, architecture, and governance specs.

Basic local flow (example):

```bash
# From your local clone root
cd ChainBridge

# (Optional) activate Python env, install backend deps
# source .venv/bin/activate
# pip install -r requirements.txt

# Run ChainBoard (frontend)
cd chainboard-ui
npm install
npm run dev

# In a new terminal, run backend services as needed
cd ../chainiq-service
# uvicorn app.api:app --reload  (example)

cd ../chainpay-service
# uvicorn app.api:app --reload  (example)
```

See `docs/` for:
- Detailed architecture (`docs/architecture/…`)
- On-chain settlement & CB-USDx design
- Agent governance & development workflow

For a guided walkthrough, start with:
- `START_HERE.md`
- `docs/architecture/REPO_STRUCTURE.md`

## 🌐 What is ChainBridge?

ChainBridge is an **ecosystem of integrated services** that brings CIA-grade intelligence and operational control to global freight and logistics. The platform combines real-time shipment tracking, automated payment rails, supply chain analytics, and predictive intelligence into a single unified control tower.

### The Ecosystem

**ChainBoard** – Single pane of glass
Mission-control UI for freight operations, payment status, risk monitoring, and supply chain intelligence. Real-time visibility across all services.

**ChainIQ** – Intelligence layer
Predictive analytics, route optimization, carrier performance scoring, and supply chain risk assessment powered by ML.

**ChainPay** – Payment automation
Milestone-based payment rails with escrow, multi-currency support, and automated reconciliation. Reduces payment friction from weeks to hours.

**ChainFreight** – Shipment orchestration
End-to-end shipment tracking, exception management, and carrier integration. Real-time ETAs and automated milestone detection.

**ChainProof** – Compliance & governance
Digital proof-of-delivery, audit trails, and regulatory compliance automation. Cryptographic verification of milestones.

---

## 🏥 System Health & Reliability

![Code Quality](https://img.shields.io/badge/code%20quality-production%20ready-brightgreen)
![API Tests](https://img.shields.io/badge/API%20tests-15%20passing-success)
![Coverage](https://img.shields.io/badge/coverage-tracked-blue)
![Python](https://img.shields.io/badge/python-3.11.14-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)

[![Tests](https://github.com/BIGmindz/ChainBridge/workflows/Tests/badge.svg)](https://github.com/BIGmindz/ChainBridge/actions/workflows/tests.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

**Status:** ✅ **Mission-Critical Ready** | **Last Updated:** November 15, 2025

### Why Health Monitoring Matters

In freight operations, **downtime = lost revenue**. A single payment delay can cascade into supply chain disruptions affecting dozens of shipments and millions in capital.

Our health monitoring infrastructure ensures:

- **Uptime Confidence**: `/health` endpoint monitored 24/7, giving operators instant "go/no-go" on system reliability
- **Safe Deployments**: Health checks before and after deployments prevent production incidents
- **Reproducible Debugging**: `/events/echo` endpoint lets engineers verify exact payloads partners send us, eliminating integration guesswork
- **Trust at Scale**: Every API call is validated, logged, and tested to ensure freight operators can make million-dollar decisions with confidence

### Test Coverage Strategy

**Coverage isn't about hitting arbitrary percentages—it's about proving our decision APIs work under stress.**

| Layer | Coverage Focus | Business Impact |
|-------|---------------|----------------|
| **API Health** | 8 tests across `/health` and `/events/echo` | Confirms system responsiveness for operational decisions |
| **Payment Rails** | Escrow state machines, multi-currency | Prevents payment holds that block shipments |
| **Shipment Lifecycle** | Milestone detection, ETA updates | Ensures accurate status for customer SLAs |
| **Risk Engine** | Exception detection, carrier scoring | Protects against high-risk routes and fraud |

**Run coverage reports:**

```bash
# API-focused coverage
make api-tests-coverage

# Full system coverage
make coverage

# View HTML report
open htmlcov/index.html
```

---

## 🎯 Business Outcomes Enabled

### For CTOs & Architects

- **Microservices-first**: Each service (ChainIQ, ChainPay, etc.) is independently deployable with clear APIs
- **Event-driven**: Milestone events trigger payment releases, notifications, and analytics updates
- **Observability**: Structured logging, health checks, and metrics for every critical path
- **Scale-ready**: FastAPI async architecture handles 10K+ concurrent shipments

### For Investors

- **TAM**: $800B+ global freight forwarding market + $1.9T trade finance market
- **Moat**: Integrated freight + payments platform (competitors solve one or the other, not both)
- **Unit Economics**: Automated payment rails reduce operational costs 70%+ vs manual reconciliation
- **Defensibility**: Network effects—more carriers = better rates, more shippers = better carrier utilization

### For Operations Teams

- **Single Source of Truth**: All shipment, payment, and exception data in ChainBoard UI
- **Exception-Driven**: Dashboard surfaces only what needs human attention (delays, payment holds, compliance flags)
- **Automated Workflows**: Payment releases, carrier notifications, and customer updates happen automatically on milestones
- **Mobile-First**: Field teams access proof-of-delivery and status updates from any device

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for ChainBoard UI)
- PostgreSQL 14+ (for ChainPay service)

### 1. Backend API (ChainBridge Core)

```bash
# Clone and setup
git clone https://github.com/BIGmindz/ChainBridge.git
cd ChainBridge

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start API server
python api/server.py
```

**API available at:** `http://localhost:8000`
**Interactive docs:** `http://localhost:8000/docs`

### 2. ChainBoard UI (Control Tower)

```bash
# Navigate to UI
cd chainboard-ui

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local: VITE_API_BASE_URL=http://localhost:8000

# Start dev server
npm run dev
```

**UI available at:** `http://localhost:5173`

### 3. Verify System Health

```bash
# Check backend health
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","version":"1.0.0","timestamp":"2025-11-15T..."}

# Test event echo
curl -X POST http://localhost:8000/events/echo \
  -H "Content-Type: application/json" \
  -d '{"test": "payload"}'
```

### 4. Seed ChainIQ demo data (Fleet Cockpit)

```bash
python -m scripts.seed_chainiq_demo
# Optional: limit demo shipments (default 24)
python -m scripts.seed_chainiq_demo --count 30
```

The seed script is idempotent—rerun any time you need a fresh, realistic set of shipment snapshots spanning OCEAN/AIR/ROAD corridors and low → critical risk levels.

### 5. Run a local snapshot worker

```bash
# In a second terminal (virtualenv activated)
python -m scripts.run_snapshot_worker

# Optional tuning
CHAINIQ_WORKER_ID=worker-alpha \
CHAINIQ_WORKER_FAILURE_RATE=0.1 \
python -m scripts.run_snapshot_worker
```

The worker continuously claims `SnapshotExportEvent` rows, simulates processing, and marks them `SUCCESS` (or retries on simulated failures). Run it alongside the API to see live updates in the Fleet Cockpit Control Tower.

---

## Backend Quickstart (API + Workers)

- Runtime: Python 3.11.x, FastAPI 0.116.2, SQLAlchemy 2.0.44, Alembic 1.13.2, Web3 7.14.0, Redis/arq 5.3.1/0.26.3
- Environment: copy `.env` (or `.env.example`) then `source .venv/bin/activate` and `python -m pip install --upgrade pip`
- Start API: `uvicorn app.main:app --port 8001 --reload` (CORS ready for http://localhost:3000 and :5173)
- Start worker: `arq app.worker.main.WorkerSettings` (demo-friendly in-memory queue if Redis is absent)
- Tests: `python -m pytest -q` or the focused Phase 6 suite `python -m pytest -q tests/test_marketplace_pricing_api.py tests/test_marketplace_buy_intents_api.py tests/test_marketplace_settlement_worker.py`
- Demo data (optional): `python -m scripts.seed_chainiq_demo` to populate shipments/risk snapshots for dashboards

---

### Backend Dev Setup (Cody)

```bash
cd /Users/johnbozza/Documents/Projects/ChainBridge-local-repo/ChainBridge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.server:app --reload --host 0.0.0.0 --port 8001
```

### Global Intel Demo Mode
- When `DEMO_MODE=True`, `/chainboard/live-positions` and `/intel/live-positions` return deterministic synthetic shipments so the Global Intel map and KPIs are never empty.
- `/intel/global-snapshot` aggregates those synthetic shipments into the KPI card values used by the ChainBoard Global Intel page.

---

## 💳 ChainPay PaymentIntent Flow

Payment intents now wire themselves off ChainIQ risk approvals—no manual API calls required once a shipment is approved.

- Shipment → ChainDocs/ChainIQ snapshot → PaymentIntent auto-created (cached by snapshot id)
- Proof attach validated against ChainDocs; conflicts return `409` if reused elsewhere
- Operator views: `GET /chainpay/payment_intents` now includes risk, has_proof, ready_for_payment, and shipment summary
- KPI strip: `GET /chainpay/payment_intents/summary` returns totals/awaiting proof/ready/blocked-by-risk

---

## 🛡️ Phase 6 – Web3 Integration (Dutch Auctions)

- **Authoritative pricing**: `GET /marketplace/listings/{id}/price` returns server-computed price, auction_state_version, ISO timestamp, and one-time `proof_nonce` used for settlement.
- **Price-proofed intents**: `POST /marketplace/listings/{id}/buy_intents` validates wallet, recomputes price server-side, enforces tolerance, rate limits, and persists a `BuyIntent` with hash of the quote.
- **ARQ worker**: `execute_dutch_settlement` transitions intents `QUEUED → SUBMITTED → CONFIRMED/FAILED`, writes a `SettlementRecord`, and emits `MARKETPLACE_SETTLEMENT_CONFIRMED`. DEMO mode produces deterministic tx hashes (no keys required).
- **Web3 adapter**: `DemoWeb3SettlementClient` is the default; plug in real RPC via `WEB3_RPC_URL`/`WEB3_OPERATOR_WALLET` without committing secrets.
- **Run the flow**:
  1) `GET /marketplace/listings/{id}/price` → capture `proof_nonce`.
  2) `POST /marketplace/listings/{id}/buy_intents` with wallet, client_price, proof_nonce.
  3) Worker job processes `execute_dutch_settlement` (ARQ or demo stub).
- **Tests**: `pytest tests/test_marketplace_pricing_api.py tests/test_marketplace_buy_intents_api.py tests/test_marketplace_settlement_worker.py` (or `pytest -q` for the suite). Logs tag financial steps (`marketplace.price.quote`, `buy_intent.created`, `settlement.confirmed`).

**Sequence (Phase 6.1 hardened)**
```
Client → GET /marketplace/listings/{id}/price
      ← {price, quoted_at, proof_nonce}
Client → POST /marketplace/listings/{id}/buy_intents (wallet, client_price, proof_nonce)
      ← {intent_id, status=QUEUED, expires_at}
Worker → execute_dutch_settlement(intent_id)
      ↳ Web3 adapter (DEMO by default) → tx_hash
      ↳ SettlementRecord persisted (auction_reference + payment_intent_id placeholder)
      ↳ EVENT: MARKETPLACE_SETTLEMENT_CONFIRMED published
```

**Example flows**
- Happy path:
  ```bash
  price=$(curl -s localhost:8000/marketplace/listings/LST-123/price)
  nonce=$(echo "$price" | jq -r .proof_nonce)
  amt=$(echo "$price" | jq -r .price)
  curl -s -X POST localhost:8000/marketplace/listings/LST-123/buy_intents \
    -H 'Content-Type: application/json' \
    -d "{\"wallet_address\":\"0x$(printf 'a%.0s' {1..40})\",\"client_price\":$amt,\"proof_nonce\":\"$nonce\",\"listing_id\":\"LST-123\"}"
  ```
- Price changed (server returns HTTP 409):
  ```bash
  # reuse an old proof_nonce after price decay
  # response detail: {"code":"PRICE_CHANGED","message":"Price changed; refresh quote"}
  ```
- Auction ended (HTTP 400):
  ```bash
  # listing expired => detail: {"code":"AUCTION_ENDED","message":"Auction has ended"}
  ```

**Observability**
- Structured logs include `event`, `listing_id`, `wallet`, `price`, `status`, `error_code`, `adapter` (`DEMO` vs future REAL).
- Metrics façade (`app/core/metrics.py`) counts quotes, buy intents, successes/failures, settlement outcomes.
- SLA endpoint `/sla/operator` now reports `marketplace_settlements_24h` and `marketplace_failed_intents_24h`.

**Settlement lifecycle (backend)**
| Step | State | Action | Notes |
| --- | --- | --- | --- |
| Quote | n/a | `GET /marketplace/listings/{id}/price` | Canonical server price, nonce, TTL |
| Intent | QUEUED | `POST /marketplace/listings/{id}/buy_intents` | Validates nonce, price match, rate limits |
| Worker start | SUBMITTED | `execute_dutch_settlement` | Loads intent/listing in fresh session |
| Worker success | CONFIRMED | SettlementRecord persisted | Emits `MARKETPLACE_SETTLEMENT_CONFIRMED` + `SETTLEMENT:COMPLETE:{intent_id}` |
| Worker fail | FAILED | SettlementRecord persisted with error | Demo tx hashes stay deterministic |

**Settlement event payload (channel: `chainbridge.settlements`)**
```json
{
  "type": "SETTLEMENT_COMPLETE",
  "intent_id": "INT-123",
  "listing_id": "LST-456",
  "status": "SETTLED",          // or FAILED, SETTLING, PENDING
  "tx_hash": "demo_tx_INT-123",
  "final_price": 123.45,
  "currency": "USDC",
  "failure_reason": null
}
```

**Marketplace error codes**
- `LISTING_NOT_FOUND` (404)
- `QUOTE_MISMATCH` (400)
- `NONCE_EXPIRED` (400)
- `LISTING_ID_MISMATCH` (400)
- `LISTING_NOT_ACTIVE` (409)
- `AUCTION_ENDED` (400)
- `RATE_LIMITED` (429)
- `SETTLEMENT_QUEUE_UNAVAILABLE` (503)
- `SETTLEMENT_FAILED` (500-equivalent payload when settlement client fails)

**Web3 configuration**
- `WEB3_MODE=demo|real` (defaults to demo when DEMO_MODE is true)
- `WEB3_RPC_URL` (required for real mode)
- `WEB3_OPERATOR_WALLET` / `WEB3_OPERATOR_KEY` (used only in real mode; never logged)
- `WEB3_STRICT=true` to hard-fail if real mode is misconfigured

**Marketplace-only tests**
```bash
python3 -m pytest -q tests/test_marketplace_pricing_api.py tests/test_marketplace_buy_intents_api.py tests/test_marketplace_settlement_worker.py
```
### ChainPay PaymentIntent + Money View

- Server-side readiness rule: proof attached AND status in {PENDING, AUTHORIZED} AND risk_level in {LOW, MEDIUM}.
- List filters: `status`, `corridor_code`, `mode`, `has_proof`, `ready_for_payment`; each item includes shipment summary + created/updated timestamps.
- Summary endpoint powers Money View KPIs with counts for total, ready_for_payment, awaiting_proof, blocked_by_risk.

**Example cURL sequence (local):**

```bash
# 1) Generate risk + snapshot (auto-creates PaymentIntent if risk is LOW/MEDIUM)
curl -s http://localhost:8001/chainiq/shipments/SHIP-42/health | jq .

# 2) List intents with computed flags
curl -s "http://localhost:8001/chainpay/payment_intents?ready_for_payment=true" | jq .

# 3) Attach proof (errors if ChainDocs cannot find the proof or it is attached elsewhere)
curl -s -X POST http://localhost:8001/chainpay/payment_intents/PAY-123/attach_proof \
  -H "Content-Type: application/json" \
  -d '{"proof_pack_id": "PROOF-abc-123"}' | jq .

# 4) Summary snapshot for Control Tower KPI strip
curl -s http://localhost:8001/chainpay/payment_intents/summary | jq .
```

---

## 🔁 ChainPay Settlement Lifecycle (Demo)

- Flow: Shipment → Risk Snapshot → PaymentIntent → SettlementEvents (timeline) → (future Settlement).
- Event types: CREATED → AUTHORIZED → CAPTURED on happy path; HIGH/CRITICAL risk yields FAILED path.
- Demo generator: `python -m scripts.generate_demo_settlement_events` (add `--rewrite` to regenerate). Uses intent created_at to space events (+5m, +15m).
- Timeline API: `GET /chainpay/payment_intents/{id}/settlement_events` (ordered ASC).
- Webhooks: `POST /webhooks/settlement/payment_status` and `/webhooks/settlement/proof_attached` append events and update readiness.
- Event bus: in-process publish/subscribe for payment_intent and settlement events (see `api/events/bus.py`).
- SLA: `GET /sla/status` (general freshness) and `GET /sla/operator` (queue depth, p95 processing, counts).

**Mini command flow**

```bash
# Seed intents however you like, then generate settlements
python -m scripts.generate_demo_settlement_events

# List intents
curl -s http://localhost:8001/chainpay/payment_intents | jq '.[0]'

# Timeline for a specific intent
curl -s http://localhost:8001/chainpay/payment_intents/PAY-XYZ/settlement_events | jq .

# Webhook demo
curl -s -X POST http://localhost:8001/webhooks/settlement/payment_status \
  -H "Content-Type: application/json" \
  -d '{"payment_intent_id":"PAY-XYZ","external_status":"AUTHORIZED","provider":"demo","raw_payload":{}}'

# SLA
curl -s http://localhost:8001/sla/operator | jq .
```

---

## 🗄️ Database migrations (Alembic)

- Alembic is the canonical migration tool for ChainBridge.
- Baseline + constraint migrations live under `alembic/versions/`.
- Run migrations locally:

```bash
python -m scripts.db_upgrade  # or
alembic upgrade head
```

- Backfill helper:

```bash
python -m scripts.backfill_latest_risk_snapshot
```

Default dev DB is SQLite (`chainbridge.db`); migrations are forward-compatible with Postgres for production.

---

## 🧪 Testing & Quality

### Run Tests

```bash
# Full test suite
python -m scripts.db_upgrade
python -m pytest tests/ -v

# API tests only
make api-tests

# Quick checks (lean, fast)
make quick-checks

# With coverage
make coverage
```

### Coverage Reports

```bash
# Generate coverage report
pytest --cov=api --cov=core --cov=tracking tests/

# HTML report
pytest --cov=api --cov=core --cov=tracking tests/ --cov-report=html
open htmlcov/index.html
```

### CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/tests.yml`) runs on every push:

1. **Lint & Type Check**: Ruff linting, Python type validation
2. **Unit Tests**: Full test suite with pytest
3. **API Tests**: Dedicated job for health & echo endpoints
4. **ALEX Governance Gate**: `alex-governance` job runs `pytest -q tests/agents` and must pass before merging to `main`
5. **Coverage**: Tracked and reported (integration ready for Codecov)

### Agent Safety & Governance

ALEX is the governance gate for legal, risk, and settlement-sensitive flows.

- Canonical prompts and checklists live in `AGENTS 2/`.
- Governance rules and tests live under `tests/agents/`.
- CI runs the **ALEX Governance Gate** status check (`alex-governance`) on every PR into `main`.
- Branch protection requires this job to pass before merging to `main`.

**How to run ALEX locally**

```bash
source .venv/bin/activate
pytest -q tests/agents

# or

make test-alex
```

See [ALEX Governance Gate](docs/ci/ALEX_GOVERNANCE_GATE.md) for details.

---

## 📐 Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      ChainBoard UI                          │
│              (React + TypeScript + Tailwind)                │
│        Mission Control for All ChainBridge Services         │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   ChainBridge API Layer                     │
│                    (FastAPI + Python)                       │
│              Unified Gateway to All Services                │
└─┬────────┬────────┬────────┬────────┬──────────────────────┘
  │        │        │        │        │
  ▼        ▼        ▼        ▼        ▼
┌────┐  ┌────┐  ┌────┐  ┌────┐  ┌────────┐
│IQ  │  │Pay │  │Frt │  │Prf │  │ IoT    │
│Svc │  │Svc │  │Svc │  │Svc │  │ Edge   │
└────┘  └────┘  └────┘  └────┘  └────────┘
  │        │        │        │        │
  └────────┴────────┴────────┴────────┘
                   │
                   ▼
          ┌────────────────┐
          │   PostgreSQL   │
          │  TimescaleDB   │
          └────────────────┘
```

### Key Design Principles

1. **API-First**: Every service exposes REST endpoints, documented with OpenAPI
2. **Event-Driven**: Milestone events trigger workflows (payment release, notifications)
3. **Microservices**: Each service (IQ, Pay, Freight, Proof) is independently deployable
4. **Observable**: Structured logging, health checks, metrics at every layer
5. **Idempotent**: Retry-safe operations for payment and status updates

---

## 🛠️ Development

### Project Structure

```
ChainBridge/
├── api/                    # FastAPI server (unified gateway)
│   ├── server.py          # Main API entrypoint
│   └── schemas/           # Pydantic models
├── chainboard-ui/         # React control tower UI
│   ├── src/
│   │   ├── components/    # HealthStatusCard, EchoEventPanel, etc.
│   │   ├── lib/           # apiClient, metrics, types
│   │   └── pages/         # OverviewPage, ShipmentsPage, etc.
│   └── package.json
├── chainiq-service/       # Intelligence & analytics
├── chainpay-service/      # Payment automation
├── chainfreight-service/  # Shipment orchestration
├── core/                  # Shared business logic
│   ├── data_processor.py
│   └── pipeline.py
├── tests/                 # API & integration tests
│   ├── test_api_health_and_echo.py  # 8 tests
│   └── test_rsi_scenarios.py
├── Makefile              # Dev commands
├── .github/workflows/    # CI/CD pipelines
└── requirements*.txt     # Python dependencies
```

### Adding a New Service

1. **Create service directory**: `chain{name}-service/`
2. **Define API contract**: OpenAPI spec in `app/main.py`
3. **Add to gateway**: Route in `api/server.py`
4. **Update UI**: Add dashboard panel in `chainboard-ui/src/components/`
5. **Write tests**: Service tests + integration tests in `tests/`

### Makefile Commands

```bash
make api-tests           # Run API tests only
make api-tests-coverage  # API tests with coverage
make pytest-all          # All tests
make quick-checks        # Fast sanity checks (RSI + integrator)
make coverage            # Full coverage report
```

---

## 🔐 Security & Configuration

### Environment Variables

**Backend** (`.env` in repo root):

```bash
# API Configuration
PORT=8000
LOG_LEVEL=INFO

# Database (for ChainPay, ChainFreight services)
DATABASE_URL=postgresql://user:pass@localhost:5432/chainbridge

# External Integrations
STRIPE_API_KEY=sk_test_...
CARRIER_API_KEY=...
```

**Frontend** (`chainboard-ui/.env.local`):

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_ENVIRONMENT=sandbox  # sandbox | staging | production
```

### Secrets Management

- **Development**: Use `.env` files (never commit to git)
- **Production**: Use environment variables via k8s secrets or AWS Secrets Manager
- **CI/CD**: GitHub Actions secrets for API keys and tokens

---

## 📊 Monitoring & Observability

### Health Checks

```bash
# System health (used by load balancers, k8s probes)
GET /health

Response:
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-11-15T12:00:00Z",
  "modules_loaded": 0,
  "active_pipelines": 0
}
```

### Event Echo (Integration Verification)

```bash
# Verify exactly what API receives from partners
POST /events/echo
Content-Type: application/json

{
  "shipment_id": "SHP-1001",
  "milestone": "customs_cleared"
}

Response:
{
  "original": {...},
  "processed_at": "2025-11-15T12:00:00Z",
  "processor_id": 4501313168
}
```

**Why this matters**: In freight, integration errors cost thousands per incident. Echo endpoint lets engineers verify partner payloads match specs before processing.

### Logging

- **Structured JSON logs** for machine parsing
- **Log levels**: DEBUG (dev) → INFO (staging) → WARNING (prod)
- **Lazy formatting**: `logger.info("Processing %s", shipment_id)` for performance

---

## 🎨 ChainBoard UI Design Philosophy

The ChainBoard interface follows **CIA/SOC war room** principles:

- **Mission-Critical Clean**: No visual noise, only actionable data
- **Decision-Focused**: Every widget answers a business question
- **Fast & Responsive**: <100ms interactions, lazy-load heavy data
- **Exception-Driven**: Surface only what needs human attention
- **Dark Theme**: Slate-900 backgrounds, cyan/emerald accents for key metrics

### Key Components

- **HealthStatusCard**: "Can I trust the system right now?"
- **EchoEventPanel**: "What exactly did we receive from partners?"
- **ExceptionStack**: "Which shipments need immediate attention?"
- **PaymentRailsIntel**: "Are payments flowing or blocked?"
- **CorridorIntel**: "Which trade lanes are performing?"

---

## 🚢 Legacy: BensonBot Multi-Signal Trading

ChainBridge evolved from BensonBot, a sophisticated crypto trading system. The core architecture—modular signals, ML pipelines, real-time processing—now powers freight intelligence.

<details>
<summary><strong>Legacy BensonBot Features (Archived)</strong></summary>

## 🚀 New Features - September 17, 2025 Update

### 📡 New Listings Radar

- Detects new coin listings on major exchanges in real-time

- Implements risk filters and confidence scoring for trading opportunities

- Generates trade signals with entry timing, stop-loss, and take-profit levels

- 20-40% average returns per successful listing

### 🌐 Region-Specific Crypto Mapping

- Maps macroeconomic signals to specific cryptocurrencies by region

- Targets the right assets for regional economic conditions

- Integrates with global macro module for comprehensive signal generation

### 📊 System Monitoring and Dashboard

- Real-time monitoring of all system components

- Trading performance dashboard with key metrics

- Automatic restart of critical components if they fail

- Resource usage tracking and optimization

## 🚀 Previous Features - Professional Budget Management & Volatile Crypto Selection

The latest version includes professional budget management with Kelly Criterion position sizing, automatic selection of the most volatile cryptocurrencies, and a comprehensive multi-signal approach combining RSI, MACD, Bollinger Bands, Volume Profile, and Sentiment Analysis.

### 💰 Professional Budget Management

- Kelly Criterion position sizing for mathematically optimal growth

- Risk management with stop-loss and take-profit

- Portfolio tracking with performance dashboard

- Dynamic risk adjustment based on drawdown

- Capital preservation with maximum position limits

### 📊 Volatile Cryptocurrency Selection

- Automatic identification of highest-volatility trading pairs

- Volatility calculation using price standard deviation

- Configuration updates with selected pairs

### 🚢 Logistics-Based Signal Module (NEW!)

- **Forward-looking signals** (30-45 days) based on supply chain metrics

- **Ultra-low correlation** (0.05) with traditional signals

- **Competitive advantage**: No other bot has these signals

- Port congestion analysis for inflation hedge predictions

- Diesel price monitoring for mining cost economics

- Container rate tracking for supply chain stress indicators

- Predictive power superior to lagging technical indicators

### One-Step Trading System

```bash

## Start the complete automated trading system

./start_trading.sh

## Run in test mode to verify functionality

./start_trading.sh --test

## Run performance analysis on your trading history

./start_trading.sh --analyze

## Set up enhanced trading with volatile cryptos and budget management

python3 run_enhanced_bot_setup.py

## Monitor performance in real-time

python3 monitor_performance.py

```text

### Individual Components

```bash

## Find the most volatile cryptocurrencies to trade

python3 dynamic_crypto_selector.py
python3 src/crypto_selector.py  # Alternative implementation

## Run the multi-signal trading bot with budget management

python3 multi_signal_bot.py

## Test the budget manager independently

python3 budget_manager.py

## Analyze trading performance with visualizations

python3 analyze_trading_performance.py

## Full automated system (selection + trading)

python3 automated_trader.py

## Monitor portfolio in real-time

python3 monitor_performance.py

```text

### Legacy API and Bot Compatibility

```bash

## Install dependencies

pip install -r requirements.txt

## Start the API server

python benson_system.py --mode api-server

## Run the original RSI bot functionality

python benson_system.py --mode rsi-compat --once

```text

## 🔐 Security Configuration

BensonBot prioritizes security by using environment variables for sensitive data. **Never commit API keys or secrets to version control.**

### Setting Up API Credentials

1. **Copy the environment template:**

   ```bash

   cp .env.example .env

   ```

1. **Edit `.env` with your credentials:**

   ```bash

   # Replace placeholder values with your actual API credentials

   API_KEY="your_actual_api_key_here"
   API_SECRET="your_actual_api_secret_here"
   EXCHANGE="kraken"  # or your preferred exchange

   ```

1. **Verify `.env` is in your `.gitignore`:**

   The `.env` file should never be committed to version control as it contains sensitive credentials.

### Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `API_KEY` | Exchange API key for live trading | `"ak_1234567890abcdef"` |
| `API_SECRET` | Exchange API secret for live trading | `"sk_abcdef1234567890"` |
| `EXCHANGE` | Exchange to use (kraken, coinbase, binance) | `"kraken"` |
| `PAPER` | Set to "true" for paper trading | `"true"` |

### Configuration Loading

The bot automatically loads environment variables using the `${VARIABLE_NAME}` syntax in `config/config.yaml`:

```yaml

api:
  key: ${API_KEY}
  secret: ${API_SECRET}

```text

### Security Best Practices

- ✅ **DO**: Store API keys in environment variables or secure vaults

- ✅ **DO**: Use paper trading (`PAPER="true"`) for testing

- ✅ **DO**: Regularly rotate API keys

- ❌ **DON'T**: Commit `.env` files or API keys to version control

- ❌ **DON'T**: Share API keys in chat, logs, or screenshots

- ❌ **DON'T**: Use production API keys in development environments

## ✅ Preflight Checks & Market Validation

Before running the bot in live mode (`PAPER=false`), the system performs a preflight check to ensure your configured symbols have exchange-reported minima and valid price data. This prevents creating orders below exchange minimums or acting on symbols with invalid prices (for example, symbols returning a last price of 0.0).

Maintainers can validate a local markets dump (an export of `exchange.markets`) using the helper script:

```bash

.venv/bin/python3 scripts/validate_markets.py /path/to/markets.json

```text

This script reads `config.yaml` to find configured symbols and prints any symbols for which minima could not be detected. Use it during diagnostics or when you update exchange market metadata.

## 🏗️ Enhanced Architecture & Features

### New Trading Components

- **Dynamic Crypto Selector**: Automatically finds the most volatile cryptocurrencies with sufficient volume

- **Multi-Signal Integration**: Combines 5 different trading signals for better decision-making

- **Adaptive Risk Management**: Trading parameters optimized based on each crypto's volatility profile

- **Performance Analysis**: Detailed metrics and visualizations for strategy evaluation

- **Regime Detection**: Optimizes strategies for bull, bear, and sideways markets

### Core Architecture

Benson features a modular architecture with the following components:

- **Core System**: Module management, data processing, and pipeline orchestration

- **API Layer**: RESTful endpoints for system interaction and integration

- **Pluggable Modules**: CSV ingestion, RSI, MACD, Bollinger Bands, Volume Profile, and Sentiment Analysis

- **Business Impact Tracking**: ROI metrics, usage analytics, and adoption tracking

- **Cloud-Native Design**: Containerized deployment with scalability support

## 📊 Available Modules

### Data Ingestion

- **CSV Ingestion**: Process CSV files with flexible column mapping

- **Alternative Data**: Geopolitical and sentiment data integration

### Trading Signal Analysis

- **RSI Module**: Technical analysis with Wilder's RSI calculation

- **MACD Module**: Moving Average Convergence Divergence momentum indicator

- **Bollinger Bands Module**: Volatility-based analysis with band squeeze detection

- **Volume Profile Module**: Volume-based support/resistance and POC analysis

- **Sentiment Analysis Module**: Alternative data sentiment scoring from multiple sources

- **Multi-Signal Aggregator**: Intelligent combination of uncorrelated signals

### Machine Learning & Forecasting

- **Sales Forecasting**: ML-powered sales predictions with trend analysis

- **Market Regime Detection**: Automatic identification of bull, bear, and sideways markets

- **Adaptive Signal Optimization**: Regime-specific signal weighting and position sizing

- **Custom Modules**: Extensible framework for additional analysis

### Business Intelligence

- **Metrics Collection**: Automated tracking of usage and performance

- **ROI Calculation**: Business impact measurement and reporting

## 📘 Documentation

- [Regime-Specific Backtesting](./docs/REGIME_SPECIFIC_BACKTESTING.md): Learn how to evaluate trading strategy performance across different market regimes

- [Market Regime Detection](./docs/MARKET_REGIME_DETECTION.md): Understand how the system identifies bull, bear, and sideways markets

## 🔧 API Examples

### Multi-Signal Analysis

```bash

curl -X POST http://localhost:8000/analysis/multi-signal \
  -H "Content-Type: application/json" \
  -d '{
    "price_data": [
      {"close": 45000, "high": 45200, "low": 44800, "volume": 1000},
      {"close": 45100, "high": 45300, "low": 44900, "volume": 1200}
    ],
    "include_individual_signals": true
  }'

```text

### Individual Signal Analysis

#### Execute RSI Analysis

```bash

curl -X POST http://localhost:8000/modules/RSIModule/execute \
  -H "Content-Type: application/json" \
  -d '{
    "module_name": "RSIModule",
    "input_data": {
      "price_data": [{"close": 45000}, {"close": 45100}]
    }
  }'

```text

#### Execute MACD Analysis

```bash

curl -X POST http://localhost:8000/modules/MACDModule/execute \
  -H "Content-Type: application/json" \
  -d '{
    "module_name": "MACDModule",
    "input_data": {
      "price_data": [{"close": 45000}, {"close": 45100}]
    }
  }'

```text

### Available Signal Modules

```bash

curl http://localhost:8000/signals/available

```text

### Multi-Signal Backtesting

```bash

curl -X POST http://localhost:8000/analysis/multi-signal/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "historical_data": [
      {"close": 45000, "high": 45200, "low": 44800, "volume": 1000},
      {"close": 45100, "high": 45300, "low": 44900, "volume": 1200}
    ],
    "initial_balance": 10000
  }'

```text

### Process CSV Data

```bash

curl -X POST http://localhost:8000/modules/CSVIngestionModule/execute \
  -H "Content-Type: application/json" \
  -d '{
    "module_name": "CSVIngestionModule",
    "input_data": {
      "file_path": "sample_data/btc_price_data.csv"
    }
  }'

```text

### Sales Forecasting

```bash

curl -X POST http://localhost:8000/modules/SalesForecastingModule/execute \
  -H "Content-Type: application/json" \
  -d '{
    "module_name": "SalesForecastingModule",
    "input_data": {
      "historical_sales": [
        {"date": "2024-01-01", "amount": 15000}
      ],
      "forecast_periods": 5
    }
  }'

```text

## 🧪 Testing

```bash

## Run comprehensive system tests (includes all signal modules)

python benson_system.py --mode test

## Run multi-signal demonstration across market scenarios

python benson_system.py --mode multi-signal-demo

## Run comprehensive integration demo

python multi_signal_demo.py

## Test original RSI functionality

python benson_rsi_bot.py --test

```text

### Developer quick checks (lean path)

See README-QUICK-CHECKS.md for a fast, TensorFlow-free validation path and pre-commit setup.

## 📈 Business Impact Features

- **Automation Savings**: Tracks time saved through automated processes

- **Usage Analytics**: Module execution patterns and adoption metrics

- **ROI Reporting**: Cost-benefit analysis of system usage

- **Performance Monitoring**: Error rates, execution times, and reliability metrics

View metrics:

```bash

curl http://localhost:8000/metrics

```text

## 🔌 Extensibility

Create custom modules by extending the base `Module` class:

```python

from core.module_manager import Module

class CustomAnalyzer(Module):
    def process(self, data):

## Your custom logic here

        return {"result": "processed"}

```text

Register and use:

```bash

curl -X POST http://localhost:8000/modules/register \
  -d '{"module_name": "CustomAnalyzer", "module_path": "path.to.module"}'

```text

## 📋 Configuration

### Environment Variables

- `PORT`: API server port (default: 8000)

- `HOST`: API server host (default: 0.0.0.0)

- `BENSON_CONFIG`: Configuration file path

### Module Configuration

Configure modules with custom parameters:

```python

{
  "rsi": {
    "period": 14,
    "buy_threshold": 30,
    "sell_threshold": 70
  }
}

```text

## 🐳 Docker Support

Multiple deployment options:

```bash

## API server mode

docker-compose up benson-api

## Legacy RSI bot mode

docker-compose --profile legacy up benson-legacy

## One-time RSI analysis

docker-compose --profile rsi-only up benson-rsi

```text

## 📚 Additional Documentation

- [Modular Architecture Guide](MODULAR_ARCHITECTURE.md)

- [API Documentation](http://localhost:8000/docs) (when running)

- [Module Development Guide](MODULAR_ARCHITECTURE.md#creating-custom-modules)

## 🛠️ Development

### Project Structure

```plaintext

├── core/                   # Core system components
├── modules/               # Pluggable analysis modules
├── api/                   # REST API server
├── tracking/              # Business impact tracking
├── sample_data/           # Example data files
├── config/                # Configuration files
└── benson_system.py       # Main entry point

```text

### Running Tests

```bash

make test                  # Run all tests
python benson_system.py --mode test  # System tests

```text

## 🌟 Features

- ✅ **Multi-Signal Architecture**: 6 uncorrelated trading signal modules

- ✅ **Intelligent Signal Aggregation**: Consensus-based decision making

- ✅ **Risk-Aware Trading**: Automatic risk assessment and position sizing

- ✅ **Market Regime Detection**: Automatic optimization for bull, bear, and sideways markets ([learn more](docs/MARKET_REGIME_DETECTION.md))

- ✅ **Signal Independence**: Verified uncorrelated indicators (diversification score: 0.90)

- ✅ **Enhanced Machine Learning**: Faster adaptation to changing market conditions

- ✅ Modular, extensible architecture

- ✅ REST API with OpenAPI documentation

- ✅ Multiple data ingestion formats

- ✅ Advanced RSI analysis with Wilder's smoothing

- ✅ ML-powered sales forecasting

- ✅ Business impact tracking and ROI metrics

- ✅ Docker containerization support

- ✅ Cloud-native deployment ready

- ✅ Backward compatibility with existing RSI bot

## 🤝 Contributing

1. Create custom modules following the `Module` interface

1. Add new API endpoints for additional functionality

1. Extend business impact tracking for new metrics

1. Improve ML models and forecasting accuracy

## 📄 License

This project is part of the BIGmindz ChainBridge freight intelligence platform.

---

**Built with precision for mission-critical freight operations.**
From shipment to settlement, ChainBridge delivers the control tower your supply chain deserves.

</details>

---

## 🤝 Contributing

We welcome contributions that align with ChainBridge's mission-critical standards:

1. **Write tests first**: All new features require tests (pytest for backend, vitest for UI)
2. **Follow conventions**: Lazy logging, type hints, structured error handling
3. **Document decisions**: Explain *why* in code comments, not just *what*
4. **Keep it fast**: Profile performance-critical paths, avoid N+1 queries
5. **Think operationally**: How will this behave at 3 AM during an incident?

### Development Workflow

```bash
# 1. Create feature branch
git checkout -b feature/payment-retry-logic

# 2. Make changes with tests
# ... code ...

# 3. Run quality checks
make quick-checks
make api-tests
npm run type-check  # in chainboard-ui/

# 4. Commit with meaningful message
git commit -m "feat(chainpay): add exponential backoff for payment retries"

# 5. Push and create PR
git push origin feature/payment-retry-logic
```

---

## 🔎 ChainAudit v1 (Reconciliation)
- PaymentIntent now stores `payout_confidence`, `auto_adjusted_amount`, and `reconciliation_explanation`.
- Run reconciliation: `curl -X POST http://localhost:8001/audit/payment_intents/<intent_id>/reconcile -H "Content-Type: application/json" -d '{"issues":["minor_delay"],"blocked":false}'`
- Fetch the latest result: `curl http://localhost:8001/audit/payment_intents/<intent_id>`

## 🪙 ChainStake v1 (Stubbed)
- Create a stake job for a shipment (auto-completes in demo): `curl -X POST http://localhost:8001/stake/shipments/<shipment_id> -H "Content-Type: application/json" -d '{"requested_amount":50.0,"payment_intent_id":"<intent_id>"}'`
- List stake jobs: `curl http://localhost:8001/stake/jobs`

## 🔐 ChainDocs Hashing & Proof Verification
- Documents track `sha256_hex`, `storage_backend`, `storage_ref`; PaymentIntents link via `proof_hash`.
- Verify authenticity: `curl -X POST http://localhost:8001/chaindocs/documents/<document_id>/verify`
- Response includes validity plus linked PaymentIntents and emits an audit event.

## 📚 Documentation

- [API Reference](http://localhost:8000/docs) - Interactive OpenAPI docs (when server running)
- [ChainBoard UI Implementation](chainboard-ui/IMPLEMENTATION.md) - UI component guide
- [Architecture Decision Records](docs/ADR/) - Key architectural choices
- [Deployment Guide](docs/DEPLOYMENT.md) - Production deployment checklist

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Questions? Issues? Ideas?**
Open an issue on GitHub or reach out to the ChainBridge team.

**ChainBridge** – Where freight meets intelligence.

## Operator Console APIs
- `/operator/queue` – paginated settlement queue with risk/intent_hash and readiness reasons
- `/operator/settlements/{id}/risk_snapshot` – latest ChainIQ snapshot
- `/operator/settlements/{id}/events` – settlement timeline (asc)
- `/operator/iot/health/summary` – IoT fleet summary (mock provider)
- `/operator/events/stream` – pollable operator events feed
- Operator Console endpoints added (/operator queue, risk_snapshot, settlement events, IoT health summary, event stream) to support OC.
- /operator/events/stream supports poll-based toasts; /operator/iot/health/summary returns IoT health counts (mock-backed for now).
