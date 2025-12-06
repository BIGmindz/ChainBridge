# ChainBridge Audit & ProofPack Specification (v0)

Last updated: 2025-12-06
Owner: ALEX (GID-08) – Governance & Alignment Engine

This document defines what it means for ChainBridge to be **audit-ready by default**, how events and decisions must be logged, and how **ProofPacks** are structured and generated for auditors, compliance teams, and internal reviewers.

---

## 1. Purpose & Scope

### 1.1 Purpose

ChainBridge is a logistics and financial OS that coordinates **Sense → Think → Act** across shipments, risk, and settlement. This spec exists to ensure that:

- External auditors, internal compliance, and regulators can **reconstruct what happened and why** for any shipment, payment, or risk decision.
- Engineers (Cody, Sonny, Dan, Sam, Maggie) have a **concrete target** for event/decision logging and audit-pack generation.
- Audit capabilities are **designed-in**, not added as an afterthought.

### 1.2 Scope

This specification applies to:

- **ChainIQ (Think)** – risk scoring and decision APIs.
- **ChainPay (Act)** – settlement, payout, and CB-USDx flows.
- **Shipment & Context Lifecycle (Sense)** – core events in the context ledger and related services.

It covers:

- Event and decision logging requirements.
- The **ProofPack** concept and structure.
- The conceptual "One-Click Audit" workflow.
- Ownership across agents for implementation and governance.

It does **not** define specific database schemas or API payloads; those will be derived from this spec in follow-on engineering PACs.

### 1.3 Audit Principles

ChainBridge must be **audit-capable by default**. Concretely:

- **Traceability:** Every material decision (risk band assignment, payout release/hold, override) must be traceable from outcome → decision → inputs → policies.
- **Explainability:** There are **no black boxes**: every automated or manual decision exposes a human-readable "why" (rules fired, model version, override justification).
- **Immutability:** Event and decision logs are **append-only**, time-stamped, and protected against tampering.
- **Correlatability:** Logs include correlation IDs (shipment, payment, customer, lane) so that auditors can link events across services.
- **Exportability:** Evidence must be exportable in auditor-friendly formats (CSV, JSON, plus optional HTML/PDF summary views).
- **Least Surprise:** Audit outputs should match what an external auditor expects to see: a clear, chronologically ordered story of what happened.

---

## 2. Event & Decision Log Requirements

This section defines the **minimum fields** and semantics required for ChainBridge audit logs. Future PACs may extend these structures, but must not remove or weaken them.

### 2.1 Event Log (What Happened)

The **Event Log** records *facts* about what occurred in the system, independent of how decisions were made.

For each event associated with a shipment, payment, or related entity, the log MUST capture at least:

- **`event_id`** – unique identifier for the log entry.
- **`event_type`** – machine-readable type, e.g.:
  - `shipment_created`
  - `shipment_status_updated`
  - `context_created`
  - `risk_evaluated`
  - `payout_released`
  - `payout_held`
  - `payout_adjusted`
  - `policy_updated`
- **`timestamp_utc`** – ISO-8601 UTC timestamp when the event was recorded.
- **`actor_type`** – one of `system`, `scheduler`, `user`.
- **`actor_id`** – optional user/service identifier (e.g. `oc_user:123`, `service:chainpay-worker`).
- **`source_system`** – origin of the event, e.g. `edi_ingestor`, `iot_gateway`, `chainiq_service`, `chainpay_service`, `oc_ui`, `api_client`.
- **`correlation_ids`** – structured IDs for linkage, e.g.:
  - `shipment_id`
  - `context_id`
  - `payment_id`
  - `customer_id`
  - `corridor_id`
- **`payload_hash`** – hash (e.g. SHA-256) of the raw payload or key fields; may include a pointer to where raw data is stored, but raw bodies do **not** need to be duplicated here.
- **`metadata`** – opaque JSON for non-critical auxiliary fields (tags, flags, debug info).

Constraints:

- Event logs must be **append-only**: changes to historical records require a new compensating event (e.g. `event_corrected`) with references to the original.
- Timestamps and IDs must be stable enough to support replay and reconstruction in downstream analytics.

### 2.2 Decision Log (Why It Happened)

The **Decision Log** captures *why* a risk or payout decision was made. It is tightly coupled to the Event Log but focuses on decision semantics.

For each decision (automated or manual), the log MUST capture:

- **`decision_id`** – unique identifier for the decision record.
- **`decision_type`** – e.g.:
  - `risk_score`
  - `risk_band_assignment`
  - `payout_decision`
  - `payout_hold`
  - `payout_release`
  - `policy_evaluation`
