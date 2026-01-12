# SCRAM Path Specification

## 🔴 CLASSIFICATION: LAW-TIER | CONSTITUTIONAL MANDATE

**PAC-SEC-P820** | Version 1.0.0  
**Constitutional Authority:** PAC-GOV-P45  
**Implementation Date:** 2026-01-12  
**Document Author:** LEXICON (GID-DOC-01)  
**Approved By:** ALEX (GID-08)

---

## 1. Overview

SCRAM (System Circuit Reduction And Mutation freeze) is the emergency shutdown capability mandated by PAC-GOV-P45. This specification defines the authoritative implementation, enforcement mechanisms, and constitutional guarantees.

### 1.1 Mission Statement

> SCRAM provides guaranteed termination of all ChainBridge execution paths within 500ms, with dual-key authorization, hardware-bound enforcement, fail-closed behavior, and immutable audit trails.

### 1.2 Classification

| Attribute | Value |
|-----------|-------|
| Governance Tier | **LAW** |
| Drift Tolerance | **ZERO** |
| Fail-Closed | **MANDATORY** |
| Bypass Permitted | **NEVER** |

---

## 2. Invariants

SCRAM enforces the following constitutional invariants:

| ID | Name | Enforcement | Violation Action |
|----|------|-------------|------------------|
| **INV-SYS-002** | No bypass of SCRAM checks permitted | HARD | TERMINATE |
| **INV-SCRAM-001** | Termination deadline ≤500ms | HARD | LOG_AND_TERMINATE |
| **INV-SCRAM-002** | Dual-key authorization required | HARD | TERMINATE_WITH_AUDIT |
| **INV-SCRAM-003** | Hardware-bound execution | SOFT | LOG_AND_CONTINUE |
| **INV-SCRAM-004** | Immutable audit trail | HARD | TERMINATE |
| **INV-SCRAM-005** | Fail-closed on error | HARD | TERMINATE |
| **INV-SCRAM-006** | 100% execution path coverage | SOFT | LOG_AND_CONTINUE |
| **INV-GOV-003** | LAW-tier constitutional compliance | HARD | TERMINATE |

---

## 3. Architecture

### 3.1 Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    SCRAM ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │  Operator Key   │    │  Architect Key  │                    │
│  │  (GID-OP-xxx)   │    │  (GID-CONST-01) │                    │
│  └────────┬────────┘    └────────┬────────┘                    │
│           │                      │                              │
│           └──────────┬───────────┘                              │
│                      ▼                                          │
│           ┌─────────────────────┐                               │
│           │  Dual-Key Verifier  │  INV-SCRAM-002               │
│           └──────────┬──────────┘                               │
│                      ▼                                          │
│           ┌─────────────────────┐                               │
│           │  SCRAM Controller   │  core/governance/scram.py    │
│           │  (Singleton)        │                               │
│           └──────────┬──────────┘                               │
│                      │                                          │
│      ┌───────────────┼───────────────┐                         │
│      ▼               ▼               ▼                         │
│  ┌───────┐      ┌───────┐      ┌───────┐                       │
│  │Path 1 │      │Path 2 │      │Path N │  Execution Paths      │
│  └───────┘      └───────┘      └───────┘                       │
│                      │                                          │
│                      ▼                                          │
│           ┌─────────────────────┐                               │
│           │  Hardware Sentinel  │  scram_sentinel.rs           │
│           │  (TITAN Kernel)     │  INV-SCRAM-003               │
│           └──────────┬──────────┘                               │
│                      ▼                                          │
│           ┌─────────────────────┐                               │
│           │  Immutable Ledger   │  INV-SCRAM-004               │
│           │  (Audit Anchor)     │                               │
│           └─────────────────────┘                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 File Locations

