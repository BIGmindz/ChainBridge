# ML Lifecycle Governance v1.0
**Governance ID: GID-08-ML | Classification: CRITICAL | Owner: Maggie (GID-02) + ALEX (GID-08)**

## Executive Summary

This document defines the **6-stage ML lifecycle governance framework** for ChainBridge. All machine learning models deployed in production must follow this lifecycle to ensure safety, explainability, calibration, and auditability.

**Core Principle:**
> "No model reaches production without proof of safety, explainability, and governance compliance."

---

## 1. THE 6-STAGE ML LIFECYCLE

### Stage 1: PROPOSAL

**Objective:** Define the problem, model architecture, and governance approach.

**Requirements:**
- ✅ Written proposal document
- ✅ Problem statement and business justification
- ✅ Proposed model type (must be glass-box)
- ✅ Feature list and data sources
- ✅ Monotonicity constraints definition
- ✅ Evaluation metrics plan
- ✅ Governance review checkpoint

**Deliverables:**
- `docs/ml_proposals/MODEL_NAME_proposal.md`
- Governance approval from ALEX

**Validation:**
```python
# Proposal checklist
proposal_requirements = [
    "problem_statement",
    "model_type",  # Must be in ALLOWED_MODEL_TYPES
    "feature_list",
    "monotonicity_constraints",
    "evaluation_metrics",
    "governance_signoff"
]
```

**Example Proposal Structure:**
```markdown
# ChainIQ Risk Model v0.2 Proposal

## Problem Statement
Predict shipment financing risk using 48 features...

## Model Type
Explainable Boosting Machine (EBM)

## Feature List
- prior_losses_flag (monotonic increasing)
- shipper_on_time_pct_90d (monotonic decreasing)
- ...

## Monotonicity Constraints
| Feature | Direction | Rationale |
|---------|-----------|-----------|
| prior_losses_flag | Increasing | More losses → higher risk |
| shipper_on_time_pct_90d | Decreasing | Better on-time → lower risk |

## Evaluation Metrics
- Brier Score < 0.10
- Log Loss < 0.25
- Calibration error < 0.05

## Governance Review
Reviewed by: ALEX (GID-08)
Approved: 2025-12-01
```

---

### Stage 2: PROTOTYPE

**Objective:** Build training scaffolding and validate data pipeline.

**Requirements:**
- ✅ Training script with stub model
- ✅ Data loading and preprocessing
- ✅ Feature engineering pipeline
- ✅ Training/validation split strategy
- ✅ Metrics calculation scaffolding
- ✅ No production deployment (training-only)

**Deliverables:**
- `training/train_MODEL_NAME_v0X.py`
- `training/feature_engineering_v0X.py`
- Sample training run with synthetic data

**Validation:**
```python
# Prototype must be isolated from production
assert "training" in script_path  # Must be in training/ directory
assert not production_deployment_enabled
assert training_mode_only
```

**Code Structure:**
```python
# training/train_risk_model_v02.py
def train_model_v02():
    """
    Prototype training script - NOT FOR PRODUCTION
    """
    # Load data
    df = load_training_data()

    # Feature engineering
    features = engineer_features(df)

    # Train EBM with monotonicity constraints
    model = ExplainableBoostingClassifier(
        monotonicity_constraints={
            'prior_losses_flag': +1,  # Increasing
            'shipper_on_time_pct_90d': -1,  # Decreasing
        }
    )
    model.fit(X_train, y_train)

    # Evaluate
    metrics = evaluate_model(model, X_val, y_val)

    # Save metadata
    save_model_metadata(model, metrics)
```

---

### Stage 3: TRAINING APPROVAL

**Objective:** Train production model and validate governance compliance.

**Requirements:**
- ✅ Full training run on production-quality data
- ✅ Recorded metrics (Brier score, log loss, calibration)
- ✅ Monotonicity constraints validated
- ✅ Explainability artifacts generated
- ✅ Model lineage documented
- ✅ ProofPack artifact created
- ✅ ALEX governance approval

