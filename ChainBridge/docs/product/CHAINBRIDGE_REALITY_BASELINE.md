# ChainBridge Reality Baseline

Last updated: 2025-11-26
Owner: Benson (CTO)
Source of truth for all AI agents and wraps.

**Governance Pointers:** See `docs/governance/ALEX_TOOL_GOVERNANCE_V1.md` (tool/auto-approve policy), `docs/governance/ALEX_MCP_POLICY_V1.md` (MCP onboarding/review), and the settings.json governance appendix in this file for required VS Code / Copilot defaults. All agents must log changes in `docs/governance/AGENT_ACTIVITY_LOG.md`.

---

## 1. Current Phase

## Governance: Tools, MCP, and Agents
- All tool usage (terminal, file edits, MCP servers) by ChainBridge agents must follow the ALEX governance docs: `docs/governance/ALEX_TOOL_GOVERNANCE_V1.md` (tool/auto-approve policy) and `docs/governance/ALEX_MCP_POLICY_V1.md` (MCP onboarding/review).
- Cody, Sonny, Cindy, Pax, Maggie, and all future agents are expected to apply these policies when using tools or proposing new MCP servers.
- A recommended baseline `settings.json` governance snippet is maintained in `docs/governance/ALEX_TOOL_GOVERNANCE_V1.md` (Appendix); treat it as the default stance unless a newer ALEX PAC says otherwise.

- We are in **Phase: Internal Pilot / Engineering Hardening**, not public launch.
- Scope:
  - Build a credible **Operator Console (OC)** + intel spine.
  - Wire basic **ChainIQ risk** and **ChainPay settlement scaffolding** end-to-end in **local/dev**.
  - Stand up an **AI-native engineering workflow** (PACs + agents) to accelerate delivery.
- No production customers. No live mainnet. No external revenue **yet**.

---

## 2. Module Status (Reality vs Roadmap)

Legend:
- ✅ Implemented (working in repo, locally runnable)
- ⚠️ Partial (scaffolding or mocks; not production-ready)
- 🟥 Roadmap (not built, concepts/spec only)

### 2.1 Operator Console / ChainBoard

- Backend (FastAPI, under `ChainBridge/api`):
  - ✅ Health endpoint, base app wiring.
  - ✅ Shipments, RiskDecisions, PaymentIntents models + DB migrations.
  - ✅ **/chainboard/live-positions**: mock/derived positions + nearest port metrics.
  - ✅ **/intel/global-snapshot**: corridor/mode/port KPIs from live_positions.
  - ✅ Auth layer wired in basic form (not hardened for production).
  - ⚠️ No external TMS/WMS/carrier integration; data is synthetic or seeded.
- Frontend (`ChainBridge/chainboard-ui`):
  - ✅ OC main page with:
    - Queue table (at-risk / pending items).
    - Detail panel with tabs (risk, legal, finance, audit).
    - Global intel / live positions cockpit wired to backend endpoints.
  - ✅ Basic error handling + loading states.
  - ⚠️ Not yet deployed behind a public URL; runs via local dev server only.
  - ⚠️ Visual polish good enough for **internal demo**, not final “investor-grade” yet.

### 2.2 ChainIQ (Risk & Intelligence)

- Service:
  - ✅ Core risk service `chainiq-service` exists with:
    - Scoring endpoint.
    - Storage layer (SQLite) for replay/history.
    - Demo seed script for mock risk scenarios.
  - ✅ L2 replay/persistence implemented (ability to log and replay decisions).
  - ⚠️ Risk logic is largely **rule-based / heuristic**, not true production ML.
  - 🟥 No training on real carrier/shipper historical data.
  - 🟥 No formal ML experimentation/metrics pipeline (AUC, calibration, etc.).

### 2.3 ChainPay (Settlement / Payments)

- Backend:
  - ✅ `chainpay-service/app/payment_rails.py` exists with:
    - Canonical IDs helpers (and fallbacks).
    - Structures for milestone-based payments.
  - ⚠️ No live payment rails integration (no XRPL, no banking API, no DeFi pool).
  - ⚠️ No real money, no production accounting, no ledgers reconciled against banks.
  - 🟥 No regulatory entity set up (no SPV, no lender-of-record, etc.).

