# A12 — State Transition Governance Lock

> **Governance Document** — PAC-ATLAS-A12-STATE-TRANSITION-GOVERNANCE-LOCK-01
> **Version:** A12
> **Effective Date:** 2025-12-22
> **Authority:** Benson (GID-00)
> **Executing Agent:** Atlas (GID-05)
> **Status:** LOCKED / CANONICAL
> **Change Authority:** Benson (GID-00) — Requires new PAC
> **Prerequisites:** A11_SYSTEM_STATE_INVARIANT_LOCK

---

## 0. PURPOSE

Lock state transition governance so that:
- Every artifact follows an **explicit lifecycle**
- **Illegal transitions are impossible** (fail-closed)
- All governed transitions are **proof-bound**
- Replay determinism is **preserved**

```
State is not just data.
State is the system's memory of what happened.
Transitions are the system's record of why it changed.
```

---

## 1. CONTEXT

| Lock | Scope | Status |
|------|-------|--------|
| A11 | State invariants (existence, replay, immutability) | ✅ ENFORCED |
| **A12** | **State transition governance** | 🔒 **THIS DOCUMENT** |

A12 builds on A11 by defining **how** state changes, not just **what** state exists.

---

## 2. CANONICAL STATE MACHINES

### 2.1 PDO Lifecycle

```
          ┌──────────┐
          │ CREATED  │  ← Initial state
          └────┬─────┘
               │
       ┌───────┴───────┐
       ▼               ▼
  ┌─────────┐     ┌─────────┐
  │ SIGNED  │     │ EXPIRED │ ← Terminal
  └────┬────┘     └─────────┘
       │
  ┌────┴────────────────┐
  ▼                     ▼
┌──────────┐    ┌───────────────────┐
│ VERIFIED │    │ VERIFICATION_FAILED│
└────┬─────┘    └─────────┬─────────┘
     │                    │
     ▼                    ▼
┌──────────┐        ┌──────────┐
│ ACCEPTED │        │ REJECTED │ ← Terminal
└──────────┘        └──────────┘
     ↑ Terminal
```

### 2.2 Settlement Lifecycle

```
         ┌─────────┐
         │ PENDING │  ← Initial state
         └────┬────┘
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
┌──────────┐ ┌─────────┐ ┌─────────┐
│ APPROVED │ │ REJECTED│ │ BLOCKED │
└────┬─────┘ └────┬────┘ └────┬────┘
     │            │           │
     ▼            ▼           ├──► PENDING
┌──────────┐ ┌──────────┐     └──► REJECTED
│ EXECUTED │ │ DISPUTED │
└────┬─────┘ └────┬─────┘
     │            │
     ▼            ▼
┌───────────┐ ┌──────────┐
│ FINALIZED │ │ RESOLVED │──► FINALIZED
└───────────┘ └──────────┘
     ↑ Terminal
```

### 2.3 Proof Lifecycle

```
         ┌─────────┐
         │ CREATED │  ← Initial state
         └────┬────┘
              │
              ▼
         ┌─────────┐
         │ SIGNED  │
         └────┬────┘
              │
    ┌─────────┴─────────┐
    ▼                   ▼
┌──────────┐      ┌───────────┐
│ VERIFIED │      │ REJECTED  │ ← Terminal
└────┬─────┘      └───────────┘
     │
     ▼
┌───────────┐
│ FINALIZED │ ← Terminal (IMMUTABLE)
└───────────┘
```

### 2.4 Deployment Lifecycle

```
         ┌──────────┐
         │ PROPOSED │  ← Initial state
         └────┬─────┘
              │
    ┌─────────┴─────────┐
    ▼                   ▼
┌──────────┐      ┌──────────┐
│ APPROVED │      │ REJECTED │ ← Terminal
└────┬─────┘      └──────────┘
     │
     ▼
┌──────────┐
│ DEPLOYED │
└────┬─────┘
     │
     ▼
┌──────────┐
│ VERIFIED │
└────┬─────┘
     │
    ┌┴────────────┐
    ▼             ▼
┌────────┐   ┌───────────┐
│ ACTIVE │   │ ROLLED_BACK│ ← Terminal
└───┬────┘   └───────────┘
    │
    ▼
┌────────────┐
│ DEPRECATED │ ← Terminal
└────────────┘
```

### 2.5 RiskDecision Lifecycle

