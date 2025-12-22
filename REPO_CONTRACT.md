# ChainBridge Repository Contract

> **This document defines what this repository is and is not.**

---

## What This Repository Is

**ChainBridge Core** — A governance-first orchestration, decision, and execution gateway.

| Component | Purpose |
|-----------|---------|
| **Governance** | ACM, DRCP, Diggi correction pipeline, ALEX enforcement |
| **Gateway** | Decision envelopes, tool binding, execution boundaries |
| **ChainBoard** | Operator control center, governance visibility |
| **ChainIQ** | ML-powered risk scoring (inference only) |
| **ChainPay** | Payment orchestration and settlement |

This is enterprise infrastructure for supply chain management and payment orchestration.

---

## What This Repository Is NOT

| Excluded | Reason |
|----------|--------|
| Trading bots | Not aligned with ChainBridge mission |
| Crypto signal engines | Not supply chain / payment infrastructure |
| Strategy experimentation | Use separate experiment repository |
| ML model training | Training pipelines belong elsewhere |
| Alpha generation | Out of scope |
| Standalone demos | Fork or create new repository |

**If your code does any of the above, it does not belong here.**

---

## Scope Enforcement

This repository has **mechanical scope enforcement**:

| Mechanism | What It Does |
|-----------|--------------|
| `make scope-guard` | Local validation of repo scope |
| `.github/workflows/scope-guard.yml` | CI gate — fails PRs with violations |
| `scripts/scope_guard/check_repo_scope.py` | Detects forbidden patterns |

### Forbidden Patterns

Files matching these patterns outside `/archive` fail CI:

- `*bot*.py`
- `*trading*.py`
- `*alpha*.py`
- `*crypto_selector*.py`
- `*rsi_bot*.py`
- `*multi_signal*.py`

### Forbidden Imports

```python
# These fail CI:
from archive import anything
import archive
```

---

## Archive

Legacy code exists in `/archive/` and is:
- **Inert** — Not executed, not imported, not built
- **Read-only** — Do not modify without governance review
- **Documented** — See `archive/ARCHIVE_CONTRACT.md`

If you need archived code, extract it to a separate repository.

---

## Contribution Rules

### Before Adding Code

1. Check if it aligns with ChainBridge Core mission
2. Run `make scope-guard` locally
3. Ensure no forbidden patterns are introduced

### If Scope Guard Fails

Your PR will be blocked. Options:
1. Remove the offending code
2. Rename to avoid forbidden patterns (if legitimate)
3. Request governance exception (rare)

---

## Authority References

| Document | Location |
|----------|----------|
| Scope Manifest | `docs/governance/REPO_SCOPE_MANIFEST.md` |
| Archive Contract | `archive/ARCHIVE_CONTRACT.md` |
| Governance Rules | `.github/ALEX_RULES.json` |
| Agent Registry | `docs/governance/AGENT_REGISTRY.json` |

---

## Contract Metadata

| Field | Value |
|-------|-------|
| Version | 1.0.0 |
| Effective | December 2024 |
| Owner | ATLAS (GID-11) |
| PAC Reference | PAC-ATLAS-LEGACY-CLEAN-02 |

---

**This repository's scope is locked. Violations fail CI. Ambiguity is operational risk.**