**Deliverables:**
- Trained model artifact (`models/chainiq_risk_v0.2.0.pkl`)
- Model metadata (`models/chainiq_risk_v0.2.0_metadata.json`)
- ProofPack (`proofpacks/pp_ml_training_20251211_001.json`)
- Training report (`reports/training_report_v0.2.0.md`)

**Validation Checklist:**
```python
def validate_training_approval(model, metadata):
    """ALEX validation for training approval"""

    # 1. Glass-box constraint
    assert metadata['model_type'] in ALLOWED_MODEL_TYPES

    # 2. Monotonicity validation
    assert validate_monotonicity_constraints(model, metadata)

    # 3. Calibration metrics
    assert metadata['calibration_metrics']['brier_score'] < 0.10
    assert metadata['calibration_metrics']['log_loss'] < 0.25

    # 4. Explainability
    assert metadata['explainability_method'] in ['EBM_native', 'SHAP', 'GAM_native']
    assert 'feature_importance' in metadata

    # 5. Lineage
    assert metadata['training_data_hash'] is not None
    assert metadata['training_script'] is not None

    # 6. ProofPack
    assert metadata['proof_pack_id'] is not None

    return True
```

**Metadata Example:**
```json
{
  "model_id": "chainiq_risk_v0.2.0",
  "model_type": "EBM",
  "training_date": "2025-12-11T10:30:00Z",
  "training_data_hash": "sha256:a3f8c92d...",
  "feature_list": [
    "prior_losses_flag",
    "shipper_on_time_pct_90d",
    "corridor_disruption_index_90d",
    "..."
  ],
  "monotonicity_constraints": {
    "prior_losses_flag": 1,
    "shipper_on_time_pct_90d": -1
  },
  "calibration_metrics": {
    "brier_score": 0.087,
    "log_loss": 0.234,
    "calibration_error": 0.042
  },
  "explainability_method": "EBM_native",
  "feature_importance": {
    "prior_losses_flag": 0.18,
    "corridor_disruption_index_90d": 0.15,
    "...": "..."
  },
  "proof_pack_id": "pp_ml_training_20251211_001",
  "lineage": {
    "parent_model": "chainiq_risk_v0.1.0",
    "training_script": "training/train_risk_model_v02.py",
    "training_data_source": "shipment_financings_2024_2025"
  },
  "governance": {
    "alex_approval": true,
    "approval_date": "2025-12-11T12:00:00Z",
    "reviewer": "ALEX-GID-08"
  }
}
```

---

### Stage 4: SHADOW MODE

**Objective:** Deploy new model alongside old model for comparison.

**Requirements:**
- ✅ Dual scoring (old model + new model)
- ✅ Both scores logged for every prediction
- ✅ No production decision-making with new model yet
- ✅ Metrics comparison dashboard
- ✅ Monitoring alerts for divergence
- ✅ Minimum 7-14 days observation period

**Deliverables:**
- Shadow mode deployment configuration
- Dual scoring logs
- Comparative metrics report

**Code Pattern:**
```python
# chainiq-service/app/services/risk_scoring.py
def score_shipment_with_shadow(shipment_features):
    """
    Shadow mode: run both models, log both, return old model score
    """
    # Production model (v0.1.0)
    old_score = old_model.predict_proba(shipment_features)

    # Shadow model (v0.2.0)
    new_score = new_model.predict_proba(shipment_features)

    # Log both scores
    logger.info("Shadow scoring", extra={
        "old_model": "v0.1.0",
        "old_score": old_score,
        "new_model": "v0.2.0",
        "new_score": new_score,
        "score_diff": abs(old_score - new_score)
    })

    # Return old model score for production decisions
    return {
        "risk_score": old_score,
        "model_version": "v0.1.0",
        "shadow_mode": True
    }
```

**Monitoring:**
- Score distribution comparison
- Divergence rate (% of predictions with >10% difference)
- Feature importance drift
- Calibration drift

**Shadow Mode Success Criteria:**
- Divergence rate < 15%
- New model calibration maintained
- No operational issues
- Performance acceptable (latency, throughput)

---

### Stage 5: CONTROLLED DEPLOYMENT

**Objective:** Gradually roll out new model to production traffic.

