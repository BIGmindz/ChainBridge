# PDO SPINE ORCHESTRATION — v1.0.0

> **Governance Document** — PAC-JEFFREY-GOV-PDO-SPINE-ORCHESTRATION-001
> **Version:** 1.0.0
> **Effective Date:** 2025-12-30
> **Authority:** Jeffrey (CTO) / Benson (GID-00)
> **Status:** LOCKED / CANONICAL / MACHINE-ENFORCED
> **Schema Reference:** CHAINBRIDGE_CANONICAL_PDO_SCHEMA v1.0.0

---

## Purpose

This document establishes **PDO as the PRIMARY SPINE OBJECT** for all ChainBridge orchestration, execution, and review flows.

- PDO is the root object for all orchestration
- All dispatch operations require PDO_ID
- All WRAPs reference PDO_ID
- All BERs bind to PDO_ID
- No execution path exists without PDO

```
Task-centric orchestration is deprecated.
PDO-centric orchestration is law.
The PDO spine is the single source of truth.
```

---

## Orchestration Model Transformation

```yaml
ORCHESTRATION_TRANSFORMATION:
  version: "1.0.0"
  authority: "PAC-JEFFREY-GOV-PDO-SPINE-ORCHESTRATION-001"
  
  DEPRECATED_MODEL:
    name: "TASK_CENTRIC_ORCHESTRATION"
    status: "FORBIDDEN"
    root_object: "Task/PAC"
    dispatch_key: "task_id"
    evidence_binding: "OPTIONAL"
    replay_support: "PARTIAL"
    
  CANONICAL_MODEL:
    name: "PDO_SPINE_ORCHESTRATION"
    status: "MANDATORY"
    root_object: "PDO"
    dispatch_key: "pdo_id"
    evidence_binding: "REQUIRED"
    replay_support: "DETERMINISTIC"
    
  MIGRATION_RULE: |
    All orchestration operations MUST:
    1. Create or reference PDO before dispatch
    2. Thread PDO_ID through all operations
    3. Bind all artifacts to PDO_ID
    4. Ensure deterministic replay via PDO
```

---

## PDO Spine Architecture

```yaml
PDO_SPINE_ARCHITECTURE:
  description: "PDO as the central orchestration object"
  
  SPINE_DEFINITION:
    primary_key: "pdo_id"
    pattern: "PDO-[DOMAIN]-[TIMESTAMP]-[SEQUENCE]"
    immutable: true
    
  SPINE_COMPONENTS:
    root:
      object: "PDO"
      fields:
        - pdo_id
        - pdo_type
        - pdo_state
        - created_at
        - sealed_at
        
    branches:
      proof:
        parent: "pdo_id"
        fields:
          - proof_id
          - proof_type
          - proof_hash
          - proof_content
          
      decision:
        parent: "pdo_id"
        fields:
          - decision_id
          - decision_type
          - decision_value
          - decision_authority
          
      outcome:
        parent: "pdo_id"
        fields:
          - outcome_id
          - outcome_state
          - outcome_hash
          
  SPINE_INVARIANTS:
    INV-SPINE-001: "All operations must reference a valid PDO_ID"
    INV-SPINE-002: "No orphan operations (operations without PDO)"
    INV-SPINE-003: "Spine is append-only, never mutated"
    INV-SPINE-004: "All branches derive from spine root"
```

---

## Dispatch Model

```yaml
DISPATCH_MODEL:
  version: "1.0.0"
  
  PDO_DISPATCH:
    description: "All dispatch operations require PDO context"
    
    DISPATCH_STRUCTURE:
      # Every dispatch includes:
      dispatch_id:
        type: "string"
        pattern: "DSP-[TIMESTAMP]-[SEQUENCE]"
        
      pdo_id:
        type: "string"
        pattern: "PDO-[DOMAIN]-[TIMESTAMP]-[SEQUENCE]"
        required: true
        enforcement: "HARD_FAIL"
        
      pac_reference:
        type: "string"
        description: "Source PAC ID"
        required: true
        
      target_agent:
        type: "string"
        description: "GID of assigned agent"
        required: true
        
      task_envelope:
        type: "object"
        description: "Task specification"
        required: true
        
  DISPATCH_REJECTION:
    condition: "pdo_id IS NULL OR pdo_id_valid = FALSE"
    action: "REJECT_DISPATCH"
    error_code: "DSP_PDO_001"
    message: "Dispatch rejected: Valid PDO_ID required"
```

