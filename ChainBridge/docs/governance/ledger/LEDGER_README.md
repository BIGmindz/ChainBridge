# ⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
# GOVERNANCE LEDGER — README
# ⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪

> **Document:** LEDGER_README.md
> **Authority:** ALEX (GID-08)
> **Version:** 1.0.0
> **Effective Date:** 2025-12-23
> **Status:** LOCKED

---

## 1. PURPOSE

The Governance Ledger is a **canonical, append-only** record of all governance artifacts in ChainBridge. It provides:

- **Auditability** — Every PAC, WRAP, Correction, and Closure is recorded
- **Lineage** — Parent-child relationships between artifacts
- **Sequence Integrity** — Monotonic, gap-free numbering
- **Enterprise Reporting** — Board-grade traceability
- **Learning** — Historical data for agent improvement

---

## 2. INVARIANTS (NON-NEGOTIABLE)

| Invariant | Enforcement |
|-----------|-------------|
| **Append-only** | No deletions, no overwrites |
| **Monotonic sequencing** | No gaps in sequence numbers |
| **Timestamp required** | Every entry has ISO-8601 timestamp |
| **Authority required** | Every entry has agent GID |
| **Immutable history** | Past entries cannot be modified |

**Violation = GOVERNANCE HALT**

---

## 3. LEDGER LOCATION

```
docs/governance/ledger/
├── GOVERNANCE_LEDGER.json    # Primary ledger (append-only)
└── LEDGER_README.md          # This document
```

---

## 4. ENTRY TYPES

| Entry Type | Description | Trigger |
|------------|-------------|---------|
| `PAC_ISSUED` | PAC created and ready for execution | PAC submission |
| `PAC_EXECUTED` | PAC execution completed | WRAP submission |
| `WRAP_SUBMITTED` | WRAP submitted for review | Agent completion |
| `WRAP_ACCEPTED` | WRAP ratified by authority | BENSON approval |
| `WRAP_REJECTED` | WRAP rejected, correction needed | Validation failure |
| `CORRECTION_OPENED` | Correction cycle started | Validation failure |
| `CORRECTION_CLOSED` | Correction cycle completed | Correction accepted |
| `POSITIVE_CLOSURE_ACKNOWLEDGED` | Artifact positively closed | Authority acknowledgment |
| `VALIDATION_PASS` | gate_pack.py validation passed | CI/precommit |
| `VALIDATION_FAIL` | gate_pack.py validation failed | CI/precommit |

---

## 5. ENTRY SCHEMA

```json
{
  "sequence": 1,
  "timestamp": "2025-12-23T00:00:00+00:00",
  "entry_type": "PAC_ISSUED",
  "agent_gid": "GID-08",
  "agent_name": "ALEX",
  "artifact_type": "PAC",
  "artifact_id": "PAC-ALEX-G1-PHASE-2-EXAMPLE-01",
  "artifact_status": "ISSUED",
  "parent_artifact": null,
  "closure_type": "NONE",
  "validation_result": null,
  "error_codes": null,
  "notes": "Optional notes",
  "file_path": "docs/governance/PAC-ALEX-G1-PHASE-2-EXAMPLE-01.md"
}
```

---

## 6. CANONICAL NUMBERING SCHEME

### PAC ID Format

```
PAC-{AGENT}-G{GENERATION}-{PHASE}-{DESCRIPTION}-{SEQUENCE}
```

**Examples:**
- `PAC-ALEX-G1-PHASE-2-GOVERNANCE-LEDGER-01`
- `PAC-BENSON-G0-PHASE-1-ARCHITECTURE-LOCK-01`
- `PAC-SAM-G1-PHASE-2-SECURITY-INVARIANTS-01`

### WRAP ID Format

```
WRAP-{AGENT}-G{GENERATION}-{PHASE}-{DESCRIPTION}-{SEQUENCE}
```

**Examples:**
- `WRAP-ALEX-G1-PHASE-2-GOVERNANCE-LEDGER-01`
- `WRAP-DAN-G1-PHASE-2-FAILURE-DRILLS-01`

### Rules

| Rule | Enforcement |
|------|-------------|
| Monotonic | Sequence numbers always increase |
| No gaps | Sequence N+1 follows N |
| No collisions | Each ID is unique |
| Agent-bound | ID includes agent name |

---

## 7. LEDGER WRITER CLI

### Location

```
tools/governance/ledger_writer.py
```

### Commands

#### Record PAC

