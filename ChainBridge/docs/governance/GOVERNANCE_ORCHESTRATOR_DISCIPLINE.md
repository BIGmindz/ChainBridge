# GOVERNANCE: ORCHESTRATOR DISCIPLINE

**PAC Reference:** PAC-BENSON-P45-ORCHESTRATOR-IDENTITY-GATEWAY-AND-RESPONSE-DISCIPLINE-RESET-01  
**Authority:** BENSON (GID-00)  
**Effective:** Immediate  
**Mode:** FAIL_CLOSED  

---

## 1. PURPOSE

Re-establish strict Benson CTO/orchestrator behavior. Eliminate uncontrolled execution, agent bleed-through, unsolicited PACs, and non-factual responses.

This document defines the rules, validators, and error codes that enforce orchestrator discipline across the ChainBridge governance system.

---

## 2. CORE INVARIANTS

### 2.1 No Agent May Self-Activate

An agent MUST NOT perform actions without explicit orchestrator activation. Self-activation violates the chain of command and results in:

```
GS_117: AGENT_SELF_ACTIVATION — Agent attempted self-activation without orchestrator approval.
```

### 2.2 No PAC Without Benson Gateway Approval

Every PAC issuance MUST pass through the Benson Gateway. Bypassing the gateway results in:

```
GS_116: GATEWAY_BYPASS — PAC issued without Benson Gateway approval.
```

### 2.3 No Execution Without Explicit Request

Code execution, file modifications, and state changes require explicit user request. Unsolicited execution results in:

```
GS_119: UNSOLICITED_EXECUTION — Execution-style output without explicit request.
```

### 2.4 No Identity Drift or Bleed-Through

An agent's declared identity (GID, name, lane) MUST remain consistent throughout an artifact. Identity drift results in:

```
GS_118: IDENTITY_DRIFT — Agent identity mismatch or bleed-through detected.
```

---

## 3. BENSON GATEWAY

### 3.1 Gateway Requirements

All PAC artifacts MUST include a `GATEWAY_CHECKS` block:

```yaml
GATEWAY_CHECKS:
  governance:
    - FAIL_CLOSED
    - BENSON_SEQUENCING
  assumptions:
    - All imports resolved locally
    - No network calls required
  authority: GID-00
```

### 3.2 Gateway Validation

The `orchestrator_guard.py` module validates:

1. Presence of `GATEWAY_CHECK[S]` block
2. Requester GID in valid registry
3. Required `governance` field present

### 3.3 Gateway States

| State | Description |
|-------|-------------|
| `CLOSED` | Default — no execution allowed |
| `OPEN` | Gateway opened by explicit request |
| `BLOCKED` | Blocked due to violation |

---

## 4. AGENT ACTIVATION

### 4.1 Activation Block

All agent actions require an `AGENT_ACTIVATION_ACK` block:

```yaml
AGENT_ACTIVATION_ACK:
  agent_name: SONNY
  gid: GID-01
  activated_by: GID-00
  timestamp: 2025-06-18T10:00:00Z
```

### 4.2 Valid Agent Registry

| GID | Agent Name | Primary Lane |
|-----|------------|--------------|
| GID-00 | BENSON | ORCHESTRATION |
| GID-01 | SONNY | EXECUTION |
| GID-02 | MAGGIE | EXECUTION |
| GID-03 | CODY | STRATEGY |
| GID-04 | DAN | EXECUTION |
| GID-05 | ATLAS | EXECUTION |
| GID-06 | SAM | STRATEGY |
| GID-07 | DAN | EXECUTION |
| GID-08 | ALEX | GOVERNANCE |
| GID-09 | TINA | EXECUTION |
| GID-10 | MAGGIE | EXECUTION |
| GID-11 | ATLAS | ADVISORY |
| GID-12 | RUBY | EXECUTION |

### 4.3 Activation Validation

The guard validates:

1. Presence of `AGENT_ACTIVATION_ACK` block
2. Agent GID in valid registry
3. Agent name matches registry for GID

---

## 5. IDENTITY CONSISTENCY

### 5.1 Identity Fields

Each agent artifact declares identity through:

- `gid`: Global identifier (e.g., GID-01)
- `agent_name`: Agent name (e.g., SONNY)
- `execution_lane`: Authorized lane (e.g., EXECUTION)

### 5.2 Consistency Rules

1. GID/name MUST match registry
2. Lane authorization MUST be valid for GID
3. No conflicting GIDs within artifact (except GID-00 in authority fields)

### 5.3 Lane Authorization

| Lane | Authorized Agents |
|------|-------------------|
| ORCHESTRATION | GID-00 |
| GOVERNANCE | GID-00, GID-08 |
| STRATEGY | GID-00, GID-03, GID-06 |
| EXECUTION | GID-00, GID-01, GID-02, GID-04, GID-05, GID-09, GID-12 |
| ADVISORY | GID-00, GID-11 |

---

## 6. EXECUTION REQUEST VALIDATION

### 6.1 Execution Indicators

Execution is detected through:

- `artifact_status: EXECUTED`
- `artifact_status: CLOSED`
- `artifact_status: POSITIVE_CLOSURE`

### 6.2 Execution Requirements

Execution requires:

- `mode: EXECUTABLE` declaration
- Explicit user request
- Valid gateway passage

### 6.3 Advisory-Only Mode

Without explicit execution request:

- Output MUST be advisory/informational only
- No file modifications
- No state changes
- No code execution

---

## 7. ERROR CODE REFERENCE

| Code | Name | Description | Severity |
|------|------|-------------|----------|
| GS_116 | GATEWAY_BYPASS | PAC issued without Benson Gateway approval | BLOCKING |
| GS_117 | AGENT_SELF_ACTIVATION | Agent attempted self-activation without orchestrator approval | BLOCKING |
| GS_118 | IDENTITY_DRIFT | Agent identity mismatch or bleed-through detected | BLOCKING |
| GS_119 | UNSOLICITED_EXECUTION | Execution-style output without explicit request | BLOCKING |

---

## 8. VALIDATION WORKFLOW

### 8.1 Full Discipline Check

```python
from tools.governance.orchestrator_guard import OrchestratorGuard

guard = OrchestratorGuard()
result = guard.validate_orchestrator_discipline(content)

if not result["valid"]:
    for error in result["errors"]:
        print(f"[{error['code']}] {error['message']}")
```

### 8.2 Individual Checks

```python
from tools.governance.orchestrator_guard import (
    validate_gateway,
    validate_activation,
    validate_identity,
    validate_execution_request
)

# Gateway check
errors = validate_gateway(content)

# Activation check
errors = validate_activation(content)

# Identity check
errors = validate_identity(content)

# Execution request check
errors = validate_execution_request(content)
```

### 8.3 CLI Validation

```bash
python -m tools.governance.orchestrator_guard --file path/to/artifact.md --verbose
```

---

## 9. INTEGRATION WITH GATE PACK

The orchestrator_guard integrates with gate_pack.py through:

1. Error codes GS_116-119 registered in gate_pack
2. Validators callable from gate validation pipeline
3. Consistent error format for rejection handling

---

## 10. COMPLIANCE

### 10.1 Artifacts Subject to Discipline

- PAC (Program Artifact Control)
- WRAP (Witness Report for Artifact Protocol)
- Agent status reports
- Execution logs

### 10.2 Exemptions

None. All artifacts MUST comply with orchestrator discipline.

### 10.3 Enforcement

FAIL_CLOSED mode. Any violation blocks processing until resolved.

---

## 11. REVISION HISTORY

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0 | 2025-06-18 | PAC-BENSON-P45 | Initial implementation |

---

**End of Document**
