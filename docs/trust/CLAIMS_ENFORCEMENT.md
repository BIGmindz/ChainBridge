# Claims Enforcement Gate

**Document:** CLAIMS_ENFORCEMENT.md
**Version:** 1.0.0
**Owner:** ALEX (GID-08), Governance & Alignment Engine
**PAC:** PAC-ALEX-CLAIMS-GATE-01
**Last Updated:** 2025-12-17

---

## Purpose

This document describes the hard governance gate that prevents trust claim drift.

**This gate exists because discipline does not scale.**

---

## What This Gate Enforces

The claims gate applies four rules to all claim-bearing surfaces:

| Rule | Name | Behavior |
|------|------|----------|
| **RULE-A** | Claim Presence Gate | Claims must reference valid `CLAIM-XX` identifiers |
| **RULE-B** | Forbidden Language Gate | Banned phrases cause CI failure |
| **RULE-C** | Surface Binding Gate | Claims must be allowed for their surface type |
| **RULE-D** | No Future Tense Gate | Truth is present tense only |

---

## Rule A: Claim Presence Gate

If a document asserts a positive capability, the claim must:

1. Reference a `CLAIM-XX` identifier (e.g., `CLAIM-01`)
2. That identifier must exist in `TRUST_CLAIMS_INDEX.md`
3. That claim must map to at least one passing test

**Valid claim IDs:** `CLAIM-01` through `CLAIM-16`

### Example

```markdown
<!-- ✅ VALID -->
ChainBridge validates agent identity before processing requests (CLAIM-01).

<!-- ❌ INVALID — missing claim ID -->
ChainBridge validates agent identity before processing requests.

<!-- ❌ INVALID — unknown claim ID -->
ChainBridge validates agent identity (CLAIM-99).
```

---

## Rule B: Forbidden Language Gate

The following phrases are globally forbidden in claim-bearing documents:

| Forbidden Phrase | Reason |
|------------------|--------|
| `secure` | Ambiguous |
| `security` | Ambiguous |
| `enterprise-grade` | Marketing |
| `production-ready` | Marketing |
| `battle-tested` | Marketing |
| `compliant` | Over-claim without certification |
| `certified` | Over-claim without certification |
| `guarantees` | Over-claim |
| `prevents` | Over-claim — we mitigate, not prevent |
| `protects against` | Over-claim |
| `zero-trust` | Buzzword |
| `unhackable` | Over-claim |
| `robust` | Marketing |
| `hardened` | Marketing |
| `military-grade` | Marketing |
| `best-in-class` | Marketing |
| `industry-leading` | Marketing |
| `hack-proof` | Over-claim |
| `bulletproof` | Over-claim |

**Exception:** These phrases may appear in `TRUST_NON_CLAIMS.md` where they are explicitly disclaimed.

---

## Rule C: Surface Binding Gate

Claims may only appear in surfaces where they are explicitly allowed.

### UI Allowed Claims

Trust Center UI may display:
- `CLAIM-01`, `CLAIM-02`, `CLAIM-03`, `CLAIM-04`, `CLAIM-06`
- `CLAIM-07`, `CLAIM-08`, `CLAIM-09`, `CLAIM-10`, `CLAIM-11`
- `CLAIM-13`, `CLAIM-14`

**Forbidden in UI:** `CLAIM-05`, `CLAIM-12`, `CLAIM-15`, `CLAIM-16`

### API Allowed Claims

Trust API may surface:
- `CLAIM-01` through `CLAIM-15`

**Forbidden in API:** `CLAIM-16`

### Sales/Product Allowed Claims

Sales materials may reference:
- All claims (`CLAIM-01` through `CLAIM-16`)

---

## Rule D: No Future Tense Gate

Trust claims must be present tense only. The following patterns are forbidden:

| Forbidden Pattern | Reason |
|-------------------|--------|
| `will` | Future promise |
| `aims to` | Aspiration |
| `designed to` | Intent, not fact |
| `planned` | Future promise |
| `future` | Future promise |
| `roadmap` | Future promise |
| `upcoming` | Future promise |
| `intends to` | Intent, not fact |

**Truth is what the system does now, not what it will do.**

---

## Enforced Files

The gate validates these file patterns:

| Pattern | Surface Type |
|---------|--------------|
| `docs/trust/*.md` | Documentation |
| `docs/product/*.md` | Sales/Product |
| `chainboard-ui/src/components/trust/**/*.tsx` | UI |
| `chainboard-ui/src/pages/*Trust*.tsx` | UI |

### Excluded Files

These files are excluded because they document the rules themselves:

- `TRUST_NON_CLAIMS.md` — Non-claims can use forbidden phrases
- `TRUST_CLAIMS_INDEX.md` — Defines the binding rules
- `CLAIM_TO_EVIDENCE_MAP.md` — References forbidden patterns as examples
- `CLAIMS_ENFORCEMENT.md` — This document
- `THREAT_COVERAGE.md` — Discusses security context

---

## Running the Gate

### Local Validation

```bash
# Run claims gate
make claims-gate

# Or directly
python scripts/validate_trust_claims.py --root .

# Verbose output (show all files checked)
python scripts/validate_trust_claims.py --root . --verbose
```

### CI Integration

The gate runs as part of CI. Any violation causes build failure.

```yaml
# In CI workflow
- name: Validate Trust Claims
  run: make claims-gate
```

---

## How to Add a New Claim

Adding a new claim requires three steps:

### Step 1: Add Tests First

Create tests that prove the claim. Tests must:
- Live in `tests/governance/` or `tests/governance/gameday/`
- Validate the claimed behavior
- Pass consistently

### Step 2: Add Claim to Index

Update `docs/trust/TRUST_CLAIMS_INDEX.md`:

1. Add the claim to the binding table
2. Specify allowed surfaces (UI, API, Sales)
3. Specify forbidden contexts

### Step 3: Add Claim to Claims Document

Update `docs/trust/TRUST_CLAIMS.md`:

1. Add claim ID and statement
2. Add evidence references (test files, event types)
3. Add scope boundary

**Claims without tests are not claims.**

---

## How to Update Bindings

To change where a claim can appear:

1. Update `TRUST_CLAIMS_INDEX.md` binding table
2. Update `scripts/validate_trust_claims.py` if surface rules change
3. Run `make claims-gate` to verify

---

## Example CI Failure Output

```
======================================================================
TRUST CLAIMS VALIDATION REPORT
PAC-ALEX-CLAIMS-GATE-01
======================================================================

❌ FAILED — 2 errors in 5 files

File: docs/product/OVERVIEW.md
--------------------------------------------------
  Line 42: [RULE-B] Forbidden phrase detected: 'secure'
    Context: ChainBridge provides a secure governance layer...

  Line 57: [RULE-D] Future tense detected: 'will'
    Context: ChainBridge will add support for...

======================================================================
Summary: 5 files, 2 errors
======================================================================
```

---

## What This Gate Does NOT Do

This gate:

- **Does NOT** validate test coverage (tests must already pass)
- **Does NOT** modify any files (read-only validation)
- **Does NOT** add new claims (enforcement only)
- **Does NOT** change runtime behavior (documentation gate only)

---

## Why This Matters

| Without Gate | With Gate |
|--------------|-----------|
| Drift is prevented by review | Drift is prevented by construction |
| Claims can expand silently | Claims expansion requires test + binding update |
| Forbidden language requires vigilance | Forbidden language causes automatic failure |
| Future promises can slip in | Future tense causes automatic failure |

**This gate makes honesty mechanical, not aspirational.**

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-17 | ALEX (GID-08) | Initial enforcement gate |

---

**CANONICAL REFERENCE** — This document describes the claims enforcement gate.
Gate configuration lives in `scripts/validate_trust_claims.py`.
