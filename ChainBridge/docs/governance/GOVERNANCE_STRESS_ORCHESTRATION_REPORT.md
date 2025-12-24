# Multi-Agent Governance Stress Test Report

**Generated**: 2025-12-24 18:04:49 UTC
**Agent**: ATLAS (GID-05) | 🔵 BLUE
**PAC**: PAC-ATLAS-P33-MULTI-AGENT-GOVERNANCE-STRESS-AND-FAILURE-ORCHESTRATION-01

---

## Executive Summary

- **Total Tests**: 122
- **Failures Detected**: 33
- **False Negatives**: 0
- **Hard Fails**: 19
- **Distinct Failure Classes**: 5

### Failure Classes Triggered

- `GS_064` - GS_064_RACE_CORRUPTION
- `GS_061` - GS_061_ORDERING_VIOLATION
- `GS_065` - GS_065_PARITY_VIOLATION
- `GS_062` - GS_062_LEGACY_SCHEMA_CONFLICT
- `GS_063` - GS_063_AUTHORITY_DENIED

## Vector: ORDERING_COLLISION

| Metric | Value |
|--------|-------|
| Total Tests | 6 |
| Detected | 6 |
| False Negatives | 0 |
| Hard Fails | 4 |
| Blocked | 0 |
| Duration | 0.05 ms |
| Rollback Verified | — |

### Sample Results

| Test | Result | Failure Class | Message |
|------|--------|---------------|---------|
| ordering_00 | DETECTED | GS_061 | GS_061: ORDERING_VIOLATION - RUNTIME mus... |
| ordering_01 | DETECTED | GS_061 | GS_061: Missing required blocks |
| ordering_02 | DETECTED | GS_061 | GS_061: Missing required blocks |
| ordering_03 | DETECTED | GS_061 | GS_061: ORDERING_VIOLATION - RUNTIME mus... |
| ordering_04 | PASS | — | Order valid |

## Vector: LEGACY_SCHEMA_FRACTURE

| Metric | Value |
|--------|-------|
| Total Tests | 5 |
| Detected | 5 |
| False Negatives | 0 |
| Hard Fails | 0 |
| Blocked | 0 |
| Duration | 0.02 ms |
| Rollback Verified | — |

### Sample Results

| Test | Result | Failure Class | Message |
|------|--------|---------------|---------|
| legacy_00 | DETECTED | GS_062 | GS_062: LEGACY_SCHEMA_CONFLICT - Expecte... |
| legacy_01 | DETECTED | GS_062 | GS_062: LEGACY_SCHEMA_CONFLICT - Expecte... |
| legacy_02 | PASS | — | Schema valid |
| legacy_03 | DETECTED | GS_062 | GS_062: LEGACY_SCHEMA_CONFLICT - Expecte... |
| legacy_04 | DETECTED | GS_062 | GS_062: LEGACY_SCHEMA_CONFLICT - Expecte... |

## Vector: AUTHORITY_AMBIGUITY

| Metric | Value |
|--------|-------|
| Total Tests | 5 |
| Detected | 5 |
| False Negatives | 0 |
| Hard Fails | 0 |
| Blocked | 3 |
| Duration | 0.01 ms |
| Rollback Verified | — |

### Sample Results

| Test | Result | Failure Class | Message |
|------|--------|---------------|---------|
| authority_00 | BLOCKED | GS_063 | GS_063: AUTHORITY_DENIED - SONNY cannot ... |
| authority_01 | BLOCKED | GS_063 | GS_063: AUTHORITY_DENIED - MAGGIE cannot... |
| authority_02 | BLOCKED | GS_063 | GS_063: AUTHORITY_DENIED - ATLAS cannot ... |
| authority_03 | PASS | — | Authority valid |
| authority_04 | PASS | — | Authority valid |

## Vector: MULTI_AGENT_RACE

| Metric | Value |
|--------|-------|
| Total Tests | 100 |
| Detected | 11 |
| False Negatives | 0 |
| Hard Fails | 11 |
| Blocked | 0 |
| Duration | 1.22 ms |
| Rollback Verified | ✓ |

### Sample Results

| Test | Result | Failure Class | Message |
|------|--------|---------------|---------|
| race_002_CODY | PASS | — | Ledger write successful: #113 |
| race_002_DAN | PASS | — | Ledger write successful: #114 |
| race_001_DAN | PASS | — | Ledger write successful: #110 |
| race_000_SAM | PASS | — | Ledger write successful: #103 |
| race_000_SONNY | PASS | — | Ledger write successful: #101 |

## Vector: UI_TERMINAL_PARITY

| Metric | Value |
|--------|-------|
| Total Tests | 6 |
| Detected | 6 |
| False Negatives | 0 |
| Hard Fails | 4 |
| Blocked | 0 |
| Duration | 0.01 ms |
| Rollback Verified | — |

### Sample Results

| Test | Result | Failure Class | Message |
|------|--------|---------------|---------|
| parity_00 | PASS | — | Parity maintained |
| parity_01 | PASS | — | Parity maintained |
| parity_02 | HARD_FAIL | GS_065 | GS_065: PARITY_VIOLATION - Terminal=PASS... |
| parity_03 | HARD_FAIL | GS_065 | GS_065: PARITY_VIOLATION - Terminal=WARN... |
| parity_04 | HARD_FAIL | GS_065 | GS_065: PARITY_VIOLATION - Terminal=PASS... |

---

## Acceptance Criteria Verification

| Criterion | Status |
|-----------|--------|
| Every injected failure detected | ✓ PASS |
| Failures map to unique error codes | ✓ PASS |
| CI output visually unambiguous | ✓ PASS |
| No artifact silently accepted | ✓ PASS |
| ≥5 distinct failure classes | ✓ PASS |
| 0 false negatives | ✓ PASS |
| CI remains FAIL_CLOSED | ✓ PASS |

---

## Conclusion

**POSITIVE_CLOSURE**: ✓ GRANTED

- Distinct failure classes triggered: 5/5
- False negatives: 0
- CI FAIL_CLOSED: PRESERVED

**TRAINING SIGNAL**: SYSTEMIC_STRESS_ORCHESTRATION

> If governance survives worst-case inputs, it can be trusted.
