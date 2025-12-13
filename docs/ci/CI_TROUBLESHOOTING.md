# ChainBridge CI/CD Troubleshooting Guide

🟠 **DAN (GID-07) — DevOps & CI/CD Lead**

---

## ⚠️ CI Doctrine (MUST READ)

> **CI is a gate, not a suggestion. Do not soften failures.**

### Hard Rules

1. **Never use `|| true` or `|| echo` on required test steps** — failures must fail CI
2. **Never use `continue-on-error: true`** on required jobs
3. **Never convert test failures to warnings** to "get green"
4. **If tests fail, fix the tests or fix the code** — not the CI config
5. **Informational-only checks must be explicitly labeled** and not part of branch protection

### What's Acceptable

- `|| true` on **genuinely optional** dependencies (e.g., PQC crypto library)
- `|| true` on **non-required informational** checks (e.g., docs formatting hints)
- Skipping tests **only when the test directory doesn't exist**

### What's NOT Acceptable

- Bypassing test failures to unblock a PR
- Making required checks "soft fail"
- Using `2>&1 || echo "warning"` patterns on test commands

---

## Quick Reference

### Local Repro Commands

```bash
# Run all tests locally before pushing
make test                     # Root-level tests (benson bot)
pytest tests/ -v             # Root pytest suite

# ChainPay Service
cd ChainBridge/chainpay-service
pip install -r requirements.txt
pytest tests/ -v --tb=short

# ChainIQ Service
cd ChainBridge/chainiq-service
pip install -r requirements.txt
pytest tests/ -v --tb=short --ignore=tests/security/

# ChainBoard UI
cd ChainBridge/chainboard-ui
npm ci
npm run type-check
npm run lint
npm run build
npm test -- --run
```

---

## Common CI Failures & Fixes

### 1. `build-test` Job Failure (ci.yml)

**Symptom:** RSI bot tests fail

**Local repro:**
```bash
python benson_rsi_bot.py --test
```

**Causes:**
- RSI calculation logic error
- Missing dependencies in `requirements.txt`

**Fix:**
```bash
pip install -r requirements.txt
python benson_rsi_bot.py --test  # Should show 5/5 tests PASSED
```

---

### 2. `chainpay-tests` Failure

**Symptom:** ChainPay service tests fail

**Local repro:**
```bash
cd ChainBridge/chainpay-service
source .venv/bin/activate  # or create new venv
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio
pytest tests/ -v --tb=short
```

**Common causes:**
- Missing test fixtures (check `conftest.py`)
- Database connection issues (tests should use mocks)
- Import errors from missing deps

---

### 3. `chainiq-tests` Failure

**Symptom:** ChainIQ ML service tests fail

**Local repro:**
```bash
cd ChainBridge/chainiq-service
pip install -r requirements.txt
pytest tests/ -v --tb=short --ignore=tests/security/
```

**Common causes:**
- ML model loading errors
- Missing numpy/scipy dependencies
- Feature engineering test data issues

---

### 4. `chainboard-ui-tests` Failure

**Symptom:** React/TypeScript tests fail

**Local repro:**
```bash
cd ChainBridge/chainboard-ui
npm ci
npm run type-check  # TypeScript errors
npm run lint        # ESLint errors
npm test -- --run   # Vitest test suite
```

**Common causes:**
- TypeScript type errors
- Missing mock data
- React Testing Library issues

**Fix missing dependencies:**
```bash
npm install @testing-library/react @testing-library/jest-dom vitest
```

---

### 5. `ALEX Pre-Check` Failure (governance_check.yml)

**Symptom:** PR description validation fails

**Fix:** Ensure PR body contains:
- A description/overview section
- A changes/modifications section

The check is now more lenient and looks for common patterns.

---

### 6. `Forbidden Regions` Failure

**Symptom:** File moves blocked without ATLAS approval

**Fix options:**
1. Revert the file move
2. Request Move Matrix from ATLAS (GID-05)
3. Add `ATLAS-MOVE-MATRIX-YYYY-MM-DD` reference to PR description

---

### 7. `Model Integrity Check` Failure

**Symptom:** ML model signature verification fails

**Local repro:**
```bash
python scripts/check_model_integrity.py --ci ChainBridge/chainiq-service/app/ml/models/
```

**Fix:**
1. Sign model files: `python -m app.ml.model_security sign <model.pkl>`
2. Ensure `.sig.json` file exists for each `.pkl` model

---

## Workflow Files Reference

| Workflow | Purpose | Triggers |
|----------|---------|----------|
| `ci.yml` | Legacy bot tests + deploy | main, develop, feature/** |
| `chainbridge-ci.yml` | Unified CI for all services | main, develop, feature/** |
| `governance_check.yml` | ALEX governance rules | PRs to main/develop |
| `forbidden_regions_check.yml` | File move validation | PRs only |
| `model-integrity-check.yml` | ML model security | .pkl file changes |
| `pac_color_check.yml` | PAC document validation | All PRs |
| `pac_reminder.yml` | PAC reference reminder | All PRs |

---

## CI Caching Strategy

The CI uses pip/npm caching to speed up builds:

```yaml
# Python caching
- uses: actions/setup-python@v5
  with:
    python-version: '3.11'
    cache: 'pip'

# Node.js caching
- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'
    cache-dependency-path: ChainBridge/chainboard-ui/package-lock.json
```

Cache keys are based on dependency file hashes.

---

## Concurrency Controls

Workflows use concurrency to cancel outdated runs:

```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```

This prevents resource waste when multiple commits are pushed quickly.

---

## Re-running Failed Jobs

1. Go to Actions tab in GitHub
2. Find the failed workflow run
3. Click "Re-run failed jobs"

Or use GitHub CLI:
```bash
gh run rerun <run-id> --failed
```

---

## Contact

- **DAN (GID-07)** — DevOps & CI/CD Lead
- **ALEX (GID-08)** — Governance check issues
- **SAM (GID-06)** — Security scan issues

---

*Last updated: December 2025*
*🟠 DAN — GID-07 — DevOps & CI/CD Lead*
