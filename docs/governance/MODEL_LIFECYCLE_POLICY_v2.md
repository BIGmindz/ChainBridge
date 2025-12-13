# Model Lifecycle Policy v2.0
**Governance ID: GID-08-LIFECYCLE-V2 | Classification: CRITICAL | Owner: ALEX (GID-08)**

## Executive Summary

This document defines the complete model lifecycle policy for ChainBridge ML systems. Version 2.0 extends the original lifecycle with enhanced ingestion governance, shadow mode requirements, and post-quantum cryptography (PQC) migration schedules.

**Core Principle:**
> "No model reaches production without passing every governance gate. Shadow mode is mandatory, not optional."

---

## 1. LIFECYCLE STATE MACHINE

### 1.1 State Diagram

```
┌─────────────┐      ┌─────────────┐      ┌──────────────┐
│  PROPOSAL   │──────│  PROTOTYPE  │──────│   TRAINING   │
│   (Draft)   │      │  (Dev Env)  │      │  (Approved)  │
└─────────────┘      └─────────────┘      └──────────────┘
                                                  │
                                                  ▼
┌─────────────┐      ┌─────────────┐      ┌──────────────┐
│ PRODUCTION  │◄─────│  STAGING    │◄─────│   SHADOW     │
│  (Frozen)   │      │ (Canary)    │      │  (Parallel)  │
└─────────────┘      └─────────────┘      └──────────────┘
       │                                         │
       │         ┌─────────────┐                 │
       └────────►│  RETIRED    │◄────────────────┘
                 │ (Archived)  │  (Rollback)
                 └─────────────┘
```

### 1.2 State Definitions

| State | Description | Min Duration | Exit Criteria |
|-------|-------------|--------------|---------------|
| **PROPOSAL** | Model concept documented | 1 day | Approved by Maggie (GID-02) |
| **PROTOTYPE** | Initial implementation | 3 days | Metrics baseline established |
| **TRAINING** | Production training run | 2 days | Training approved, lineage captured |
| **SHADOW** | Parallel scoring (no client impact) | 7-14 days | Drift < 0.15, metrics pass |
| **STAGING** | Canary deployment (5-10% traffic) | 3-7 days | No degradation detected |
| **PRODUCTION** | Full deployment | Indefinite | Next version enters shadow |
| **RETIRED** | Model archived | Permanent | Audit trail preserved |

---

## 2. REQUIRED EVALUATION METRICS

### 2.1 Mandatory Metrics by Stage

**SHADOW Stage Requirements:**

| Metric | Threshold | Enforcement |
|--------|-----------|-------------|
| **Brier Score** | < 0.10 | BLOCK if exceeded |
| **Precision@10%** | > 0.20 | BLOCK if below |
| **AUC-ROC** | > 0.70 | BLOCK if below |
| **Calibration Slope** | 0.8 - 1.2 | WARNING outside range |
| **Mean Absolute Delta** | < 0.15 | BLOCK if exceeded |
| **P95 Absolute Delta** | < 0.25 | WARNING if exceeded |
| **P99 Absolute Delta** | < 0.35 | BLOCK if exceeded |

**STAGING Stage Requirements:**

| Metric | Threshold | Enforcement |
|--------|-----------|-------------|
| **P99 Latency** | < 500ms | BLOCK if exceeded |
| **Error Rate** | < 0.1% | BLOCK if exceeded |
| **Score Distribution KL** | < 0.10 | WARNING if exceeded |
| **Feature Drift** | < 0.05 per feature | WARNING if exceeded |

**PRODUCTION Stage Requirements:**

| Metric | Threshold | Enforcement |
|--------|-----------|-------------|
| **Model Staleness** | < 90 days | WARNING at 60 days |
| **Calibration Drift** | < 0.10 | Trigger re-calibration |
| **Score Stability** | σ < 0.05 weekly | WARNING if exceeded |

