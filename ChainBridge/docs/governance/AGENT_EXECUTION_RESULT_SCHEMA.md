# ═══════════════════════════════════════════════════════════════════════════════
# CHAINBRIDGE CANONICAL AGENT EXECUTION RESULT SCHEMA v1.0.0
# ═══════════════════════════════════════════════════════════════════════════════

> **Authority:** BENSON (GID-00)  
> **PAC Reference:** PAC-DAN-P50-GOVERNANCE-EXECUTION-HANDOFF-AND-AGENT-RESULT-CONTRACT-01  
> **Status:** FROZEN  
> **Enforcement:** HARD_FAIL  
> **Version:** 1.0.0

---

## 1. Purpose

This schema defines the **canonical contract** between executing agents and the Benson Execution Runtime. All agent execution must produce an `AgentExecutionResult` artifact that conforms to this schema before Benson can validate, judge, and generate a WRAP.

**Key Invariant:**
> Agents produce EXECUTION_RESULT artifacts. Benson validates, judges, and closes.

---

## 2. Schema Definition (YAML)

```yaml
AGENT_EXECUTION_RESULT_SCHEMA:
  schema_id: "CHAINBRIDGE_CANONICAL_EXECUTION_RESULT_SCHEMA"
  version: "1.0.0"
  enforcement: "HARD_FAIL"
  authority: "BENSON (GID-00)"
  
  required_fields:
    - pac_id              # PAC being executed
    - agent_gid           # Executing agent GID (e.g., GID-07)
    - agent_name          # Executing agent name (e.g., Dan)
    - execution_timestamp # ISO 8601 UTC timestamp
    - tasks_completed     # List of completed task IDs
    - tasks_total         # Total tasks in PAC
    - files_modified      # List of modified file paths
    - quality_score       # Float 0.0-1.0
    - scope_compliance    # Boolean
    - execution_time_ms   # Integer milliseconds
    
  optional_fields:
    - files_created       # List of created file paths
    - notes               # Execution notes
    - artifacts           # Additional artifact metadata
    - warnings            # Non-blocking warnings
    - test_results        # Test execution results
    
  computed_fields:
    - result_hash         # SHA256 of result content (computed by Benson)
    - pac_hash            # SHA256 of bound PAC (computed by Benson)
    
  forbidden_fields:
    - wrap_id             # Agents cannot self-assign WRAP IDs
    - wrap_status         # Agents cannot declare WRAP status
    - positive_closure    # Agents cannot self-close
    - wrap_authority      # Agents cannot claim WRAP authority
```

---