| Component | Path | Language |
|-----------|------|----------|
| Core Controller | `core/governance/scram.py` | Python |
| Policies | `core/governance/scram_policies.json` | JSON |
| Configuration | `config/scram_config.yaml` | YAML |
| Event Schema | `schemas/scram_event_schema.json` | JSON Schema |
| Hardware Sentinel | `chainbridge_kernel/src/scram_sentinel.rs` | Rust |
| Test Suite | `tests/governance/test_scram.py` | Python |
| CI Workflow | `.github/workflows/scram-validation.yml` | YAML |
| Specification | `docs/governance/SCRAM_PATH_SPEC.md` | Markdown |

---

## 4. State Machine

SCRAM follows a strict state machine with monotonic progression:

```
            ┌─────────────────────────────────────────┐
            │                                         │
            ▼                                         │
        ┌───────┐                                     │
    ┌──▶│ ARMED │◀────────────────────────────────────┤
    │   └───┬───┘                                     │
    │       │ activate()                              │
    │       ▼                                         │
    │   ┌────────────┐                                │
    │   │ ACTIVATING │                                │
    │   └─────┬──────┘                                │
    │         │                                       │
    │    ┌────┴────┐                                  │
    │    ▼         ▼                                  │
    │ ┌──────────┐  ┌────────┐                        │
    │ │EXECUTING │  │ FAILED │────────────────────────┤
    │ └────┬─────┘  └────────┘                        │
    │      │                                          │
    │      ▼                                          │
    │ ┌──────────┐                                    │
    │ │ COMPLETE │────────────────────────────────────┘
    │ └──────────┘
    │      │
    │      │ reset() [LAW-tier required]
    └──────┘
```

### 4.1 State Descriptions

| State | Description | Allowed Transitions |
|-------|-------------|---------------------|
| **ARMED** | Ready for activation | → ACTIVATING |
| **ACTIVATING** | Dual-key verification in progress | → EXECUTING, FAILED |
| **EXECUTING** | Termination sequence running | → COMPLETE, FAILED |
| **COMPLETE** | All paths terminated successfully | → ARMED (via reset) |
| **FAILED** | Error occurred (still terminates) | → ARMED (via reset) |

---

## 5. Authorization Model

### 5.1 Dual-Key Requirement (INV-SCRAM-002)

SCRAM activation requires authorization from **both**:

1. **Operator Key** (`key_type: "operator"`)
   - Issued to designated operators
   - Bound to operator identity (GID)
   - Time-limited validity

2. **Architect Key** (`key_type: "architect"`)
   - Issued to constitutional authority
   - Currently: Jeffrey (GID-CONST-01)
   - Strategic-level authorization

### 5.2 Key Structure

```python
@dataclass(frozen=True)
class SCRAMKey:
    key_id: str           # Unique identifier
    key_type: str         # "operator" or "architect"
    key_hash: str         # SHA-256 hash of key material
    issued_at: str        # ISO 8601 timestamp
    expires_at: str       # Optional expiration
```

### 5.3 Authorization Flow

```
1. Operator requests SCRAM activation
2. Operator key authorized → stored in controller
3. Architect key authorized → stored in controller
4. Dual-key verification performed
5. If PASS: proceed to execution
6. If FAIL: fail-closed termination with audit
```

---

## 6. Termination Guarantees

### 6.1 500ms Deadline (INV-SCRAM-001)

SCRAM guarantees termination within **500 milliseconds** from activation:

- All registered execution paths receive termination signal
- All termination hooks execute
- Hardware sentinel acknowledges
- Audit event committed

**If deadline exceeded:**
- Termination continues (fail-closed)
- INV-SCRAM-001 violation logged
- Audit event records actual latency

### 6.2 Execution Path Coverage (INV-SCRAM-006)

All ChainBridge execution paths must register with SCRAM:

```python
controller = get_scram_controller()
controller.register_execution_path(
    path_id="finance.settlement",
    termination_handler=cleanup_settlements
)
```

Discovery modules:
- `core.decisions`
- `core.finance`
- `core.ledger`
- `core.swarm`
- `api`
- `gateway`

---

## 7. Fail-Closed Behavior (INV-SCRAM-005)

