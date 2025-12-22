# A11 — SYSTEM STATE INVARIANT LOCK

**Version:** 1.0.0
**Status:** LOCKED
**Authority:** Benson (GID-00)
**Custodian:** Atlas (GID-05)
**Ratified:** 2025-12-22

---

## 1. PURPOSE

This document defines the **immutable invariants** governing ChainBridge system state.

Atlas (GID-05) is the **System State Engine** — a read-only, facts-only observer that:
- Verifies reality
- Detects contradictions
- Enforces time-ordering
- Never decides, never executes

---

## 2. CANONICAL STATE DOMAINS

The following domains constitute ChainBridge system state:

| Domain | Description | Primary Key |
|--------|-------------|-------------|
| `shipment` | Logistics entity lifecycle | `shipment_id` |
| `event` | Time-ordered occurrences | `event_id` |
| `pdo` | Proof Decision Outcomes | `pdo_id` |
| `proof` | Cryptographic evidence artifacts | `proof_id` |
| `settlement` | Financial resolution states | `settlement_id` |
| `risk_verdict` | CRO policy evaluation results | `verdict_id` |
| `override` | Human/agent intervention records | `override_id` |

---

## 3. STATE INVARIANTS (IMMUTABLE)

### INV-S01: One State Per Artifact
```
∀ artifact_id: |state(artifact_id)| = 1
```
No artifact may exist in multiple simultaneous states.

### INV-S02: Forward-Only Transitions
```
∀ transition(s1 → s2): timestamp(s2) > timestamp(s1)
```
State transitions are monotonically forward in time.

### INV-S03: No Retroactive Mutation
```
∀ state(t): immutable after t + finality_window
```
Once finalized, state cannot be altered. Corrections require new artifacts.

### INV-S04: No Conflicting Truths
```
∀ artifact_id, source_a, source_b:
  state(artifact_id, source_a) = state(artifact_id, source_b)
```
All observers must see identical state for the same artifact.

### INV-S05: Time Monotonicity
```
∀ event_sequence: timestamp(e[n]) ≤ timestamp(e[n+1])
```
Events within a sequence maintain temporal ordering.

### INV-S06: Proof Lineage Required
```
∀ state_change: ∃ proof_id referencing state_change
```
No state transition without associated proof artifact.

### INV-S07: State-Proof Bidirectional Binding
```
∀ proof: ∃ state_reference(proof)
∀ state_change: ∃ proof_reference(state_change)
```
Proofs and states must mutually reference each other.

### INV-S08: Replay Determinism
```
replay(event_log) = current_state
```
Given the same event log, replay must produce identical state.

### INV-S09: No Orphan Artifacts
```
∀ artifact: ∃ parent_reference OR artifact.type = GENESIS
```
Every artifact must trace to a parent or be explicitly marked as genesis.

### INV-S10: Transition Validity
```
∀ transition(s1 → s2): valid(s1, s2) ∈ ALLOWED_TRANSITIONS
```
Only declared state transitions are permitted.

---

## 4. ALLOWED STATE TRANSITIONS

### Shipment States
```
CREATED → IN_TRANSIT → DELIVERED → SETTLED
CREATED → IN_TRANSIT → EXCEPTION → RESOLVED → SETTLED
CREATED → CANCELLED
IN_TRANSIT → CANCELLED (with penalty)
```

### Settlement States
```
PENDING → APPROVED → EXECUTED → FINALIZED
PENDING → REJECTED → DISPUTED → RESOLVED
PENDING → BLOCKED (risk hold)
```

### PDO States
```
CREATED → SIGNED → VERIFIED → ACCEPTED
CREATED → SIGNED → VERIFICATION_FAILED → REJECTED
CREATED → EXPIRED
```

---

## 5. VIOLATION HANDLING

| Violation | Severity | Action |
|-----------|----------|--------|
| Duplicate state | CRITICAL | Halt + Alert |
| Backward transition | CRITICAL | Reject + Log |
| Missing proof | HIGH | Block transition |
| Orphan artifact | MEDIUM | Quarantine + Investigate |
| Temporal violation | HIGH | Reject + Alert |
| Replay divergence | CRITICAL | Halt system |

---

## 6. READ-ONLY API CONTRACT

Atlas exposes state via read-only interfaces:

```
GET /api/state/v1/shipment/{shipment_id}
GET /api/state/v1/event/{event_id}
GET /api/state/v1/pdo/{pdo_id}
GET /api/state/v1/proof/{proof_id}
GET /api/state/v1/settlement/{settlement_id}
GET /api/state/v1/history/{artifact_type}/{artifact_id}
GET /api/state/v1/validate/{artifact_type}/{artifact_id}
POST /api/state/v1/replay (idempotent, read-only verification)
```

**Write endpoints: NONE**

---

## 7. AUDIT & COMPLIANCE

- All state queries logged with requester identity
- All state snapshots hashable for integrity verification
- Event logs retained per RETENTION_POLICY.md
- Replay capability required for dispute resolution

---

## 8. CUSTODIANSHIP

| Role | Agent | Authority |
|------|-------|-----------|
| Schema Definition | Atlas (GID-05) | READ |
| Invariant Enforcement | Atlas (GID-05) | VALIDATE |
| State Modification | NONE | FORBIDDEN |
| Replay Verification | Atlas (GID-05) | EXECUTE (read-only) |

---

## 9. AMENDMENT PROCESS

Amendments to A11 require:
1. PAC from Benson (GID-00)
2. Security review by Sam (GID-06)
3. Governance approval by Alex (GID-08)
4. Version increment
5. All agents notified

---

## 10. REFERENCES

- A3_SETTLEMENT_IMMUTABILITY_LOCK.md
- A4_PROOF_SURFACE_LOCK.md
- A6_RISK_POLICY_LOCK.md
- PDO_INVARIANTS.md
- PROOFPACK_INVARIANTS.md

---

**LOCK STATEMENT**

This document is LOCKED as of 2025-12-22.
No modification without explicit PAC from Benson (GID-00).

---

*Atlas (GID-05) — System State Engine — Facts Only*
