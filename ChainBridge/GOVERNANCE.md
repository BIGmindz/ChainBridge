# ChainBridge Governance Framework

**ALEX Governance Layer - Installed by DAN-PAC-A (December 2025)**

> "Robust, Radical, Secure, Scalable, Commercially Viable"
> — ChainBridge Mantra

---

## Overview

The ChainBridge governance framework enforces **SPIE** principles across all code, ML models, and infrastructure:

- **S**afety
- **P**erformance
- **I**ntegrity
- **E**xplainability

All pull requests, commits, and deployments are subject to ALEX governance rules enforced via:
- Pre-commit hooks (`.pre-commit-config.yaml`)
- GitHub Actions workflows (`.github/workflows/alex-governance.yml`)
- Manual governance tool (`tools/governance_python.py`)

---

## ALEX Governance Rules

### 1. Security & Cryptography

**Rule:** Only quantum-safe cryptography is permitted.

**Forbidden:**
- RSA encryption/signatures
- ECDSA signatures
- DSA signatures
- Any `cryptography.hazmat.primitives.asymmetric` usage

**Allowed:**
- Dilithium (post-quantum signatures)
- Kyber (post-quantum key encapsulation)
- ChaCha20-Poly1305 (symmetric authenticated encryption)
- BLAKE3 (hashing)

**Enforcement:**
- `tools/governance_python.py` scans for forbidden imports
- Pre-commit hook blocks commits with forbidden crypto
- CI/CD fails on forbidden crypto usage

**Rationale:** Quantum computers will break RSA/ECDSA within 10 years. ChainBridge is crypto-agile and quantum-ready.

---

### 2. ML Safety & Explainability

**Rule:** All ML models must be explainable and versioned.

**Required:**
- Every ML model class must have `@model_version` decorator or `model_version` attribute
- Model predictions must include explanations (SHAP values, feature contributions)
- No black-box models (no opaque neural networks without interpretability layer)
- Shadow Mode required for new models before production deployment

**Forbidden:**
- Models without version metadata
- Models without explanation generation
- Direct production deployment of new models

**Enforcement:**
- `tools/governance_python.py` checks for `@model_version` on model classes
- Pre-commit hook warns on missing metadata
- CI/CD requires explanation outputs in model tests

**Rationale:** Financial services require explainable AI. Regulators and customers need to understand model decisions.

---

### 3. Performance & Scalability

**Rule:** No heavy ML imports in request path.

**Forbidden in request handlers:**
- `torch` (PyTorch)
- `tensorflow` / `keras`
- `transformers`
- `sklearn` (scikit-learn)
- `xgboost` / `lightgbm`

**Allowed:**
- Lazy loading of ML libraries
- Background worker pattern
- Pre-loaded model singletons (with startup overhead)

**Enforcement:**
- `tools/governance_python.py` scans API handlers for heavy imports
- CI/CD warns on request path performance issues

**Rationale:** Heavy ML imports add 2-5 seconds to cold start latency. Request handlers must stay lean.

---

### 4. Code Quality

**Rule:** All code must pass linting, formatting, and type checking.

**Required:**
- Black formatting (Python)
- Ruff linting (Python)
- MyPy type checking (Python)
- Prettier formatting (TypeScript/React)

**Enforcement:**
- Pre-commit hooks auto-format code
- CI/CD fails on linting/formatting violations
- GitHub Actions runs quality checks on every PR

---

### 5. Governance Tags

**Rule:** All commits must include governance tags.

**Required tags (at least one):**
- `[GOV]` - Governance/policy change
- `[RISK]` - Risk management/scoring change
- `[SEC]` - Security/crypto change
- `[ML]` - Machine learning model/pipeline change
- `[ALEX-APPROVED]` - Manual approval for large changes

**Large changes (>600 lines) require `[ALEX-APPROVED]` tag.**

**Enforcement:**
- `tools/governance_python.py` checks recent commit messages
- CI/CD warns on missing governance tags
- Pre-commit hook reminds developers

**Rationale:** Governance tags enable audit trails and change tracking for compliance.

---

### 6. Test Coverage

**Rule:** Test suite must pass before merge.

**Required:**
- All tests pass (`pytest -vv --maxfail=1`)
- No test skips without ALEX approval
- Critical paths have >80% coverage

**Enforcement:**
- CI/CD runs full test suite on every PR
- Test failures block merge
- Coverage reports published on PRs

---

## Governance Workflow

### Pre-Commit (Developer Machine)

1. Developer runs `git commit`
2. Pre-commit hooks execute:
   - Black/Ruff formatting
   - MyPy type checking
   - ALEX governance checks (`governance_python.py`)
   - Detect-secrets scan
3. Commit blocked if violations found
4. Developer fixes issues and re-commits

### Pull Request (GitHub)

1. Developer opens PR
2. GitHub Actions triggers:
   - `alex-governance.yml` - ALEX governance layer
   - `python-ci.yml` - Test suite
   - `ci-basic.yml` - Basic checks
3. PR checks display:
   - ✅ ALEX Governance: Passed
   - ✅ Python CI: All tests passed
   - ✅ Security Scan: No violations
4. PR mergeable only if all checks pass

### Merge to Main

1. PR approved by code owner (see `CODEOWNERS`)
2. All governance checks pass
3. At least one approval from team
4. Merge executes
5. Post-merge:
   - Deployment pipeline (if applicable)
   - Production monitoring
   - ALEX audit log updated

---

## Disabling Governance (Emergency Only)

**WARNING:** Governance can only be disabled by CTO (Benson) in emergencies.

To temporarily disable governance:

```bash
# Disable pre-commit (NOT RECOMMENDED)
git commit --no-verify

# Skip governance in CI (requires admin)
# Add to commit message:
[SKIP-GOVERNANCE] [EMERGENCY] [BENSON-APPROVED]
```

**Emergency bypass requires:**
1. CTO approval
2. Incident ticket
3. Post-incident review
4. Re-enable governance within 24 hours

---

## Governance Metrics

ALEX tracks governance metrics:

- **Governance violations per week**
- **Time to fix violations**
- **Commits with governance tags (%)**
- **Quantum-safe crypto compliance (%)**
- **ML model version compliance (%)**

**Target SLOs:**
- <5 violations per week
- 100% quantum-safe crypto
- 100% ML models versioned
- >90% commits with governance tags

---

## SPIE Framework Detail

### Safety
- Quantum-safe cryptography
- No unsafe imports
- Security scanning
- Secrets detection

### Performance
- No heavy ML imports in request path
- Lazy loading
- Async patterns
- Caching

### Integrity
- Test coverage
- Type safety
- Linting
- Code reviews

### Explainability
- Model versioning
- Explanation generation
- Audit trails
- Governance tags

---

## Contact

**ALEX Oversight:** Benson (GID-00) - CTO
**Governance Enforcement:** Dan (GID-07) - DevOps & CI/CD Lead
**ML Safety:** Maggie (GID-03) - ML Engineer
**Security:** Cody (GID-02) - Backend Lead

**Report governance violations:** governance@chainbridge.ai

---

**Document Version:** 1.0
**Last Updated:** December 11, 2025
**Owner:** DAN (GID-07) / ALEX Oversight
