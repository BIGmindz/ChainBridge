# Execution Spine Invariants
**ALEX (GID-08) | PAC-ALEX-GOVERNANCE-LOCK-01**

---

## Purpose

This document defines the **non-negotiable invariants** of the ChainBridge Minimum Execution Spine (MES). These invariants MUST hold at all times. Violations are stop-the-line events.

---

## Invariants

### INV-01: Event → Decision → Action → Proof

Every execution MUST follow this exact sequence:

| Step | Component | Requirement |
|------|-----------|-------------|
| 1 | **Event** | Canonical event schema (`SpineEvent`) |
| 2 | **Decision** | Pure function, deterministic output |
| 3 | **Action** | Real side effect, explicit success/failure |
| 4 | **Proof** | Immutable artifact with deterministic hash |

**Violation:** Any execution path that skips a step.

---

### INV-02: No Execution Without Proof

Every spine execution MUST produce an `ExecutionProof` artifact.

```
proof.id         → UUID (unique)
proof.event_hash → SHA-256 of event
proof.decision_hash → SHA-256 of decision
proof.timestamp  → ISO8601 UTC
```

**Violation:** Execution completes without proof generation.

---

### INV-03: Deterministic Hashing

All hashes MUST be computed identically given the same inputs:

```python
# Canonical hash computation (PAC-BENSON-EXEC-SPINE-01)
def compute_hash(data: dict) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
```

**Violation:** Non-deterministic hash computation or collision.

---

### INV-04: No Silent Failures

Every failure MUST:

1. Raise an explicit exception OR
2. Return an explicit failure status with error message

```python
# CORRECT
ActionStatus.FAILED + error_message

# VIOLATION
return None  # Silent failure
pass         # Swallowed exception
```

**Violation:** Any code path that fails without explicit error surfacing.

---

### INV-05: Append-Only Persistence

Proof artifacts are **immutable and append-only**.

| Operation | Allowed |
|-----------|---------|
| CREATE | ✅ Yes |
| READ | ✅ Yes |
| UPDATE | ❌ NO |
| DELETE | ❌ NO |

**Violation:** Modification or deletion of proof artifacts.

---

### INV-06: Decision Logic is Pure

Decision functions MUST be pure:

- Same inputs → Same outputs
- No side effects
- No external state access
- No randomness

```python
# CORRECT - Pure decision
def decide(event: SpineEvent, rules: RuleSet) -> DecisionResult:
    return rules.apply(event)

# VIOLATION - Impure decision
def decide(event: SpineEvent) -> DecisionResult:
    if random.random() > 0.5:  # Non-deterministic
        return approve()
    db.read_state()  # External state
```

**Violation:** Non-deterministic or side-effecting decision logic.

---

### INV-07: Actions Must Be Traceable

Every action MUST have:

| Field | Required |
|-------|----------|
| `action_id` | UUID |
| `decision_id` | Reference to triggering decision |
| `status` | SUCCESS or FAILED (binary) |
| `timestamp` | ISO8601 UTC |

**Violation:** Action without traceability to its decision.

---

## Enforcement

| Invariant | Enforcement Point | Method |
|-----------|-------------------|--------|
| INV-01 | `SpineExecutor.execute()` | Type system + runtime check |
| INV-02 | `SpineExecutor.execute()` | Return type enforcement |
| INV-03 | `ExecutionProof.compute_hash()` | Unit tests |
| INV-04 | All spine modules | Linting + code review |
| INV-05 | `ProofStore` | No update/delete methods |
| INV-06 | `DecisionEngine` | Unit tests for determinism |
| INV-07 | `ActionResult` | Pydantic model validation |

---

## Reference Files

- [api/spine.py](../../api/spine.py) - HTTP endpoint
- [core/spine/executor.py](../../core/spine/executor.py) - Execution engine
- [core/spine/decision.py](../../core/spine/decision.py) - Decision logic
- [core/spine/event.py](../../core/spine/event.py) - Event schema
- [tests/spine/test_spine.py](../../tests/spine/test_spine.py) - Invariant tests

---

## FORBIDDEN INTERPRETATIONS

- ❌ This document does NOT grant ALEX authority
- ❌ This document does NOT override Benson decisions
- ❌ This document does NOT self-enforce
- ❌ ALEX is NOT the owner of this content
- ❌ ALEX cannot accept changes to this document

---

**Prepared by:** ALEX (GID-08)  
**Date:** 2025-12-19  
**PAC Reference:** PAC-ALEX-GOVERNANCE-LOCK-01  
**Classification:** Reference document. Navigational aid only. Non-authoritative.
