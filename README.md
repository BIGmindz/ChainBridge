# ChainBridge

> **Verifiable freight + programmable payments for enterprise supply chains.**  
> Pipe real-world events (EDI/API) through proofs and policies, then settle cash—automatically.

[![Status](https://img.shields.io/badge/status-early%20alpha-orange)](#)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](#license)
[![Built for](https://img.shields.io/badge/domain-Logistics%20%7C%20Fintech%20%7C%20RWA-black)](#)
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-lightgrey)](#)

---

## Table of Contents
- [Why ChainBridge](#why-chainbridge)
- [What It Does](#what-it-does)
- [Architecture](#architecture)
- [Canonical Flows](#canonical-flows)
- [Modules](#modules)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API (ChainFreight)](#api-chainfreight)
- [Milestone Payments (ChainPay)](#milestone-payments-chainpay)
- [Observability & Ops](#observability--ops)
- [Security & Compliance](#security--compliance)
- [Enterprise Readiness Matrix](#enterprise-readiness-matrix)
- [Roadmap (30/60/90)](#roadmap-306090)
- [Repository Layout](#repository-layout)
- [Contributing](#contributing)
- [License](#license)

---

## Why ChainBridge
Enterprises want the **benefits of blockchain** (auditability, automation, instant reconciliation) **without the drama** (vendor lock-in, privacy leaks, “blockchain theater”). ChainBridge is the practical middle layer that:
- **Ingests events** from legacy + modern systems (EDI 945/856, APIs, webhooks) via the **Unifier** (powered by SEEBURGER BizHub).
- **Attaches verifiable proofs** (verifiable compute / zk attestations) to each event.
- **Executes policy** to **settle payments** and/or **actuate** off-chain/on-chain systems.
- **Writes clean audit trails** your auditors will actually accept.

**Mantra:**  
*Speed without proof gets blocked. Proof without pipes doesn’t scale. Pipes without cash don’t settle. You need all three.*

**PoC Corridor:** USD→MXN with targets: **P95 < 90s**, **STP ≥ 95%**, **audit prep time −80%**.

---

## What It Does
- **Tokenize shipments** → create a **FreightToken** with immutable metadata + proofs + risk context.
- **Score operational risk** via **ChainIQ** (ML engine) to shape holdbacks & payment timing.
- **Prove data lineage** via **Space and Time** (verifiable compute / zk proofs).
- **Settle cash** on **Ripple/XRPL** (pluggable rails later) with **policy-driven milestone releases**.
- **Actuate off-chain systems** with **Chainlink** jobs or direct adapters.
- **Reconcile + report** back to ERP/TMS with artifacts suitable for compliance.

---

## Architecture

```mermaid
flowchart LR
    A[Enterprise Systems\nERP / TMS / WMS] -->|EDI 945/856, API| U[Unifier (BizHub)]
    U --> C[ChainBridge Core]
    C -->|Tokenize| CF[ChainFreight API]
    C -->|Risk| IQ[ChainIQ ML Scoring]
    C -->|Proof| SxT[Space & Time\nVerifiable Compute / zk]
    C -->|Actuate| CL[Chainlink\nJobs/EA]
    C -->|Settle| XRPL[Ripple / XRPL]
    C -->|Notify| AUD[Audit Store\nERP/TMS Receipts]
    CF -->|FreightToken + Proofs + Risk| 
Here you go—one complete README.md you can paste as-is:

# ChainBridge

> **Verifiable freight + programmable payments for enterprise supply chains.**  
> Pipe real-world events (EDI/API) through proofs and policies, then settle cash—automatically.

[![Status](https://img.shields.io/badge/status-early%20alpha-orange)](#)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](#license)
[![Built for](https://img.shields.io/badge/domain-Logistics%20%7C%20Fintech%20%7C%20RWA-black)](#)
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-lightgrey)](#)

---

## Table of Contents
- [Why ChainBridge](#why-chainbridge)
- [What It Does](#what-it-does)
- [Architecture](#architecture)
- [Canonical Flows](#canonical-flows)
- [Modules](#modules)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API (ChainFreight)](#api-chainfreight)
- [Milestone Payments (ChainPay)](#milestone-payments-chainpay)
- [Observability & Ops](#observability--ops)
- [Security & Compliance](#security--compliance)
- [Enterprise Readiness Matrix](#enterprise-readiness-matrix)
- [Roadmap (30/60/90)](#roadmap-306090)
- [Repository Layout](#repository-layout)
- [Contributing](#contributing)
- [License](#license)

---

## Why ChainBridge
Enterprises want the **benefits of blockchain** (auditability, automation, instant reconciliation) **without the drama** (vendor lock-in, privacy leaks, “blockchain theater”). ChainBridge is the practical middle layer that:
- **Ingests events** from legacy + modern systems (EDI 945/856, APIs, webhooks) via the **Unifier** (powered by SEEBURGER BizHub).
- **Attaches verifiable proofs** (verifiable compute / zk attestations) to each event.
- **Executes policy** to **settle payments** and/or **actuate** off-chain/on-chain systems.
- **Writes clean audit trails** your auditors will actually accept.

**Mantra:**  
*Speed without proof gets blocked. Proof without pipes doesn’t scale. Pipes without cash don’t settle. You need all three.*

**PoC Corridor:** USD→MXN with targets: **P95 < 90s**, **STP ≥ 95%**, **audit prep time −80%**.

---

## What It Does
- **Tokenize shipments** → create a **FreightToken** with immutable metadata + proofs + risk context.
- **Score operational risk** via **ChainIQ** (ML engine) to shape holdbacks & payment timing.
- **Prove data lineage** via **Space and Time** (verifiable compute / zk proofs).
- **Settle cash** on **Ripple/XRPL** (pluggable rails later) with **policy-driven milestone releases**.
- **Actuate off-chain systems** with **Chainlink** jobs or direct adapters.
- **Reconcile + report** back to ERP/TMS with artifacts suitable for compliance.

---

## Architecture

```mermaid
flowchart LR
    A[Enterprise Systems\nERP / TMS / WMS] -->|EDI 945/856, API| U[Unifier (BizHub)]
    U --> C[ChainBridge Core]
    C -->|Tokenize| CF[ChainFreight API]
    C -->|Risk| IQ[ChainIQ ML Scoring]
    C -->|Proof| SxT[Space & Time\nVerifiable Compute / zk]
    C -->|Actuate| CL[Chainlink\nJobs/EA]
    C -->|Settle| XRPL[Ripple / XRPL]
    C -->|Notify| AUD[Audit Store\nERP/TMS Receipts]
    CF -->|FreightToken + Proofs + Risk| C


⸻

Canonical Flows

A) Payment Settlement Path

sequenceDiagram
    participant ERP as ERP/TMS/WMS
    participant U as Unifier (BizHub)
    participant CB as ChainBridge
    participant IQ as ChainIQ
    participant SxT as Space&Time
    participant XRPL as Ripple/XRPL
    participant AUD as Audit Store

    ERP->>U: EDI 945/856 (shipment events)
    U->>CB: Normalized event (JSON)
    CB->>IQ: Request risk_score
    IQ-->>CB: risk_score, category, recommended_action
    CB->>SxT: Generate proof (event lineage)
    SxT-->>CB: Verification artifact
    CB->>XRPL: Milestone settlement (policy-weighted)
    XRPL-->>CB: TxID, confirmation
    CB->>AUD: Token + proof + risk + tx receipts
    CB-->>U: Status + artifacts for ERP/TMS

B) On-Chain/Off-Chain Actuation

sequenceDiagram
    participant EVT as External Event
    participant CB as ChainBridge
    participant SxT as Space&Time
    participant CL as Chainlink
    participant SYS as Target System

    EVT->>CB: Trigger (rule/threshold)
    CB->>SxT: Request attestations
    SxT-->>CB: Proof bundle
    CB->>CL: Job call w/ proof
    CL->>SYS: API/adapter invocation
    SYS-->>CB: Ack


⸻

Modules
	•	ChainFreight — Shipment + tokenization service (FastAPI).
FreightToken includes: risk_score, risk_category, recommended_action, proof refs, event history.
	•	ChainIQ — ML risk scoring client + policy adapters.
Features (lane, carrier history, delays, claims, geofencing…) → returns 0–100 risk_score.
	•	ChainPay — Event-driven, milestone-based payments.
Default release: 20% / 70% / 10% (Pickup / Transit / Delivery), dynamically adjusted by risk.
	•	Connectors — Unifier inbound (EDI/API), ERP/TMS return adapters, Chainlink jobs, XRPL settlement.

⸻

Quick Start

Prerequisites
	•	Docker + Docker Compose
	•	Python 3.11 (for local dev), Node 20+ (for future UI)
	•	XRPL testnet wallet (PoC), Space and Time credentials, optional Chainlink node

Run the stack

git clone https://github.com/BIGmindz/ChainBridge.git
cd ChainBridge

# Create env from template and fill in values
cp .env.example .env

# Start
docker compose up -d

# Logs
docker compose logs -f

Default services:
	•	chainfreight-api : FastAPI → http://localhost:8080
	•	chainpay-worker : Background worker (Celery/RQ)
	•	postgres : Primary DB
	•	redis : Queue + cache

⸻

Configuration

Create .env (see .env.example):

# Core
APP_ENV=dev
APP_SECRET=change_me
DATABASE_URL=postgresql+psycopg2://chainbridge:chainbridge@postgres:5432/chainbridge
REDIS_URL=redis://redis:6379/0

# Integrations
UNIFIER_INBOUND_TOKEN=...      # inbound auth for Unifier (BizHub)
CHAINIQ_URL=https://chainiq.local/api
CHAINIQ_API_KEY=...

# Space & Time (SxT)
SXT_ENDPOINT=https://api.spaceandtime.dev
SXT_API_KEY=...

# Chainlink (optional)
CHAINLINK_NODE_URL=https://chainlink.node
CHAINLINK_JOB_ID=...
CHAINLINK_ACCESS_KEY=...
CHAINLINK_SECRET=...

# XRPL (Ripple)
XRPL_NETWORK=testnet
XRPL_SEED=...
XRPL_WALLET_ADDRESS=...

# Policy
DEFAULT_RELEASE_WEIGHTS=0.2,0.7,0.1
RISK_WEIGHT_MAX_DELTA=0.15


⸻

API (ChainFreight)

Base URL (local): http://localhost:8080

Create Shipment

curl -X POST http://localhost:8080/shipments \
  -H "Content-Type: application/json" \
  -d '{
    "reference_id": "XPO-12345",
    "origin": "Erie, PA",
    "destination": "Monterrey, MX",
    "carrier": "CarrierXYZ",
    "value_usd": 125000
  }'

Tokenize Shipment (auto-scores risk + attaches proof)

curl -X POST http://localhost:8080/shipments/{shipment_id}/tokenize

Response (abridged):

{
  "freight_token_id": "ftok_01HF...",
  "risk_score": 18,
  "risk_category": "LOW",
  "recommended_action": "PROCEED",
  "proof_ref": "sxt://proof/0xabc...",
  "status": "TOKENIZED"
}

List Tokens

curl http://localhost:8080/tokens

Retrieve Token

curl http://localhost:8080/tokens/{freight_token_id}


⸻

Milestone Payments (ChainPay)

Default policy: Pickup 20%, Transit 70%, Delivery 10%.
Weights adjust with risk_score (0 = safest, 100 = riskiest):
	•	Let W = [0.2, 0.7, 0.1] and Δ = min(RISK_WEIGHT_MAX_DELTA, risk_score/100 * RISK_WEIGHT_MAX_DELTA).
	•	We pull weight from earlier milestones toward final delivery as risk increases.

Example: risk_score = 40, RISK_WEIGHT_MAX_DELTA = 0.15 → Δ = 0.06
Adjusted: Pickup 0.14, Transit 0.64, Delivery 0.22.

Settlement produces XRPL tx receipts stored with the token + proof bundle for audit.

⸻

Observability & Ops
	•	Structured logs with correlation IDs per shipment/token.
	•	Metrics: STP rate, P50/P95 settlement time, risk-adjusted release deltas, proof latency.
	•	Dashboards: /ops/health, /ops/metrics (Prometheus); Grafana in /infra/observability/.
	•	Retries & Idempotency: all external calls are idempotent; payments guarded by once-only locks.
	•	Backpressure: queue depth thresholds auto-throttle ingestion.

⸻

Security & Compliance
	•	Data minimization: tokenize only what’s required; PII stays in source systems.
	•	Proof-first posture: verifiable artifacts attached to every settlement decision.
	•	Secrets: 12-factor env, vault-ready; key rotation; KMS/HSM recommended in prod.
	•	Tenant isolation: per-tenant namespaces and DB schemas; audited RBAC.
	•	Standards: SOC 2, ISO 27001, GDPR-aware logging and export.
	•	Kill-switch: policy-enforced safe holds on anomalies (carrier bans, lane alerts, claims spikes).

⸻

Enterprise Readiness Matrix

Concern (Typical Blocker)	ChainBridge Answer
Scalability / Throughput	Event-driven, horizontally scalable workers; queue-backed; P95 < 90s target in PoC.
Privacy / Data Leakage	Proofs, not raw data; selective hashing; minimal on-chain footprint; private connectors.
Interoperability	Unifier covers EDI/APIs; Chainlink bridges on/off-chain; pluggable rails (XRPL first).
Governance & Control	Enterprise-owned policy; approvals/holds; RBAC with full audit trails.
Vendor Lock-in	Interface-driven adapters; swap rails (XRPL/ACH/SEPA), proof providers, risk models.
Auditability	Proof bundle + tx receipts + normalized event history; export packs for auditors.
Cost & ROI	STP ↑, dispute time ↓, DSO ↓, audit prep −80%; risk-weighted holds reduce loss severity.
Change Mgmt	Non-disruptive: sits beside ERP/TMS; cutover by lane/carrier; feature flags + rollback.


⸻

Roadmap (30/60/90)

Day 0–30
	•	ChainFreight v1 (tokenize/list/get) ✅
	•	ChainIQ client integration ✅
	•	SxT proof stub + artifact storage
	•	XRPL testnet settlement path (Pickup/Transit/Delivery)
	•	Ops: health checks, Prometheus metrics

Day 31–60
	•	Dynamic risk-weighted release policy (Δ) ✅ + config
	•	Chainlink job for external actuation
	•	ERP/TMS adapters for receipts + artifacts
	•	Audit bundle export (zip of proofs/tx/logs)
	•	Hardening: idempotent tx & double-spend guards

Day 61–90
	•	Multi-corridor support (USD→MXN→EUR)
	•	SLA guardrails (auto-hold, human-in-loop review)
	•	Tenant isolation & RBAC
	•	DR/BCP playbooks + chaos drills
	•	Performance: load tests toward >100 TPS equivalent event throughput

⸻

Repository Layout

.
├─ apps/
│  ├─ chainfreight-api/        # FastAPI service (shipments, tokenization)
│  ├─ chainpay-worker/         # Milestone settlement, XRPL integration
│  └─ chainiq-client/          # Risk scoring client + adapters
├─ connectors/                 # Unifier/ERP adapters, Chainlink EA, etc.
├─ contracts/                  # On-chain job specs / interfaces (if used)
├─ infra/
│  ├─ docker/                  # Dockerfiles, compose, dev containers
│  ├─ k8s/                     # Helm charts, manifests
│  └─ observability/           # Prometheus, Grafana, alerts
├─ docs/                       # ADRs, diagrams, runbooks
├─ tests/                      # Unit + integration tests
├─ .env.example
├─ docker-compose.yml
├─ Makefile
└─ README.md


⸻

Contributing

We use a standard trunk-based flow:

# Create a feature branch
git checkout -b feat/risk-weighting

# Run checks
make lint test

# Commit
git commit -m "feat(chainpay): dynamic risk-weighting on milestones"

# Push & PR
git push origin feat/risk-weighting

	•	Style: Python (ruff + black), Typescript (eslint + prettier)
	•	Tests: pytest -q (unit), docker compose -f compose.test.yml up (integration)
	•	Security: run make sec (bandit/trivy) before opening a PR
	•	Docs: update /docs and this README when behavior changes

⸻

License

Apache-2.0 (see LICENSE). For partner deployments that require different terms, open an issue to discuss.

⸻

Notes for Maintainers
	•	Default corridor is USD→MXN; override via env.
	•	Risk policy is configurable per lane/carrier.
	•	If ChainIQ is unavailable, tokenization degrades gracefully: risk_score=null, policy falls back to conservative releases.
	•	External calls are idempotent; settlement includes double-spend guardrails.

⸻

Contact / Maintainers:
ChainBridge Team — BIGmindz / Benson CTO
Issues → GitHub Issues • Security disclosures → security@yourdomain.tld (PGP preferred)

⸻

No blockchain theater. Real pipes. Real proof. Real cash.

