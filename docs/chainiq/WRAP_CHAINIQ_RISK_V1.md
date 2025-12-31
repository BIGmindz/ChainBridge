# ChainIQ Risk Model v1 — WRAP Attestation

**WRAP_SCHEMA:** CHAINBRIDGE_CANONICAL_WRAP_SCHEMA v1.0.0  
**PAC_ID:** PAC-BENSON-EXEC-MAGGIE-CHAINIQ-008  

---

## IDENTITY BLOCK

```yaml
wrap_id: WRAP-CHAINIQ-RISK-V1-20251226
pac_id: PAC-BENSON-EXEC-MAGGIE-CHAINIQ-008
schema_version: CHAINBRIDGE_CANONICAL_WRAP_SCHEMA v1.0.0

agent:
  name: Maggie
  gid: GID-10
  role: ML & Applied AI Lead
  color: 💗 Pink
  
dispatcher:
  name: Benson
  role: Lead Orchestrator
  
runtime:
  environment: ChainBridge Local
  env_type: DEV
  governance: GOLD_STANDARD
  
lane:
  name: ChainIQ Risk Engine
  scope: Scoring, Calibration, Explainability
  boundary: READ/COMPUTE ONLY
  mutation: FORBIDDEN

timestamps:
  dispatched_at: 2025-12-26T00:00:00Z
  completed_at: 2025-12-26T00:00:00Z
```

---

## PROOF BLOCK — Specifications Delivered

### Deliverables Produced

| Document | Status | Description |
|----------|--------|-------------|
| [risk_model_v1.md](risk_model_v1.md) | ✅ COMPLETE | Risk model architecture and specification |
| [feature_spec_v1.md](feature_spec_v1.md) | ✅ COMPLETE | Feature definitions and engineering rules |
| [calibration_plan.md](calibration_plan.md) | ✅ COMPLETE | Calibration methodology and metrics |
| [explainability_contract.md](explainability_contract.md) | ✅ COMPLETE | Glass-box explainability requirements |
| [risk_pdo_schema.json](risk_pdo_schema.json) | ✅ COMPLETE | JSON schema for Risk PDO |

### Specification Summary

```yaml
risk_model:
  model_id: chainiq_risk_glassbox
  version: v1.0.0
  family: EBM (Explainable Boosting Machine)
  interpretability: GLASS_BOX
  monotonicity: ENFORCED
  runtime_learning: DISABLED
  
features:
  count: 24
  categories:
    - Transit & Operational (7)
    - Temperature & IoT (4)
    - Documentation (3)
    - Collateral & Financial (3)
    - Counterparty & Historical (5)
    - Sentiment & Macro (4)
  normalization: pre-computed
  null_handling: FAIL_CLOSED
  
calibration:
  method: platt_scaling
  target_ece: 0.03
  validation: temporal_holdout
  monitoring: daily_drift_detection
  
explainability:
  attribution_minimum: 3
  attribution_maximum: 10
  format: structured + plain_english
  shape_functions: exportable
  audit_trail: full_lineage
```

---

## DECISION BLOCK — Model Design Choices

### Architecture Decision

**Selected:** Explainable Boosting Machine (EBM)

**Rationale:**
1. **Interpretability** — Additive structure with visible shape functions
2. **Monotonicity** — Enforced on key risk drivers
3. **Performance** — Competitive with gradient boosting on tabular data
4. **Auditability** — Shape functions exportable for regulatory inspection
5. **Stability** — Deterministic inference, no runtime updates

### Alternatives Rejected

| Model | Rejection Reason |
|-------|------------------|
| Deep Neural Network | ❌ Black-box violation |
| XGBoost (unconstrained) | ❌ No intrinsic interpretability |
| Random Forest | ❌ Cannot enforce monotonicity |
| LSTM/Transformer | ❌ Overkill for tabular; black-box |

### Calibration Decision

**Selected:** Platt Scaling (post-hoc sigmoid calibration)

**Rationale:**
1. Preserves monotonicity of raw scores
2. Minimal parameters (A, B only)
3. Well-understood, interpretable transformation
4. Isotonic regression available as fallback

### Fail Policy Decision

**Selected:** FAIL-CLOSED

**Rationale:**
1. No default scores on failure
2. All failures emit explicit FailedPDO
3. Prevents silent degradation
4. Aligns with GOLD_STANDARD governance

---

## OUTCOME BLOCK — Risk PDO Fields

### PDO Structure Summary

