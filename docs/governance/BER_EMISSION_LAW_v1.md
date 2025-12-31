# BER Emission Law v1

**PAC Reference:** PAC-BENSON-EXEC-GOVERNANCE-BER-EMISSION-ENFORCEMENT-021  
**Effective Date:** 2025-12-26  
**Status:** ACTIVE  
**Classification:** LAW-LEVEL (PERMANENT)  
**Supersedes:** PAC-020 (Partial Loop Closure)

---

## 1. Purpose

This law establishes **mandatory BER emission enforcement** to eliminate the final failure mode:

```
WRAP exists → BER issued internally → USER NEVER RECEIVES BER
```

This must be **IMPOSSIBLE**.

---

## 2. Core Principle

```
BER WITHOUT EXTERNAL EMISSION = INVALID SESSION
```

A BER is not complete until:
1. BER is **ISSUED** by ORCHESTRATION_ENGINE
2. BER is **EMITTED** via terminal renderer
3. BER artifact is **RETURNED** to external caller

**Internal state ≠ Delivered outcome**

---

## 3. New Invariant: INV-BER-007

### 3.1 Definition

```
INV-BER-007: BER MUST BE EXTERNALLY EMITTED
───────────────────────────────────────────────────────────────────────────────
∀ session s:
  BER_ISSUED(s) → BER_EMITTED(s)

A BER that is issued but not emitted is a governance violation.
```

### 3.2 Enforcement

```python
if ber_issued and not ber_emitted:
    raise BERNotEmittedError(pac_id)
```

### 3.3 Observable Completion

Loop closure is not complete until **externally observable**:
- Terminal emission: `🟩 BER EMITTED — LOOP CLOSED`
- BER artifact returned to caller
- Session state: `BER_EMITTED`

---

## 4. Drafting Surface Prohibition

### 4.1 Rule

```
DRAFTING SURFACES MAY NEVER APPEAR IN BER FLOW
```

The following are **PROHIBITED**:
- Drafting surface issuing BER
- Drafting surface receiving BER for completion
- Drafting surface referenced in BER state transitions
- Drafting surface authority in BER processing

### 4.2 Rationale

- Drafting surfaces are conversational interfaces
- They have no execution authority
- They cannot complete loops
- They are not governance components

### 4.3 Valid BER Flow

```
Agent (GID-01+)
    ↓ WRAP
ORCHESTRATION_ENGINE (GID-00)
    ↓ Issues BER
    ↓ Emits BER
    ↓ Returns BER
EXTERNAL CALLER (User)
```

### 4.4 Invalid BER Flow

```
❌ Agent → WRAP → Drafting Surface → BER
❌ Agent → WRAP → ORCHESTRATION_ENGINE → BER → Drafting Surface
❌ Drafting Surface issues BER
```

---

## 5. BER Emission States

### 5.1 State Machine Update

```
PAC_DISPATCHED
    │
    ▼
WRAP_RECEIVED
    │
    ▼
BER_REQUIRED
    │
    ▼
BER_ISSUED  ←── INTERNAL (not yet complete)
    │
    ▼
BER_EMITTED ←── EXTERNAL (loop closed)
    │
    ▼
SESSION_COMPLETE ✓
```

### 5.2 New Terminal States

| State | Description |
|-------|-------------|
| `BER_EMITTED` | BER has been issued AND emitted |
| `BER_NOT_EMITTED` | BER issued but emission failed → INVALID |

### 5.3 BER_ISSUED is Non-Terminal

`BER_ISSUED` without `BER_EMITTED` is **non-terminal**.
Session cannot end in `BER_ISSUED` state.

---

## 6. Terminal Visibility Requirements

### 6.1 Mandatory Emissions

| Event | Emission | Required |
|-------|----------|----------|
| BER processing | `🧠 ORCHESTRATION ENGINE ISSUING BER` | ✓ |
| BER emitted | `🟩 BER EMITTED — LOOP CLOSED` | ✓ |
| Emission failed | `🟥 BER NOT EMITTED — SESSION TERMINATED` | ✓ |

### 6.2 Emission Format

```
════════════════════════════════════════════════════════════════════════════════
🧠 ORCHESTRATION ENGINE ISSUING BER
   PAC_ID: PAC-EXAMPLE-001
   WRAP_STATUS: COMPLETE
   BER_DECISION: APPROVE
════════════════════════════════════════════════════════════════════════════════

════════════════════════════════════════════════════════════════════════════════
🟩 BER EMITTED — LOOP CLOSED
   PAC_ID: PAC-EXAMPLE-001
   DECISION: APPROVE
   ISSUER: GID-00 (ORCHESTRATION_ENGINE)
   EMITTED_TO: EXTERNAL_CALLER
   STATE: SESSION_COMPLETE
════════════════════════════════════════════════════════════════════════════════
```

### 6.3 Failure Emission

```
════════════════════════════════════════════════════════════════════════════════
🟥 BER NOT EMITTED — SESSION TERMINATED
   PAC_ID: PAC-EXAMPLE-001
   BER_STATUS: ISSUED_NOT_EMITTED
   ERROR: Emission failed
   STATE: SESSION_INVALID
   VIOLATION: INV-BER-007
════════════════════════════════════════════════════════════════════════════════
```