```bash
python tools/governance/ledger_writer.py record-pac \
  --artifact-id "PAC-ALEX-G1-PHASE-2-EXAMPLE-01" \
  --agent-gid "GID-08" \
  --agent-name "ALEX" \
  --status issued \
  --file-path "docs/governance/PAC-ALEX-G1-PHASE-2-EXAMPLE-01.md"
```

#### Record WRAP

```bash
python tools/governance/ledger_writer.py record-wrap \
  --artifact-id "WRAP-ALEX-G1-PHASE-2-EXAMPLE-01" \
  --agent-gid "GID-08" \
  --agent-name "ALEX" \
  --parent-pac "PAC-ALEX-G1-PHASE-2-EXAMPLE-01" \
  --status submitted
```

#### Record Validation

```bash
python tools/governance/ledger_writer.py record-validation \
  --artifact-id "PAC-ALEX-G1-PHASE-2-EXAMPLE-01" \
  --agent-gid "GID-08" \
  --agent-name "ALEX" \
  --artifact-type PAC \
  --result pass
```

#### Record Positive Closure

```bash
python tools/governance/ledger_writer.py record-positive-closure \
  --artifact-id "WRAP-ALEX-G1-PHASE-2-EXAMPLE-01" \
  --agent-gid "GID-08" \
  --agent-name "ALEX" \
  --parent-artifact "PAC-ALEX-G1-PHASE-2-EXAMPLE-01" \
  --closure-authority "BENSON (GID-00)"
```

#### Query Ledger

```bash
# All entries
python tools/governance/ledger_writer.py query

# By agent
python tools/governance/ledger_writer.py query --by-agent GID-08

# By type
python tools/governance/ledger_writer.py query --by-type PAC_ISSUED

# By artifact
python tools/governance/ledger_writer.py query --by-artifact PAC-ALEX-G1-PHASE-2-EXAMPLE-01

# JSON format
python tools/governance/ledger_writer.py query --format json
```

#### Generate Report

```bash
# Text report
python tools/governance/ledger_writer.py report

# JSON report
python tools/governance/ledger_writer.py report --format json
```

#### Validate Integrity

```bash
# Full integrity validation (sequence + hash chain)
python tools/governance/ledger_writer.py validate

# JSON format
python tools/governance/ledger_writer.py validate --format json
```

#### Record BSRG Review (v1.1.0+)

```bash
python tools/governance/ledger_writer.py record-bsrg \
  --artifact-id "PAC-ATLAS-G1-PHASE-2-EXAMPLE-01" \
  --artifact-sha256 "abc123def456..." \
  --status PASS \
  --file-path "docs/governance/PAC-ATLAS-G1-PHASE-2-EXAMPLE-01.md"
```

---

## 8. BSRG-01 REVIEW ENTRIES (v1.1.0+)

### Entry Type: `BSRG_REVIEW`

BSRG (Benson Self-Review Gate) entries record the results of PAC self-review
validation. Every PAC must pass BSRG-01 before issuance.

### BSRG Entry Schema

```json
{
  "sequence": 42,
  "timestamp": "2025-12-24T00:00:00+00:00",
  "entry_type": "BSRG_REVIEW",
  "agent_gid": "GID-00",
  "agent_name": "BENSON",
  "artifact_type": "PAC",
  "artifact_id": "PAC-ATLAS-G1-PHASE-2-EXAMPLE-01",
  "artifact_status": "REVIEWED",
  "validation_result": "PASS",
  "error_codes": null,
  "artifact_sha256": "a1b2c3d4e5f6...",
  "bsrg_gate_id": "BSRG-01",
  "bsrg_status": "PASS",
  "bsrg_failed_items": [],
  "bsrg_checklist_results": {
    "identity_correct": "PASS",
    "agent_color_correct": "PASS"
  },
  "validation_version": "1.1.0-BSRG",
  "prev_hash": "prev_entry_hash...",
  "entry_hash": "current_entry_hash..."
}
```

### BSRG Required Fields

| Field | Description | Constraint |
|-------|-------------|------------|
| `artifact_sha256` | SHA256 of PAC content | Computed at validation |
| `bsrg_gate_id` | Gate identifier | Must be "BSRG-01" |
| `bsrg_status` | Review result | PASS or FAIL |
| `bsrg_failed_items` | Failed checklist items | Empty for PASS |
| `validation_version` | Tool version | For audit trail |

---

## 9. HASH-CHAIN IMMUTABILITY (v1.1.0+)

### Overview

Starting v1.1.0, the ledger implements hash-chain immutability:

