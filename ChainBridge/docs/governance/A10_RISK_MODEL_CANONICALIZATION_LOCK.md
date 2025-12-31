# A10 — Risk Model Canonicalization Lock

## Document Metadata

| Field | Value |
|-------|-------|
| **Lock ID** | A10_RISK_MODEL_CANONICALIZATION |
| **Author** | Maggie (GID-10) — ML & Applied AI Lead |
| **Authority** | Benson (GID-00) |
| **Date** | 2025-12-22 |
| **Status** | 🔒 **LOCKED** / **CANONICAL** |
| **PAC Reference** | PAC-MAGGIE-A10-RISK-MODEL-CANONICALIZATION-LOCK-01 |
| **Correction PAC** | PAC-MAGGIE-A10-GOVERNANCE-CORRECTION-01 |
| **Prerequisites** | A1, A2, A3, A4, A5, A6 |

---

## 0. Canonical Status Declaration

```
CANONICAL_STATUS:
  lock_id: "A10_RISK_MODEL_CANONICALIZATION"
  status: "LOCKED"
  canonical: true
  ratified_by: "Benson (GID-00)"
  ratification_date: "2025-12-22"
  drift_detected: false
  governance_compliant: true
```

---

## 1. Purpose

This lock establishes the **canonical risk model architecture** for ChainIQ,
ensuring all risk intelligence operates as an enterprise-grade, regulator-defensible,
glass-box system suitable for moving real money.

**Core Principle:**
> ChainIQ is decision science, not ML theater.

---

## 2. Model Architecture Stack (LOCKED)

### 2.1 Canonical Model Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                    DECISION BOUNDARY (LOCKED)                   │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │     GLASS-BOX MODELS ONLY                               │   │
│   │     ─────────────────────                               │   │
│   │     • Explainable Boosting Machine (EBM)                │   │
│   │     • Generalized Additive Model (GAM)                  │   │
│   │     • Monotonic Logistic Regression                     │   │
│   │     • Additive Weighted Rules (ChainIQ v1)              │   │
│   └─────────────────────────────────────────────────────────┘   │
│                            ▲                                    │
│                            │                                    │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │     FEATURE GENERATION LAYER (UPSTREAM ONLY)            │   │
│   │     ────────────────────────────────────────            │   │
│   │     • GNN embeddings (context signals only)             │   │
│   │     • NLP features (extracted, not learned)             │   │
│   │     • Statistical aggregates (versioned)                │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Allowed Models at Decision Boundary

| Model Type | Status | Justification |
|------------|--------|---------------|
| Additive Weighted Rules | ✅ ALLOWED | Fully transparent, deterministic |
| EBM (InterpretML) | ✅ ALLOWED | Glass-box, feature-level explainability |
| GAM (pyGAM) | ✅ ALLOWED | Monotonic constraints, interpretable |
| Monotonic Logistic | ✅ ALLOWED | Audit-friendly, regulatory-safe |
| Linear Models | ✅ ALLOWED | Maximum interpretability |

### 2.3 Forbidden Models at Decision Boundary

| Model Type | Status | Reason |
|------------|--------|--------|
| Neural Networks | ❌ FORBIDDEN | Black-box, non-explainable |
| Deep Learning | ❌ FORBIDDEN | Opaque inference |
| Random Forest | ❌ FORBIDDEN | Ensemble opacity |
| XGBoost/LightGBM | ❌ FORBIDDEN | Tree ensemble complexity |
| Transformer Models | ❌ FORBIDDEN | Attention opacity |
| Black-box Ensembles | ❌ FORBIDDEN | Combined opacity |

### 2.4 GNN/Neural Network Usage (STRICTLY LIMITED)

```
GNN_USAGE_POLICY {
  role: "FEATURE_GENERATION_ONLY"
  location: "UPSTREAM_OF_DECISION_BOUNDARY"
  output_type: "EXTRACTED_FEATURES"
  decision_influence: "INDIRECT_VIA_FEATURES"
  audit_requirement: "FEATURE_LINEAGE_DOCUMENTED"
}
```

**Hard Rule:** Neural networks may generate features but NEVER make final decisions.

---

## 3. Risk Scoring Contract (LOCKED)

### 3.1 Input Specification