### 2.2 Metric Validation Code

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ModelMetrics:
    """ALEX-governed model evaluation metrics"""

    # Calibration
    brier_score: float
    calibration_slope: float
    calibration_intercept: float

    # Discrimination
    auc_roc: float
    precision_at_10: float
    recall_at_10: float

    # Drift (shadow mode)
    mean_abs_delta: Optional[float] = None
    p95_abs_delta: Optional[float] = None
    p99_abs_delta: Optional[float] = None

    # Performance
    p99_latency_ms: Optional[float] = None
    error_rate: Optional[float] = None

    def validate_shadow_gate(self) -> tuple[bool, list[str]]:
        """Validate metrics for shadow-to-staging promotion"""
        violations = []

        if self.brier_score >= 0.10:
            violations.append(f"Brier score {self.brier_score:.3f} >= 0.10")

        if self.precision_at_10 <= 0.20:
            violations.append(f"Precision@10% {self.precision_at_10:.3f} <= 0.20")

        if self.auc_roc <= 0.70:
            violations.append(f"AUC-ROC {self.auc_roc:.3f} <= 0.70")

        if not (0.8 <= self.calibration_slope <= 1.2):
            violations.append(f"Calibration slope {self.calibration_slope:.3f} outside [0.8, 1.2]")

        if self.mean_abs_delta and self.mean_abs_delta >= 0.15:
            violations.append(f"Mean abs delta {self.mean_abs_delta:.3f} >= 0.15")

        if self.p99_abs_delta and self.p99_abs_delta >= 0.35:
            violations.append(f"P99 abs delta {self.p99_abs_delta:.3f} >= 0.35")

        return len(violations) == 0, violations

    def validate_staging_gate(self) -> tuple[bool, list[str]]:
        """Validate metrics for staging-to-production promotion"""
        violations = []

        if self.p99_latency_ms and self.p99_latency_ms >= 500:
            violations.append(f"P99 latency {self.p99_latency_ms:.0f}ms >= 500ms")

        if self.error_rate and self.error_rate >= 0.001:
            violations.append(f"Error rate {self.error_rate:.4f} >= 0.1%")

        return len(violations) == 0, violations
```

---

## 3. SHADOW MODE REQUIREMENTS

### 3.1 Shadow Duration Rules

| Model Type | Min Shadow Duration | Min Sample Size |
|------------|---------------------|-----------------|
| **Risk Scoring** | 14 days | 25,000 requests |
| **Classification** | 7 days | 10,000 requests |
| **Anomaly Detection** | 21 days | 50,000 requests |
| **Ranking** | 14 days | 15,000 requests |

### 3.2 Shadow Completion Checklist

```python
def validate_shadow_completion(model_version: str) -> tuple[bool, dict]:
    """
    ALEX governance check for shadow mode completion
    """
    checklist = {
        "min_duration_met": False,
        "min_samples_met": False,
        "drift_severity_acceptable": False,
        "metrics_pass_gate": False,
        "no_integrity_violations": False,
        "no_recent_escalations": False,
        "performance_budget_met": False,
        "statistical_tests_documented": False,
    }

    shadow_data = get_shadow_data(model_version)

    # Check 1: Duration
    days_elapsed = (datetime.utcnow() - shadow_data.start_date).days
    checklist["min_duration_met"] = days_elapsed >= 7

    # Check 2: Sample size
    checklist["min_samples_met"] = shadow_data.sample_count >= 10000

    # Check 3: Drift severity
    drift_severity = shadow_data.drift_severity
    checklist["drift_severity_acceptable"] = drift_severity in ["LOW", "MEDIUM"]

    # Check 4: Metrics gate
    metrics = shadow_data.metrics
    passed, _ = metrics.validate_shadow_gate()
    checklist["metrics_pass_gate"] = passed

    # Check 5: Integrity violations
    violations = get_integrity_violations(model_version, days=7)
    checklist["no_integrity_violations"] = len(violations) == 0

    # Check 6: Recent escalations
    escalations = get_escalations(model_version, days=7)
    checklist["no_recent_escalations"] = len(escalations) == 0

    # Check 7: Performance budget
    checklist["performance_budget_met"] = shadow_data.p99_latency_ms < 750

    # Check 8: Statistical documentation
    checklist["statistical_tests_documented"] = shadow_data.statistical_tests is not None

    # All must pass
    all_passed = all(checklist.values())

    return all_passed, checklist
