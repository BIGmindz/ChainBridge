# Quantum-Ready Checklist for ChainBridge

> Goal: Make ChainBridge/ChainIQ/ChainPay/ChainScore *future-proof* for advanced AI and quantum optimizers by enforcing clean IDs, append-only event history, explainable decisions, policy-driven incentives, and crypto agility.

---

## 0. Scope & Principles

- **Scope:** ChainBridge core (ChainIQ, ChainPay, ChainScore, ChainBoard, ChainSense, ProofPack).
- **Principles:**
  - Single source of truth for IDs and vocab.
  - Everything important is an **event**.
  - Every decision is **replayable and explainable**.
  - Incentives are defined as **policies**, not hard-coded.
  - Proof and crypto are **abstracted**, not scattered.
  - All intelligence is exposed via **stable APIs**.

---

## 1. Canonical IDs & Ontology

**Objective:** Every entity in the system has a stable, canonical identifier and standard enums, so AI/quantum solvers see a clean graph, not a mess.

**Canonical IDs (must exist and be used everywhere):**

- `shipment_id`
- `shipment_leg_id`
- `carrier_id`
- `shipper_id`
- `facility_id` (port, ramp, DC, airport, rail ramp)
- `corridor_id` (e.g., `US-PA__MX-NL__OCEAN`, `US-PA__US-TX__TRUCK_FTL`)
- `event_id`
- `proof_id`
- `payment_id`
- `score_snapshot_id` (ChainScore snapshots)

**Standard enums (no free-text):**

- Modes:
  - `TRUCK_FTL`, `TRUCK_LTL`, `OCEAN`, `AIR`, `RAIL`, `INTERMODAL`
- Shipment statuses:
  - `PLANNED`, `IN_TRANSIT`, `AT_FACILITY`, `DELAYED`, `DELIVERED`, `CANCELLED`, `EXCEPTION`
- Milestones (event types):
  - `PICKUP_CONFIRMED`, `GATE_IN`, `LOADED_ON_VESSEL`, `VESSEL_DEPARTED`, `VESSEL_ARRIVED`, `DISCHARGED`, `OUT_FOR_DELIVERY`, `POD_CONFIRMED`, etc.