---

## WRAP PDO Binding

```yaml
WRAP_PDO_BINDING:
  version: "1.0.0"
  authority: "PAC-JEFFREY-GOV-PDO-SPINE-ORCHESTRATION-001"
  
  BINDING_REQUIREMENT:
    enforcement: "MANDATORY"
    scope: "ALL_EXECUTION_WRAPS"
    
  WRAP_STRUCTURE_UPDATE:
    # Every WRAP must include:
    pdo_reference:
      field: "pdo_id"
      location: "WRAP_HEADER"
      required: true
      validation: "MUST_EXIST_IN_SPINE"
      
    pdo_state_at_wrap:
      field: "pdo_state"
      location: "WRAP_CONTEXT"
      required: true
      
  WRAP_REJECTION:
    condition: |
      IF wrap_type = EXECUTION
      AND pdo_reference IS NULL
      THEN REJECT
    error_code: "WRP_PDO_001"
    message: "WRAP rejected: PDO reference required"
    
  WRAP_HEADER_TEMPLATE:
    required_fields:
      - wrap_id
      - wrap_type
      - pdo_id           # NEW: Mandatory PDO reference
      - pac_reference
      - execution_agent
      - timestamp
```

---

## BER PDO Binding

```yaml
BER_PDO_BINDING:
  version: "1.0.0"
  authority: "PAC-JEFFREY-GOV-PDO-SPINE-ORCHESTRATION-001"
  
  BINDING_REQUIREMENT:
    enforcement: "MANDATORY"
    scope: "ALL_GOVERNANCE_BERS"
    
  BER_STRUCTURE_UPDATE:
    # Every BER must include:
    pdo_reference:
      field: "pdo_id"
      location: "BER_HEADER"
      required: true
      validation: "MUST_EXIST_IN_SPINE"
      
    pdo_decision_binding:
      description: "BER decision becomes PDO decision component"
      bidirectional: true
      
  BER_PDO_SYNCHRONIZATION:
    on_ber_issuance:
      - Update PDO.decision_component with BER decision
      - Update PDO.state to DECISION_MADE
      - Record BER_ID in PDO.decision_reference
      
  BER_REJECTION:
    condition: |
      IF ber_type = GOVERNANCE
      AND pdo_decision_binding IS NULL
      THEN REJECT
    error_code: "BER_PDO_001"
    message: "BER rejected: PDO decision binding required"
    
  BER_HEADER_TEMPLATE:
    required_fields:
      - ber_id
      - ber_type
      - pdo_id           # NEW: Mandatory PDO reference
      - wrap_reference
      - decision_authority
      - timestamp
```

---

## Orchestration Entry Points

```yaml
ORCHESTRATION_ENTRY_POINTS:
  version: "1.0.0"
  
  BENSON_INGRESS:
    description: "All requests enter through Benson with PDO context"
    
    PAC_INGRESS:
      trigger: "PAC received"
      action: "Create or resolve PDO"
      pdo_creation_rule: |
        IF pac_class IN [GOVERNANCE, EXECUTION, SETTLEMENT]
        THEN CREATE_PDO with:
          - pdo_type = pac_class
          - pdo_state = INITIALIZED
          - proof.source = PAC
          
    REQUEST_INGRESS:
      trigger: "Direct request"
      action: "Require existing PDO"
      rejection_rule: |
        IF pdo_id IS NULL
        THEN REJECT with error INGRESS_PDO_001
        
  REJECTION_PROTOCOL:
    on_missing_pdo:
      error_code: "INGRESS_PDO_001"
      message: "Request rejected: PDO_ID required at ingress"
      action: "HARD_FAIL"
      retry_allowed: false
```

---

## Execution Context Model