```

---

## 4. REQUIRED MODEL METADATA (10 FIELDS)

### 4.1 Metadata Schema

Every model artifact MUST include these 10 fields:

```python
@dataclass
class ModelMetadata:
    """
    ALEX Rule #15: Model Metadata Minimum
    All 10 fields required for production deployment
    """

    # 1. Identity
    model_id: str  # Unique identifier (UUID)

    # 2. Type classification
    model_type: str  # "EBM", "GAM", "LogisticRegression", "MonotoneGBDT"

    # 3. Version
    version: str  # Semantic version (e.g., "0.3.0")

    # 4. Training timestamp
    training_date: datetime  # ISO 8601 UTC timestamp

    # 5. Data lineage
    training_data_hash: str  # SHA-256 of training dataset

    # 6. Constraints
    monotonicity_constraints: dict  # {"feature": "increasing"|"decreasing"|"none"}

    # 7. Calibration proof
    calibration_metrics: dict  # {"brier": float, "slope": float, "intercept": float}

    # 8. Explainability
    explainability_method: str  # "global_feature_importance", "local_shap", "ebm_native"

    # 9. Governance proof
    proof_pack_id: str  # ProofPack artifact ID

    # 10. Lineage chain
    lineage: dict  # {"parent_model": str, "training_script": str, "config_hash": str}
```

### 4.2 Metadata Validation

```python
REQUIRED_METADATA_FIELDS = [
    "model_id",
    "model_type",
    "version",
    "training_date",
    "training_data_hash",
    "monotonicity_constraints",
    "calibration_metrics",
    "explainability_method",
    "proof_pack_id",
    "lineage"
]

ALLOWED_MODEL_TYPES = ["EBM", "GAM", "LogisticRegression", "MonotoneGBDT"]

def validate_model_metadata(metadata: dict) -> tuple[bool, list[str]]:
    """
    ALEX Rule #15 validation
    """
    violations = []

    # Check all required fields present
    missing = [f for f in REQUIRED_METADATA_FIELDS if f not in metadata]
    if missing:
        violations.append(f"Missing required fields: {missing}")

    # Check model type
    if metadata.get("model_type") not in ALLOWED_MODEL_TYPES:
        violations.append(
            f"Invalid model_type: {metadata.get('model_type')}. "
            f"Allowed: {ALLOWED_MODEL_TYPES}"
        )

    # Check calibration metrics present
    cal_metrics = metadata.get("calibration_metrics", {})
    required_cal = ["brier", "slope", "intercept"]
    missing_cal = [m for m in required_cal if m not in cal_metrics]
    if missing_cal:
        violations.append(f"Missing calibration metrics: {missing_cal}")

    # Check monotonicity constraints non-empty
    mono = metadata.get("monotonicity_constraints", {})
    if not mono:
        violations.append("monotonicity_constraints cannot be empty")

    # Check proof_pack_id format
    proof_id = metadata.get("proof_pack_id", "")
    if not proof_id.startswith("PP-"):
        violations.append(f"Invalid proof_pack_id format: {proof_id}")

    return len(violations) == 0, violations
```

---

## 5. INGESTION LIFECYCLE INTEGRATION

### 5.1 Feature Catalog Governance

Models MUST consume features from the governed feature catalog:

```yaml
# Feature catalog validation for model ingestion
feature_governance:
  catalog_path: "chainiq-service/config/feature_catalog.yaml"
  validation_rules:
    - all_features_in_catalog: true
    - null_handling_defined: true
    - timezone_utc_enforced: true
    - no_data_leakage_patterns: true

  schema_change_protocol:
    requires_approval: true
    approval_tag: "[ALEX-APPROVAL]"
    migration_notes_required: true