- **`timestamp_utc`** – ISO-8601 UTC timestamp when the decision was made.
- **`actor_type`** – `system` or `user`.
- **`actor_id`** – system/service ID or user ID/role.
- **`correlation_ids`** – same structure as Event Log (shipment, payment, context, customer, corridor).
- **`inputs_snapshot`** – structured or hashed snapshot of the key inputs used to make the decision, such as:
  - Risk features (e.g. lane volatility, prior dispute count).
  - IoT health indicators (e.g. `signal_confidence`, temperature band status).
  - Monetary amounts, currency, corridor.
  - Current policy configuration (IDs only; full policy captured separately).
- **`output`** – the decision outcome, e.g.:
  - `risk_score`: numeric.
  - `risk_band`: `LOW` / `MEDIUM` / `HIGH` / `CRITICAL`.
  - `payout_action`: `approve`, `hold`, `reject`, `partial`.
  - `payout_plan`: reference to a payout schedule (e.g. `20/70/10`) and adjustments.
- **`policy_version_ids`** – references to policies/models in force at decision time, such as:
  - `risk_policy_version`
  - `payout_policy_version`
  - `payout_matrix_version`
  - `model_version` (for ML-driven decisions)
- **`explanations`** – structured explanation fields:
  - For rules: list of `rule_ids` that fired (true) and optionally those evaluated false.
  - For models: pointer to an explanation artifact (e.g. feature importance summary, SHAP report ID).
- **`linked_event_ids`** – list of associated `event_id`s (e.g. the `risk_evaluated` event that triggered this decision).

Constraints:

- Every **payout** and **risk** decision must have exactly one primary decision log entry linking to relevant events.
- Decision logs must be stable and reconstructable – enough detail to answer: "Given these inputs and policies, why did the system choose this outcome?"

### 2.3 Overrides & Exceptions

Manual overrides and exceptions are **first-class** audit entities, not ad hoc notes.

For each override:

- **`override_id`** – unique identifier.
- **`original_decision_id`** – reference to the automated decision being overridden.
- **`new_decision`** – same structure as `output` in the Decision Log, plus any changed policy references.
- **`actor_id` / `actor_role`** – user performing the override (e.g. `compliance_officer`, `senior_risk_analyst`).
- **`timestamp_utc`** – when the override was applied.
- **`justification`** – **mandatory free-text** explanation.
- **`supporting_evidence_refs`** – pointers to documents, IoT snapshots, or external tickets (optional, but recommended).

Overrides MUST:

- Be logged as **separate decision entries**, not edits to the original.
- Preserve a clear before/after view for auditors.

---

## 3. ProofPack Specification

### 3.1 What Is a ProofPack?

A **ProofPack** is a self-contained, exportable audit bundle that captures the full story for:

- A single shipment or payment (most common case), or
- A scoped time window and filter (e.g. monthly audit for a specific customer/corridor).

It is designed to be:

- **Machine-readable** for automated checks and analytics.
- **Human-readable** for auditors and compliance officers.
- **Portable** so it can be shared securely outside the core system.

### 3.2 ProofPack Contents (Per Shipment/Payment)

At minimum, a ProofPack for a shipment or payment SHOULD contain:

- **`summary`** (e.g. `summary.json` or `summary.yaml`):
  - Key identifiers: shipment, context, payment, customer, corridor.
  - Final outcome: fully paid / partially paid / held / rejected.
  - High-level risk trajectory: initial risk band → final risk band.
  - Counts: number of events, decisions, overrides.
  - Generation metadata: timestamp, generator version, requesting user.

- **`events`** (e.g. `events.csv`):
  - Flattened event log entries related to the scope, sorted by time.

- **`decisions`** (e.g. `decisions.csv`):
  - Decision log entries and overrides, sorted by time.

- **`policies`** (e.g. `policies.json`):
  - Snapshot or references (IDs + hashes) for policies and payout matrices active during the period.

- **`proofs`** (e.g. `proofs.json`):
  - Hashes of key artifacts (payloads, documents, IoT snapshots, policy definitions).
  - Optional reference to on-chain anchors (XRPL, SxT) if/when wired.

- **`attachments/`** (optional subdirectory):
  - Binary or rendered artifacts (e.g. POD PDFs, HTML summaries, charts) as needed in later versions.

### 3.3 Formats

Minimum baseline formats:

- **Structured data:**
  - `summary.json` or `summary.yaml`
  - `events.csv`
  - `decisions.csv`
  - `policies.json`
  - `proofs.json`
- **Optional human-friendly:**
  - `summary.html` or PDF export for non-technical reviewers.

ProofPacks SHOULD be delivered as a **single ZIP archive** containing the structured files and optional attachments.

### 3.4 Immutability & Integrity

