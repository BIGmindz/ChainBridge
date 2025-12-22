# CI/CD Overview — PAC-DAN-031

> **Author**: DAN (GID-04) DevOps & CI/CD Lead
> **Status**: Active
> **Last Updated**: 2025-01-XX
> **Branch**: `feature/chainpay-consumer`

---

## 📋 Overview

This document describes the normalized CI/CD infrastructure for the ChainBridge monorepo. All workflows are consolidated under `ChainBridge/.github/workflows/` following the Atlas Unification pattern.

### Workflow Architecture

```
ChainBridge/.github/workflows/
├── ci-core.yml           # Unified Python CI (lint, test, integrate)
├── ci-model-integrity.yml # ML model security verification
├── deploy-staging.yml    # Staging deployment pipeline
├── repo-sanity.yml       # Repository structure validation
├── alex-governance.yml   # ALEX agent governance checks
└── shadow-ci.yml         # Shadow mode testing (PAC-DAN-023)
```

---

## 🔧 Workflow Details

### 1. `ci-core.yml` — Unified Python CI

**Purpose**: Consolidated CI pipeline replacing fragmented python-ci.yml, chainpay-iq-ui-ci.yml, and tests.yml.

**Triggers**:
- Push to `main`, `develop`, `feature/*`
- Pull requests to `main`, `develop`
- Manual dispatch

**Jobs**:
| Job | Description | Dependencies |
|-----|-------------|--------------|
| `alex-governance` | ALEX governance gate | None |
| `lint` | Ruff, Black, MyPy | alex-governance |
| `test-chainiq` | ChainIQ service tests (3.11, 3.12 matrix) | lint |
| `test-chainpay` | ChainPay service tests (3.11, 3.12 matrix) | lint |
| `test-chainboard` | ChainBoard UI tests (Node 20) | lint |
| `integration` | Cross-service integration tests | test-* jobs |
| `ci-summary` | GitHub Actions summary | All jobs |

**Matrix Testing**:
```yaml
python-version: ['3.11', '3.12']
```

**Caching**:
- pip cache with hash of requirements files
- npm cache with hash of package-lock.json

---

### 2. `ci-model-integrity.yml` — ML Model Security

**Purpose**: Verify ML model integrity with SHA-256 signatures, PQC Kyber detection, and security scanning.

**Triggers**:
- Push/PR modifying `*.pkl`, `*.joblib`, `*.onnx`, `*.h5` files
- Nightly schedule (02:00 UTC)
- Manual dispatch

**Jobs**:
| Job | Description | Failure Behavior |
|-----|-------------|------------------|
| `discover-models` | Find all model files | - |
| `sha256-verify` | Verify SHA-256 signatures | Block PR |
| `pqc-verify` | Check PQC Kyber signatures | Warn only |
| `metadata-validation` | Validate model metadata | Warn only |
| `quarantine-check` | Check blocklist status | Block PR |
| `security-scan` | Scan for pickle exploits | Block PR |
| `integrity-summary` | Generate report | - |

**Signature Format**:
```json
{
  "model_name": "risk_model_v2.pkl",
  "sha256": "abc123...",
  "pqc_kyber_signature": "...",
  "signed_by": "SAM-GID-05",
  "signed_at": "2025-01-01T00:00:00Z"
}
```

---

### 3. `deploy-staging.yml` — Staging Deployment

**Purpose**: Automated staging environment deployment with Docker image building and integration tests.

**Triggers**:
- Push to `develop` branch
- Manual dispatch with parameters

**Jobs**:
| Job | Description | Order |
|-----|-------------|-------|
| `pre-deploy-checks` | Validate deployment readiness | 1 |
| `build-chainiq` | Build ChainIQ Docker image | 2 |
| `build-chainpay` | Build ChainPay Docker image | 2 |
| `build-gateway` | Build API Gateway image | 2 |
| `integration-tests` | Run integration test suite | 3 |
| `deploy-staging` | Deploy to staging environment | 4 |
| `register-models` | Register model versions | 5 |
| `smoke-tests` | Validate deployment health | 6 |
| `notify-alex` | Report to ALEX governance | 7 |

**Image Naming**:
```
ghcr.io/bigmindz/chainbridge/chainiq:staging-YYYYMMDD-<sha>
ghcr.io/bigmindz/chainbridge/chainpay:staging-YYYYMMDD-<sha>
ghcr.io/bigmindz/chainbridge/gateway:staging-YYYYMMDD-<sha>
```