```python
RISK_INPUT_CONTRACT = {
    # Shipment Facts (REQUIRED)
    "shipment_id": str,           # Unique identifier
    "value_usd": float,           # Cargo value
    "is_hazmat": bool,            # Hazardous materials
    "is_temp_control": bool,      # Temperature controlled
    "expected_transit_days": int, # Planned duration

    # Counterparty History (REQUIRED)
    "carrier_id": str,
    "carrier_incident_rate_90d": float,  # 0.0-1.0
    "carrier_tenure_days": int,

    # Lane/Route Context (REQUIRED)
    "origin": str,
    "destination": str,
    "lane_risk_index": float,     # 0.0-1.0
    "border_crossing_count": int,

    # Real-time Signals (OPTIONAL)
    "recent_delay_events": int,
    "iot_alert_count": int,

    # External Signals (BOUNDED)
    "external_signals": Dict[str, float],  # Max 10 signals
}
```

### 3.2 Output Specification

```python
RISK_OUTPUT_CONTRACT = {
    # Core Scores (REQUIRED)
    "risk_score": float,          # 0-100 scale
    "risk_band": Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"],
    "confidence": float,          # 0.0-1.0

    # Explainability (REQUIRED - NEVER EMPTY)
    "reason_codes": List[str],    # Enumerated reasons
    "top_factors": List[{
        "feature": str,
        "contribution": float,    # Signed contribution
        "direction": Literal["INCREASES_RISK", "DECREASES_RISK"],
    }],

    # Versioning (REQUIRED)
    "model_version": str,         # Immutable version tag
    "data_version": str,          # Training data version

    # Audit (REQUIRED)
    "assessed_at": str,           # ISO-8601 UTC
    "evaluation_id": str,         # Unique scoring event ID
}
```

### 3.3 Invariants

| Invariant | Rule |
|-----------|------|
| **INV-RISK-001** | `risk_score` MUST be monotonic with negative signals |
| **INV-RISK-002** | `risk_band` MUST be derived from `risk_score` via fixed thresholds |
| **INV-RISK-003** | `reason_codes` MUST NOT be empty |
| **INV-RISK-004** | `top_factors` MUST contain at least 1 factor |
| **INV-RISK-005** | Same inputs + same model_version ⇒ identical output |

---

## 4. Monotonic Constraints (LOCKED)

### 4.1 Core Monotonicity Rules

```
MONOTONIC_CONSTRAINTS {
  # Higher risk signals MUST increase score
  increasing_features: [
    "carrier_incident_rate_90d",
    "recent_delay_events",
    "iot_alert_count",
    "border_crossing_count",
    "value_usd",
    "lane_risk_index"
  ]

  # Missing data MUST increase uncertainty, not optimism
  missing_data_policy: "INCREASE_UNCERTAINTY"

  # No feature can decrease risk below baseline
  floor_policy: "BASELINE_RISK_PRESERVED"
}
```

### 4.2 Monotonicity Test Requirements

Every risk model deployment MUST pass:
1. **Positive monotonicity tests** — increasing risk signal ⇒ non-decreasing score
2. **Boundary tests** — extreme values produce expected extreme scores
3. **Missing data tests** — nulls degrade conservatively

---

## 5. Calibration & Drift Policy (LOCKED)

### 5.1 Calibration Requirements

```
CALIBRATION_POLICY {
  # Calibration curves stored as versioned artifacts
  artifact_type: "JSON"
  storage: "chainiq-service/calibration/"

  # Calibration metadata
  required_fields: [
    "model_version",
    "calibration_date",
    "calibration_dataset_hash",
    "observed_vs_predicted_curve",
    "brier_score",
    "ece_score"  # Expected Calibration Error
  ]

  # Recalibration triggers
  recalibration_threshold: 0.05  # ECE > 5%
}
```

### 5.2 Drift Detection Policy

```
DRIFT_POLICY {
  # Drift detection runs continuously
  detection_frequency: "HOURLY"

  # Thresholds (from drift_engine.py)
  thresholds: {
    "STABLE": 0.05,    # 0-5% drift
    "MINOR": 0.10,     # 5-10% drift
    "MODERATE": 0.20,  # 10-20% drift
    "SEVERE": 0.35,    # 20-35% drift
    "CRITICAL": 1.0    # 35%+ drift
  }

  # CRITICAL RULE: Drift ESCALATES, never auto-corrects
  auto_correction: "FORBIDDEN"
  escalation_path: "DRIFT → ALERT → HUMAN_REVIEW → RETRAIN_DECISION"
}
```