**Requirements:**
- ✅ Shadow mode success criteria met
- ✅ Gradual rollout (10% → 25% → 50% → 100%)
- ✅ Real-time monitoring and alerting
- ✅ Rollback plan ready
- ✅ Metrics validation at each stage
- ✅ Business stakeholder approval

**Rollout Schedule:**
```
Week 1: 10% of traffic → new model
  ↓ (validate metrics)
Week 2: 25% of traffic → new model
  ↓ (validate metrics)
Week 3: 50% of traffic → new model
  ↓ (validate metrics)
Week 4: 100% of traffic → new model
  ↓
Production freeze
```

**Rollout Configuration:**
```python
# config/model_rollout.yaml
model_rollout:
  model_id: "chainiq_risk_v0.2.0"
  rollout_percentage: 50  # 50% of traffic
  canary_groups:
    - "low_risk_corridors"  # Start with lower-risk shipments
  rollback_on:
    - "calibration_error > 0.08"
    - "divergence_rate > 20%"
    - "prediction_latency_p99 > 500ms"
```

**Validation at Each Stage:**
- Calibration maintained
- Business metrics stable (approval rates, loss rates)
- Operational metrics stable (latency, errors)
- Feature importance stable

**Rollback Triggers:**
- Calibration degrades
- Business metrics regress
- Operational issues
- Unexpected score distribution

---

### Stage 6: PRODUCTION FREEZE

**Objective:** Lock model version as stable, versioned, immutable artifact.

**Requirements:**
- ✅ 100% rollout successful
- ✅ Minimum 30 days in production
- ✅ No rollback events
- ✅ Metrics stable and validated
- ✅ Model artifact versioned and immutable
- ✅ Documentation finalized
- ✅ Governance sign-off

**Deliverables:**
- Production model artifact (immutable)
- Production metadata (versioned)
- Production deployment record
- Governance certification

**Production Certification:**
```json
{
  "model_id": "chainiq_risk_v0.2.0",
  "certification": {
    "status": "PRODUCTION_CERTIFIED",
    "certification_date": "2026-01-15T00:00:00Z",
    "certifier": "ALEX-GID-08",
    "production_since": "2025-12-18T00:00:00Z",
    "rollout_completion": "2026-01-08T00:00:00Z",
    "observations": {
      "predictions_served": 125000,
      "calibration_error": 0.041,
      "divergence_rate": 0.08,
      "rollback_events": 0
    },
    "governance_compliance": {
      "glass_box": true,
      "monotonicity": true,
      "explainability": true,
      "calibration": true,
      "lineage": true,
      "proof_pack": true
    }
  }
}
```

**Immutability:**
- Model artifact stored in immutable storage (S3 with versioning)
- Model hash recorded in governance log
- No modifications allowed (new version required)

---

## 2. BLOCKED CONDITIONS (VIOLATIONS)

ALEX will block model deployment if:

### Violation 1: Black-Box Model
```python
# ❌ BLOCKED
model = RandomForestClassifier()  # Not explainable enough
model = XGBClassifier()  # Not monotone by default
model = NeuralNetwork()  # Black-box
```

### Violation 2: Missing Monotonicity
```python
# ❌ BLOCKED
model = ExplainableBoostingClassifier()  # No constraints!
model.fit(X, y)
```

### Violation 3: Uncalibrated Model
```python
# ❌ BLOCKED
brier_score = 0.15  # > 0.10 threshold
# Model is not well-calibrated
```

### Violation 4: Missing Explainability
```python
# ❌ BLOCKED
metadata = {
    "model_type": "EBM",
    # Missing: explainability_method, feature_importance
}
```

### Violation 5: No Lineage
```python
# ❌ BLOCKED
metadata = {
    "model_type": "EBM",
    # Missing: training_data_hash, training_script, parent_model
}
```

### Violation 6: No ProofPack
```python
# ❌ BLOCKED
metadata = {
    "model_type": "EBM",
    # Missing: proof_pack_id
}
```

---

## 3. MODEL METADATA SCHEMA

All models must provide complete metadata:

```json
{
  "model_id": "string (required)",
  "model_type": "enum: [EBM, GAM, LogisticRegression, MonotoneGBDT] (required)",
  "version": "string (required)",
  "training_date": "ISO 8601 datetime (required)",
  "training_data_hash": "SHA-256 hash (required)",
  "feature_list": ["array of strings (required)"],
  "feature_count": "integer (required)",
  "monotonicity_constraints": {
    "feature_name": "integer: -1 (decreasing) or +1 (increasing)"
  },
  "calibration_metrics": {
    "brier_score": "float (required, must be < 0.10)",
    "log_loss": "float (required, must be < 0.25)",
    "calibration_error": "float (required, must be < 0.05)",
    "auc_roc": "float (optional)",
    "auc_pr": "float (optional)"
  },
  "explainability_method": "enum: [EBM_native, SHAP, GAM_native] (required)",
  "feature_importance": {
    "feature_name": "float (contribution score)"
  },
  "proof_pack_id": "string (required)",
  "lineage": {
    "parent_model": "string (model_id of previous version, or null)",
    "training_script": "string (path to training script)",
    "training_data_source": "string (description of data source)"
  },
  "governance": {
    "alex_approval": "boolean (required)",
    "approval_date": "ISO 8601 datetime (required)",
    "reviewer": "string (ALEX-GID-08)"
  },
  "deployment": {
    "shadow_mode_start": "ISO 8601 datetime",
    "shadow_mode_end": "ISO 8601 datetime",
    "production_start": "ISO 8601 datetime",
    "production_certified": "ISO 8601 datetime or null"
  }
}
```

---

## 4. GOVERNANCE CHECKPOINTS

### Checkpoint 1: Proposal Review (ALEX)
- ✅ Model type is glass-box
- ✅ Monotonicity constraints defined
- ✅ Evaluation plan is sound

### Checkpoint 2: Training Approval (ALEX)
- ✅ Calibration metrics pass thresholds
- ✅ Monotonicity validated
- ✅ Explainability artifacts generated
- ✅ Lineage documented
- ✅ ProofPack created

### Checkpoint 3: Shadow Mode Review (ALEX + Maggie)
- ✅ Shadow mode duration sufficient (7-14 days)
- ✅ Divergence rate acceptable (< 15%)
- ✅ No operational issues

### Checkpoint 4: Rollout Review (ALEX + Business)
- ✅ Each rollout stage validated
- ✅ Business metrics stable
- ✅ Operational metrics stable

### Checkpoint 5: Production Certification (ALEX)
- ✅ 30+ days in production
- ✅ Zero rollbacks
- ✅ Metrics stable
- ✅ Governance compliance verified

---

## 5. ALLOWED MODEL TYPES (GLASS-BOX ONLY)

| Model Type | Explainability | Monotonicity | Calibration | ALEX Approval |
|------------|----------------|--------------|-------------|---------------|
| **EBM** (Explainable Boosting Machine) | ✅ Native | ✅ Supported | ✅ Good | **APPROVED** |
| **GAM** (Generalized Additive Model) | ✅ Native | ✅ Supported | ✅ Excellent | **APPROVED** |
| **Logistic Regression** | ✅ Coefficients | ✅ Linear | ✅ Excellent | **APPROVED** |
| **Monotone GBDT** | ✅ SHAP required | ✅ Enforced | ⚠️ Needs calibration | **CONDITIONAL** |
| **Isolation Forest** | ⚠️ Limited | ❌ N/A | ❌ N/A | **UPSTREAM ONLY** |
| **GNN** (Graph Neural Network) | ⚠️ Limited | ❌ Not enforced | ❌ Poor | **FEATURE GEN ONLY** |
| **Random Forest** | ❌ Opaque | ❌ Not enforced | ⚠️ Moderate | **BLOCKED** |
| **XGBoost** (default) | ❌ Opaque | ❌ Not enforced | ⚠️ Needs calibration | **BLOCKED** |
| **Neural Networks** | ❌ Black-box | ❌ Not enforced | ❌ Poor | **BLOCKED** |

**Legend:**
- ✅ Excellent support
- ⚠️ Conditional/limited support
- ❌ Not suitable

