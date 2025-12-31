# EXECUTION_DISPATCH_AUTH

## PAC Reference
**PAC-BENSON-P54-AGENT-DISPATCH-EXECUTION-BINDING-01**

## Overview

The `EXECUTION_DISPATCH_AUTH` artifact is an explicit dispatch authorization primitive that must be created before any agent can execute under Benson Execution. It binds a PAC → Agent → Execution Session, preventing implicit or accidental agent execution.

## Authority

- **Generator**: BENSON (GID-00) ONLY
- **Mode**: FAIL_CLOSED
- **Enforcement**: HARD_BLOCK on violation

## Purpose

This artifact enforces the following governance invariants:

1. **GS_160**: Agent execution without dispatch authorization triggers FAIL_CLOSED
2. **GS_161**: Session mismatch (PAC or agent) triggers FAIL_CLOSED  
3. **GS_162**: Expired dispatch authorization triggers FAIL_CLOSED

## Artifact Schema

```python
@dataclass
class ExecutionDispatchAuth:
    dispatch_id: str              # Unique identifier for this dispatch
    pac_id: str                   # PAC being dispatched
    agent_gid: str                # Agent authorized for execution
    agent_name: str               # Agent name for audit
    dispatch_session_id: str      # Unique session ID binding PAC → Agent → Execution
    dispatch_timestamp: str       # When dispatch was authorized
    authority_gid: str            # Must be GID-00 (Benson)
    authority_name: str           # Must be BENSON
    dispatch_hash: str            # Integrity hash of dispatch
    expires_at: Optional[str]     # Optional expiry (default: no expiry)
    notes: Optional[str]          # Optional notes for audit
```

## Key Fields

| Field | Description | Invariant |
|-------|-------------|-----------|
| `dispatch_session_id` | Unique session identifier | Globally unique, format: `SESS-{16-char-hex}` |
| `authority_gid` | Generator authority | Must be `GID-00` |
| `dispatch_hash` | SHA256 integrity hash | Computed from pac_id + agent_gid + session_id + timestamp |

## Usage

### Creating a Dispatch Authorization

```python
from benson_execution import BensonExecutionEngine

engine = BensonExecutionEngine()

# Create dispatch authorization
dispatch = engine.dispatch_agent(
    pac_id="PAC-DAN-P54-EXAMPLE-01",
    agent_gid="GID-01",
    agent_name="DAN",
    notes="Live execution for P54 implementation",
    expires_in_seconds=3600  # Optional: 1 hour expiry
)

print(f"Dispatch ID: {dispatch.dispatch_id}")
print(f"Session ID: {dispatch.dispatch_session_id}")
```

### Executing with Dispatch

```python
from benson_execution import BensonExecutionEngine, ExecutionResult

engine = BensonExecutionEngine()

# 1. Create dispatch
dispatch = engine.dispatch_agent(
    pac_id="PAC-DAN-P54-EXAMPLE-01",
    agent_gid="GID-01",
    agent_name="DAN"
)

# 2. Agent performs work and returns ExecutionResult
execution_result = ExecutionResult(
    pac_id="PAC-DAN-P54-EXAMPLE-01",
    agent_gid="GID-01",
    agent_name="DAN",
    execution_timestamp="2025-12-26T12:00:00Z",
    tasks_completed=["T1", "T2"],
    files_modified=["benson_execution.py"],
    quality_score=0.95,
    scope_compliance=True,
    execution_time_ms=5000
)

# 3. Execute with dispatch binding
result = engine.execute_pac_with_dispatch(
    dispatch_session_id=dispatch.dispatch_session_id,
    execution_result=execution_result
)

# Dispatch is automatically revoked after successful execution
```

### Validating a Dispatch

```python
# Validate before execution
validation = engine.validate_dispatch(
    dispatch_session_id=dispatch.dispatch_session_id,
    pac_id="PAC-DAN-P54-EXAMPLE-01",
    agent_gid="GID-01"
)

if validation["valid"]:
    print("Dispatch valid - execution can proceed")
else:
    print(f"Dispatch invalid: {validation['error_code']}")
    print(f"Message: {validation['message']}")
```