### 5.3 Drift Response Matrix

| Drift Level | Response | Auto-Action |
|-------------|----------|-------------|
| STABLE | Continue | None |
| MINOR | Monitor | Log only |
| MODERATE | Alert | Notify team |
| SEVERE | Escalate | Page on-call |
| CRITICAL | Halt | Block new scores, require human |

---

## 6. PDO Integration Boundary (LOCKED)

### 6.1 Binding Contract

```
RISK_PDO_BINDING {
  # ChainIQ provides METADATA to PDO
  binding_type: "METADATA_ONLY"

  # ChainIQ NEVER blocks execution
  execution_effect: "NONE"

  # Enforcement is Ruby's domain
  enforcement_location: "RUBY_CRO_POLICY_LAYER"

  # Risk attached to PDO as metadata
  pdo_fields: [
    "risk_score",
    "risk_band",
    "risk_assessment_id",
    "model_version"
  ]
}
```

### 6.2 CRO Override Protocol

```
CRO_OVERRIDE_POLICY {
  # CRO can override risk assessment
  override_allowed: true

  # Override MUST emit proof
  override_proof_required: true
  override_proof_type: "OverrideProof"

  # Override fields
  override_fields: [
    "original_risk_score",
    "override_risk_score",
    "override_reason",
    "cro_agent_id",
    "override_timestamp",
    "approval_chain"
  ]
}
```

### 6.3 Settlement Gate Integration

```
SETTLEMENT_RISK_RULE {
  # No settlement without risk verdict
  risk_verdict_required: true

  # Risk downgrade prohibited post-PDO
  post_pdo_downgrade: "FORBIDDEN"

  # Risk upgrade triggers re-evaluation
  post_pdo_upgrade: "TRIGGERS_REVIEW"
}
```

---

## 7. Risk Replay Contract (LOCKED)

### 7.1 Replay Guarantee

```
REPLAY_CONTRACT {
  # Determinism requirement
  guarantee: "IDENTICAL_OUTPUT"

  # Given:
  inputs: "SAME_INPUTS"
  model_version: "SAME_MODEL_VERSION"

  # Then:
  output: "BYTE_FOR_BYTE_IDENTICAL"

  # Use cases:
  use_cases: [
    "AUDIT",
    "DISPUTE_RESOLUTION",
    "REGULATORY_INQUIRY",
    "INCIDENT_INVESTIGATION"
  ]
}
```

### 7.2 Replay Requirements

| Requirement | Specification |
|-------------|---------------|
| **Determinism** | No random seeds, no non-deterministic ops |
| **Versioning** | Model version immutable after deployment |
| **Input Preservation** | All inputs logged for replay |
| **Output Verification** | Replay output must hash-match original |

---

## 8. Failure & Safety Modes (LOCKED)

### 8.1 Failure Handling

```
FAILURE_MODES {
  # Missing data: degrade conservatively
  missing_data: "DEGRADE_GRACEFULLY"
  missing_data_effect: "INCREASE_UNCERTAINTY"

  # Low confidence: escalate
  low_confidence_threshold: 0.6
  low_confidence_action: "ESCALATE"

  # Model error: fail closed
  model_error: "FAIL_CLOSED"
  model_error_effect: "NO_SCORE_EMITTED"

  # CRITICAL: No silent fallbacks
  silent_fallback: "FORBIDDEN"
}
```

### 8.2 Degradation Hierarchy

```
1. PRIMARY_MODEL_AVAILABLE
   └── Use primary model

2. PRIMARY_MODEL_UNAVAILABLE
   └── Use fallback model (if approved)
   └── Emit DEGRADED_MODE flag

3. ALL_MODELS_UNAVAILABLE
   └── FAIL_CLOSED
   └── Return error, no score
   └── Alert immediately
```

---

## 9. Version Immutability (LOCKED)

### 9.1 Model Versioning Rules

```
MODEL_VERSION_POLICY {
  # Version format
  format: "chainiq_v{major}_{author}"
  example: "chainiq_v1_maggie"

  # Immutability
  post_deployment_changes: "FORBIDDEN"

  # New version required for:
  requires_new_version: [
    "Weight changes",
    "Threshold changes",
    "Feature additions",
    "Feature removals",
    "Logic changes"
  ]

  # Version registry
  registry_location: "chainiq-service/models/version_registry.json"
}
```

