# ChainBridge Bootstrap & Session Reset Protocol v1

**PAC Reference:** PAC-BENSON-EXEC-GOVERNANCE-BOOTSTRAP-PROTOCOL-016  
**Effective Date:** 2025-12-26  
**Status:** ACTIVE  
**Discipline:** FAIL-CLOSED  

---

## 1. PURPOSE

This protocol defines the **mandatory entry gate** before any PAC execution.  
No agent may execute governance-controlled operations without completing bootstrap.

**Invariants:**
- `INV-BOOT-001`: No PAC execution without bootstrap
- `INV-BOOT-002`: Bootstrap is idempotent within session
- `INV-BOOT-003`: Re-bootstrap mid-session is forbidden
- `INV-BOOT-004`: Partial bootstrap equals no bootstrap (FAIL-CLOSED)
- `INV-BOOT-005`: All locks must be acquired atomically

---

## 2. BOOTSTRAP SEQUENCE

```
┌─────────────────────────────────────────────────────────────────┐
│                    BOOTSTRAP SEQUENCE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  STEP 1: IDENTITY LOCK                                          │
│  ├─ Declare GID (e.g., GID-01)                                  │
│  ├─ Validate against gid_registry.json                          │
│  └─ Lock identity_locked = True                                 │
│                                                                 │
│  STEP 2: MODE LOCK                                              │
│  ├─ Declare MODE (e.g., EXECUTION)                              │
│  ├─ Validate mode permitted for GID                             │
│  └─ Lock mode_locked = True                                     │
│                                                                 │
│  STEP 3: LANE LOCK                                              │
│  ├─ Declare LANE (e.g., GOVERNANCE)                             │
│  ├─ Validate lane permitted for GID                             │
│  └─ Lock lane_locked = True                                     │
│                                                                 │
│  STEP 4: TOOL STRIP                                             │
│  ├─ Evaluate MODE + LANE → tool matrix                          │
│  ├─ Strip disallowed tools                                      │
│  └─ Lock tools_locked = True                                    │
│                                                                 │
│  STEP 5: ECHO HANDSHAKE                                         │
│  ├─ Format: "GID-XX | MODE | LANE"                              │
│  ├─ Emit to terminal                                            │
│  └─ Lock handshake_complete = True                              │
│                                                                 │
│  STEP 6: BOOTSTRAP SEAL                                         │
│  ├─ Verify all 5 locks acquired                                 │
│  ├─ Generate bootstrap_token                                    │
│  └─ Emit BOOTSTRAP COMPLETE to terminal                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. TERMINAL OUTPUT FORMAT

### 3.1 Bootstrap Start

```
════════════════════════════════════════════════════════════════════════════════
🔐 BOOTSTRAP SEQUENCE INITIATED
════════════════════════════════════════════════════════════════════════════════
```

### 3.2 Lock Acquisition

```
BOOT-01  Identity Lock             ✅ LOCKED  GID-01
BOOT-02  Mode Lock                 ✅ LOCKED  EXECUTION
BOOT-03  Lane Lock                 ✅ LOCKED  GOVERNANCE
BOOT-04  Tool Strip                ✅ LOCKED  12 tools permitted
BOOT-05  Echo Handshake            ✅ LOCKED  GID-01 | EXECUTION | GOVERNANCE
```

### 3.3 Bootstrap Complete

```
════════════════════════════════════════════════════════════════════════════════
🟩 BOOTSTRAP COMPLETE — SESSION SEALED
════════════════════════════════════════════════════════════════════════════════
TOKEN:       boot_<timestamp>_<gid>
IDENTITY:    GID-01 (CODY)
MODE:        EXECUTION
LANE:        GOVERNANCE
TOOLS:       12 permitted, 8 stripped
STATUS:      READY_FOR_PAC
════════════════════════════════════════════════════════════════════════════════
```

### 3.4 Bootstrap Failure

```
════════════════════════════════════════════════════════════════════════════════
🟥 BOOTSTRAP FAILED — SESSION NOT SEALED
════════════════════════════════════════════════════════════════════════════════
FAILED_LOCKS:
   └─ BOOT-02: Mode INVALID not permitted for GID-01
ACTION:      BOOTSTRAP_REQUIRED
════════════════════════════════════════════════════════════════════════════════
```

---

## 4. PROGRAMMATIC ENFORCEMENT

### 4.1 Bootstrap State Model

```python
@dataclass(frozen=True)
class BootstrapState:
    gid: str
    mode: str
    lane: str
    identity_locked: bool
    mode_locked: bool
    lane_locked: bool
    tools_locked: bool
    handshake_complete: bool
    bootstrap_token: Optional[str]
    sealed_at: Optional[str]
    
    @property
    def is_sealed(self) -> bool:
        return all([
            self.identity_locked,
            self.mode_locked,
            self.lane_locked,
            self.tools_locked,
            self.handshake_complete,
            self.bootstrap_token is not None,
        ])
```

### 4.2 Enforcement Check

```python
def require_bootstrap(state: BootstrapState) -> None:
    """Raises BootstrapRequiredError if not sealed."""
    if not state.is_sealed:
        raise BootstrapRequiredError(
            "PAC execution blocked: bootstrap not complete"
        )
```

---

## 5. FAILURE MODES

| Failure | Behavior | Recovery |
|---------|----------|----------|
| Missing bootstrap | PAC execution blocked | Complete bootstrap |
| Partial bootstrap | Session invalid, all locks released | Restart bootstrap |
| Invalid GID | Bootstrap rejected | Correct GID |
| Invalid Mode | Bootstrap rejected | Correct Mode |
| Invalid Lane | Bootstrap rejected | Correct Lane |
| Re-bootstrap attempt | Session terminated | New session required |

---

## 6. CROSS-SURFACE CONSISTENCY

This protocol applies identically to:

| Surface | Bootstrap Entry Point |
|---------|----------------------|
| ChatGPT | First message in conversation |
| VS Code Copilot | First interaction in session |
| API Clients | First request in session |
| Future Surfaces | MUST implement bootstrap gate |

---

## 7. ANTI-PATTERNS (FORBIDDEN)

❌ **Implicit bootstrap** — Assuming identity from context  
❌ **Deferred bootstrap** — Starting work before locks acquired  
❌ **Partial execution** — Acting on subset of bootstrap  
❌ **Bootstrap override** — Changing locks mid-session  
❌ **Silent failure** — Continuing without terminal output  

---

## 8. VERIFICATION CHECKLIST

Before issuing any PAC, verify:

- [ ] Bootstrap sequence completed
- [ ] All 5 locks acquired (identity, mode, lane, tools, handshake)
- [ ] Terminal output emitted
- [ ] Bootstrap token generated
- [ ] Session marked as sealed

---

## 9. REVISION HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-26 | GID-01 (Cody) | Initial protocol |

---

**END OF DOCUMENT**
