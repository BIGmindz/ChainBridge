# Repository Scope Lock

> **GOVERNANCE-LOCKED** — This document defines what this repository IS and IS NOT.
> Enforced by CI. No exceptions.

---

## What This Repository IS

**ChainBridge Core** is a multi-service platform for:

- Supply chain management
- Payment orchestration
- Agent governance (ALEX, ACM, DRCP, Diggi)
- Deterministic decision pipelines
- Audit-first execution boundaries

---

## What This Repository IS NOT

This repository is **explicitly not**:

| Excluded Category | Reason |
|-------------------|--------|
| Trading bots | Not supply chain / payment orchestration |
| RSI / alpha strategies | Not aligned with ChainBridge mission |
| Crypto selection tools | Belongs in separate experiment repo |
| Market simulation | Not production governance scope |
| Streamlit dashboards | Use ChainBoard UI instead |
| Jupyter notebooks | Training belongs in ML pipeline repo |

---

## Where Legacy Systems Live

All legacy RSI / trading bot artifacts are quarantined in:

```
archive/legacy-rsi-bot/
```

This directory is:
- **Read-only** — Do not modify
- **Inert** — Not executed by any CI, test, or runtime
- **Non-importable** — CI fails on `from archive` imports
- **Reference only** — Extract and migrate elsewhere if needed

**There is no other location for legacy trading code.**

---

## Allowed Domains

The following top-level directories are IN SCOPE:

```
core/           # Core business logic
gateway/        # Decision envelopes, tool binding
api/            # API Gateway
tests/          # Test suite
docs/           # Documentation
scripts/        # CI, dev, utility scripts
config/         # Configuration files
manifests/      # Agent manifests
ChainBridge/    # Nested services (legacy structure, being consolidated)
chainboard-ui/  # ChainBoard React UI
chainiq-service/ # ML risk scoring
```

---

## CI Enforcement

This scope is enforced by hard CI guardrails:

| Check | Behavior |
|-------|----------|
| Forbidden files | CI **fails** if `*rsi*`, `*trading*`, `*crypto*`, `*signal*` files appear outside `/archive` |
| Forbidden extensions | CI **fails** if `.ipynb`, `.streamlit` appear at runtime paths |
| Archive imports | CI **fails** if any code imports from `/archive` |
| Makefile references | CI **fails** if Makefile references legacy patterns |
| Requirements lock | CI **fails** if new `requirements-*.txt` files appear |

**No warnings. Only PASS or FAIL.**

---

## Governance Override

Bypassing scope lock requires **BOTH**:

1. Commit message containing:
   ```
   GOVERNANCE-OVERRIDE: APPROVED
   ```

2. File updated in same PR:
   ```
   docs/governance/OVERRIDE.md
   ```

Override attempts without both conditions = CI failure.

---

## Governance Lock

```
DOCUMENT: REPO_SCOPE_LOCK.md
VERSION: 1.0.0
LOCKED_BY: DAN (GID-07)
LOCKED_DATE: 2025-12-17
PAC_REFERENCE: PAC-DAN-03
ENFORCEMENT: .github/workflows/scope-guard.yml
UNLOCK_REQUIRES: Governance review + BENSON approval
```

---

**This scope lock is enforced. Violations cause CI failure.**

🟢 DAN (GID-07) — Repo integrity > velocity