- Each ProofPack ZIP MUST have a deterministic **bundle hash** (e.g. SHA-256 over ordered contents).
- The hash SHOULD be stored in:
  - An internal audit ledger table, and/or
  - An external anchoring mechanism (e.g. XRPL memo, SxT or similar), when available.
- Regeneration of the same scope with the same inputs/policies should ideally produce the **same hash**, or record a clear version bump if policies or data changed.

Anchoring details (e.g. XRPL transaction formats) are **future work**; this spec only defines the expectation that ProofPacks are hashable and integrity-verifiable.

---

## 4. One-Click Audit Workflow (Conceptual)

### 4.1 User Types & Roles

- **`compliance_viewer` role:**
  - Can search and filter shipments/payments.
  - Can generate and download ProofPacks.
  - Cannot modify policies, payouts, or raw logs.
- **`ops_user`, `risk_analyst` roles:**
  - May generate ProofPacks for their own scope (e.g. specific customer or corridor).
  - May request overrides (subject to separate authorization flows).
- **`admin` / `supervisor` roles:**
  - Configure retention and export limits, but are not required for basic ProofPack generation.

### 4.2 Operator Console / ChainBoard Interaction

From ChainBoard or a dedicated Compliance View:

1. User selects **scope**:
   - **Entity-based:** a specific shipment, context, or payment.
   - **Time-based:** date range + filters (customer, corridor, risk tier).
2. User clicks **"Generate Audit Pack"**.
3. System:
   - Validates permissions and scope.
   - Queries event and decision logs.
   - Assembles the ProofPack structure (summary, events, decisions, policies, proofs).
   - Computes bundle hash.
   - Stores a ProofPack record (ID + hash + metadata) in an internal audit table.
4. User:
   - Downloads the ProofPack ZIP, or
   - Obtains a secure link/ID to share with auditors.

### 4.3 Backend Requirements (Conceptual API)

Sketch of potential endpoints (names are illustrative, not final):

- `POST /audit/proofpacks` – request ProofPack generation for a given scope.
  - Body includes filters (entity IDs, date range, customer, corridor, etc.).
  - Response returns ProofPack ID, status (e.g. `pending`, `ready`).

- `GET /audit/proofpacks/{proofpack_id}` – download or stream the generated bundle.
  - Enforces access control and logs access events.

- `GET /audit/proofpacks` – list historical ProofPacks for a tenant/customer (with filters).

Safety requirements:

- All ProofPack generation and download requests must be **logged** as audit events.
- Access must be governed by roles and tenant scoping.
- Large scopes must be paginated or processed asynchronously to avoid impacting core operations.

---

## 5. Agent Responsibilities & Future Work

### 5.1 Agent Responsibilities

- **CODY (GID-01 – Backend):**
  - Design and implement event and decision log storage (DB models, append-only semantics).
  - Implement backend services to generate ProofPacks and expose the conceptual audit endpoints.
  - Ensure correlation IDs and policy/version references are consistent across services.

- **SONNY (GID-02 – Frontend):**
  - Build Compliance/Audit views in ChainBoard.
  - Implement scope selection UI and "One-Click Audit" triggers.
  - Provide clear, human-friendly summaries for non-technical reviewers.

- **SAM (GID-06 – Security & Threat):**
  - Define tamper-resistance measures for logs (append-only constraints, signing strategies).
  - Design integrity checks for ProofPacks (hashing, optional on-chain anchoring).
  - Review access control, redaction, and data minimization for audit exports.

- **DAN (GID-07 – DevOps & CI/CD):**
  - Add CI checks to ensure audit code paths are covered by tests.
  - Monitor ProofPack generation performance and error rates.
  - Ensure safe storage and rotation of audit artifacts.

- **MAGGIE (GID-10 – ML & AI):**
  - Define ML decision explanation requirements (feature attribution, model metadata).
  - Ensure model-driven decisions log sufficient context for later analysis and audits.

- **ALEX (GID-08 – Governance & Alignment):**
  - Keep this spec aligned with what is actually implemented.
  - Update reality baseline docs as features ship or change.
  - Coordinate future PACs for expanding audit capabilities.

### 5.2 Future Work

- **On-chain Anchoring:**
  - Define how ProofPack hashes are anchored to XRPL or similar systems (transaction formats, timing, privacy considerations).

- **Data Retention Policies:**
  - Specify per-tenant, per-region retention periods and deletion workflows for audit logs and ProofPacks.

- **Customer-Specific Audit Profiles:**
  - Allow customers to define which data fields and time windows must be included for their audits.

- **Automated Audit Health Checks:**
  - Periodic background jobs that verify sample ProofPacks against source logs to detect drift or gaps.

This v0 specification is intended to be **implementable in small steps**. Future versions will refine schemas and APIs as Cody, Sonny, Sam, and Dan build out the concrete audit pipeline.
