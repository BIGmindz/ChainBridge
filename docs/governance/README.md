# ChainBridge Governance Framework
**ALEX (GID-08) Protection Mode | Status: ACTIVE | Level: ELEVATED**

## Quick Start

ChainBridge is governed by **ALEX (Autonomous Logic Enforcement eXecutive)**, enforcing 11 hard constraints across all agents, services, and code changes.

### Core Governance Documents

1. **[ALEX Protection Manual](./ALEX_PROTECTION_MANUAL.md)** - Master governance document defining all 11 rules
2. **[ML Lifecycle Governance](./ML_LIFECYCLE_GOVERNANCE.md)** - 6-stage model deployment process
3. **[ChainPay Governance Rules](./CHAINPAY_GOVERNANCE_RULES.md)** - Deterministic settlement requirements
4. **[ChainIQ Governance Rules](./CHAINIQ_GOVERNANCE_RULES.md)** - Glass-box ML model constraints
5. **[Security Baseline v1.0](./SECURITY_BASELINE_V1.md)** - Cryptography, auth, and security controls
6. **[Governance Audit Report](./ALEX_GOVERNANCE_AUDIT_REPORT.md)** - Current compliance status and roadmap

---

## The 11 Hard Constraints

| # | Rule | Enforcement | Severity |
|---|------|-------------|----------|
| 1 | **Glass-Box Models Only** | Block PR | CRITICAL |
| 2 | **Proof Over Performance** | Runtime Check | CRITICAL |
| 3 | **Quantum-Ready Cryptography** | Block PR | CRITICAL |
| 4 | **No Unbounded Attack Surface** | Block PR | HIGH |
| 5 | **Canonical DB Fields** | Block PR | HIGH |
| 6 | **Deterministic Settlement** | Runtime Check | CRITICAL |
| 7 | **ML Lifecycle Governance** | Block Deployment | CRITICAL |
| 8 | **CI/CD Governance Hooks** | Block PR | HIGH |
| 9 | **Multi-Agent Safety Override** | Override All | CRITICAL |
| 10 | **No Side-Effects in Imports** | Block PR | MEDIUM |
| 11 | **Zero Silent Failures** | Warning | MEDIUM |

---

## Current Status (Dec 11, 2025)

**Governance Level:** 🟡 **ELEVATED** (Partial Enforcement)

### ✅ Completed
- Governance framework documented (5 core documents)
- CI/CD governance workflow active
- Security baseline established
- PQC roadmap defined
- Agent compliance matrix defined

### ⚠️ In Progress
- XGBoost → EBM migration (Q1 2026)
- CanonicalBaseModel implementation (Sprint 1)
- ChainPay settlement logic (Sprint 2-3)
- Training scripts creation (Immediate)

### 🎯 Target: 🟢 **PRODUCTION-GRADE** (Q2 2026)

---

## For Developers

### Before You Commit

```bash
# ALEX pre-commit checks run automatically
git commit -m "Your commit message"

# If blocked, fix violations and try again
```

### Before You Create a PR

**Required PR sections:**
- Description
- Changes
- Risk Assessment
- Governance Statement

**Automatic checks:**
- Rule #1: Glass-box models only
- Rule #3: PQC compliance
- Rule #4: No dangerous patterns (eval, exec, unsafe yaml)
- Rule #5: Canonical DB fields
- Rule #10: No import side-effects
- Test coverage > 80%

### When Deploying ML Models

**Follow 6-stage lifecycle:**
1. Proposal → 2. Prototype → 3. Training Approval → 4. Shadow Mode → 5. Controlled Deployment → 6. Production Freeze

**Required metadata:**
```json
{
  "model_type": "EBM",
  "monotonicity_constraints": {...},
  "calibration_metrics": {"brier_score": 0.087},
  "explainability_method": "EBM_native",
  "proof_pack_id": "pp_ml_training_..."
}
```

---

## For Agents

### Agent Compliance Matrix

