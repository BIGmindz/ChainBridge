# AT-02 Model Output Contract — ChainIQ Integration

## 1. BLUF

This document defines the **JSON output contract** between the AT-02 Accessorial Fraud Engine and ChainIQ / backend services. The primary object is the **Fraud Assessment Object**, which is the only shape that downstream systems (ChainIQ, ALEX, SxT ProofPack, ChainPay) rely on.

---

## 2. Fraud Assessment Object

### 2.1. JSON Schema (Conceptual)

```jsonc
{
  "fraud_score": 0.87,               // number, 0.0–1.0
  "confidence": 0.76,                // number, 0.0–1.0
  "reason": "High claim vs contract and low IoT alignment",
  "dominant_features": [
    {
      "name": "claimed_vs_contract_ratio",
      "contribution": 0.25,
      "direction": "increase"
    },
    {
      "name": "detention_window_alignment_score",
      "contribution": 0.18,
      "direction": "decrease"
    }
  ],
  "counterfactual": {
    "feature": "claimed_amount_usd",
    "from": 850.0,
    "to": 400.0,
    "delta": -450.0,
    "note": "Reducing claimed amount to align with contract and IoT dwell would drop fraud risk below 0.6."
  },
  "recommended_action": "hold",     // "approve" | "review" | "hold" | "deny"
  "alex_gate": "fail",              // "pass" | "fail"
  "model_metadata": {
    "model_version_id": "at02_gbdt_v1",
    "schema_version": "at02_schema_v1",
    "generated_at": "2025-10-01T12:34:56Z",
    "inference_id": "uuid-1234",
    "training_data_window": {
      "start": "2025-07-01",
      "end": "2025-09-30"
    }
  }
}
```

---

## 3. Field Definitions

### 3.1. `fraud_score`

- **Type:** number (float)
- **Range:** [0.0, 1.0]
- **Definition:** Calibrated probability that the accessorial is fraudulent or materially invalid.
- **Source:** Monotonic GBDT ensemble, calibrated via Platt/isotonic scaling.
- **Usage:** Input to ALEX governance thresholds and ChainIQ risk scoring.

### 3.2. `confidence`

- **Type:** number (float)
- **Range:** [0.0, 1.0]
- **Definition:** Confidence score derived from ensemble variance and data completeness.
- **Usage:**
  - Low confidence triggers downgrades from auto-`deny` to `hold`/`review`.
  - Used by ALEX to manage decisions on poor data.

### 3.3. `reason`

- **Type:** string
- **Definition:** Human-readable summary of why the fraud score is high or low.
- **Construction:**
  - Derived from top SHAP features and templates.
  - Example: "Claimed detention exceeds IoT-observed dwell and carrier has high dispute loss rate."

### 3.4. `dominant_features`

- **Type:** array of objects

Each element:

```jsonc
{
  "name": "string",
  "contribution": 0.25,   // absolute SHAP value or normalized importance
  "direction": "increase" // "increase" | "decrease"
}
```

- **Purpose:**
  - Make the decision glass-box.
  - Enable dashboards and ALEX governance explanations.

### 3.5. `counterfactual`

- **Type:** object or `null`

Fields:

- `feature`: Feature name that, if changed, would most efficiently reduce fraud_score across governance thresholds.
- `from`: Original value.
- `to`: Proposed value.
- `delta`: Numerical difference (when applicable).
- `note`: Short explanation (e.g., "Aligning claimed dwell with IoT-observed dwell").

**Constraint:** Only includes *actionable* or *disputable* fields (no IoT raw data tampering).

### 3.6. `recommended_action`

- **Type:** string enum
- **Values:** `"approve" | "review" | "hold" | "deny"`
- **Definition:**
  - Derived from fraud_score, confidence, data completeness, and ALEX rules.
  - See `ALEX_AT02_GOVERNANCE_RULES.md`.

### 3.7. `alex_gate`

- **Type:** string enum
- **Values:** `"pass" | "fail"`
- **Definition:**
  - Governance gate result for this accessorial instance.
  - `pass` means no additional ALEX enforcement; `fail` means governance guardrails require intervention.

### 3.8. `model_metadata`

- **Type:** object
- **Fields:**
  - `model_version_id`: Unique ID of the deployed model.
  - `schema_version`: Feature schema version.
  - `generated_at`: ISO UTC timestamp when inference was run.
  - `inference_id`: Unique ID for this inference event for traceability.
  - `training_data_window`: Optional object with `start` and `end` dates.

---

## 4. Extended Contract (Contextual IDs)

In many calls, this object will be wrapped with contextual IDs for ChainIQ and token graph alignment.

```jsonc
{
  "movement_token_id": "MT-01-...",
  "accessorial_token_id": "AT-02-...",
  "invoice_token_id": "IT-01-...",
  "carrier_id": "CARRIER-123",
  "facility_id": "FAC-456",
  "fraud_assessment": { /* Fraud Assessment Object */ }
}
```

These IDs are not used as raw model features but are necessary for:
- Linking decisions back to tokens.
- Triggering follow-on workflows (ChainPay, disputes, ledger entries).

---

## 5. Error Handling & Status Codes

When served over an HTTP API (see `AT02_TO_BACKEND_INTEGRATION.md`), the response will include:

```jsonc
{
  "status": "ok" | "error",
  "error_code": "string | null",
  "error_message": "string | null",
  "fraud_assessment": { ... } | null
}
```

- If `status = "error"`, `fraud_assessment` must be `null`.
- Error conditions (examples):
  - `MISSING_REQUIRED_FEATURES`
  - `MODEL_NOT_AVAILABLE`
  - `INVALID_SCHEMA_VERSION`
  - `INTERNAL_ERROR`

---

## 6. Determinism & Reproducibility

- For a fixed model_version_id, schema_version, and input feature vector, the Fraud Assessment Object must be **deterministic**.
- All randomization (e.g., for counterfactual search) must be:
  - Seeded with a reproducible `inference_id`, or
  - Confined to non-critical outputs, with a clear note.

---

## 7. Backward Compatibility

- The `fraud_assessment` object is versioned via `schema_version`.
- Additive changes (adding new optional fields) are allowed without breaking compatibility.
- Removing or renaming fields requires a new `schema_version` and migration plan.

---

## 8. Regulator-Safe Summary

- This contract ensures that for every accessorial claim, ChainIQ and ALEX receive:
  - A **numeric fraud probability**
  - A **confidence estimate**
  - A **clear explanation** of the decision
  - A **counterfactual suggestion** where applicable
  - A **governance-ready action recommendation**
- All of this is constrained to a stable, well-documented JSON shape suitable for audits, logging, and long-term archival.