```
Risk PDO v1
├── pdo_id (UUID)
├── schema_version (v1.0.0)
├── created_at (UTC timestamp)
├── issuer
│   ├── service (chainiq-risk-engine)
│   ├── model_id
│   ├── model_version
│   └── model_checksum
├── request_context
│   ├── request_id
│   ├── shipment_id
│   └── corridor_id
├── proof
│   ├── features (24 fields)
│   ├── feature_version
│   ├── feature_lineage[]
│   └── feature_vector_hash
├── decision
│   ├── risk_score [0.0, 1.0]
│   ├── risk_tier (LOW|MODERATE|HIGH|SEVERE|CRITICAL)
│   ├── attributions[] (3-10)
│   ├── eli5_summary
│   └── calibration metadata
├── outcome
│   ├── status
│   ├── inference_latency_ms
│   └── actionability
├── governance
│   ├── governance_mode (GOLD_STANDARD)
│   ├── model_policy (GLASS_BOX_ONLY)
│   └── fail_policy (FAIL_CLOSED)
├── trace
│   └── correlation_ids[]
└── integrity
    ├── canonical_hash
    ├── signature
    └── signing_key_id
```

### Score Semantics

| Score Range | Risk Tier | Action |
|-------------|-----------|--------|
| 0.00 – 0.15 | LOW | APPROVE |
| 0.15 – 0.35 | MODERATE | ENHANCED_MONITORING |
| 0.35 – 0.60 | HIGH | MANUAL_REVIEW |
| 0.60 – 0.85 | SEVERE | ESCALATE |
| 0.85 – 1.00 | CRITICAL | HOLD |

---

## CALIBRATION EVIDENCE

### Calibration Targets

| Metric | Target | Enforcement |
|--------|--------|-------------|
| ECE (Expected Calibration Error) | < 0.03 | REQUIRED |
| MCE (Maximum Calibration Error) | < 0.10 | REQUIRED |
| Brier Score | < 0.15 | RECOMMENDED |
| Segment ECE | < 0.05 | REQUIRED |

### Monitoring Plan

```yaml
calibration_monitoring:
  frequency: daily
  lookback: 30_days_rolling
  
  alerts:
    - condition: ECE > 0.05
      action: ALERT_ML_TEAM
      
    - condition: ECE > 0.08 for 7 days
      action: TRIGGER_RECALIBRATION
      
    - condition: score_distribution_shift > 0.20
      action: ALERT_ML_TEAM
```

---

## DEVIATIONS

```yaml
deviations: NONE

# All deliverables completed per PAC specification:
# - ✅ Glass-box model only
# - ✅ No black-box models
# - ✅ No neural networks
# - ✅ No runtime learning
# - ✅ No policy enforcement (Lex only)
# - ✅ Fail-closed behavior
# - ✅ Full explainability
```

---

## ATTESTATION

```yaml
attestation:
  wrap_id: WRAP-CHAINIQ-RISK-V1-20251226
  pac_id: PAC-BENSON-EXEC-MAGGIE-CHAINIQ-008
  
  agent:
    name: Maggie
    gid: GID-10
    role: ML & Applied AI Lead
    
  deliverables:
    - risk_model_v1.md: COMPLETE
    - feature_spec_v1.md: COMPLETE
    - calibration_plan.md: COMPLETE
    - explainability_contract.md: COMPLETE
    - risk_pdo_schema.json: COMPLETE
    
  constraints_honored:
    glass_box_only: true
    no_black_box: true
    no_neural_nets: true
    no_runtime_learning: true
    no_policy_enforcement: true
    fail_closed: true
    
  governance:
    mode: GOLD_STANDARD
    lane: ChainIQ Risk Engine
    boundary: READ/COMPUTE ONLY
    mutation: FORBIDDEN
    
  status: COMPLETE
  completed_at: 2025-12-26T00:00:00Z
```

---

## BER (Benson Execution Record)

```yaml
ber_id: BER-CHAINIQ-RISK-V1-20251226
pac_id: PAC-BENSON-EXEC-MAGGIE-CHAINIQ-008
wrap_id: WRAP-CHAINIQ-RISK-V1-20251226

execution:
  dispatcher: Benson (Lead Orchestrator)
  agent: Maggie (GID-10)
  lane: ChainIQ Risk Engine
  mode: EXECUTION
  
proof:
  objective: Design ChainIQ Risk Scoring v1 producing Risk PDO
  constraints:
    - Glass-box only
    - No black-box models
    - No end-to-end neural nets
    - No learning at runtime
    - No policy enforcement
    
decision:
  route_to: Maggie (GID-10)
  deliverables_required: 5
  wrap_required: true
  ber_required: true
  
outcome:
  deliverables_produced: 5
  deviations: NONE
  status: SUCCESS
  
ledger:
  write_enabled: true
  entry_created: 2025-12-26T00:00:00Z
  
final_state:
  wrap_required: true
  ber_required: true
  mode: EXECUTION
  status: COMPLETE
```

---

## NEXT STEPS

1. **Model Implementation** — Implement EBM model per specification
2. **Feature Pipeline** — Build FeatureBuilder conforming to feature_spec_v1
3. **Calibration Pipeline** — Implement Platt scaling per calibration_plan
4. **PDO Emitter** — Build PDO generator conforming to risk_pdo_schema.json
5. **Integration Tests** — Validate end-to-end scoring pipeline
6. **Shadow Deployment** — Deploy in shadow mode for validation

---

**END OF WRAP — WRAP-CHAINIQ-RISK-V1-20251226**
