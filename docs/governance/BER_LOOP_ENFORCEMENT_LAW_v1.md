# BER Loop Enforcement Law v1

**PAC Reference:** PAC-BENSON-EXEC-GOVERNANCE-BER-LOOP-ENFORCEMENT-020  
**Effective Date:** 2025-12-26  
**Status:** ACTIVE  
**Classification:** LAW-LEVEL (PERMANENT)

---

## 1. Purpose

This law establishes **mandatory BER loop enforcement** to eliminate the failure mode where:
- WRAP is delivered
- BER is never issued
- Session terminates in "awaiting BER" limbo

This must be **impossible**.

---

## 2. Core Principle

```
WRAP WITHOUT BER = INVALID SESSION
```

A session cannot complete successfully unless:
1. WRAP is received by ORCHESTRATION_ENGINE
2. BER is **synchronously** issued by ORCHESTRATION_ENGINE
3. BER is returned to user

---

## 3. Mandatory Post-WRAP Orchestration Callback

### 3.1 WRAP Receipt Triggers BER Requirement

When WRAP is received:
```
WRAP_RECEIVED → BER_REQUIRED (state transition)
```

The `BER_REQUIRED` state is **non-terminal**. Session cannot close in this state.

### 3.2 Synchronous BER Issuance

BER issuance must be **synchronous**, not:
- Deferred
- Async
- Queued
- Implicit

The ORCHESTRATION_ENGINE must invoke BER issuance **immediately** upon WRAP receipt.

### 3.3 No Implicit Handoffs

The following are **prohibited**:
- Terminal-level acknowledgment without orchestration handoff
- Assumption that Benson Execution will "pick up" WRAP
- Drafting surface consuming WRAP without BER
- Agent self-issuing BER

---

## 4. Terminal States

### 4.1 Valid Terminal States

| State | Description |
|-------|-------------|
| `BER_ISSUED` | BER has been issued, loop closed |
| `SESSION_INVALID` | Session terminated due to violation |

### 4.2 Invalid Terminal States

| State | Why Invalid |
|-------|-------------|
| `AWAITING_BER` | Loop not closed, session incomplete |
| `WRAP_RECEIVED` | Intermediate state, must transition |
| `BER_REQUIRED` | Non-terminal, must resolve |

### 4.3 State Machine

```
PAC_DISPATCHED
    │
    ▼
WRAP_RECEIVED
    │
    ▼
BER_REQUIRED  ←── NON-TERMINAL (cannot end here)
    │
    ├──► BER_ISSUED ──► SESSION_COMPLETE ✓
    │
    └──► TIMEOUT ──► SESSION_INVALID ✗
```

---

## 5. Authority Model

### 5.1 BER Issuance Authority

**ONLY** `GID-00 (ORCHESTRATION_ENGINE)` may issue BER.

The following entities **CANNOT** issue BER:
- Drafting Surface (Jeffrey)
- Execution Agents (GID-01, GID-02, etc.)
- External systems

### 5.2 WRAP Authority

WRAP may be issued by:
- Execution Agents (as return artifact)

WRAP **MUST** be routed to ORCHESTRATION_ENGINE.

---

## 6. Enforcement Mechanism

### 6.1 BER Loop Enforcer

The `BERLoopEnforcer` component:
1. Monitors all active sessions
2. Tracks WRAP receipt
3. Enforces BER issuance
4. Terminates invalid sessions

### 6.2 Timeout Handling

If BER is not issued within timeout:
```
BER_REQUIRED + TIMEOUT → SESSION_INVALID
```

Default timeout: 0 (synchronous, no timeout allowed)

### 6.3 Error Handling

```python
class BERNotIssuedError(GovernanceError):
    """Raised when BER is not issued for received WRAP."""
    pass

class SessionInvalidError(GovernanceError):
    """Raised when session cannot be completed validly."""
    pass
```

---

## 7. Terminal Visibility

### 7.1 Required Emissions

| Event | Emission |
|-------|----------|
| WRAP received | `📥 WRAP RECEIVED — ROUTING TO ORCHESTRATION ENGINE` |
| BER processing | `🧠 ORCHESTRATION ENGINE REVIEWING WRAP` |
| BER issued | `🟩 BER ISSUED — LOOP CLOSED` |
| BER missing | `🟥 BER MISSING — SESSION TERMINATED` |

### 7.2 Emission Format