SCRAM implements fail-closed semantics:

| Condition | Action |
|-----------|--------|
| Authorization failure | Terminate + Audit |
| Handler exception | Continue termination |
| Hook exception | Continue execution |
| Timeout | Force terminate |
| Config error | Use safe defaults |
| Any unexpected error | Terminate |

**Constitutional Guarantee:**
> Under no circumstance may SCRAM fail in a way that leaves execution paths running.

---

## 8. Hardware Binding (INV-SCRAM-003)

### 8.1 TITAN Sentinel Integration

SCRAM integrates with the TITAN kernel sentinel (`scram_sentinel.rs`) for hardware-level enforcement:

```
Python Layer (scram.py)
        │
        ▼ [Signal File]
Rust Layer (scram_sentinel.rs)
        │
        ▼ [Process Termination]
Operating System
```

### 8.2 Signal File Protocol

Location: `/tmp/chainbridge_scram_sentinel`

```json
{
  "command": "SCRAM_ACTIVATE",
  "timestamp": "2026-01-12T19:45:00Z",
  "pid": 12345,
  "reason": "operator_initiated"
}
```

### 8.3 Sentinel Behavior

1. Monitors signal file continuously (10ms poll interval)
2. On SCRAM_ACTIVATE detected:
   - Records activation timestamp
   - Executes hardware-level termination
   - Writes audit log
   - Terminates process (exit code 1)

---

## 9. Audit Trail (INV-SCRAM-004)

### 9.1 Immutable Event Structure

Every SCRAM activation produces an immutable audit event:

```json
{
  "event_id": "SCRAM-20260112194500123456",
  "timestamp": "2026-01-12T19:45:00.123456+00:00",
  "scram_state": "COMPLETE",
  "reason": "operator_initiated",
  "operator_key_hash": "a1b2c3d4...",
  "architect_key_hash": "f6e5d4c3...",
  "execution_paths_terminated": 15,
  "termination_latency_ms": 127.45,
  "invariants_checked": ["INV-SYS-002", ...],
  "invariants_passed": ["INV-SYS-002", ...],
  "invariants_failed": [],
  "hardware_sentinel_ack": true,
  "ledger_anchor_hash": "1234567890abcdef...",
  "content_hash": "abcdef1234567890..."
}
```

### 9.2 Immutability Guarantees

- **Content Hash:** SHA-256 of event content prevents tampering
- **Ledger Anchor:** Event anchored to immutable ledger
- **Append-Only:** Audit log is append-only (no deletions)
- **Retention:** Infinite retention (retention_days: -1)

### 9.3 Audit Log Location

Default: `/var/log/chainbridge/scram.log`

Configurable via `config/scram_config.yaml`.

---

## 10. Valid Activation Reasons

SCRAM may be activated for the following reasons:

| Reason | Description | Typical Initiator |
|--------|-------------|-------------------|
| `operator_initiated` | Manual operator activation | Operator |
| `architect_initiated` | Strategic-level activation | Architect |
| `invariant_violation` | System invariant breached | ALEX |
| `security_breach` | Security threat detected | CIPHER/AEGIS |
| `governance_mandate` | Constitutional requirement | ALEX |
| `system_critical` | Critical system failure | Automatic |
| `constitutional_override` | LAW-tier override | Architect |
| `sentinel_trigger` | Hardware sentinel activation | TITAN |
| `chronos_deadline` | Temporal invariant violation | CHRONOS |

---

## 11. Configuration Reference

### 11.1 YAML Configuration (`config/scram_config.yaml`)

```yaml
scram:
  version: "1.0.0"
  pac_id: "PAC-SEC-P820"
  governance_tier: "LAW"
  
  # Termination (INV-SCRAM-001)
  max_termination_ms: 500          # IMMUTABLE
  deadline_enforcement: "HARD"
  
  # Authorization (INV-SCRAM-002)
  require_dual_key: true           # IMMUTABLE
  authorization_timeout_seconds: 30
  
  # Hardware Binding (INV-SCRAM-003)
  hardware_sentinel_required: true
  sentinel_path: "/tmp/chainbridge_scram_sentinel"
  
  # Fail-Closed (INV-SCRAM-005)
  fail_closed_on_error: true       # IMMUTABLE
```

