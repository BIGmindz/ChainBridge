# PDO Enforcement CI Gate

**PAC:** PAC-DAN-PDO-CI-GATE-01 (CORRECTIVE)
**Author:** Dan (GID-07) — DevOps & CI/CD Lead
**Doctrine:** PDO Enforcement Model v1 (LOCKED)
**Status:** ACTIVE

---

## Overview

The PDO Enforcement Gate is a **non-skippable** CI workflow that validates PDO enforcement guarantees on every push and pull request. This gate exists to ensure:

1. **PDO enforcement cannot regress** — All PDO tests must pass
2. **No bypass mechanisms can be merged** — Code is scanned for bypass patterns
3. **Signing and validation invariants are test-gated** — Coverage thresholds enforced

---

## Workflow File

**Location:** `.github/workflows/pdo-enforcement-gate.yml`

---

## Gate Structure

The PDO Enforcement Gate consists of 4 sequential/parallel jobs that ALL must pass:

```
┌─────────────────────────────┐
│  pdo-bypass-detection       │  ← Gate 1: Scan for bypass patterns
└──────────────┬──────────────┘
               │
     ┌─────────┼─────────┐
     │                   │
     ▼                   ▼
┌─────────────────┐ ┌─────────────────┐
│ pdo-enforcement │ │ pdo-invariants  │  ← Gates 2 & 4: Tests + Invariants
│     -tests      │ │                 │
└────────┬────────┘ └────────┬────────┘
         │                   │
         ▼                   │
┌─────────────────┐          │
│  pdo-coverage   │  ← Gate 3: Coverage threshold
└────────┬────────┘          │
         │                   │
         └─────────┬─────────┘
                   ▼
         ┌─────────────────┐
         │ pdo-gate-summary│  ← Final: All must pass
         └─────────────────┘
```

---

## Gate Details

### Gate 1: PDO Bypass Detection 🛡️

**Purpose:** Ensure no bypass mechanisms exist in the codebase.

**Scanned Patterns:**
| Pattern | Risk |
|---------|------|
| `PDO_SKIP` | Would allow skipping PDO validation |
| `BYPASS_PDO` | Direct bypass mechanism |
| `DISABLE_PDO` | Environment-based disable |
| `PDO_DISABLED` | Flag-based disable |
| `SKIP_PDO_VALIDATION` | Validation skip |
| `PDO_ENFORCEMENT_OFF` | Enforcement toggle |
| `NO_PDO_CHECK` | Check bypass |
| `pdo_enforcement.*=.*False` | Python disable pattern |
| `pdo_enabled.*=.*False` | Enable flag bypass |
| `skip_pdo.*=.*True` | Skip flag |

**Failure Behavior:** BLOCKING — Any pattern match fails the gate.

---

### Gate 2: PDO Enforcement Tests 🔒

**Purpose:** Execute all PDO enforcement tests with 100% pass requirement.

**Test Files:**
- `tests/test_pdo_enforcement.py` — Core enforcement tests
- `tests/test_pdo_risk_integration.py` — Risk integration tests (if present)

**Validated Scenarios:**
| Scenario | Expected Result |
|----------|-----------------|
| Request without PDO | HTTP 403 Forbidden |
| Request with invalid PDO | HTTP 403/409 |
| Request with valid PDO | HTTP 2xx |
| PDO validation failure | Logged for audit |
| Hash integrity failure | HTTP 409 Conflict |

**Failure Behavior:** BLOCKING — Any test failure blocks merge.

---

### Gate 3: PDO Coverage Check 📊

**Purpose:** Ensure test coverage of PDO modules meets threshold.

**Coverage Targets:**
| Module | Minimum Coverage |
|--------|------------------|
| `app/services/pdo/` | 90% |
| `app/middleware/pdo_enforcement.py` | 90% |

**Current Threshold:** 90%

**Failure Behavior:** BLOCKING — Coverage below threshold blocks merge.

---

### Gate 4: PDO Invariant Validation 🔐

**Purpose:** Validate architectural invariants required by PDO Enforcement Model v1.

**Checked Invariants:**

| # | Invariant | Validation Method |
|---|-----------|-------------------|
| 1 | Middleware imports validator | grep import statement |
| 2 | REQUIRED_FIELDS defined | grep REQUIRED_FIELDS |
| 3 | Enforcement gates exist | grep gate definitions |
| 4 | HTTP 403 response configured | grep 403 status |
| 5 | Audit logging present | grep logger/logging |
| 6 | Hash validation exists | grep hash functions |

**Failure Behavior:** BLOCKING — Any invariant violation blocks merge.

---

## Branch Protection Requirements

To fully enforce PDO guarantees, configure branch protection rules:

### Required Status Checks for `main` Branch:
```
✅ pdo-gate-summary (required)
```

### Recommended Additional Settings:
- ☑️ Require branches to be up to date before merging
- ☑️ Require conversation resolution before merging
- ☑️ Do not allow bypassing the above settings

---

## Non-Skippable Design

This gate is intentionally designed to be **non-skippable**:

1. **No `workflow_dispatch`** — Cannot be triggered manually to bypass
2. **No `continue-on-error`** — All jobs fail hard
3. **No environment conditionals** — No `if: env.SKIP_PDO` patterns
4. **Scans for bypass patterns** — Detects attempts to add skip mechanisms

---

## Artifacts Produced

| Artifact | Retention | Purpose |
|----------|-----------|---------|
| `pdo-enforcement-test-results` | 30 days | Test execution log |
| `pdo-coverage-report` | 30 days | Coverage XML report |

---

## Doctrine Compliance

This gate enforces the following doctrine from **PDO Enforcement Model v1 (LOCKED)**:

> - No execution without a valid PDO
> - No agent can bypass enforcement
> - Violations are surfaced deterministically
> - All failures logged for audit

---

## Rollback Considerations

If the PDO Enforcement Gate fails after previously passing:

1. **Do NOT disable the gate** — This violates doctrine
2. **Identify the regression** — Check test output artifacts
3. **Fix the enforcement code** — Restore compliant state
4. **Re-run the gate** — Validate fix

---

## Troubleshooting

### "Bypass pattern detected"
A file contains a pattern that could disable PDO enforcement. Search for the pattern in your code and remove it.

### "PDO enforcement tests failed"
One or more enforcement tests failed. Check the test output artifact for details.

### "PDO coverage below threshold"
Add more tests to cover uncovered PDO enforcement code paths.

### "Invariant X violated"
An architectural requirement is missing. Check the invariant description and add the required code.

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-22 | Dan (GID-07) | Initial implementation per PAC-DAN-PDO-CI-GATE-01 |

---

## Related Documents

- [WRAP-DAN-PDO-CI-CD-ALIGNMENT-01](../pacs/WRAP-DAN-PDO-CI-CD-ALIGNMENT-01.md) — Architecture analysis
- [PDO Enforcement Model v1](../../docs/pdo/) — Doctrine definition
- [CI Overview](CI_OVERVIEW.md) — Full CI pipeline documentation