```

### 5.2 Ingestion-Model Linkage

```python
def validate_model_feature_linkage(
    model_version: str,
    feature_catalog: dict
) -> tuple[bool, list[str]]:
    """
    Ensure model only uses features from governed catalog
    """
    model_features = get_model_input_features(model_version)
    catalog_features = set(feature_catalog.keys())

    violations = []

    # Check all model features exist in catalog
    unknown_features = model_features - catalog_features
    if unknown_features:
        violations.append(
            f"Model uses features not in catalog: {unknown_features}"
        )

    # Check feature types match
    for feature in model_features & catalog_features:
        expected_dtype = feature_catalog[feature]["dtype"]
        actual_dtype = get_model_feature_dtype(model_version, feature)
        if expected_dtype != actual_dtype:
            violations.append(
                f"Feature '{feature}' dtype mismatch: "
                f"catalog={expected_dtype}, model={actual_dtype}"
            )

    return len(violations) == 0, violations
```

---

## 6. POST-QUANTUM CRYPTOGRAPHY (PQC) MIGRATION SCHEDULE

### 6.1 Migration Timeline

| Phase | Timeline | Scope | Deliverables |
|-------|----------|-------|--------------|
| **Phase 0: Assessment** | Q1 2026 | Inventory all crypto usage | Crypto audit report |
| **Phase 1: Dual-Mode** | Q2 2026 | Add PQC alongside classical | Dual signature support |
| **Phase 2: Primary PQC** | Q3 2026 | PQC becomes primary | Classical as fallback |
| **Phase 3: PQC-Only** | Q4 2026 | Remove classical crypto | Full PQC deployment |

### 6.2 PQC Algorithm Standards

**Approved PQC Algorithms:**

| Use Case | Algorithm | Key Size | Notes |
|----------|-----------|----------|-------|
| **Digital Signatures** | Dilithium-3 | 1952 bytes | Primary choice |
| **Digital Signatures** | SPHINCS+-SHA256-128f | 17,088 bytes | Stateless alternative |
| **Key Exchange** | Kyber-768 | 1,088 bytes | ML-KEM standard |
| **Encryption** | AES-256 + Kyber-768 | Hybrid | For data at rest |

**Blocked Algorithms (after Q3 2026):**

| Algorithm | Reason | Migration Path |
|-----------|--------|----------------|
| RSA-2048/4096 | Quantum vulnerable | → Dilithium-3 |
| ECDSA (P-256/P-384) | Quantum vulnerable | → Dilithium-3 |
| ECDH | Quantum vulnerable | → Kyber-768 |
| DSA | Quantum vulnerable | → Dilithium-3 |

### 6.3 Model Artifact Signing

```python
# PQC signing for model artifacts
from pqcrypto.sign import dilithium3

class ModelArtifactSigner:
    """
    ALEX Rule #3: Quantum-ready cryptography
    All model artifacts must be signed with PQC
    """

    def __init__(self, private_key: bytes):
        self.private_key = private_key

    def sign_model(self, model_artifact: bytes) -> bytes:
        """Sign model artifact with Dilithium-3"""
        signature = dilithium3.sign(model_artifact, self.private_key)
        return signature

    @staticmethod
    def verify_signature(
        model_artifact: bytes,
        signature: bytes,
        public_key: bytes
    ) -> bool:
        """Verify model artifact signature"""
        try:
            dilithium3.verify(signature, model_artifact, public_key)
            return True
        except Exception:
            return False
```

### 6.4 Migration Governance

```yaml
# PQC Migration Configuration
pqc_migration:
  current_phase: "Phase 0"
  target_completion: "2026-Q4"

  enforcement:
    phase_0:
      - audit_all_crypto_usage
      - document_migration_plan
    phase_1:
      - dual_mode_required_for_new_code
      - classical_allowed_as_fallback
    phase_2:
      - pqc_primary_for_new_code
      - classical_fallback_only
    phase_3:
      - pqc_only_enforced
      - classical_blocked_in_ci

  model_signing:
    algorithm: "Dilithium-3"
    key_rotation: "90 days"
    signature_verification: "MANDATORY"

  affected_services:
    - chainiq-service  # Model signing, proof verification
    - chainpay-service  # Settlement signatures, custody proofs
    - chainboard-service  # API authentication