- Risk levels:
  - `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
- Payment statuses:
  - `SCHEDULED`, `RELEASED`, `ON_HOLD`, `DISPUTED`, `CANCELLED`

**Checks:**

- [ ] Single schema/module defines IDs + enums for backend (e.g., `api/models/common_ids.py` or similar).
- [ ] All services (ChainIQ, ChainPay, ChainScore, ProofPack) use these IDs/enums instead of service-local variants.
- [ ] Frontend types mirror these enums exactly (no drift).

**Owner:** Cody (backend IDs & models) + Sonny (frontend types & use).

---

## 2. Global Event Log & Replay

**Objective:** Treat the system as an event-sourced network. Every important change is an event that can be replayed.

**Event families:**

- `ShipmentEvent` – lifecycle + movements
- `RiskEvent` – risk score changes, alerts created/resolved
- `IoTEvent` – GPS pings, temp readings, shocks, door events
- `PaymentEvent` – payouts scheduled/released/held
- `ScoreEvent` – ChainScore updates for carriers/lanes/facilities

**Minimum fields for any event:**

- `event_id` (UUID)
- `event_type` (enum)
- `shipment_id` (optional but required for shipment-scoped events)
- `shipment_leg_id` (where applicable)
- `actor` (`SYSTEM`, `OPERATOR`, `CARRIER`, etc.)
- `source_service` (`CHAINIQ`, `CHAINPAY`, `CHAINBOARD`, `CHAINSENSE`, etc.)
- `occurred_at` (real-world time)
- `recorded_at` (when we wrote it)
- `payload` (JSON with typed content)

**Checks:**

- [ ] Central event model(s) exist (DB + schemas).
- [ ] ChainIQ, ChainPay, ChainScore all emit normalized events into this log.
- [ ] It is possible to reconstruct **a single shipment's entire story** from these events alone.
- [ ] Operator actions from the Operator Console (e.g., snapshot export, payment override) emit events.

**Owner:** Cody.

---

## 3. ChainIQ: Risk Decisions & Features

**Objective:** Make every risk score explainable and re-trainable.

For each risk scoring decision:

- Store a `RiskDecision` record with:
  - `decision_id`
  - `shipment_id`
  - `risk_score` (numeric)
  - `risk_level` (`LOW`/`MEDIUM`/`HIGH`/`CRITICAL`)
  - `model_version` or `rule_version`
  - `features` (JSON: dwell_time, port_congestion_index, days_late, etc.)
  - `decided_at`

**Checks:**

- [ ] ChainIQ persists risk decisions with feature snapshots (not just the final score).
- [ ] Feature building lives in a dedicated module (no scattered ad-hoc logic).
- [ ] It is possible to query: "Show me all decisions for shipment X, with features and outcomes."

**Owner:** Cody.

---

## 4. ChainPay & ChainScore: Policy-First Design

**Objective:** Incentives (payments and scores) are defined by data/policies, not hard-coded logic, so we can simulate and optimize them later.

### Payout policies (ChainPay):

Represent payout rules as:

- `payout_policy_id`
- `name`
- `version`
- `rules` (JSON structure for milestones, percentages, holds, risk thresholds)
- `effective_from`, `effective_to`

No "magic numbers" buried in code.

### ChainScore formula:

- `score_policy_id`
- Weights for:
  - On-time performance
  - Claims/damage rate
  - Data quality (ping coverage, milestone completeness)
  - Responsiveness (exception response time)
- Decay over time (recent performance weighted more).

**Checks:**

- [ ] ChainPay payout rules live in DB/config and are versioned.
- [ ] ChainScore calculation pulls weights from a policy table/config, not inline constants.
- [ ] It is possible to simulate "what if we change weight X?" without a deploy.

**Owner:** Cody.

---

## 5. Crypto & Proof Abstraction (ProofPack)

**Objective:** Be able to swap hashes/signatures and chains without touching business logic.

**Abstractions:**

Create a single proof/crypto module with:

- `sign_proof(proof_bytes, algorithm_version) -> signature`
- `verify_proof(proof_bytes, signature, algorithm_version) -> bool`
- `hash_proof(proof_bytes, hash_algorithm_version) -> hash`

**Proof metadata:**

Each ProofPack stored with:

- `proof_id`
- `hash_algorithm` (e.g., `SHA256`, `SHA3_256`)
- `signature_scheme` (e.g., `ECDSA_secp256k1`)
- `version`
- `chain_reference` (optional: tx hash, chain id)
- `created_at`

**Checks:**

- [ ] All signing/hashing runs through a single internal interface.
- [ ] Proof records include which algorithms were used.
- [ ] The system can support dual-anchoring (classical + PQ-safe) without major refactor in future.

**Owner:** Cody.

---

## 6. Optimization Interfaces (AI / Quantum)

**Objective:** Define stable contracts between ChainBridge and future optimizers.

### Optimization Input (for external solver):

A logical schema like:

- Network state snapshot:
  - Lanes, capacities, current shipments
  - Carrier attributes and ChainScore
  - Constraints (SLAs, costs, legal)
- Objective:
  - Minimize cost / delay / risk / CO2 / some combination
- Time horizon:
  - Planning window

### Optimization Output:

- Route assignments:
  - Which carrier gets which shipment, on which lane/mode
- Policy suggestions:
  - Adjusted payout/score weights
- Recommended holds / reroutes.

**Checks:**

- [ ] We have a documented schema (JSON/OpenAPI) for "optimization input" and "optimization output".
- [ ] Backend can generate a consistent, self-contained snapshot from live DB.
- [ ] Backend can ingest optimization results and implement them via ChainIQ/ChainPay/ChainScore without manual hacking.

**Owner:** Cody.

---

## 7. Data Governance & Privacy for ChainScore

**Objective:** Make ChainScore sellable and safe as a product.

**Requirements:**

- Clear separation between:
  - Raw shipment data
  - Aggregated performance metrics
  - ChainScore outputs
- No PII or sensitive contract data leaks into external APIs.
- Ability to:
  - Export per-carrier or per-lane performance safely.
  - Honor contractual limits on data sharing.

**Checks:**

- [ ] ChainScore API only returns aggregated, non-sensitive metrics.
- [ ] There is a clear map of what data can/cannot be shared externally.
- [ ] Logging/audit controls around who queries what.

**Owner:** Cody (with product/legal input later).

---

## 8. Frontend / UX Constraints (Sonny)

**Objective:** ChainBoard (UI) remains a thin, reliable client on top of the brains, not a place where business logic gets buried.

**Rules:**

- All scores, risk levels, payout statuses, and policies come from backend APIs.
- No business rules duplicated in frontend (e.g., no homegrown risk scoring).
- Enums and IDs in TypeScript mirror backend exactly (single source of truth).
- Shipment Journey and Operator Console:
  - Consume event streams / risk decisions / scores via API contracts.
  - Never compute "final truth" locally, only visualize.

**Checks:**

- [ ] Frontend types (`chainbridge.ts`) are aligned with canonical enums/IDs.
- [ ] Any "if risk > X do Y" logic is backend-driven and provided as flags/fields.
- [ ] New visualizations (e.g., Journey map, HUDs, badges) are driven by stable, documented API responses.

**Owner:** Sonny.

---

## 9. Observability & Performance

**Objective:** Ensure that as we add AI/quantum, the platform remains observable and performant.

**Checks:**

- [ ] Key endpoints (Operator Console, scoring, payments) have SLOs and monitoring.
- [ ] We can track latency and error rates by service.
- [ ] We can trace a single shipment across services via IDs.

**Owner:** Cody (infra) + Sonny (UI error handling).

---

## Status Tracking

Use this section to track progress:

- [ ] 1. Canonical IDs & Ontology
- [ ] 2. Global Event Log & Replay
- [ ] 3. ChainIQ: Risk Decisions & Features
- [ ] 4. ChainPay & ChainScore: Policy-First Design
- [ ] 5. Crypto & Proof Abstraction
- [ ] 6. Optimization Interfaces
- [ ] 7. Data Governance & Privacy
- [ ] 8. Frontend / UX Constraints
- [ ] 9. Observability & Performance

---

## Notes

- **Last Updated:** 2025-11-19
- **Version:** 1.0
- **Status:** Ready for Implementation Review