```yaml
EXECUTION_CONTEXT_MODEL:
  version: "1.0.0"
  description: "PDO-rooted execution context for all operations"
  
  CONTEXT_STRUCTURE:
    root:
      pdo_id:
        type: "string"
        required: true
        description: "Root PDO for this execution context"
        
      pac_reference:
        type: "string"
        required: true
        description: "Originating PAC"
        
    execution_state:
      agents_dispatched:
        type: "array"
        items: "GID string"
        description: "Agents with active tasks"
        
      tasks_in_flight:
        type: "array"
        items: "TaskEnvelope"
        description: "Active task envelopes"
        
      wraps_collected:
        type: "array"
        items: "WRAP_ID"
        description: "WRAPs generated in this context"
        
    pdo_state:
      current_state:
        type: "string"
        enum:
          - "INITIALIZED"
          - "PROOF_COLLECTING"
          - "PROOF_COLLECTED"
          - "DECISION_PENDING"
          - "DECISION_MADE"
          - "OUTCOME_RECORDING"
          - "OUTCOME_RECORDED"
          - "SEALED"
          
  CONTEXT_PROPAGATION:
    rule: "PDO_ID must propagate through all execution paths"
    enforcement: "AUTOMATIC"
    failure_mode: "HARD_FAIL"
```

---

## Deterministic Replay

```yaml
DETERMINISTIC_REPLAY:
  version: "1.0.0"
  description: "PDO enables full execution replay"
  
  REPLAY_CAPABILITY:
    enabled: true
    scope: "ALL_PDO_BOUND_OPERATIONS"
    
  REPLAY_INPUTS:
    from_pdo:
      - pdo_id
      - proof_component (all evidence)
      - decision_component (all decisions)
      - outcome_component (all results)
      
    from_spine:
      - dispatch_records
      - wrap_references
      - ber_references
      
  REPLAY_GUARANTEES:
    deterministic: true
    idempotent: true
    auditable: true
    
  REPLAY_ASSERTION: |
    Given a PDO_ID, the entire execution history can be replayed
    deterministically with identical outputs.
    
    This is impossible in task-centric orchestration.
    This is guaranteed in PDO-spine orchestration.
```

---

## Security Attestation Requirements

```yaml
SECURITY_ATTESTATION:
  version: "1.0.0"
  authority: "Sam (GID-06)"
  
  BYPASS_PREVENTION:
    INV-SEC-001: "No implicit PDO creation permitted"
    INV-SEC-002: "No synthetic PDO injection permitted"
    INV-SEC-003: "No PDO_ID forgery permitted"
    INV-SEC-004: "PDO_ID validation at every boundary"
    
  INJECTION_PREVENTION:
    rule: "All PDO_IDs must originate from canonical spine"
    validation: "Hash-chain verification required"
    
  IMPLICIT_CHANNEL_PREVENTION:
    rule: "No decision channel outside PDO"
    enforcement: "All decisions flow through PDO.decision_component"
    
  ATTESTATION_REQUIREMENT:
    on_deployment:
      - Security review of PDO spine implementation
      - Bypass test suite execution
      - Injection test suite execution
      - Sam attestation in WRAP
```

---

## Canon Verification Requirements

```yaml
CANON_VERIFICATION:
  version: "1.0.0"
  authority: "Atlas (GID-11)"
  
  VERIFICATION_SCOPE:
    all_execution_paths:
      - PAC ingress → PDO creation
      - Dispatch → PDO threading
      - WRAP emission → PDO binding
      - BER issuance → PDO binding
      - Settlement → PDO outcome
      
  DETERMINISM_VERIFICATION:
    requirement: "Full replay from any PDO"
    test_cases:
      - Replay governance PAC execution
      - Replay settlement operation
      - Replay multi-agent execution
      
  ATTESTATION_REQUIREMENT:
    on_implementation:
      - Canon compliance verification
      - Deterministic replay verification
      - Atlas attestation in WRAP
```

---

## Benson Rejection Configuration