- Each entry includes `prev_hash` (hash of previous entry)
- Each entry includes `entry_hash` (hash of current entry)
- Any modification to prior entries breaks the chain
- Validation detects tampering

### Hash Computation

```python
# Deterministic JSON serialization
canonical_json = json.dumps(entry_dict, sort_keys=True, separators=(',', ':'))
entry_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
```

### Validation Output

```
======================================================================
GOVERNANCE LEDGER INTEGRITY VALIDATION
======================================================================

Timestamp: 2025-12-24T12:00:00+00:00

--- Overall Status ---
  Verdict: INTEGRITY_VERIFIED
  Valid: ✅ YES

--- Sequence Validation ---
  Total Entries: 150
  Sequence Valid: ✅

--- Hash Chain Validation ---
  Entries with Hashes: 100
  Chain Intact: ✅
  No Tampering: ✅

======================================================================
```

### Tampering Detection

If tampering is detected:

```
--- Hash Chain Validation ---
  Entries with Hashes: 100
  Chain Intact: ❌
  No Tampering: ❌
    ⚠ [CRITICAL] HASH_MISMATCH: seq 42 - PAC-TEST-01
    ⚠ [CRITICAL] CHAIN_BROKEN: seq 43 - PAC-TEST-02
```

---

## 10. CI INTEGRATION

### Sequence Continuity Check

Add to CI pipeline:

```yaml
- name: Validate Ledger Integrity
  run: python tools/governance/ledger_writer.py validate
```

**Exit codes:**
- `0` = Valid (integrity verified)
- `1` = Invalid (tampering detected or sequence gaps)

### BSRG Recording in CI

To enable BSRG recording during CI:

```yaml
- name: Validate PAC with BSRG Recording
  env:
    LEDGER_WRITE_ENABLED: "1"
  run: python tools/governance/gate_pack.py --file $PAC_FILE
```

---

## 11. AGENT STATISTICS

The ledger tracks per-agent productivity:

```json
{
  "agent_sequences": {
    "GID-08": {
      "pac_count": 5,
      "wrap_count": 5,
      "correction_count": 0,
      "positive_closure_count": 3,
      "bsrg_stats": {
        "reviews_passed": 5,
        "reviews_failed": 0,
        "total_reviews": 5
      }
    }
  }
}
```

This enables:
- Agent ROI tracking
- Productivity metrics
- Quality metrics (correction rate)
- BSRG compliance metrics

---

## 12. AUDIT REPORT FORMAT

```
======================================================================
GOVERNANCE LEDGER AUDIT REPORT
======================================================================

Generated: 2025-12-23T12:00:00+00:00
Total Entries: 150

Sequence Continuity: ✅ VALID

--- Entry Type Distribution ---
  PAC_ISSUED: 30
  PAC_EXECUTED: 28
  WRAP_SUBMITTED: 28
  WRAP_ACCEPTED: 25
  CORRECTION_OPENED: 5
  CORRECTION_CLOSED: 5
  POSITIVE_CLOSURE_ACKNOWLEDGED: 20
  VALIDATION_PASS: 50
  VALIDATION_FAIL: 9
  BSRG_REVIEW: 30

--- Agent Distribution ---
  GID-00: 30
  GID-03: 20
  GID-06: 18
  GID-07: 25
  GID-08: 22
  GID-10: 15
  GID-11: 35

--- Validation Summary ---
  Pass: 50
  Fail: 9
  Pass Rate: 84.7%

--- Correction Summary ---
  Opened: 5
  Closed: 5
  Open: 0

--- Positive Closures: 20 ---
======================================================================
```

---

## 13. FORBIDDEN OPERATIONS

The following operations are **FORBIDDEN**:

| Operation | Reason |
|-----------|--------|
| Delete entry | History is immutable |
| Modify entry | Hash chain would break |
| Skip sequence | Monotonic guarantee |
| Backdate entry | Timestamp integrity |
| Manual JSON edit | Hash mismatch detection |
| Override BSRG | FAIL_CLOSED enforcement |

**Any violation triggers GOVERNANCE HALT.**

---

## 14. VERSION HISTORY

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0.0 | 2025-12-23 | ALEX (GID-08) | Initial ledger specification |
| 1.1.0 | 2025-12-24 | ATLAS (GID-05) | Added BSRG_REVIEW entry type, hash-chain immutability |

---

**Document Status: 🔒 LOCKED**

*Authority: ALEX (GID-08) — Governance & Alignment Engine*
