# ALEX Protection Manual v1.0
**Governance ID: GID-08 | Classification: PROTECTION MODE | Status: ACTIVE**

## Executive Summary

ALEX (Autonomous Logic Enforcement eXecutive) is the master governance layer for the ChainBridge operating system. This manual defines the 11 hard constraints, enforcement mechanisms, and operational protocols that ensure ChainBridge operates as a financial-grade, auditable, and self-governing event settlement network.

**Core Principle:**
> "Speed without proof gets blocked. Proof without pipes doesn't scale. Pipes without cash don't settle."

---

## 1. GOVERNANCE ARCHITECTURE

### 1.1 Protection Mode Overview

When ALEX operates in **Protection Mode**, all code changes, model deployments, and architectural decisions are subject to strict governance gates. No agent (Cody, Maggie, Sonny, Dan, etc.) may override ALEX enforcement rules.

**Protection Mode Guarantees:**
- ✅ Financial-grade code quality
- ✅ Glass-box ML models only
- ✅ Quantum-safe cryptography
- ✅ Deterministic settlement logic
- ✅ Complete auditability
- ✅ Zero unbounded attack surface

### 1.2 Governance Scope

ALEX governs the following ChainBridge components:

| Component | Governance Domain | Enforcement Level |
|-----------|-------------------|-------------------|
| **ChainPay** | Settlement determinism, token logic, PQC compliance | **CRITICAL** |
| **ChainIQ** | ML lifecycle, glass-box constraints, calibration | **CRITICAL** |
| **ChainSense** | Data provenance, sensor integrity, IoT validation | **HIGH** |
| **ChainBoard** | UI security, token handling, data exposure | **HIGH** |
| **OC (Operating Console)** | Admin controls, audit logs, privilege management | **CRITICAL** |
| **ChainDocs** | ProofPack generation, document integrity | **HIGH** |

---

## 2. THE 11 HARD CONSTRAINTS (NON-NEGOTIABLE)

### Rule 1: Glass-Box Financial Models Only

**PROHIBITED:**
- ❌ Opaque neural networks
- ❌ Black-box ML models
- ❌ Uncalibrated probability outputs
- ❌ Non-monotonic risk scoring
- ❌ Models lacking explainability

**ALLOWED:**
- ✅ Explainable Boosting Machines (EBMs)
- ✅ Generalized Additive Models (GAMs)
- ✅ Logistic Regression with L1/L2 regularization
- ✅ Monotone Gradient Boosted Decision Trees (with monotonicity constraints)
- ✅ Isolation Forest (anomaly detection upstream only)
- ✅ Graph Neural Networks (GNNs) as feature generators only, never final scoring

**Enforcement:**
- All model training must record monotonicity constraints
- All deployed models must generate human-readable explanations
- All risk scores must include feature contribution breakdowns

**Validation:**
```python
# All ChainIQ models must pass this validation
def validate_model_governance(model, model_metadata):
    assert model_metadata.get('model_type') in ALLOWED_MODEL_TYPES
    assert model_metadata.get('monotonicity_constraints') is not None
    assert model_metadata.get('calibration_metrics') is not None
    assert model_metadata.get('explainability_method') in ['SHAP', 'EBM_native', 'GAM_native']
    assert model_metadata.get('proof_pack_id') is not None
```

---

### Rule 2: Proof Over Performance

**Mantra:**
> "Speed without proof gets blocked. Proof without pipes doesn't scale. Pipes without cash don't settle."

**Requirements:**
- Every financial transaction must have a **ChainIQ risk score**
- Every settlement must have a **ProofPack artifact**
- Every state transition must be **event-sourced**
- Every custody transfer must have **cryptographic proof**

**Enforcement:**
- No ChainPay settlement may execute without a risk score
- No ProofPack may be generated without a complete event chain
- No audit trail may have gaps or missing events

---

### Rule 3: Quantum-Ready Cryptography

