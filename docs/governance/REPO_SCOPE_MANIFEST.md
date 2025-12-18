# ChainBridge Repository Scope Manifest

> **LOCKED** — This document defines the canonical scope of this repository.
> Changes require governance review.

---

## Repository Definition

**ChainBridge Core** is a governance-first orchestration, decision, and execution gateway for supply chain management and payment orchestration. It enforces deterministic agent governance, sealed execution boundaries, and auditable decision pipelines.

This repository is **not** a general-purpose experimentation space.

---

## Explicitly IN SCOPE

| Component | Description |
|-----------|-------------|
| **Governance** | ACM, DRCP, Diggi correction pipeline, ALEX enforcement |
| **Gateway** | Decision envelopes, tool binding, execution boundary |
| **ChainBoard UI** | Governance visibility, execution monitoring |
| **ChainIQ** | Risk scoring service (ML inference only, not training) |
| **ChainPay** | Payment orchestration service |
| **CI Enforcement** | Boot checks, scope validation, test gates |
| **Archive** | Read-only historical artifacts (inert, non-executable) |

---

## Explicitly OUT OF SCOPE

| Category | Why Excluded |
|----------|--------------|
| Trading bots | Not supply chain / payment orchestration |
| Strategy experimentation | Use separate experiment repo |
| Crypto alpha generation | Not aligned with ChainBridge mission |
| ML model training | Training belongs in dedicated ML pipeline |
| Standalone demos | Use `examples/` or separate repo |
| POCs not tied to ChainBridge | Fork or create new repo |

---

## What To Do Instead

### If you want to experiment:
1. Fork this repository
2. Create a separate `chainbridge-experiments` repo
3. Use the `/archive/` folder as read-only reference

### If you want to add a new service:
1. Propose via governance review
2. Ensure alignment with ChainBridge Core mission
3. Follow existing service patterns (ChainIQ, ChainPay)

### If you found archived code you need:
1. Read from `/archive/legacy-rsi-bot/`
2. Do NOT import or execute archived code
3. Extract and migrate to separate repo if needed

---

## Enforcement

This scope is enforced by:

| Mechanism | Location |
|-----------|----------|
| CI Scope Guard | `.github/workflows/scope-guard.yml` |
| Pre-commit Hook | `scripts/scope_guard/check_repo_scope.py` |
| Makefile Lock | Root `Makefile` (allowed targets block) |
| Import Guard | CI fails on `from archive` imports |

Violations cause CI failure. No exceptions.

---

## Allowed Directory Structure

```
/                           # Root (Makefile, Dockerfile, requirements)
├── api/                    # API Gateway
├── core/                   # Core business logic (governance, OC, OCC)
├── gateway/                # Decision envelopes, tool binding
├── src/                    # Source modules
├── tests/                  # Test suite
├── scripts/                # CI, dev, gatekeeper scripts
├── docs/                   # Documentation
├── config/                 # Configuration files
├── .github/                # CI workflows, governance rules
├── chainboard-service/     # ChainBoard backend
├── chainboard-ui/          # ChainBoard React UI
├── chainiq-service/        # ML risk scoring service
├── ChainBridge/            # Nested services (legacy structure)
├── archive/                # READ-ONLY archived artifacts
└── [standard dotfiles]     # .env, .gitignore, etc.
```

---

## Forbidden Patterns

The following patterns are blocked by CI:

| Pattern | Reason |
|---------|--------|
| `*bot*.py` (outside archive) | Trading bot code |
| `*trading*.py` | Trading logic |
| `*strategy*.py` (outside strategies/) | Strategy experimentation |
| `*alpha*.py` | Alpha generation |
| `*crypto_selector*` | Crypto-specific tooling |
| `from archive` imports | Archive must remain inert |

---

## Governance Lock

```
MANIFEST_VERSION: 1.0.0
LOCKED_BY: ATLAS (GID-11)
LOCKED_DATE: 2024-12-17
PAC_REFERENCE: PAC-REPO-SCOPE-LOCK-01
UNLOCK_REQUIRES: Governance review + BENSON approval
```

---

**This repository scope is locked and enforced.**