### Revoking a Dispatch

```python
# Manual revocation (automatic after execution)
result = engine.revoke_dispatch(dispatch.dispatch_session_id)
if result["revoked"]:
    print("Dispatch revoked successfully")
```

## Error Codes

| Code | Name | Description | Block Reason |
|------|------|-------------|--------------|
| GS_160 | DISPATCH_NOT_FOUND | No dispatch authorization exists for session | DISPATCH_NOT_AUTHORIZED |
| GS_161 | DISPATCH_SESSION_MISMATCH | PAC or agent doesn't match dispatch | DISPATCH_SESSION_MISMATCH |
| GS_162 | DISPATCH_EXPIRED | Dispatch authorization has expired | DISPATCH_EXPIRED |

## Telemetry Events

The dispatch system emits the following telemetry events:

| Event Type | When Emitted |
|------------|--------------|
| `DISPATCH_AUTHORIZED` | When `dispatch_agent()` creates authorization |
| `DISPATCH_VALIDATION_FAILED` | When validation fails (GS_160/161/162) |
| `PAC_DISPATCH_START_WITH_SESSION` | When execution begins with valid dispatch |
| `WRAP_GENERATED_WITH_DISPATCH` | When WRAP is generated with dispatch binding |
| `DISPATCH_REVOKED` | When dispatch is revoked (after execution or manually) |

## Lifecycle

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DISPATCH AUTHORIZATION LIFECYCLE                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   1. dispatch_agent()                                                 │
│      ├─ Generate unique dispatch_session_id                          │
│      ├─ Compute dispatch_hash                                        │
│      ├─ Store in _active_dispatches                                  │
│      └─ Emit DISPATCH_AUTHORIZED telemetry                           │
│                                                                       │
│   2. execute_pac_with_dispatch()                                     │
│      ├─ validate_dispatch()                                          │
│      │   ├─ Check session exists (GS_160)                            │
│      │   ├─ Check PAC matches (GS_161)                               │
│      │   ├─ Check agent matches (GS_161)                             │
│      │   └─ Check not expired (GS_162)                               │
│      ├─ Run execution checkpoints                                    │
│      ├─ Generate WRAP with dispatch binding                          │
│      └─ revoke_dispatch() on success                                 │
│                                                                       │
│   3. revoke_dispatch()                                                │
│      ├─ Remove from _active_dispatches                               │
│      └─ Emit DISPATCH_REVOKED telemetry                              │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Integration with BER

The Benson Execution Report (BER) includes dispatch information:

```json
{
  "dispatch_session_id": "SESS-ABC123DEF456",
  "dispatch_id": "DISPATCH-DAN-P54-20251226120000",
  "wrap": {
    "wrap_hash": "...",  // Includes dispatch_session_id in hash
    "pac_id": "...",
    "agent_gid": "..."
  }
}
```

## Governance Rules

The following rules are registered in `governance_rules.json`:

```json
{
  "rule_id": "GR-021",
  "scope": "EXECUTION",
  "trigger": "Agent execution without dispatch authorization",
  "enforcement": "HARD_BLOCK",
  "error_code": "GS_160",
  "description": "Agent execution requires explicit dispatch authorization from Benson"
}
```

## Version History

| Version | PAC | Changes |
|---------|-----|---------|
| 1.3.0 | PAC-BENSON-P54 | Initial dispatch authorization system |

## Related Documents

- [GOVERNANCE_DOCTRINE_V1.md](GOVERNANCE_DOCTRINE_V1.md)
- [BENSON_EXECUTION_REPORT_SCHEMA.md](BENSON_EXECUTION_REPORT_SCHEMA.md)
- [BENSON_EXECUTION_TELEMETRY.md](BENSON_EXECUTION_TELEMETRY.md)
- [AGENT_EXECUTION_RESULT_SCHEMA.md](AGENT_EXECUTION_RESULT_SCHEMA.md)
