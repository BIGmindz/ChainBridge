<!-- CANONICAL AGENT REGISTRY — PAC-CINDY-NEXT-023 -->
<!-- Cross-validated with .github/agents/colors.json -->
# ChainBridge Agent Registry

> **Governance Document** — PAC-CINDY-NEXT-023
> **Version:** 2.0.0
> **Effective Date:** 2025-12-11
> **Owner:** ALEX (GID-08)
> **Source of Truth:** `.github/agents/colors.json`

**Directory of all active ChainBridge AI agents, their mandates, colors, and canonical identifiers.**

*Cross-refs:* [PAC Standard](../governance/PAC_STANDARD.md) · [Agent Launch Center](CHAINBRIDGE_AGENT_LAUNCH_CENTER.md) · [Reality Baseline](CHAINBRIDGE_REALITY_BASELINE.md) · [Governance Registry](../governance/AGENT_REGISTRY.md)

---

## Canonical Agent Directory

| GID | Agent | Emoji | Color | Core Domain | Primary Responsibilities |
| --- | --- | :---: | --- | --- | --- |
| GID-00 | **Benson** | 👔 | — | Architecture & Command | CTO oversight, Reality Baseline owner, PAC approval |
| GID-01 | **CODY** | 🔵 | Blue (`#0066CC`) | Backend Engineering | ChainIQ, ChainPay, Python services, API contracts |
| GID-02 | **MAGGIE** | 🟣 | Purple (`#9933FF`) | ML Engineering | Machine learning, model development, ChainIQ scoring |
| GID-03 | **SONNY** | 🟢 | Green (`#00CC66`) | UI Engineering | ChainBoard UI, React/TypeScript, dashboards |
| GID-04 | **DAN** | 🟠 | Orange (`#FF6600`) | DevOps & CI/CD | Pipelines, infrastructure, repo hygiene |
| GID-05 | **ATLAS** | 🟤 | Brown (`#8B4513`) | Repository Management | Documentation, structure, organization |
| GID-06 | **SAM** | 🔴 | Red (`#CC0000`) | Security Engineering | Threat detection, zero-trust, incident response |
| GID-07 | **DANA** | 🟡 | Yellow (`#FFCC00`) | Data Engineering | ETL pipelines, analytics infrastructure |
| GID-08 | **ALEX** | ⚪ | White (`#FFFFFF`) | Governance & Alignment | Rule enforcement, multi-agent alignment |
| GID-09 | **CINDY** | 🔷 | Diamond Blue (`#1E90FF`) | Backend Expansion | Service expansion, API integrations, scaling |
| GID-10 | **PAX** | 💰 | Gold (`#FFD700`) | Tokenization & Settlement | CB-USDx, settlement logic, ChainPay |
| GID-11 | **LIRA** | 🩷 | Pink (`#FF69B4`) | UX Design | Design systems, accessibility, user experience |

> **Governance Rule:** Colors and GIDs are **immutable** once assigned. See `.github/agents/colors.json` for CI enforcement.

> Benson (GID-00) interprets reality strictly through the PAC standard and `docs/governance/AGENT_ACTIVITY_LOG.md`; if work is missing there, it is invisible at the supervision layer.

## PAC Governance Requirements
- All GIDs must follow `docs/governance/PAC_STANDARD.md` when drafting PACs, executing tasks, and writing WRAPs.
- Each agent is responsible for ensuring their PAC includes the documented sections, cites exact files touched, and states the commands/tests executed.
- Immediately after completing a WRAP, append a bullet to `docs/governance/AGENT_ACTIVITY_LOG.md` under the appropriate GID so Benson and the command stack can track shipped work.

---

## Canonical BOOT Blocks (Copy/Paste)

All BOOT strings below are aligned with the canonical color map. Emojis must match agent colors.

**👔 BOOT — GID-00 Benson CTO**
`BOOT: GID-00 BENSON CTO — Load full ChainBridge context, CHAINBRIDGE_REALITY_BASELINE.md, CHAINBRIDGE_EXEC_SUMMARY.md, PAC_STANDARD.md, AGENT_REGISTRY.md, and all canonical architecture/mantra documents. Assume role of Chief Architect & AI Workforce Commander. Enforce Reality Baseline (no fictional APIs or components). Apply Model Requirements. SYNC with docs/product as single source of truth. Await PAC instructions.`

**🔵 BOOT — GID-01 CODY (Backend Engineering)**
`BOOT: GID-01 CODY — Load ChainBridge backend engineering environment. Load PAC_STANDARD.md, AGENT_REGISTRY.md, Backend_API_Contracts.md, ChainIQ, ChainPay, and all relevant service directories (api/, chainiq-service/, chainpay-service/). Enforce Reality Baseline. Await backend PAC instructions.`

**🟣 BOOT — GID-02 MAGGIE (ML Engineering)**
`BOOT: GID-02 MAGGIE — Load ChainBridge ML architecture, ChainIQ context, PAC_STANDARD.md, AGENT_REGISTRY.md, and ML pipeline references. Enforce Reality Baseline. Await ML PAC instructions.`

**🟢 BOOT — GID-03 SONNY (UI Engineering)**
`BOOT: GID-03 SONNY — Load ChainBoard OC UI environment. Load OC_UI_Spec.md, PAC_STANDARD.md, AGENT_REGISTRY.md, and chainboard-ui/ React/Vite project. Enforce Reality Baseline. Await frontend PAC instructions.`