### 9.2 Data Versioning Rules

```
DATA_VERSION_POLICY {
  # Training data hash required
  data_hash_algorithm: "SHA-256"

  # Data lineage required
  lineage_fields: [
    "source_tables",
    "extraction_date",
    "row_count",
    "feature_schema_version"
  ]
}
```

---

## 10. Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| No black-box models in final decision path | ✅ LOCKED |
| Monotonic constraints enforced and tested | ✅ LOCKED |
| Risk replay deterministic | ✅ LOCKED |
| Drift escalates, never auto-corrects | ✅ LOCKED |
| CRO override emits OverrideProof | ✅ LOCKED |
| Risk model versioning immutable | ✅ LOCKED |
| No settlement without risk verdict | ✅ LOCKED |
| Risk downgrade prohibited post-PDO | ✅ LOCKED |

---

## 11. Explicit Forbidden Actions (NON-GOALS)

The following actions are **explicitly prohibited** under A10:

### 11.1 Model Architecture Violations

| Forbidden Action | Severity | Consequence |
|------------------|----------|-------------|
| Black-box models at decision boundary | 🔴 CRITICAL | Immediate halt, rollback required |
| Neural networks for final risk score | 🔴 CRITICAL | Governance violation, escalate |
| Adaptive monotonic relaxation | 🔴 CRITICAL | Contract breach |
| Online learning without governance | 🔴 CRITICAL | Unversioned drift, halt |
| Runtime model swapping | 🔴 CRITICAL | Non-deterministic, audit fail |
| Post-hoc explanation models | 🟠 HIGH | Glass-box violation |

### 11.2 Drift & Calibration Violations

| Forbidden Action | Severity | Consequence |
|------------------|----------|-------------|
| Auto-correcting drift | 🔴 CRITICAL | Governance bypass |
| Silent fallback on CRITICAL drift | 🔴 CRITICAL | Settlement risk |
| Unversioned calibration artifacts | 🟠 HIGH | Audit trail gap |
| ECE threshold bypass | 🟠 HIGH | Calibration contract breach |

### 11.3 Replay & Audit Violations

| Forbidden Action | Severity | Consequence |
|------------------|----------|-------------|
| Non-deterministic replay | 🔴 CRITICAL | Audit failure |
| Missing input hash on RiskOutput | 🟠 HIGH | Replay contract breach |
| Incomplete reason codes | 🟠 HIGH | Explainability gap |

### 11.4 Settlement Integration Violations

| Forbidden Action | Severity | Consequence |
|------------------|----------|-------------|
| Settlement without risk_verdict | 🔴 CRITICAL | A6 contract breach |
| Risk downgrade post-PDO | 🔴 CRITICAL | Override governance bypass |
| CRO override without OverrideProof | 🔴 CRITICAL | Audit gap |

---

## 12. Unlock Authority

This lock may ONLY be modified by:
- **Benson (GID-00)** — Full authority
- **Maggie (GID-10)** — With Benson approval

Changes require:
1. New PAC with explicit unlock request
2. Benson gateway approval
3. Full regression test suite pass
4. Audit trail of change rationale

---

## 13. References

| Document | Location |
|----------|----------|
| A1 Architecture Lock | [A1_ARCHITECTURE_LOCK.md](A1_ARCHITECTURE_LOCK.md) |
| A6 Governance Alignment Lock | [A6_GOVERNANCE_ALIGNMENT_LOCK.md](A6_GOVERNANCE_ALIGNMENT_LOCK.md) |
| PDO Signing Model | [PDO_SIGNING_MODEL_V1.md](PDO_SIGNING_MODEL_V1.md) |
| Risk Engine Implementation | [chainiq-service/app/risk/engine.py](../../chainiq-service/app/risk/engine.py) |
| Drift Engine | [chainiq-service/app/ml/drift_engine.py](../../chainiq-service/app/ml/drift_engine.py) |

---

**END OF A10 LOCK DOCUMENT**

```
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║   🔒 A10 RISK MODEL CANONICALIZATION — LOCKED                              ║
║                                                                            ║
║   Glass-box only. Deterministic. Regulator-defensible.                     ║
║   ML assists decisions; it does not override doctrine.                     ║
║                                                                            ║
║   Author: Maggie (GID-10) 🩷                                               ║
║   Authority: Benson (GID-00)                                               ║
║   Drift: ZERO                                                              ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```