### 11.2 Immutable Settings

The following settings **CANNOT** be disabled:
- `require_dual_key`
- `fail_closed_on_error`
- `max_termination_ms` (cannot exceed 500)

---

## 12. API Reference

### 12.1 SCRAMController

```python
from core.governance.scram import get_scram_controller, SCRAMReason, SCRAMKey

# Get singleton controller
controller = get_scram_controller()

# Check state
assert controller.is_armed

# Register execution path
controller.register_execution_path("my-service", cleanup_handler)

# Authorize keys
controller.authorize_key(operator_key)
controller.authorize_key(architect_key)

# Activate SCRAM
event = controller.activate(SCRAMReason.OPERATOR_INITIATED)

# Check result
assert event.termination_latency_ms < 500
```

### 12.2 Emergency SCRAM

```python
from core.governance.scram import emergency_scram, SCRAMReason

# Immediate activation with keys
event = emergency_scram(
    reason=SCRAMReason.SECURITY_BREACH,
    operator_key=op_key,
    architect_key=arch_key,
    metadata={"threat_id": "THREAT-001"}
)
```

---

## 13. Testing Requirements

### 13.1 Coverage Requirements (INV-SCRAM-006)

Test suite must cover:

- [ ] Singleton pattern enforcement
- [ ] Initial ARMED state
- [ ] Key authorization (valid/invalid/expired)
- [ ] Dual-key verification
- [ ] Execution path termination
- [ ] Termination hook execution
- [ ] 500ms deadline validation
- [ ] Fail-closed on handler errors
- [ ] Audit event generation
- [ ] Content hash immutability
- [ ] State transitions
- [ ] Reset functionality
- [ ] All invariant checks

### 13.2 Running Tests

```bash
# Run SCRAM tests
pytest tests/governance/test_scram.py -v

# With coverage
pytest tests/governance/test_scram.py --cov=core/governance/scram
```

---

## 14. Agent Responsibilities

| Agent | GID | Responsibility |
|-------|-----|----------------|
| **BENSON** | GID-00 | Orchestration, BER generation |
| **ALEX** | GID-08 | Constitutional compliance, governance certification |
| **CIPHER** | GID-SEC-01 | Cryptographic audit trails, key security |
| **AEGIS** | GID-WARGAME-01 | Adversarial testing, fail-closed validation |
| **CODY** | GID-01 | Core implementation, execution paths |
| **DAN** | GID-07 | Infrastructure integration, Docker/K8s |
| **TITAN** | GID-KERNEL-01 | Hardware sentinel, kernel enforcement |
| **SAM** | GID-06 | Key management, HSM integration |
| **SENTINEL** | GID-TEST-01 | Test suite, coverage validation |
| **LEXICON** | GID-DOC-01 | Documentation, specifications |
| **ATLAS** | GID-11 | Integration verification, gap analysis |
| **CHRONOS** | GID-TIME-01 | Timing validation, deadline enforcement |

---

## 15. Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-12 | LEXICON (GID-DOC-01) | Initial specification per PAC-SEC-P820 |

---

## 16. References

- **PAC-GOV-P45:** Invariant Enforcement (SCRAM mandate)
- **PAC-SEC-P820:** SCRAM Implementation PAC
- **INV-SYS-002:** Non-bypassable checks invariant
- **ATLAS Canonical Overview:** Gap analysis identifying missing scram.py

---

🔴 **CONSTITUTIONAL NOTICE** 🔴

This specification is a LAW-tier governance document. Modifications require:
1. PAC issuance by Architect (GID-CONST-01)
2. Review by ALEX (GID-08)
3. Verification by BENSON (GID-00)

Unauthorized modifications constitute a constitutional violation.