| Agent | Role | Key Requirements |
|-------|------|------------------|
| **ALEX (GID-08)** | Governance Master | Enforces all rules, overrides all agents |
| **Cody (GID-01)** | Backend | Cryptography (Rule #3), DB fields (Rule #5) |
| **Maggie (GID-02)** | ML Engineering | Glass-box (Rule #1), Lifecycle (Rule #7) |
| **Sonny (GID-03)** | UI | Security (Rule #4), Data handling |
| **Dan (GID-04)** | DevOps | CI/CD governance (Rule #8) |
| **Sam (GID-06)** | Security | Security baseline, PQC migration |
| **Pax (GID-10)** | Tokenization | Deterministic settlement (Rule #6) |

**No agent may override ALEX.**

---

## Quick Reference

### Allowed ML Models
✅ EBM, GAM, Logistic Regression, Monotone GBDT
❌ Random Forest, XGBoost (default), Neural Networks

### Allowed Cryptography
✅ SPHINCS+, Dilithium-3, Kyber-768, SHA-256
❌ RSA, ECDSA, DSA

### Required DB Fields (All Tables)
```python
canonical_id: str
created_at: datetime
updated_at: datetime
version: int
source: str
```

### Additional Required (Financial Tables)
```python
proof_pack_id: str
```

---

## Reporting Violations

If you encounter governance violations:

1. **Check the error message** - Contains specific rule violated
2. **Read the relevant governance doc** - Links provided in error
3. **Review remediation examples** - Compliant code samples
4. **Fix and resubmit** - ALEX will re-validate

**Escalation:** If unclear, consult [ALEX Protection Manual](./ALEX_PROTECTION_MANUAL.md) or file an issue.

---

## Governance Metrics

Track governance health:
- Weekly governance reports
- Quarterly governance reviews
- Real-time CI/CD feedback
- Agent compliance dashboard

**Current Metrics:**
- Glass-box models: 0% (migration pending)
- CI/CD governance: ✅ Active
- PQC compliance: 🟢 Clean slate, ready
- Test coverage: Measuring baseline
- Governance violations: 3 major (remediation planned)

---

## Timeline to Production-Grade

```
Dec 2025:
✅ Governance framework deployed
✅ CI/CD enforcement active

Q1 2026:
🔄 XGBoost → EBM migration
🔄 CanonicalBaseModel implementation
🔄 PQC library integration

Q2 2026:
🎯 Production-grade status achieved
🎯 All 11 rules fully enforced
🎯 ChainPay & ChainIQ compliant

Q3-Q4 2026:
🚀 PQC migration complete
🚀 SOC2 Type II audit
🚀 External security certification
```

---

## Documentation Structure

```
docs/governance/
├── README.md                          # This file
├── ALEX_PROTECTION_MANUAL.md          # Master governance document
├── ML_LIFECYCLE_GOVERNANCE.md         # 6-stage ML deployment
├── CHAINPAY_GOVERNANCE_RULES.md       # Settlement determinism
├── CHAINIQ_GOVERNANCE_RULES.md        # Glass-box ML constraints
├── SECURITY_BASELINE_V1.md            # Security standards
└── ALEX_GOVERNANCE_AUDIT_REPORT.md    # Current compliance status

.github/
├── workflows/
│   └── governance_check.yml           # CI/CD enforcement
└── ALEX_RULES.json                    # Machine-readable rules
```

---

## Support & Contact

**Governance Questions:** Review [ALEX Protection Manual](./ALEX_PROTECTION_MANUAL.md)
**Technical Issues:** Check [Governance Audit Report](./ALEX_GOVERNANCE_AUDIT_REPORT.md)
**Security Concerns:** Contact Sam (GID-06)
**Violations:** ALEX will provide remediation guidance automatically

---

**ALEX (GID-08) - Governance Above All • Integrity Before Speed • Proof Before Execution**

*Last Updated: 2025-12-11 | Next Review: Q1 2026*