---

## 6. MONITORING & ALERTING

### Production Model Monitoring

**Real-time Metrics:**
- Prediction latency (p50, p95, p99)
- Error rate
- Score distribution
- Feature distribution drift

**Batch Metrics (daily):**
- Calibration error
- Feature importance drift
- Business outcome correlation

**Alerts:**
```yaml
alerts:
  - name: "Calibration Degradation"
    condition: "calibration_error > 0.08"
    action: "Page on-call ML engineer"

  - name: "Feature Drift"
    condition: "feature_drift_score > 0.15"
    action: "Slack alert to ML team"

  - name: "Prediction Latency Spike"
    condition: "prediction_latency_p99 > 500ms"
    action: "Page on-call DevOps + ML"
```

---

## 7. ROLLBACK PROCEDURES

### When to Rollback

- Calibration degrades beyond threshold
- Business metrics regress (approval rates, loss rates)
- Operational issues (latency, errors, crashes)
- Unexpected score distribution changes
- Feature importance drift beyond threshold

### Rollback Process

```python
# 1. Immediate rollback to previous model
def emergency_rollback(current_model_id, previous_model_id):
    logger.critical(f"Emergency rollback: {current_model_id} → {previous_model_id}")

    # Switch model in production
    set_production_model(previous_model_id)

    # Log event
    log_governance_event({
        "event": "MODEL_ROLLBACK",
        "from_model": current_model_id,
        "to_model": previous_model_id,
        "reason": "Governance violation or performance degradation"
    })

    # Alert stakeholders
    alert_ml_team("Model rollback executed")
    alert_business_stakeholders("Risk model reverted to previous version")

# 2. Investigation
# - Analyze logs and metrics
# - Identify root cause
# - Document findings

# 3. Remediation
# - Fix model issues
# - Retrain if necessary
# - Restart lifecycle from Stage 2 or 3
```

---

## 8. DOCUMENTATION REQUIREMENTS

### Training Report Template

```markdown
# Model Training Report: [model_id]

## Executive Summary
- Model type: [EBM/GAM/LogReg/etc]
- Training date: [ISO 8601]
- Purpose: [business justification]
- Status: [Approved/Pending/Rejected]

## Data
- Training data: [description, hash]
- Sample size: [N rows]
- Date range: [start - end]
- Feature count: [N features]

## Model Architecture
- Model type: [details]
- Hyperparameters: [list]
- Monotonicity constraints: [table]

## Performance Metrics
- Brier score: [value]
- Log loss: [value]
- Calibration error: [value]
- AUC-ROC: [value]
- AUC-PR: [value]

## Explainability
- Method: [EBM_native/SHAP/etc]
- Top 10 features: [table with importance scores]
- Feature interaction effects: [if applicable]

## Governance
- ALEX approval: [Yes/No]
- Approval date: [ISO 8601]
- ProofPack ID: [pp_...]

## Next Steps
- Shadow mode deployment: [date]
- Monitoring plan: [description]
```

---

## 9. LIFECYCLE GOVERNANCE METRICS

### Key Performance Indicators

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Models in production | N/A | 1 | ✅ |
| Models in shadow mode | N/A | 1 | ✅ |
| Models in development | N/A | 0 | ✅ |
| Governance violations | 0 | 0 | ✅ |
| Rollback events (30d) | 0 | 0 | ✅ |
| Average shadow mode duration | 7-14 days | 10 days | ✅ |
| Average deployment time | < 30 days | 21 days | ✅ |

---

## 10. CHANGELOG

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2025-12-11 | Initial ML Lifecycle Governance (ALEX GID-08 activation) |

---

## 11. REFERENCES

- [ALEX Protection Manual](./ALEX_PROTECTION_MANUAL.md)
- [ChainIQ Governance Rules](./CHAINIQ_GOVERNANCE_RULES.md)
- [Model Proposal Template](../templates/model_proposal_template.md)
- [Training Report Template](../templates/training_report_template.md)

---

**ALEX (GID-08) - No Model Without Proof • Glass-Box Only • Lifecycle Enforced**