```
         ┌─────────┐
         │ PENDING │  ← Initial state
         └────┬────┘
              │
              ▼
         ┌───────────┐
         │ EVALUATED │
         └─────┬─────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
┌─────────┐ ┌────────┐ ┌─────────┐
│ ALLOWED │ │ BLOCKED│ │ REVIEW  │
└────┬────┘ └───┬────┘ └────┬────┘
     │          │           │
     ▼          ▼           ▼
┌───────────┐ ┌─────────┐ ┌──────────┐
│ FINALIZED │ │FINALIZED│ │ ESCALATED│
└───────────┘ └─────────┘ └────┬─────┘
     ↑ Terminal    ↑ Terminal   │
                               ▼
                        ┌──────────────┐
                        │ OVERRIDE_APPLIED│
                        └───────┬──────┘
                                ▼
                          ┌───────────┐
                          │ FINALIZED │ ← Terminal
                          └───────────┘
```

---

## 3. TRANSITION INVARIANTS (HARD)

```yaml
A12_TRANSITION_INVARIANTS:
  # INV-T01: Explicit definition required
  all_transitions_declared: true
  implicit_transitions_forbidden: true
  
  # INV-T02: Fail-closed semantics
  undefined_transition_result: "REJECT"
  validation_failure_result: "REJECT"
  
  # INV-T03: Proof binding
  governed_transitions_require_proof: true
  proof_must_reference_transition: true
  
  # INV-T04: Authority binding
  transitions_require_authority_gid: true
  authority_must_be_valid_agent: true
  
  # INV-T05: Determinism
  same_input_same_output: true
  no_side_effects_in_validation: true
  
  # INV-T06: Terminal finality
  terminal_states_immutable: true
  no_transitions_from_terminal: true
  
  # INV-T07: Replay safety
  transition_history_preserved: true
  replay_produces_identical_state: true
```

---

## 4. TRANSITION PROOF SCHEMA

Every governed transition emits a `StateTransitionProof`:

```yaml
StateTransitionProof:
  proof_id: string        # Unique proof identifier
  artifact_type: enum     # PDO, PROOF, SETTLEMENT, DEPLOYMENT, RISK_DECISION
  artifact_id: string     # Target artifact identifier
  from_state: string      # Previous state
  to_state: string        # New state
  triggering_proof_id: string  # Proof that authorized this transition
  authority_gid: string   # Agent GID that authorized
  timestamp: datetime     # ISO 8601 timestamp
  hash: string            # SHA-256 of (artifact_id + from_state + to_state + timestamp)
```

---

## 5. AUTHORITY REQUIREMENTS

| Artifact Type | Transition | Required Authority |
|---------------|------------|-------------------|
| PDO | CREATED → SIGNED | Originator (any agent) |
| PDO | SIGNED → VERIFIED | Verifier agent |
| PDO | VERIFIED → ACCEPTED | System (automated) |
| Settlement | PENDING → APPROVED | CRO or delegate |
| Settlement | APPROVED → EXECUTED | System (automated) |
| Settlement | * → DISPUTED | Any authorized agent |
| Proof | * → FINALIZED | System (automated) |
| Deployment | PROPOSED → APPROVED | Benson (GID-00) |
| RiskDecision | REVIEW → ESCALATED | Risk agent |
| RiskDecision | ESCALATED → OVERRIDE_APPLIED | Human + 2 agents |

---

## 6. ILLEGAL TRANSITIONS (IMPLICIT DENY)

Any transition not explicitly declared is **ILLEGAL** and will be **REJECTED**.

Examples of illegal transitions:
- `FINALIZED → *` (terminal state)
- `ACCEPTED → CREATED` (backward)
- `PENDING → FINALIZED` (skipped states)
- `* → *` without proof (ungoverned)

---

## 7. CI ENFORCEMENT

```yaml
CI_TRANSITION_GATES:
  verify_all_states_reachable: true
  verify_no_orphan_transitions: true
  verify_no_implicit_transitions: true
  verify_proof_requirements_declared: true
  verify_authority_requirements_declared: true
  verify_terminal_states_enforced: true
  fail_on_undefined_transition: true
```

---

## 8. IMPLEMENTATION FILES

| File | Purpose |
|------|---------|
| `core/state/state_machine.py` | Canonical state machine definitions |
| `core/state/transition_validator.py` | Transition validation engine |
| `core/state/transition_proof.py` | Transition proof emission |
| `scripts/ci/verify_state_transitions.py` | CI verification |
| `tests/state/test_state_transitions.py` | Transition tests |

---

## 9. CHANGELOG

| Version | Date | Author | Change |
|---------|------|--------|--------|
| A12 v1.0.0 | 2025-12-22 | Atlas (GID-05) | Initial state transition governance lock |

---

**Document Status: 🔒 LOCKED**

🟦 Atlas (GID-05) — System State Engine