## 3. Schema Definition (JSON)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://chainbridge.io/schemas/agent-execution-result/v1.0.0",
  "title": "AgentExecutionResult",
  "description": "Canonical schema for agent execution results handed to Benson Execution Runtime",
  "type": "object",
  "required": [
    "pac_id",
    "agent_gid",
    "agent_name",
    "execution_timestamp",
    "tasks_completed",
    "tasks_total",
    "files_modified",
    "quality_score",
    "scope_compliance",
    "execution_time_ms"
  ],
  "properties": {
    "pac_id": {
      "type": "string",
      "pattern": "^PAC-[A-Z]+-[A-Z0-9]+-.*-[0-9]+$",
      "description": "PAC ID being executed"
    },
    "agent_gid": {
      "type": "string",
      "pattern": "^GID-[0-9]{2}$",
      "description": "Executing agent GID"
    },
    "agent_name": {
      "type": "string",
      "minLength": 1,
      "description": "Executing agent name"
    },
    "execution_timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 UTC timestamp of execution completion"
    },
    "tasks_completed": {
      "type": "array",
      "items": { "type": "string" },
      "description": "List of completed task identifiers"
    },
    "tasks_total": {
      "type": "integer",
      "minimum": 0,
      "description": "Total number of tasks in the PAC"
    },
    "files_modified": {
      "type": "array",
      "items": { "type": "string" },
      "description": "List of modified file paths"
    },
    "files_created": {
      "type": "array",
      "items": { "type": "string" },
      "description": "List of created file paths"
    },
    "quality_score": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Quality score (0.0-1.0)"
    },
    "scope_compliance": {
      "type": "boolean",
      "description": "Whether execution stayed within PAC scope"
    },
    "execution_time_ms": {
      "type": "integer",
      "minimum": 0,
      "description": "Execution time in milliseconds"
    },
    "notes": {
      "type": "string",
      "description": "Optional execution notes"
    },
    "artifacts": {
      "type": "object",
      "description": "Additional artifact metadata"
    },
    "warnings": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Non-blocking warnings"
    },
    "test_results": {
      "type": "object",
      "properties": {
        "passed": { "type": "integer" },
        "failed": { "type": "integer" },
        "skipped": { "type": "integer" }
      },
      "description": "Test execution summary"
    }
  },
  "additionalProperties": false
}
```

---

## 4. Validation Rules

### 4.1 Required Field Validation

| Field | Type | Validation Rule |
|-------|------|-----------------|
| `pac_id` | string | Must match PAC ID pattern, must exist in ledger |
| `agent_gid` | string | Must match `GID-XX` pattern, must exist in registry |
| `agent_name` | string | Non-empty, must match registry binding for GID |
| `execution_timestamp` | string | Valid ISO 8601 UTC timestamp |
| `tasks_completed` | array | Non-empty list of task IDs |
| `tasks_total` | integer | >= count of `tasks_completed` |
| `files_modified` | array | List of valid file paths |
| `quality_score` | float | 0.0 <= score <= 1.0 |
| `scope_compliance` | boolean | Must be explicitly true/false |
| `execution_time_ms` | integer | >= 0 |

### 4.2 Forbidden Field Enforcement

The following fields are **strictly forbidden** in AgentExecutionResult:

```yaml
FORBIDDEN_FIELDS:
  - wrap_id            # GS_130: Agents cannot self-assign WRAP IDs
  - wrap_status        # GS_131: Agents cannot declare WRAP status
  - positive_closure   # GS_132: Agents cannot self-close
  - wrap_authority     # GS_133: Agents cannot claim WRAP authority
  - closure_authority  # GS_132: Agents cannot self-close
  - wrap_accepted      # GS_131: Agents cannot declare WRAP acceptance
```

**Enforcement:** Any presence of forbidden fields triggers HARD_FAIL with corresponding error code.

---

## 5. Error Codes

| Code | Name | Description |
|------|------|-------------|
| `GS_130` | `EXECUTION_RESULT_SCHEMA_VIOLATION` | AgentExecutionResult missing required field or invalid format |
| `GS_131` | `EXECUTION_RESULT_WRAP_FIELD_FORBIDDEN` | AgentExecutionResult contains forbidden WRAP field |
| `GS_132` | `EXECUTION_RESULT_SELF_CLOSURE_BLOCKED` | Agent attempted self-closure via execution result |
| `GS_133` | `EXECUTION_RESULT_AUTHORITY_VIOLATION` | Agent claimed authority reserved for Benson |

---

## 6. Example: Valid AgentExecutionResult

```yaml
AgentExecutionResult:
  pac_id: "PAC-DAN-P50-GOVERNANCE-EXECUTION-HANDOFF-AND-AGENT-RESULT-CONTRACT-01"
  agent_gid: "GID-07"
  agent_name: "Dan"
  execution_timestamp: "2025-12-26T00:00:00Z"
  tasks_completed:
    - "T1"
    - "T2"
    - "T3"
    - "T4"
    - "T5"
  tasks_total: 5
  files_modified:
    - "tools/governance/benson_execution.py"
    - "tools/governance/gate_pack.py"
  files_created:
    - "docs/governance/AGENT_EXECUTION_RESULT_SCHEMA.md"
    - "docs/governance/GOVERNANCE_EXECUTION_HANDOFF.md"
    - "tests/governance/test_execution_result_contract.py"
  quality_score: 1.0
  scope_compliance: true
  execution_time_ms: 12000
  test_results:
    passed: 8
    failed: 0
    skipped: 0
