# OCC Invariants Governance

**PAC Reference:** PAC-BENSON-P22-C — OCC + Control Plane Deepening  
**Author:** ALEX (GID-08) — Governance Enforcer  
**Version:** 1.0.0  
**Date:** 2025-01-12

---

## Overview

This document defines the governance invariants for the Operator Control Center (OCC). These invariants ensure timeline completeness, evidence immutability, and full transition visibility across all OCC operations.

---

## INV-OCC-004: Timeline Completeness

### Definition
The OCC timeline must show all PAC lifecycle transitions without gaps.

### Requirements
1. All lifecycle state transitions must be recorded in timeline
2. Timeline must include: ADMISSION → RUNTIME_ACTIVATION → AGENT_ACTIVATION → EXECUTING → WRAP_COLLECTION → REVIEW_GATE → BER_ISSUED → SETTLED
3. No transition may be omitted or hidden from timeline view
4. Agent ACK records must be captured for all activated agents
5. WRAP milestones must be visible for all WRAP phases
6. BER records must be linked to parent PAC timeline
7. Timeline gaps longer than 30 seconds must generate warning

### Validation
- Endpoint: `/occ/timeline/{pac_id}`
- Required fields: `lifecycle_state`, `events`, `agent_acks`, `wrap_milestones`, `ber_records`
- Valid states: ADMISSION, RUNTIME_ACTIVATION, AGENT_ACTIVATION, EXECUTING, WRAP_COLLECTION, REVIEW_GATE, BER_ISSUED, SETTLED, FAILED, CANCELLED

### Enforcement
- **Type:** RUNTIME_CHECK
- **Severity:** HIGH

---

## INV-OCC-005: Evidence Immutability

### Definition
OCC evidence artifacts and timeline records are immutable once created.

### Requirements
1. All OCC timeline endpoints must be READ-ONLY (GET only)
2. POST/PUT/PATCH/DELETE requests must return 405 Method Not Allowed
3. Evidence artifacts must have cryptographic `content_hash`
4. Evidence hashes must be preserved across all API responses
5. No retroactive modification of timeline events permitted
6. BER records are immutable after FINAL status
7. Mutation rejection must cite INV-OCC-005 in error response

### Blocked Operations
| Endpoints | Blocked Methods |
|-----------|-----------------|
| `/occ/timeline/*` | POST, PUT, PATCH, DELETE |
| `/occ/agents/*` | POST, PUT, PATCH, DELETE |
| `/occ/diff/*` | POST, PUT, PATCH, DELETE |

### Error Response Format
```json
{
  "detail": "Timeline endpoints are READ-ONLY. INV-OCC-005: Evidence immutability."
}
```

### Enforcement
- **Type:** BLOCK_REQUEST
- **Severity:** CRITICAL

---

## INV-OCC-006: No Hidden Transitions

### Definition
All state transitions must be visible and traceable in OCC.

### Requirements
1. Every agent activation must be recorded with ACK timestamp
2. Every execution start/complete must generate timeline event
3. Every failure must be recorded with stack trace when available
4. Decision diffs must show all field changes (added/removed/modified)
5. WRAP collection must show pending and completed agents
6. Review gate outcomes must be visible (passed/failed/pending)
7. No silent state changes permitted in control plane

### Event Categories
All timeline events must be categorized:
- `pac_lifecycle` - PAC state transitions
- `agent_activation` - Agent ACK events
- `execution` - Task execution events
- `decision` - Decision/approval events
- `wrap` - WRAP milestone events
- `review_gate` - Review gate events
- `ber` - BER issuance events
- `governance` - Governance check events
- `error` - Error/failure events

### Diff Change Types
All diff changes must be classified:
- `added` - New field/value
- `removed` - Removed field/value
- `modified` - Changed field/value
- `unchanged` - No change (for context)

### Monitoring
- Alert on hidden transition detection
- Audit all state changes
- Require trace correlation for all events

### Enforcement
- **Type:** RUNTIME_CHECK
- **Severity:** HIGH

---

## Implementation Reference

### API Endpoints (PAC-BENSON-P22-C)

| Endpoint | Description | Invariants |
|----------|-------------|------------|
| `GET /occ/timeline/{pac_id}` | Full PAC timeline | INV-OCC-004, INV-OCC-005, INV-OCC-006 |
| `GET /occ/timeline/{pac_id}/events` | Timeline events (paginated) | INV-OCC-005, INV-OCC-006 |
| `GET /occ/timeline/{pac_id}/wraps` | WRAP milestones | INV-OCC-004, INV-OCC-005 |
| `GET /occ/timeline/{pac_id}/ber` | BER records | INV-OCC-004, INV-OCC-005 |
| `GET /occ/agents/{agent_id}/drilldown` | Agent drilldown | INV-OCC-004, INV-OCC-005 |
| `GET /occ/agents/{agent_id}/history` | Execution history | INV-OCC-005, INV-OCC-006 |
| `GET /occ/agents/{agent_id}/failures` | Failure records | INV-OCC-005, INV-OCC-006 |
| `GET /occ/agents/{agent_id}/evidence` | Evidence artifacts | INV-OCC-005 |
| `GET /occ/agents/{agent_id}/metrics` | Performance metrics | INV-OCC-005 |
| `GET /occ/diff/{left}/{right}` | Generic diff | INV-OCC-005, INV-OCC-006 |
| `GET /occ/diff/ber/{a}/{b}` | BER diff | INV-OCC-005, INV-OCC-006 |
| `GET /occ/diff/pdo/{a}/{b}` | PDO diff | INV-OCC-005, INV-OCC-006 |

### Frontend Components (SONNY)

| Component | Invariants Enforced |
|-----------|---------------------|
| `TimelineView` | INV-OCC-004, INV-OCC-006 |
| `TimelineEventCard` | INV-OCC-005 (displays evidence hash) |
| `AgentDrilldown` | INV-OCC-004, INV-OCC-006 |
| `DecisionDiffViewer` | INV-OCC-005, INV-OCC-006 |
| `ExecutionStateBanner` | INV-OCC-006 |

---

## Test Coverage

Tests are located in:
- `tests/occ/test_occ_timeline.py` - Timeline invariant tests
- `tests/occ/test_occ_agents.py` - Agent drilldown invariant tests
- `tests/occ/test_occ_diff.py` - Diff comparison invariant tests

All tests verify:
1. READ-ONLY enforcement (INV-OCC-005)
2. Evidence hash presence (INV-OCC-005)
3. Complete state visibility (INV-OCC-004, INV-OCC-006)
4. Proper error response format

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-01-12 | Initial OCC invariants (PAC-BENSON-P22-C) |

---

**ALEX — GID-08 — Governance Enforcer**