```

---

## 7. GOVERNANCE GATES

### 7.1 Stage Transition Gates

```python
class LifecycleGate:
    """ALEX-governed stage transition gates"""

    @staticmethod
    def proposal_to_prototype(model_id: str) -> tuple[bool, list[str]]:
        """Gate: PROPOSAL → PROTOTYPE"""
        checks = []

        # Proposal document exists
        if not proposal_exists(model_id):
            checks.append("Model proposal document required")

        # ML team approval
        if not has_approval(model_id, approver="GID-02"):
            checks.append("Maggie (GID-02) approval required")

        return len(checks) == 0, checks

    @staticmethod
    def training_to_shadow(model_id: str) -> tuple[bool, list[str]]:
        """Gate: TRAINING → SHADOW"""
        checks = []

        # Metadata complete
        metadata = get_model_metadata(model_id)
        passed, violations = validate_model_metadata(metadata)
        if not passed:
            checks.extend(violations)

        # Training lineage captured
        if not metadata.get("training_data_hash"):
            checks.append("Training data hash required")

        # Model type allowed
        if metadata.get("model_type") not in ALLOWED_MODEL_TYPES:
            checks.append("Model type must be glass-box (EBM/GAM/LogReg)")

        return len(checks) == 0, checks

    @staticmethod
    def shadow_to_staging(model_id: str) -> tuple[bool, list[str]]:
        """Gate: SHADOW → STAGING"""
        passed, checklist = validate_shadow_completion(model_id)

        if not passed:
            failures = [k for k, v in checklist.items() if not v]
            return False, [f"Shadow completion failed: {failures}"]

        return True, []

    @staticmethod
    def staging_to_production(model_id: str) -> tuple[bool, list[str]]:
        """Gate: STAGING → PRODUCTION"""
        checks = []

        # Staging metrics pass
        metrics = get_staging_metrics(model_id)
        passed, violations = metrics.validate_staging_gate()
        if not passed:
            checks.extend(violations)

        # ALEX approval for production
        if not has_approval(model_id, approver="GID-08"):
            checks.append("ALEX (GID-08) production approval required")

        # ProofPack exists
        if not proofpack_exists(model_id):
            checks.append("ProofPack artifact required")

        return len(checks) == 0, checks
```

---

## 8. ROLLBACK PROCEDURES

### 8.1 Automatic Rollback Triggers

| Trigger | Threshold | Action |
|---------|-----------|--------|
| **Error Rate Spike** | > 1% for 5 min | Immediate rollback |
| **Latency Degradation** | P99 > 1000ms | Immediate rollback |
| **Score Distribution Shift** | KL > 0.25 | Alert + manual review |
| **Integrity Violations** | > 100/hour | Immediate rollback |
| **Calibration Drift** | slope < 0.6 or > 1.4 | Alert + scheduled rollback |

### 8.2 Rollback Procedure

```python
def execute_model_rollback(
    current_version: str,
    target_version: str,
    reason: str
) -> dict:
    """
    ALEX-governed model rollback procedure
    """
    rollback_record = {
        "timestamp": datetime.utcnow().isoformat(),
        "from_version": current_version,
        "to_version": target_version,
        "reason": reason,
        "initiated_by": "ALEX_AUTOMATED",
        "status": "IN_PROGRESS"
    }

    try:
        # 1. Disable current model
        disable_model(current_version)

        # 2. Verify target model exists and is valid
        if not model_exists(target_version):
            raise RollbackError(f"Target model {target_version} not found")

        # 3. Enable target model
        enable_model(target_version)

        # 4. Verify traffic routing
        verify_traffic_routing(target_version)

        # 5. Alert stakeholders
        alert_rollback_complete({
            "from": current_version,
            "to": target_version,
            "reason": reason
        })

        rollback_record["status"] = "COMPLETED"

    except Exception as e:
        rollback_record["status"] = "FAILED"
        rollback_record["error"] = str(e)

        # Escalate to on-call
        page_on_call({
            "alert": "MODEL_ROLLBACK_FAILED",
            "error": str(e),
            "severity": "P0"
        })

    # Log rollback for audit
    log_governance_event(rollback_record)

    return rollback_record