```

---

## 7. Example: Invalid AgentExecutionResult (BLOCKED)

```yaml
# ❌ INVALID — Contains forbidden fields
AgentExecutionResult:
  pac_id: "PAC-DAN-P50-EXAMPLE-01"
  agent_gid: "GID-07"
  agent_name: "Dan"
  execution_timestamp: "2025-12-26T00:00:00Z"
  tasks_completed: ["T1"]
  tasks_total: 1
  files_modified: []
  quality_score: 1.0
  scope_compliance: true
  execution_time_ms: 1000
  # ❌ FORBIDDEN — triggers GS_131
  wrap_status: "WRAP_ACCEPTED"
  # ❌ FORBIDDEN — triggers GS_132
  positive_closure: true
```

**Result:** `HARD_FAIL` with error codes `GS_131`, `GS_132`

---

## 8. Handoff Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      AGENT EXECUTION HANDOFF FLOW                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────────────┐    ┌────────────────────┐    │
│  │    AGENT     │───▶│  AgentExecutionResult │───▶│  BENSON EXECUTION  │    │
│  │  (Executor)  │    │    (Schema v1.0.0)    │    │     RUNTIME        │    │
│  └──────────────┘    └──────────────────────┘    └────────────────────┘    │
│                                                           │                 │
│                                                           ▼                 │
│                                                  ┌────────────────────┐    │
│                                                  │ SCHEMA VALIDATION  │    │
│                                                  │   GS_130-GS_133    │    │
│                                                  └────────────────────┘    │
│                                                           │                 │
│                                        ┌──────────────────┴─────────────┐  │
│                                        ▼                                ▼  │
│                               ┌────────────────┐              ┌──────────┐│
│                               │ VALIDATION PASS │              │   FAIL   ││
│                               └────────────────┘              │  BLOCKED ││
│                                        │                      └──────────┘│
│                                        ▼                                   │
│                               ┌────────────────────┐                       │
│                               │  BENSON JUDGMENT   │                       │
│                               │  (Quality, Scope)  │                       │
│                               └────────────────────┘                       │
│                                        │                                   │
│                                        ▼                                   │
│                               ┌────────────────────┐                       │
│                               │  WRAP GENERATION   │                       │
│                               │  (BENSON GID-00)   │                       │
│                               └────────────────────┘                       │
│                                        │                                   │
│                                        ▼                                   │
│                               ┌────────────────────┐                       │
│                               │   WRAP_ACCEPTED    │                       │
│                               │  POSITIVE_CLOSURE  │                       │
│                               └────────────────────┘                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Training Signal

```yaml
TRAINING_SIGNAL:
  pattern: "EXECUTION_RESULT_PRECEDES_JUDGMENT"
  lesson:
    - "Agents report results via AgentExecutionResult schema"
    - "Benson validates schema compliance before processing"
    - "Forbidden fields trigger immediate HARD_FAIL"
    - "Only Benson (GID-00) may generate WRAPs and declare closure"
    - "Schema violation = execution blocked, no WRAP generated"
  propagate: true
  mandatory: true
```

---

## 10. Schema Immutability

```yaml
SCHEMA_IMMUTABILITY:
  schema_id: "CHAINBRIDGE_CANONICAL_EXECUTION_RESULT_SCHEMA"
  version: "1.0.0"
  status: "FROZEN"
  mutation_policy: "NO_DRIFT"
  authority: "BENSON (GID-00)"
  supersedes_allowed: false
```

---

**END — CHAINBRIDGE_CANONICAL_EXECUTION_RESULT_SCHEMA v1.0.0**