```yaml
BENSON_REJECTION_CONFIG:
  version: "1.0.0"
  authority: "PAC-JEFFREY-GOV-PDO-SPINE-ORCHESTRATION-001"
  
  NON_PDO_REJECTION:
    enabled: true
    enforcement: "HARD_FAIL"
    
    REJECTION_TRIGGERS:
      pac_without_pdo:
        condition: "PAC received without pdo_reference"
        action: "REJECT_AT_INGRESS"
        error_code: "INGRESS_PDO_001"
        message: "PAC rejected: PDO reference required"
        
      dispatch_without_pdo:
        condition: "Dispatch requested without pdo_id"
        action: "BLOCK_DISPATCH"
        error_code: "DSP_PDO_001"
        message: "Dispatch rejected: Valid PDO_ID required"
        
      wrap_without_pdo:
        condition: "WRAP emitted without pdo_reference"
        action: "REJECT_WRAP"
        error_code: "WRP_PDO_001"
        message: "WRAP rejected: PDO reference required"
        
      ber_without_pdo:
        condition: "BER issued without pdo_binding"
        action: "REJECT_BER"
        error_code: "BER_PDO_001"
        message: "BER rejected: PDO decision binding required"
        
    REJECTION_RESPONSE:
      format: "STRUCTURED_ERROR"
      includes:
        - error_code
        - error_message
        - failed_checkpoint
        - pdo_state_expected
        - remediation_hint
        
  ORCHESTRATION_WRAP_CONFIG:
    enabled: true
    keyed_by: "pdo_id"
    
    WRAP_EMISSION:
      trigger: "On orchestration completion"
      required_fields:
        - pdo_id
        - pac_reference
        - tasks_executed
        - agents_dispatched
        - evidence_collected
      pdo_state_update: "PROOF_COLLECTED"
```

---

## Error Codes

| Error Code | Context | Message | Severity |
|------------|---------|---------|----------|
| `DSP_PDO_001` | Dispatch | "Dispatch rejected: Valid PDO_ID required" | HARD_FAIL |
| `WRP_PDO_001` | WRAP | "WRAP rejected: PDO reference required" | HARD_FAIL |
| `BER_PDO_001` | BER | "BER rejected: PDO decision binding required" | HARD_FAIL |
| `INGRESS_PDO_001` | Ingress | "Request rejected: PDO_ID required at ingress" | HARD_FAIL |
| `CTX_PDO_001` | Context | "Context invalid: PDO_ID not found in spine" | HARD_FAIL |
| `REPLAY_PDO_001` | Replay | "Replay failed: PDO spine corrupted" | HARD_FAIL |

---

## Enforcement Chain

```yaml
ENFORCEMENT_CHAIN:
  level_1: "Ingress Gate — PDO required at entry"
  level_2: "Dispatch Gate — PDO threading required"
  level_3: "WRAP Gate — PDO binding required"
  level_4: "BER Gate — PDO decision binding required"
  level_5: "Settlement Gate — PDO outcome required"
  
  GATE_SEQUENCE: |
    INGRESS → DISPATCH → WRAP → BER → SETTLEMENT
    PDO_ID must propagate through ALL gates.
    Any gate without PDO_ID = HARD_FAIL.
```

---

## Implementation Checklist

```yaml
IMPLEMENTATION_CHECKLIST:
  T1_Orchestration_Update:
    - [ ] Root execution context = PDO
    - [ ] Dispatch requires PDO_ID
    - [ ] PDO creation on PAC ingress
    - [ ] PDO resolution on request ingress
    
  T2_WRAP_Enforcement:
    - [ ] PDO_ID field in WRAP header
    - [ ] PDO state at WRAP time
    - [ ] Rejection without PDO reference
    
  T3_BER_Enforcement:
    - [ ] PDO_ID field in BER header
    - [ ] PDO decision binding
    - [ ] Bidirectional synchronization
    
  T4_Security_Attestation:
    - [ ] Bypass prevention verified
    - [ ] Injection prevention verified
    - [ ] Sam attestation collected
    
  T5_Canon_Verification:
    - [ ] All paths verified
    - [ ] Deterministic replay verified
    - [ ] Atlas attestation collected
```

---

## Training Signal

```yaml
TRAINING_SIGNAL:
  ts_id: "TS-20"
  signal: |
    PDO is the primary spine object for all orchestration, execution, and review.
    Task-centric orchestration is deprecated. PDO-centric orchestration is law.
    
  learned_behavior:
    - PDO_ID required at ingress
    - PDO_ID threaded through dispatch
    - PDO_ID bound in all WRAPs
    - PDO_ID bound in all BERs
    - Deterministic replay via PDO
```

---

## Document Status

| Attribute | Value |
|-----------|-------|
| Status | LOCKED |
| Enforcement | MACHINE-ENFORCED |
| Override | FORBIDDEN |
| Effective | 2025-12-30 |

---

**END PDO_SPINE_ORCHESTRATION v1.0.0**