**PROHIBITED:**
- ❌ RSA (vulnerable to Shor's algorithm)
- ❌ ECDSA (vulnerable to quantum attacks)
- ❌ DH key exchange (quantum-vulnerable)
- ❌ Any non-post-quantum cryptographic primitive

**ALLOWED:**
- ✅ Hash-based signatures (XMSS, LMS, SPHINCS+)
- ✅ Lattice-based schemes (Dilithium, Kyber)
- ✅ Code-based cryptography (Classic McEliece)
- ✅ PQC key rotation functions
- ✅ Hybrid schemes (classical + PQC)

**Enforcement:**
- All new cryptographic usage must be declared in `docs/governance/CRYPTO_REGISTRY.md`
- All key generation must use PQC-ready libraries
- All signature verification must support PQC algorithms

**Migration Timeline:**
- Q1 2026: All new code must use PQC primitives
- Q2 2026: Begin migration of existing RSA/ECDSA usage
- Q3 2026: Complete PQC transition
- Q4 2026: Deprecate all classical cryptography

---

### Rule 4: No Unbounded Attack Surface

**PROHIBITED:**
- ❌ `eval()`, `exec()` on untrusted input
- ❌ `yaml.load()` without `SafeLoader`
- ❌ Dynamic imports from user-controlled paths
- ❌ Schema-less persistence (no JSON blobs without schema)
- ❌ Uncontrolled network calls (must use allow-lists)
- ❌ Direct browser `localStorage` for sensitive data

**ENFORCEMENT:**
- All user input must be validated against schemas
- All imports must be static or from allow-listed paths
- All YAML loading must use `yaml.safe_load()`
- All network destinations must be in `config/allowed_endpoints.yaml`
- All sensitive data in browser must use secure, encrypted storage

**Code Review Checklist:**
```python
# ❌ BLOCKED
data = eval(user_input)
config = yaml.load(file)
module = __import__(user_provided_path)

# ✅ ALLOWED
data = json.loads(user_input)  # + schema validation
config = yaml.safe_load(file)
module = importlib.import_module(ALLOWED_MODULES[user_choice])
```

---

### Rule 5: All DB Models Must Have Canonical Fields

**REQUIRED FIELDS (every table):**
```python
canonical_id: str  # Unique, immutable identifier
created_at: datetime  # Immutable creation timestamp
updated_at: datetime  # Last modification timestamp
version: int  # Optimistic locking version
source: str  # Data provenance (system/user/import)
```

**ADDITIONAL REQUIRED (financial tables):**
```python
proof_pack_id: str  # Link to ProofPack artifact
```

**ENFORCEMENT:**
- All SQLAlchemy models must inherit from `CanonicalBaseModel`
- All migrations must include these fields
- All API responses must expose `canonical_id`, not internal IDs

**Example:**
```python
class ShipmentFinancing(CanonicalBaseModel):
    __tablename__ = 'shipment_financings'

    # Canonical fields (inherited)
    # canonical_id, created_at, updated_at, version, source

    # Financial fields
    proof_pack_id = Column(String, nullable=False)
    shipment_id = Column(String, nullable=False)
    amount = Column(Numeric, nullable=False)
    # ... other fields
```

---

### Rule 6: ChainPay Settlement Execution Must Be Deterministic

**REQUIREMENTS:**
- ✅ All settlement logic must be pure functions
- ✅ All state transitions must be deterministic
- ✅ All settlement triggers must be event-driven
- ✅ All settlements must have ChainIQ risk scores
- ✅ All settlement failures must be retryable

**PROHIBITED:**
- ❌ Non-deterministic randomness in settlement logic
- ❌ Non-verifiable oracle inputs
- ❌ Settlements without event chains
- ❌ Settlements without risk scores
- ❌ Side-effects during settlement calculation

**ENFORCEMENT:**
```python
# All settlement functions must follow this pattern
def calculate_settlement(
    event_chain: List[Event],
    risk_score: RiskScore,
    pricing_snapshot: PricingData
) -> SettlementResult:
    """
    Pure function: same inputs -> same outputs
    No database calls, no API calls, no randomness
    """
    assert event_chain, "Cannot settle without event chain"
    assert risk_score, "Cannot settle without risk score"
    assert pricing_snapshot, "Cannot settle without pricing data"

    # Deterministic calculation only
    return SettlementResult(...)
```

---

### Rule 7: ML Lifecycle Governance

**REQUIRED STAGES:**
1. **Proposal** - Architecture document, governance review
2. **Prototype** - Training stubs, shadow scoring
3. **Training Approval** - Metrics, calibration, explainability
4. **Shadow Mode** - Dual scoring (old vs new model)
5. **Controlled Deployment** - Gradual rollout with monitoring
6. **Production Freeze** - Versioned, immutable model artifact

**BLOCKED CONDITIONS:**
- ❌ Model deployed without lineage
- ❌ Model deployed without metrics
- ❌ Model deployed without calibration proof
- ❌ Model deployed without monotonicity validation
- ❌ Model deployed without human-readable explanation
- ❌ Model deployed without ProofPack artifact

**METADATA REQUIREMENTS:**
```yaml
model_metadata:
  model_id: "chainiq_risk_v0.2.0"
  model_type: "EBM"
  training_date: "2025-12-11"
  training_data_hash: "sha256:..."
  feature_list: [...]
  monotonicity_constraints:
    - feature: "prior_losses_flag"
      direction: "increasing"
  calibration_metrics:
    brier_score: 0.087
    log_loss: 0.234
  explainability_method: "EBM_native"
  proof_pack_id: "pp_ml_training_20251211_001"
  lineage:
    parent_model: "chainiq_risk_v0.1.0"
    training_script: "chainiq-service/training/train_risk_model_v02.py"
```

---

### Rule 8: CI/CD Governance Hooks

**PR REQUIREMENTS (enforced by GitHub Actions):**
- ✅ Migration notes (if DB changes)
- ✅ Risk assessment section
- ✅ Governance statement
- ✅ Test coverage > 80%
- ✅ No linting errors
- ✅ All governance rules passing

**BLOCKING CONDITIONS:**
- ❌ ChainPay logic changes without settlement correctness proof
- ❌ ChainIQ scoring changes without feature list update
- ❌ Cryptographic changes without PQC compliance check
- ❌ DB schema changes without canonical fields
- ❌ Missing docstrings on public functions

**Workflow Integration:**
```yaml
# .github/workflows/governance_check.yml
- name: ALEX Governance Check
  run: python scripts/governance/alex_check.py
  env:
    ALEX_MODE: protection
    FAIL_ON_VIOLATION: true
```

---

### Rule 9: Multi-Agent Safety Override

**ALEX OVERRIDE AUTHORITY:**

ALEX has veto power over all other agents:

| Agent | Violation Type | ALEX Action |
|-------|---------------|-------------|
| **Cody** | Unsafe backend code | **BLOCK PR** |
| **Maggie** | Black-box ML model | **BLOCK DEPLOYMENT** |
| **Sonny** | Insecure UI component | **BLOCK PR** |
| **Atlas** | Repo-unsafe structural change | **BLOCK PR** |
| **Pax** | Unmanaged token logic | **BLOCK PR** |
| **Sam** | Security threat detected | **ESCALATE + BLOCK** |

**Escalation Path:**
1. Agent proposes change
2. ALEX governance check runs
3. If violation detected → Block + log + notify Benson
4. Agent receives remediation guidance
5. Agent resubmits with fixes
6. ALEX re-validates

---

### Rule 10: No Side-Effects in Import Paths

**PROHIBITED:**
- ❌ Heavy imports in FastAPI startup (e.g., loading ML models at `app = FastAPI()`)
- ❌ ML model loading in module-level globals
- ❌ Database connections at import time
- ❌ File I/O during module import

**ENFORCEMENT:**
```python
# ❌ BLOCKED
import pandas as pd
MODEL = load_heavy_ml_model()  # Runs at import time!

app = FastAPI()

# ✅ ALLOWED
import pandas as pd

app = FastAPI()

@app.on_event("startup")
async def load_model():
    global MODEL
    MODEL = load_heavy_ml_model()  # Runs after app starts
```

**Rationale:**
- Enables fast testing (mocking without heavy loads)
- Prevents circular dependency issues
- Allows graceful degradation

---

### Rule 11: Zero Silent Failures

**PROHIBITED:**
- ❌ `except: pass` (swallows all exceptions)
- ❌ Silent retry loops without logging
- ❌ Returning `None` on critical failures
- ❌ Catching exceptions without re-raising or logging

**ENFORCEMENT:**
```python
# ❌ BLOCKED
try:
    result = critical_operation()
except:
    pass  # Silent failure!

# ✅ ALLOWED
try:
    result = critical_operation()
except OperationError as e:
    logger.error(f"Critical operation failed: {e}", exc_info=True)
    raise  # Re-raise for upstream handling
```

**Logging Requirements:**
- All exceptions must be logged with context
- All retries must be logged with attempt count
- All failures must escalate or alert

---

## 3. ENFORCEMENT MECHANISMS

### 3.1 Pre-Commit Hooks

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run ALEX governance checks
python scripts/governance/alex_precommit_check.py

if [ $? -ne 0 ]; then
  echo "❌ ALEX GOVERNANCE CHECK FAILED"
  echo "Fix violations before committing"
  exit 1
fi
```

### 3.2 GitHub Actions Workflow

See [CI/CD Governance Workflow](#rule-8-cicd-governance-hooks)

### 3.3 Runtime Enforcement

```python
# ChainIQ runtime checks
def enforce_model_governance(model_id: str):
    metadata = get_model_metadata(model_id)

    violations = []

    if metadata.model_type not in ALLOWED_MODEL_TYPES:
        violations.append(f"Disallowed model type: {metadata.model_type}")

    if not metadata.monotonicity_constraints:
        violations.append("Missing monotonicity constraints")

    if violations:
        raise GovernanceViolation(
            f"Model {model_id} violates ALEX rules",
            violations=violations
        )
```

---

## 4. GOVERNANCE WORKFLOW

### 4.1 Standard Development Flow

```
Developer writes code
     ↓
Pre-commit hook runs ALEX checks
     ↓
[PASS] → Commit allowed
[FAIL] → Commit blocked, remediation guidance provided
     ↓
Push to GitHub
     ↓
CI runs full ALEX governance suite
     ↓
[PASS] → PR reviewable
[FAIL] → PR blocked, violations logged
     ↓
Code review + ALEX approval
     ↓
Merge to main
     ↓
Deployment (with runtime governance checks)
```

### 4.2 ML Model Deployment Flow

```
Maggie trains model
     ↓
Generate model metadata + ProofPack
     ↓
ALEX validates:
  - Glass-box constraint
  - Monotonicity
  - Calibration
  - Explainability
     ↓
[PASS] → Shadow mode deployment
     ↓
Dual scoring (old vs new model)
     ↓
Metrics validation (7-14 days)
     ↓
ALEX approves production promotion
     ↓
Production deployment (versioned, immutable)
```

---

## 5. GOVERNANCE AUDIT & REPORTING

### 5.1 Weekly Governance Report

ALEX generates weekly reports:
- ✅ Governance rule compliance rate
- ⚠️ Violations detected and remediated
- 🚫 Blocked PRs and reasons
- 📊 Model governance metrics
- 🔐 Cryptography posture
- 📈 Trends and recommendations

### 5.2 Quarterly Governance Review

- Review all 11 hard constraints
- Update threat model
- Validate PQC migration progress
- Audit ML model lineage
- Verify settlement determinism
- Update governance policies

---

## 6. ACCEPTANCE CRITERIA (PROTECTION MODE ACTIVE)

Protection Mode is fully active when:

1. ✅ All governance documents written and published
2. ✅ CI governance gate active and enforcing
3. ✅ ML lifecycle controls activated
4. ✅ No agent produces ungoverned output
5. ✅ ALEX can block PRs automatically
6. ✅ ChainIQ & ChainPay operate under strict constraints
7. ✅ Quantum-safe posture documented and enforced

**Status Levels:**

| Level | Status | Description |
|-------|--------|-------------|
| 🟢 **PRODUCTION-GRADE** | Governance fully active | All rules enforced |
| 🟡 **ELEVATED** | Partial enforcement | Some rules in shadow mode |
| 🟠 **BASELINE** | Documentation only | No active enforcement |
| 🔴 **UNGOVERNED** | No governance | Development mode |

**Current Target:** 🟢 **PRODUCTION-GRADE**

---

## 7. AGENT COMPLIANCE MATRIX

| Agent | Role | Compliance Requirements |
|-------|------|------------------------|
| **ALEX (GID-08)** | Governance Master | Enforces all rules, overrides all agents |
| **Cody (GID-01)** | Backend Engineering | Must satisfy cryptographic + DB rules |
| **Maggie (GID-02)** | ML Engineering | Must follow glass-box + lifecycle rules |
| **Sonny (GID-03)** | UI Engineering | Must comply with security + tokenization |
| **Dan (GID-04)** | DevOps | Must implement governance CI checks |
| **Sam (GID-06)** | Security | Mandatory review for security changes |
| **Atlas (GID-07)** | Repo Management | Must maintain compliant structure |
| **Cindy (GID-09)** | Backend Expansion | Must follow ALEX governance |
| **Pax (GID-10)** | Tokenization | Must follow settlement rules |
| **Lira (GID-11)** | UX Design | Must honor data-handling constraints |

**Override Hierarchy:**
```
ALEX (GID-08) → OVERRIDES ALL
Sam (GID-06) → Security escalations to ALEX
All other agents → Report to ALEX
```

---

## 8. REMEDIATION GUIDANCE

When ALEX blocks code, the developer receives:

1. **Violation Summary** - What rule was violated
2. **Code Location** - Exact file and line number
3. **Remediation Steps** - How to fix
4. **Examples** - Compliant code samples
5. **Documentation Links** - Relevant governance docs

**Example:**
```
❌ ALEX GOVERNANCE VIOLATION

Rule: #4 - No Unbounded Attack Surface
File: chainiq-service/app/api/v1/endpoints.py
Line: 142

Violation:
  yaml.load(config_file)  # Unsafe YAML loading

Remediation:
  yaml.safe_load(config_file)  # Use SafeLoader

Documentation:
  docs/governance/ALEX_PROTECTION_MANUAL.md#rule-4
```

---

## 9. CHANGELOG

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2025-12-11 | Initial ALEX Protection Manual (GID-08 activation) |

---

## 10. REFERENCES

- [ML Lifecycle Governance](./ML_LIFECYCLE_GOVERNANCE.md)
- [ChainPay Governance Rules](./CHAINPAY_GOVERNANCE_RULES.md)
- [ChainIQ Governance Rules](./CHAINIQ_GOVERNANCE_RULES.md)
- [Security Baseline Policy](./SECURITY_BASELINE_V1.md)
- [Cryptography Registry](./CRYPTO_REGISTRY.md)

---

**ALEX (GID-08) - Governance Above All • Integrity Before Speed • Proof Before Execution**