```

---

## 9. DOCUMENTATION COMPLIANCE

### 9.1 Required Documentation by Stage

| Stage | Required Documents |
|-------|-------------------|
| **PROPOSAL** | Model proposal (goals, approach, risks) |
| **PROTOTYPE** | Feature analysis, baseline metrics |
| **TRAINING** | Training config, hyperparameters, data summary |
| **SHADOW** | Drift report, statistical significance analysis |
| **STAGING** | Canary results, performance report |
| **PRODUCTION** | Production metrics dashboard, runbook |
| **RETIRED** | Retirement justification, migration notes |

### 9.2 Documentation Schema

```yaml
# Model documentation structure
documentation:
  proposal:
    required_sections:
      - objective
      - business_justification
      - technical_approach
      - risk_assessment
      - success_criteria
    approval_required: true

  training:
    required_sections:
      - training_data_description
      - feature_list
      - hyperparameters
      - validation_strategy
      - training_metrics
    lineage_capture: mandatory

  shadow:
    required_sections:
      - drift_analysis
      - statistical_tests
      - integrity_violations_review
      - recommendation
    alex_review: required

  production:
    required_sections:
      - deployment_runbook
      - monitoring_dashboard_link
      - rollback_procedure
      - on_call_contacts
    proofpack: mandatory
```

---

## 10. ACCEPTANCE CRITERIA

**Model lifecycle is governance-compliant when:**

1. ✅ All state transitions pass governance gates
2. ✅ Shadow mode minimum duration enforced (7+ days)
3. ✅ All 10 metadata fields present and valid
4. ✅ Metrics meet thresholds (Brier < 0.10, AUC > 0.70, etc.)
5. ✅ Feature catalog linkage validated
6. ✅ PQC migration schedule followed
7. ✅ Rollback procedures tested
8. ✅ Documentation complete for each stage
9. ✅ ProofPack generated before production
10. ✅ ALEX approval obtained for production deployment

---

## 11. AGENT OBLIGATIONS

### Maggie (GID-02) - ML Engineering

**Must:**
- Approve model proposals before prototype
- Ensure glass-box model types only
- Complete all documentation requirements
- Validate calibration metrics

**Cannot:**
- Deploy models without shadow mode
- Skip governance gates
- Use black-box models (XGBoost, RandomForest, etc.)

### Cody (GID-01) - Backend Engineering

**Must:**
- Implement feature catalog validation
- Ensure metadata schema compliance
- Support rollback procedures
- Implement PQC signing

**Cannot:**
- Deploy models without metadata validation
- Skip feature catalog checks

### Dan (GID-04) - DevOps

**Must:**
- Implement CI/CD governance checks
- Monitor rollback triggers
- Manage PQC key rotation

**Cannot:**
- Bypass governance gates in deployment
- Deploy without staging validation

---

## 12. CHANGELOG

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2025-12-11 | Initial ML Lifecycle Governance |
| v2.0 | 2025-12-11 | PAC-ALEX-GOV-022: Added ingestion integration, PQC migration, enhanced metrics |

---

## 13. REFERENCES

- [ALEX Protection Manual](./ALEX_PROTECTION_MANUAL.md)
- [Model Ingestion Governance](./MODEL_INGESTION_GOVERNANCE.md)
- [Shadow Mode Governance](./SHADOW_MODE_GOVERNANCE.md)
- [Security Baseline v1](./SECURITY_BASELINE_V1.md)
- [ChainIQ Governance Rules](./CHAINIQ_GOVERNANCE_RULES.md)

---

**ALEX (GID-08) - Every Gate Must Pass • Shadow Mode Is Mandatory • No Ungoverned Models**