```
════════════════════════════════════════════════════════════════════════════════
📥 WRAP RECEIVED — ROUTING TO ORCHESTRATION ENGINE
   PAC_ID: PAC-BENSON-EXEC-GOVERNANCE-EXAMPLE-001
   FROM: GID-01 (Cody)
   STATUS: COMPLETE
════════════════════════════════════════════════════════════════════════════════

════════════════════════════════════════════════════════════════════════════════
🧠 ORCHESTRATION ENGINE REVIEWING WRAP
   PAC_ID: PAC-BENSON-EXEC-GOVERNANCE-EXAMPLE-001
   DELIVERABLES: 5/5 VERIFIED
   STATE: BER_REQUIRED
════════════════════════════════════════════════════════════════════════════════

════════════════════════════════════════════════════════════════════════════════
🟩 BER ISSUED — LOOP CLOSED
   PAC_ID: PAC-BENSON-EXEC-GOVERNANCE-EXAMPLE-001
   DECISION: APPROVE
   ISSUER: GID-00 (ORCHESTRATION_ENGINE)
   STATE: SESSION_COMPLETE
════════════════════════════════════════════════════════════════════════════════
```

---

## 8. Invariants

### INV-BER-001: WRAP Triggers BER Requirement
```
∀ session s:
  WRAP_RECEIVED(s) → BER_REQUIRED(s)
```

### INV-BER-002: No Awaiting BER Terminal State
```
∀ session s:
  TERMINAL(s) → ¬AWAITING_BER(s)
```

### INV-BER-003: BER Required Non-Terminal
```
∀ session s:
  BER_REQUIRED(s) → ¬TERMINAL(s)
```

### INV-BER-004: Valid Terminal States Only
```
∀ session s:
  TERMINAL(s) → (BER_ISSUED(s) ∨ SESSION_INVALID(s))
```

### INV-BER-005: BER Authority Restricted
```
∀ ber:
  ISSUED(ber) → ISSUER(ber) = GID-00
```

### INV-BER-006: Loop Closure Mechanical
```
∀ pac p:
  WRAP_RECEIVED(p) →◇ (BER_ISSUED(p) ∨ SESSION_INVALID(p))
```
(Every WRAP eventually leads to BER or invalid session)

---

## 9. Integration Points

### 9.1 Orchestration Engine

```python
class GovernanceOrchestrationEngine:
    def receive_wrap(self, pac_id: str, status: WRAPStatus) -> LoopState:
        """
        Receive WRAP and SYNCHRONOUSLY process to BER.
        
        This method MUST NOT return until BER is issued or session invalidated.
        """
        # 1. Record WRAP receipt
        loop = self._record_wrap(pac_id, status)
        
        # 2. Transition to BER_REQUIRED
        self._enforcer.require_ber(pac_id)
        
        # 3. SYNCHRONOUS BER processing
        ber_status = self._process_wrap_to_ber(pac_id, status)
        
        # 4. Issue BER (cannot skip)
        return self.issue_ber(pac_id, ber_status)
```

### 9.2 Session State

```python
class SessionState(Enum):
    # Active states
    PAC_DISPATCHED = "PAC_DISPATCHED"
    WRAP_RECEIVED = "WRAP_RECEIVED"
    BER_REQUIRED = "BER_REQUIRED"  # Non-terminal
    
    # Terminal states (valid)
    BER_ISSUED = "BER_ISSUED"
    
    # Terminal states (invalid)
    SESSION_INVALID = "SESSION_INVALID"
```

---

## 10. Failure Modes Eliminated

| Failure Mode | Prevention |
|--------------|------------|
| WRAP in limbo | Synchronous BER processing |
| Implicit BER assumption | Explicit BER_REQUIRED state |
| Agent self-BER | Authority validation |
| Deferred BER | No async BER allowed |
| Terminal without BER | State machine enforcement |

---

## 11. Training Signal

```
TRAINING_EVENT:     BER_LOOP_BREAK_CORRECTION
SIGNAL_TYPE:        GOVERNANCE_ENFORCEMENT
ERROR_CLASS:        LOOP_TERMINATION_FAILURE
ROOT_CAUSE:         Missing deterministic WRAP → BER routing
CORRECTION:         Mandatory BER loop enforcement + state machine
GENERALIZATION:     Enforce post-artifact obligations system-wide
MODEL_IMPACT:       Eliminate silent terminal states
RETENTION:          PERMANENT (LAW-LEVEL)
```

---

## 12. Compliance Checklist

- [ ] BER issued for every WRAP
- [ ] No sessions terminate in AWAITING_BER
- [ ] All BERs issued by GID-00
- [ ] Terminal emissions visible
- [ ] State transitions enforced
- [ ] Timeouts handled

---

## 13. Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-26 | Initial law (PAC-020) |
