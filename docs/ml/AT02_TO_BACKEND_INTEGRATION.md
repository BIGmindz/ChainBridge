# AT-02 → Backend Integration Blueprint (Cody)

> **Legend**:
> 🩷 **MAGGIE** (GID-10) — Chief AI Architect
> 🟢 **ALEX** (GID-08) — Governance & Alignment
> 🔵 **ATLAS** — Infrastructure & Security

## 1. BLUF

This document defines how Cody should integrate the AT-02 Accessorial Fraud Engine into the ChainBridge backend stack (ChainIQ, APIs, event router). It covers endpoints, payloads, async flows, and dependencies.

---

## 2. Services & Boundaries

- **AT-02 Scoring Service:**
  - Logical component that computes Fraud Assessment Objects.
  - Could be a Python service within `chainiq-service` or a separate microservice.

- **ChainIQ Core:**
  - Consumes Fraud Assessments and updates risk views.

- **🟢 ALEX Governance:**
  - Reads model outputs and applies governance rules (`ALEX_AT02_GOVERNANCE_RULES.md`).

- **Event Router / Message Bus:**
  - Propagates events to other systems (ChainPay, SxT ProofPack, ChainBoard UI).

---

## 3. Core Endpoints

All examples assume a RESTful interface in `chainiq-service` (FastAPI-style), but the contract is transport-agnostic.

### 3.1. `POST /ml/at02/evaluate`

- **Purpose:** Compute fraud score and governance recommendation for a single accessorial claim.

**Request Body (simplified):**

```jsonc
{
  "movement_token_id": "MT-01-...",
  "accessorial_token_id": "AT-02-...",
  "invoice_token_id": "IT-01-...",
  "carrier_id": "CARRIER-123",
  "facility_id": "FAC-456",
  "feature_payload": {
    "claimed_amount_usd": 850.0,
    "claimed_vs_contract_ratio": 1.8,
    "dwell_duration_observed_minutes": 45,
    "claimed_dwell_duration_minutes": 120,
    "dwell_duration_delta_minutes": 75,
    "detention_window_alignment_score": 0.2,
    "carrier_dispute_rate_90d": 0.35,
    "carrier_dispute_loss_rate_90d": 0.4,
    "gps_signal_quality_score": 0.9,
    "data_completeness_score": 0.85,
    "num_critical_features_missing": 0,
    "...": "other features as per AT02_FEATURE_SCHEMA.md"
  },
  "schema_version": "at02_schema_v1"
}
```

**Response Body:**

```jsonc
{
  "status": "ok",
  "error_code": null,
  "error_message": null,
  "fraud_assessment": { /* see AT02_OUTPUT_CONTRACT.md */ }
}
```

- **Notes:**
  - Synchronous call, suitable for inline workflows during invoice ingestion.

---

### 3.2. `POST /ml/at02/explain`

- **Purpose:** Provide detailed explanations (SHAP values, plots, narratives) for an already-scored claim.

**Request Body:**

```jsonc
{
  "inference_id": "uuid-1234",
  "accessorial_token_id": "AT-02-..."
}
```

**Response Body (example):**

```jsonc
{
  "status": "ok",
  "error_code": null,
  "error_message": null,
  "explanations": {
    "dominant_features": [
      { "name": "claimed_vs_contract_ratio", "shap_value": 0.35 },
      { "name": "dwell_duration_delta_minutes", "shap_value": 0.22 }
    ],
    "global_context": {
      "model_version_id": "at02_gbdt_v1",
      "schema_version": "at02_schema_v1"
    }
  }
}
```

- **Notes:**
  - Could be merged with `/evaluate` for single-shot responses, but separating keeps latency for simple calls lower.

---

### 3.3. `POST /ml/at02/counterfactual`

- **Purpose:** Compute minimal actionable change to drop fraud score below a target threshold.

**Request Body:**

```jsonc
{
  "inference_id": "uuid-1234",
  "target_fraud_score": 0.6,
  "allowed_features": [
    "claimed_amount_usd",
    "claimed_dwell_duration_minutes",
    "accessorial_reason_code"
  ]
}
```

**Response Body:**

```jsonc
{
  "status": "ok",
  "error_code": null,
  "error_message": null,
  "counterfactual": {
    "feature": "claimed_amount_usd",
    "from": 850.0,
    "to": 400.0,
    "delta": -450.0,
    "note": "Reducing claimed amount to align with contract and IoT dwell would drop fraud risk below 0.6."
  }
}
```

---

## 4. Async Pipeline & Event Router

For high throughput and better user experience, consider an **event-driven flow**:

1. **Invoice Ingestion:**
   - ChainIQ ingests an invoice and associated accessorials.
   - Emits event: `invoice.accessorial.received` with token IDs and raw data.

2. **Feature Builder Service:**
   - Subscribes to `invoice.accessorial.received`.
   - Resolves MT-01, IT-01, CCT-01, IoT streams.
   - Builds `feature_payload` as per `AT02_FEATURE_SCHEMA.md`.
   - Calls `/ml/at02/evaluate`.

3. **AT-02 Scoring:**
   - Produces Fraud Assessment Object.
   - Emits `invoice.accessorial.scored` with fraud assessment and metadata.

4. **🟢 ALEX Governance:**
   - Subscribes to `invoice.accessorial.scored`.
   - Applies `ALEX_AT02_GOVERNANCE_RULES.md`.
   - Emits `invoice.accessorial.decision` with final action.

5. **Downstream Consumers:**
   - ChainPay adjusts payment flows.
   - ChainBoard UI shows decision and explanations.
   - SxT ProofPack verifies and anchors proofs.

---

## 5. Performance & SLAs

- **Synchronous scoring latency target:**
  - P95 < 200ms per `/evaluate` call (after feature payload is prepared).
- **Throughput:**
  - Support batch scoring via an additional endpoint: `POST /ml/at02/evaluate-batch`.

---

## 6. Security & Access Control

- Endpoints must be protected via:
  - Service-to-service authentication (mTLS or JWT).
  - Role-based access to `/explain` and `/counterfactual` (only for authorized staff/tools).
- All requests and responses logged with:
  - `inference_id`
  - calling service
  - timestamps

No PII is required for AT-02; payloads should be de-identified where possible.

---

## 7. Error & Retry Semantics

- If `/ml/at02/evaluate` fails:
  - Return `status = "error"` with `error_code`.
  - Event router may retry with backoff or route to a **degraded path** (e.g., rules-based fallback).

- Degraded path example:
  - If model unavailable, mark accessorial as `review` with a governance flag `MODEL_UNAVAILABLE`.

---

## 8. Logging & Observability

- For each inference:
  - Log `inference_id`, token IDs, model version, fraud_score, confidence, recommended_action.
- Metrics:
  - Count of evaluations per time window.
  - Distribution of fraud_score and actions per carrier, lane, facility.
  - Error rates and latency stats.

---

## 9. Implementation Notes for Cody

- Place implementation stubs in `chainiq-service` (e.g., `app/routers/ml_at02.py`, `app/services/ml_at02.py`).
- Use `AT02_OUTPUT_CONTRACT.md` as the single source of truth for response shapes.
- Coordinate with Maggie for any schema changes; bump `schema_version` when needed.

---

🩷 **MAGGIE** — Chief AI Architect