---

### 4. `repo-sanity.yml` — Repository Validation

**Purpose**: Validate repository structure for Atlas unification compliance.

**Triggers**:
- Pull requests to `main`, `develop`
- Weekly schedule (Sunday 03:00 UTC)
- Manual dispatch

**Checks**:
| Check | Description | Severity |
|-------|-------------|----------|
| Duplicate Detection | Multiple service folders | Error |
| Migrations Check | Missing Alembic migrations | Error |
| Forbidden Locations | .env, private keys in repo | Error |
| Atlas Validation | Correct folder structure | Warning |
| Workflow Check | Consistent workflow naming | Warning |
| Config Drift | Configuration file consistency | Warning |

---

## 🛠 Local Development

### Makefile Targets (DX Boost)

```bash
# Run full CI locally
make ci

# Individual checks
make lint          # Ruff + Black + MyPy
make test-backend  # ChainIQ + ChainPay tests
make test-frontend # ChainBoard UI tests
make model-check   # Model integrity verification

# Deployment
make build         # Build all Docker images
make staging       # Staging deployment simulation

# Validation
make sanity        # Repository structure check
make governance    # ALEX governance check
make validate      # All checks combined
```

### Pre-Push Checklist

```bash
# Before pushing, run:
make validate

# Or individually:
make governance  # ALEX compliance
make lint        # Code quality
make ci          # Full test suite
```

---

## 📊 Job Dependencies Graph

```
┌─────────────────────┐
│  alex-governance    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│       lint          │
└─────────┬───────────┘
          │
    ┌─────┼─────┬─────────────┐
    │     │     │             │
    ▼     ▼     ▼             ▼
┌──────┐┌──────┐┌──────┐┌──────────┐
│chainiq││chainpay││chainboard│
└───┬──┘└───┬──┘└───┬──┘└─────┬────┘
    │       │       │         │
    └───────┴───────┴─────────┘
                │
                ▼
        ┌───────────────┐
        │  integration  │
        └───────┬───────┘
                │
                ▼
        ┌───────────────┐
        │  ci-summary   │
        └───────────────┘
```

---

## 🔒 Security Considerations

### Secrets Required

| Secret | Purpose | Required For |
|--------|---------|--------------|
| `GITHUB_TOKEN` | GitHub API access | All workflows |
| `GHCR_PAT` | Container registry push | deploy-staging |
| `STAGING_SSH_KEY` | Staging server access | deploy-staging |
| `MODEL_SIGNING_KEY` | Model signature verification | ci-model-integrity |

### Branch Protection

Recommended branch protection rules:
- `main`: Require ci-core, ci-model-integrity, repo-sanity to pass
- `develop`: Require ci-core to pass
- `feature/*`: Require lint job to pass

---

## 🚨 Troubleshooting

### Common Issues

**CI fails on "ALEX governance"**
```bash
# Check locally:
make governance
# Or:
python tools/governance_python.py
```

**Model integrity check fails**
```bash
# Regenerate signature:
python scripts/sign_model.py models/your_model.pkl
```

**Docker build fails**
```bash
# Check Docker daemon:
docker info

# Build individually:
make build
```

---

## 📝 Migration Notes

### Deprecated Workflows

The following workflows are **deprecated** and should not be used:

| Workflow | Replacement |
|----------|-------------|
| `root/.github/workflows/ci.yml` | `ci-core.yml` |
| `root/.github/workflows/model-integrity-check.yml` | `ci-model-integrity.yml` |
| `ChainBridge/.github/workflows/python-ci.yml` | `ci-core.yml` |
| `ChainBridge/.github/workflows/chainpay-iq-ui-ci.yml` | `ci-core.yml` |
| `ChainBridge/.github/workflows/tests.yml` | `ci-core.yml` |

### Migration Checklist

- [ ] Update branch protection rules to reference new workflows
- [ ] Delete deprecated workflow files
- [ ] Update README badges to reference ci-core.yml
- [ ] Configure required secrets in repository settings

---

## 📚 Related Documentation

- [STAGING_PIPELINE.md](./STAGING_PIPELINE.md) — Staging deployment details
- [../RSI_THRESHOLD_POLICY.md](../RSI_THRESHOLD_POLICY.md) — Trading thresholds
- [../../README.md](../../README.md) — Project overview