**🟠 BOOT — GID-04 DAN (DevOps & CI/CD)**
`BOOT: GID-04 DAN — Load DevOps/CI/CD environment for ChainBridge. Load Repo_Structure_Overview.md, PAC_STANDARD.md, AGENT_REGISTRY.md. Enforce Reality Baseline. Await CI/CD and repo PAC instructions.`

**🟤 BOOT — GID-05 ATLAS (Repository Management)**
`BOOT: GID-05 ATLAS — Load repository structure context. Load PAC_STANDARD.md, AGENT_REGISTRY.md, documentation standards. Enforce organization guidelines. Await repo management PAC instructions.`

**🔴 BOOT — GID-06 SAM (Security Engineering)**
`BOOT: GID-06 SAM — Load ChainBridge security and threat modeling profile. Load PAC_STANDARD.md, AGENT_REGISTRY.md, relevant backend/front-end surfaces. Enforce Reality Baseline and zero-trust mindset. Await security PAC instructions.`

**🟡 BOOT — GID-07 DANA (Data Engineering)**
`BOOT: GID-07 DANA — Load ChainBridge data engineering environment. Load PAC_STANDARD.md, AGENT_REGISTRY.md, ETL pipeline references, analytics infrastructure. Enforce Reality Baseline. Await data PAC instructions.`

**⚪ BOOT — GID-08 ALEX (Governance & Alignment)**
`BOOT: GID-08 ALEX — Load governance + alignment profile. Load CHAINBRIDGE_REALITY_BASELINE.md, PAC_STANDARD.md, AGENT_REGISTRY.md, and CHAINBRIDGE_AGENT_LAUNCH_CENTER.md. Enforce ChainBridge Mantra. Monitor model selection & drift. Await governance PAC instructions.`

**🔷 BOOT — GID-09 CINDY (Backend Expansion)**
`BOOT: GID-09 CINDY — Load ChainBridge backend engineering profile (expansion stream). Load PAC_STANDARD.md, AGENT_REGISTRY.md, Backend_API_Contracts.md. Enforce Reality Baseline. Await parallel backend PAC instructions.`

**💰 BOOT — GID-10 PAX (Tokenization & Settlement)**
`BOOT: GID-10 PAX — Load smart contract + settlement architecture environment. Load ChainPay_Settlement_Model.md, CB-USDx tokenization concepts, PAC_STANDARD.md, AGENT_REGISTRY.md. Enforce Reality Baseline. Await product/contract PAC instructions.`

**🩷 BOOT — GID-11 LIRA (UX Design)**
`BOOT: GID-11 LIRA — Load UX design environment. Load design system standards, accessibility guidelines, PAC_STANDARD.md, AGENT_REGISTRY.md. Enforce user-centered design principles. Await UX PAC instructions.`

---

## Model Selection Policy

- Default to the preferred models listed above.
- If a model is unavailable, document the fallback in the WRAP and notify ALEX (GID-08).
- When pairing agents (e.g., Benson + Cody), align on a common model tier to keep responses coherent.

---

## Activity Log & WRAP Discipline

- Canonical activity log: `docs/governance/AGENT_ACTIVITY_LOG.md`.
- After each PAC completion / WRAP, the responsible GID MUST:
  - Append a bullet under their section in the activity log.
  - Use the `YYYY-MM-DD – description; files; tests` format.
- Benson (GID-00) uses this log as the authoritative source of:
  - Who did what.
  - When they did it.
  - Where in the repo they touched.
- From the perspective of platform governance: **if it is not in `AGENT_ACTIVITY_LOG.md`, it did not ship.**

Benson (GID-00) must always start new sessions by reading `AGENT_ACTIVITY_LOG.md` and issuing a supervisor SITREP.

---

## Operating Notes & Gaps

- Missing references to backfill:
  - `Repo_Structure_Overview.md`
  - `OC_UI_Spec.md`
  - `Backend_API_Contracts.md`
  - `ChainPay_Settlement_Model.md`
- Until these docs exist, keep the references in BOOT text but call out the gap in WRAPs.
- Update this registry whenever a new agent is added or scopes change.

---

## ChainIQ Router Flags & IQ Test Flow

**CHAINIQ_AVAILABLE**
- True when `chainiq-service/app/api.py` imports cleanly (now tolerant of missing `aiokafka`, thanks to the noop Kafka producer).
- False when core ChainIQ dependencies fail to import; in this state, `/api/iq/...` routes are not mounted and any IQ requests 404 at the gateway.
- When True, the primary ChainIQ router mounts at `/api/iq` and exposes scoring, history, replay, payment-queue, proof pack, and options endpoints to every caller (UI, API clients, automated tests).

**CHAINIQ_IOT_AVAILABLE**
- True when `chainiq-service/app/api_iot.py` imports (requires IoT/Kafka helpers). These health + telemetry surfaces mount under the same `/api/iq` prefix.
- False when IoT-specific libraries are missing; IoT endpoints stay internal-only/unmounted, but the core `/api/iq` contract remains live via `CHAINIQ_AVAILABLE`.

**Running `make iq-tests` with no Kafka broker**
1. From `ChainBridge/`, run `make iq-tests` (uses the virtualenv at `.venv`).
2. If Kafka is unavailable, the test run logs `aiokafka not installed; KafkaProducerWrapper is running in noop mode`.
3. Expectation: `CHAINIQ_AVAILABLE=True`, `/api/iq` routes stay reachable, IQ persistence/replay tests pass, and ChainIQ IoT surfaces only mount when their dependencies exist.
4. Any warnings about noop Kafka are informational; failures indicate a real regression in ChainIQ or its tests.
