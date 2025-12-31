# ChainIQ Risk Model v1 — Specification

**PAC Reference:** PAC-BENSON-EXEC-MAGGIE-CHAINIQ-008  
**Author:** Maggie (GID-10) — ML & Applied AI Lead  
**Status:** CANONICAL  
**Version:** v1.0.0  
**Governance:** GOLD_STANDARD  
**Model Policy:** GLASS-BOX ONLY  
**Fail Policy:** FAIL-CLOSED  

---

## 1. Executive Summary

ChainIQ Risk Model v1 produces a **Risk PDO** (Proof → Decision → Outcome) for shipment-level risk scoring. The model is fully interpretable, monotonic in key risk drivers, and emits deterministic, auditable outputs with reason codes.

**Design Constraints (Enforced):**
- ❌ No black-box models
- ❌ No end-to-end neural networks
- ❌ No learning at runtime
- ❌ No policy enforcement (Lex only)
- ✅ Glass-box only
- ✅ Fail-closed on uncertainty

---

## 2. Model Architecture

### 2.1 Model Family Selection

**Primary Model:** Explainable Boosting Machine (EBM) — GAM-based additive model

**Rationale:**
- Fully interpretable: each feature has a visible shape function
- Additive structure: `risk_score = Σ f_i(x_i) + Σ f_ij(x_i, x_j)`
- Monotonicity constraints enforced on key risk drivers
- No hidden interactions beyond specified pairs
- Deterministic inference (no sampling, no dropout)

**Alternative Fallback:** Logistic Regression with spline-encoded features (if EBM unavailable)

### 2.2 Model Identity

```yaml
model_id: chainiq_risk_glassbox
version: v1.0.0
family: EBM (Explainable Boosting Machine)
framework: interpret-ml
checksum: SHA256:<computed_at_training>
training_frozen: true
runtime_learning: disabled
```

### 2.3 Inference Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    ChainIQ Risk Scoring v1                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [1] Feature Ingestion                                          │
│       └─ ShipmentFeaturesV1 (deterministic, pre-computed)       │
│                                                                 │
│  [2] Feature Validation (FAIL-CLOSED)                           │
│       └─ Null check, bounds check, schema validation            │
│       └─ On failure → emit FailedValidationPDO                  │
│                                                                 │
│  [3] Glass-Box Inference                                        │
│       └─ EBM shape functions (frozen weights)                   │
│       └─ Monotonic constraints enforced                         │
│       └─ No runtime gradient updates                            │
│                                                                 │
│  [4] Score Computation                                          │
│       └─ raw_score = Σ f_i(x_i) + Σ f_ij(x_i, x_j) + intercept  │
│       └─ calibrated_score = sigmoid(raw_score) → [0.0, 1.0]     │
│                                                                 │
│  [5] Attribution Extraction                                     │
│       └─ Per-feature contributions from shape functions         │
│       └─ Top-K reason codes (K=5 default)                       │
│                                                                 │
│  [6] Risk PDO Emission                                          │
│       └─ Proof: inputs + feature values + model version         │
│       └─ Decision: score + tier + reason codes                  │
│       └─ Outcome: risk_pdo_id + timestamp + hash                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Score Semantics

### 3.1 Risk Score Definition

| Score Range | Risk Tier | Semantic Meaning |
|-------------|-----------|------------------|
| 0.00 – 0.15 | LOW | Negligible risk; baseline corridor performance |
| 0.15 – 0.35 | MODERATE | Elevated risk; enhanced monitoring recommended |
| 0.35 – 0.60 | HIGH | Significant risk; manual review required |
| 0.60 – 0.85 | SEVERE | High probability of adverse outcome |
| 0.85 – 1.00 | CRITICAL | Near-certain loss; immediate escalation |

### 3.2 Calibration Target

Scores are calibrated to approximate **empirical loss probabilities**:
- A score of 0.30 implies ~30% historical loss rate for similar feature profiles
- Calibration validated via reliability diagrams (see calibration_plan.md)

### 3.3 Monotonicity Constraints

The following features have **enforced monotonic relationships**:

| Feature | Direction | Rationale |
|---------|-----------|-----------|
| `eta_deviation_hours` | ↑ Increasing | More delay → more risk |
| `temperature_violations_count` | ↑ Increasing | More violations → more risk |
| `missing_docs_count` | ↑ Increasing | More gaps → more risk |
| `counterparty_risk_tier` | ↑ Increasing | Higher tier → more risk |
| `corridor_default_rate` | ↑ Increasing | Higher corridor default → more risk |
| `collateral_coverage_ratio` | ↓ Decreasing | More coverage → less risk |
| `shipper_historical_success_rate` | ↓ Decreasing | Better history → less risk |

---

## 4. Fail-Closed Behavior

### 4.1 Failure Modes

| Condition | Response | PDO Emitted |
|-----------|----------|-------------|
| Missing required feature | REJECT | `FailedValidationPDO` |
| Feature out of bounds | REJECT | `FailedValidationPDO` |
| Schema version mismatch | REJECT | `FailedValidationPDO` |
| Model file corrupted | REJECT | `ModelIntegrityFailurePDO` |
| Inference timeout (>500ms) | REJECT | `TimeoutPDO` |
| Score computation error | REJECT | `ComputationFailurePDO` |