---

## 7. BER Artifact

### 7.1 Structure

```python
@dataclass(frozen=True)
class BERArtifact:
    """
    Immutable BER artifact returned to external caller.
    """
    pac_id: str
    decision: BERDecision  # APPROVE, CORRECTIVE, REJECT
    issuer: str  # Always "GID-00"
    issued_at: str
    emitted_at: str
    wrap_status: str
    session_state: str  # BER_EMITTED or SESSION_INVALID
```

### 7.2 Return Contract

The `receive_wrap()` method MUST return a `BERArtifact`:

```python
def receive_wrap(pac_id: str, status: WRAPStatus) -> BERArtifact:
    """
    Receive WRAP and synchronously issue, emit, and return BER.
    
    Returns:
        BERArtifact: Immutable artifact proving BER emission
    """
```

---

## 8. Error Handling

### 8.1 BERNotEmittedError

```python
class BERNotEmittedError(BERLoopError):
    """
    Raised when BER is issued but not emitted.
    
    This is a governance violation of INV-BER-007.
    """
    
    def __init__(self, pac_id: str):
        self.pac_id = pac_id
        super().__init__(
            f"BER_NOT_EMITTED: PAC {pac_id} — BER was issued but not emitted. "
            f"Violation of INV-BER-007. Session invalid."
        )
```

### 8.2 DraftingSurfaceInBERFlowError

```python
class DraftingSurfaceInBERFlowError(BERLoopError):
    """
    Raised when drafting surface appears in BER flow.
    
    Drafting surfaces have no authority in BER processing.
    """
    
    def __init__(self, pac_id: str, operation: str):
        self.pac_id = pac_id
        self.operation = operation
        super().__init__(
            f"DRAFTING_SURFACE_IN_BER_FLOW: PAC {pac_id} — "
            f"Drafting surface cannot {operation}. "
            f"Only ORCHESTRATION_ENGINE may process BER."
        )
```

---

## 9. Invariants (Complete Set)

| ID | Invariant | Description |
|----|-----------|-------------|
| INV-BER-001 | WRAP → BER_REQUIRED | WRAP receipt triggers BER requirement |
| INV-BER-002 | No AWAITING_BER terminal | Cannot end awaiting BER |
| INV-BER-003 | BER_REQUIRED non-terminal | Must resolve to BER or INVALID |
| INV-BER-004 | Valid terminal states only | BER_EMITTED or SESSION_INVALID |
| INV-BER-005 | GID-00 authority | Only ORCHESTRATION_ENGINE issues BER |
| INV-BER-006 | Loop closure mechanical | WRAP → BER guaranteed |
| **INV-BER-007** | **BER emission required** | **BER_ISSUED → BER_EMITTED** |
| **INV-BER-008** | **No drafting surfaces** | **Drafting surfaces prohibited from BER flow** |

---

## 10. Implementation Requirements

### 10.1 orchestration_engine.py

```python
def receive_wrap(
    self,
    pac_id: str,
    status: WRAPStatus,
    from_gid: str = None,
) -> BERArtifact:
    """
    Receive WRAP and synchronously issue, emit, and return BER.
    
    PAC-021 ENFORCEMENT:
    1. Issue BER
    2. Emit BER via terminal renderer
    3. Return BERArtifact to caller
    
    Returns:
        BERArtifact: Proof of BER emission (not just issuance)
    """
```

### 10.2 ber_loop_enforcer.py

```python
def issue_and_emit_ber(
    self,
    pac_id: str,
    ber_status: str,
) -> BERArtifact:
    """
    Issue AND emit BER synchronously.
    
    INV-BER-007: BER without emission = SESSION_INVALID
    """
```

---

## 11. Training Signal

```
TRAINING_EVENT:     BER_EMISSION_GAP_CORRECTION
SIGNAL_TYPE:        GOVERNANCE_ENFORCEMENT
ERROR_CLASS:        LOOP_EMISSION_FAILURE
ROOT_CAUSE:         BER issued internally but not emitted externally
CORRECTION:         Enforce BER_EMISSION_REQUIRED invariant
LESSONS:
  - Loop closure is not complete until externally observable
  - Internal state ≠ delivered outcome
  - Drafting surfaces must never be asked to complete execution loops
GENERALIZATION:     All artifacts must be both processed AND delivered
MODEL_IMPACT:       Eliminate silent internal completion
RETENTION:          PERMANENT (LAW-LEVEL)
```

---

## 12. Compliance Checklist

- [ ] Every WRAP results in emitted BER or terminal failure
- [ ] User ALWAYS receives BER artifact
- [ ] Drafting surface never referenced in BER flow
- [ ] BER_ISSUED without BER_EMITTED → SESSION_INVALID
- [ ] Terminal emissions visible for all BER operations
- [ ] BERArtifact returned to caller

---

## 13. Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-26 | Initial law (PAC-021), supersedes PAC-020 |