### 2.4 ChainSense (IoT / Telemetry)

- Backend:
  - ✅ IoT-related schemas and mock fixture generators (`IoTHealthSummaryResponse`, etc.).
  - ✅ Mock IoT panels on OC side wired to **fake/mock data**.
  - 🟥 No real IoT device ingestion (no Samsara, no telematics hardware, no signed telemetry).
  - 🟥 No on-chain attestation for IoT signals.

### 2.5 ChainFreight (EDI / Ingestion)

- Backend:
  - ✅ Models + mock fixtures to represent shipments/events similar to EDI flows.
  - ⚠️ Some ingestion logic exists, but operates on **mocked data** only.
  - 🟥 No production-grade EDI integration (no live Seeburger BIS hookup, no Project44, etc.).
  - 🟥 No large-scale ingestion performance tuning.

### 2.6 ChainDocs (Ricardian / Audit)

- Backend:
  - ✅ Schemas for legal wrapper concepts (Ricardian-like).
  - ✅ Fields to store wrapper status and some audit attributes.
  - ⚠️ No external doc hashing/verification services (IPFS, SxT, or banks) wired.
  - 🟥 No public “Check My BOL” verification endpoint/page.

### 2.7 Crypto / Trading Bot (Legacy / Non-Core)

- `ChainBridge/legacy/legacy-benson-bot/*`:
  - ✅ Contains trading bot ML/RSI experiments and infra.
  - ⚠️ Not wired into ChainBridge core flows.
  - 🟥 No active trading associated with ChainBridge P&L yet.
- Crypto-1.0, Kraken, etc. are **separate R&D**, not production revenue for ChainBridge today.

---

## 3. AI Workforce Reality

- Agents (conceptual roles): Sonny (FE), Cody (BE), Dan (DevOps), Pax (protocol), Sam/Sand (security), Mira (governance), Research Benson, etc.
- Reality:
  - ✅ We have **prompt packs and docs** describing these roles.
  - ✅ You (John) manually copy/paste PACs into different tools (ChatGPT, Gemini, Claude, Codex, etc.).
  - ⚠️ No autonomous multi-agent orchestrator in the repo (no runtime that coordinates them automatically).
  - ⚠️ Quality varies by model; some outputs are aspirational and must be **CTO-reviewed**.
  - 🟥 No formal benchmarks or scoring system for agent output quality yet.

---

## 4. Engineering Maturity

- Testing:
  - ✅ Unit tests for core services (API, intel, some agents, RSI scenarios).
  - ✅ Pre-commit: ruff, formatting, quick-checks.
  - ⚠️ E2E flows not fully covered (OC → backend → DB → mock “chain”).
- CI/CD:
  - ✅ GitHub Actions workflows for tests, linting, some ALEX governance checks.
  - ⚠️ Some workflows still carry legacy naming (e.g. trading-bot CI).
  - ⚠️ Deployment pipeline to a real staging environment is **not** fully in place.

---

## 5. Business Reality

- Customers:
  - No paying customers.
  - No live pilots with real customer data **yet**.
- Market Position:
  - Strong narrative + architecture for tokenized supply chain + settlements.
  - Still in **prototype / pilot-prep** stage.
- Revenue:
  - $0 in realized revenue from ChainBridge.
- Capital:
  - No external investors committed yet (friends/family or institutional).
  - Platform is engineered to be **fundable**, but **not yet funded**.

---

## 6. ChainBridge Mantra (for all agents)

- **Robust**: Enterprise-grade, no toys, no hacky shortcuts for core flows.
- **Radical**: Bold architecture and product decisions, but still grounded in reality.
- **Scalable**: Design for multi-tenant, high-volume, many-corridor future.
- **Secure**: Security-by-default; no “we’ll secure it later” thinking.
- **Commercially Viable**: If it doesn’t make money or save money, it’s deprioritized.

All AI agents must honor this baseline and clearly distinguish:
- What exists in the repo now.
- What is partial work-in-progress.
- What is future roadmap / concept.