### 4.2 No Default Scoring

**FORBIDDEN:** Returning a default/fallback score on failure.

All failures emit a PDO documenting:
- Failure reason code
- Input state at failure
- Recommended remediation
- Correlation ID for trace

---

## 5. Model Governance

### 5.1 Training Constraints

```yaml
training:
  data_source: historical_shipment_outcomes
  label: binary_loss_indicator
  training_window: 24_months_rolling
  validation_split: temporal_holdout_3_months
  test_split: temporal_holdout_3_months
  
  prohibited:
    - runtime_updates: true
    - online_learning: true
    - user_feedback_loops: true
    
  required:
    - deterministic_seed: true
    - reproducible_build: true
    - artifact_versioning: true
```

### 5.2 Deployment Rules

1. **Shadow Mode Required:** All new model versions must run in shadow mode for 14 days
2. **A/B Testing:** Maximum 10% traffic to new model during validation
3. **Rollback Ready:** Prior model artifact retained for instant reversion
4. **No Hot Updates:** Model weights are frozen at deployment; no runtime modification

### 5.3 Audit Trail

Every inference logs:
```yaml
logged_fields:
  - pdo_id
  - shipment_id
  - model_id
  - model_version
  - model_checksum
  - feature_vector_hash
  - risk_score
  - risk_tier
  - top_5_contributions
  - inference_latency_ms
  - timestamp_utc
```

---

## 6. Integration Contract

### 6.1 Input Contract

See [feature_spec_v1.md](feature_spec_v1.md) for full feature specification.

```python
@dataclass
class RiskModelInputV1:
    shipment_id: str
    corridor_id: str
    feature_vector: ShipmentFeaturesV1
    request_id: str
    timestamp: datetime
```

### 6.2 Output Contract

See [risk_pdo_schema.json](risk_pdo_schema.json) for full JSON schema.

```python
@dataclass
class RiskPDO:
    # Identity
    pdo_id: str
    schema_version: str = "v1.0.0"
    
    # Proof
    inputs: RiskModelInputV1
    model_id: str
    model_version: str
    model_checksum: str
    
    # Decision
    risk_score: float  # [0.0, 1.0]
    risk_tier: RiskTier  # LOW | MODERATE | HIGH | SEVERE | CRITICAL
    reason_codes: List[ReasonCode]  # Top-K attributions
    
    # Outcome
    created_at: datetime
    canonical_hash: str
    signature: str
    ttl: timedelta
```

### 6.3 Reason Code Format

```python
@dataclass
class ReasonCode:
    feature_name: str  # Human-readable feature name
    feature_value: Any  # Actual value observed
    contribution: float  # Magnitude of impact on score
    direction: str  # "INCREASES_RISK" | "DECREASES_RISK"
    explanation: str  # Plain-English explanation
```

**Example:**
```json
{
  "feature_name": "ETA Deviation",
  "feature_value": 18.5,
  "contribution": 0.23,
  "direction": "INCREASES_RISK",
  "explanation": "Shipment is 18.5 hours behind schedule, significantly increasing risk."
}
```

---

## 7. Explainability Contract

See [explainability_contract.md](explainability_contract.md) for full requirements.

**Summary:**
- Every score includes top-5 feature attributions
- All attributions are in plain English (no feature indices)
- Contribution magnitudes are normalized and auditable
- Shape functions are exportable for regulatory inspection

---

## 8. Versioning & Compatibility

### 8.1 Semantic Versioning

```
MAJOR.MINOR.PATCH

MAJOR: Breaking changes to input/output contract
MINOR: New features, backward compatible
PATCH: Bug fixes, calibration updates
```

### 8.2 Deprecation Policy

- Models deprecated with 90-day notice
- Shadow period required before any model replacement
- Deprecated models remain available for audit replay

---

## 9. References

- [feature_spec_v1.md](feature_spec_v1.md) — Feature specification
- [calibration_plan.md](calibration_plan.md) — Calibration methodology
- [explainability_contract.md](explainability_contract.md) — Explainability requirements
- [risk_pdo_schema.json](risk_pdo_schema.json) — JSON schema
- [CHAINIQ_ML_CONTRACT_V0.md](CHAINIQ_ML_CONTRACT_V0.md) — Base ML contract
- [../pdo/pdo_explainability_standard_v1.md](../pdo/pdo_explainability_standard_v1.md) — PDO standard

---

## 10. Attestation

```yaml
attestation:
  pac_id: PAC-BENSON-EXEC-MAGGIE-CHAINIQ-008
  author: Maggie (GID-10)
  role: ML & Applied AI Lead
  lane: ChainIQ Risk Engine
  scope: Scoring, Calibration, Explainability
  boundary: READ/COMPUTE ONLY
  mutation: FORBIDDEN
  governance: GOLD_STANDARD
  created_at: 2025-12-26T00:00:00Z
  status: CANONICAL
```

---

**END OF DOCUMENT — risk_model_v1.md**
