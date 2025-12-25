# ═══════════════════════════════════════════════════════════════════════════════
# CHAINBRIDGE CANONICAL WRAP SCHEMA v1.1.0
# Authority: PAC-SAM-P31-GOVERNANCE-SECURITY-GATE-HARDENING-AND-WRAP-INGESTION-01
# Mode: FROZEN | Enforcement: HARD_FAIL
# ═══════════════════════════════════════════════════════════════════════════════

## Schema Metadata

```yaml
SCHEMA_METADATA:
  schema_id: "CHAINBRIDGE_CANONICAL_WRAP_SCHEMA"
  version: "1.1.0"
  authority: "PAC-SAM-P31-GOVERNANCE-SECURITY-GATE-HARDENING-AND-WRAP-INGESTION-01"
  previous_version: "1.0.0"
  status: "FROZEN"
  enforcement: "HARD_FAIL"
  mutable: false
  effective_date: "2025-12-24"
  security_hardened: true
```

---

## 1. WRAP vs PAC Separation (Non-Negotiable)

```yaml
ARTIFACT_SEPARATION:
  wrap_is_pac: false
  wrap_type: "REPORT_ONLY"
  pac_type: "CONTROL_PLANE"
  
  WRAP_CHARACTERISTICS:
    - Documents completed work
    - Reports on PAC execution
    - Contains training signals for BENSON
    - No persona activation required
    - No execution authority
    
  PAC_CHARACTERISTICS:
    - Authorizes work
    - Contains execution constraints
    - Requires persona activation (PAG-01)
    - Has execution authority
    - Requires review gates
```

---

## 2. WRAP Ingestion Preamble (Mandatory First Block)

All WRAPs must begin with the `WRAP_INGESTION_PREAMBLE` block:

```yaml
WRAP_INGESTION_PREAMBLE:
  artifact_type: "WRAP"
  schema: "CHAINBRIDGE_CANONICAL_WRAP_SCHEMA"
  schema_version: "1.0.0"
  pac_gates_disabled: true
  pag01_required: false
  review_gate_required: false
  bsrg_required: false
  mode: "REPORT_ONLY"
```

---

## 3. Blocks FORBIDDEN in WRAPs

The following PAC control-plane blocks must NOT appear in WRAPs:

```yaml
FORBIDDEN_WRAP_BLOCKS:
  - "BENSON_SELF_REVIEW_GATE"
  - "REVIEW_GATE"
  - "PAG01_ACTIVATION"
  - "EXECUTION_LANE"  # as control-plane block
  - "PACK_IMMUTABILITY"
  - "GOVERNANCE_MODE"
```

---

## 4. Required WRAP Blocks

```yaml
REQUIRED_WRAP_BLOCKS:
  mandatory:
    - "WRAP_INGESTION_PREAMBLE"  # Must be FIRST
    - "WRAP_HEADER"              # Identification
    - "PAC_REFERENCE"            # Links to authorizing PAC
    - "EXECUTION_SUMMARY"        # What was done
    - "BENSON_TRAINING_SIGNAL"   # Learning for BENSON
    - "FINAL_STATE"              # Terminal state
    
  optional:
    - "RUNTIME_ACTIVATION_ACK"   # For context only, not enforcement
    - "AGENT_ACTIVATION_ACK"     # For context only, not enforcement
    - "DELIVERABLES"             # Files created/modified
    - "ACCEPTANCE_CRITERIA"      # What was met
    - "ATTESTATION"              # Agent attestation
```

---

## 5. BENSON Training Signal (Mandatory)

All WRAPs must include a `BENSON_TRAINING_SIGNAL` block:

```yaml
BENSON_TRAINING_SIGNAL:
  signal_type: "[POSITIVE_REINFORCEMENT | NEGATIVE_CONSTRAINT_REINFORCEMENT | SYSTEMIC_CORRECTION]"
  pattern: "[Pattern name]"
  lesson:
    - "[Lesson 1]"
    - "[Lesson 2]"
  scope: "BENSON_INTERNAL"
  persist: true
  mandatory: true
```

---

## 6. Block Ordering

```yaml
WRAP_BLOCK_ORDER:
  position_1: "WRAP_INGESTION_PREAMBLE"  # MUST be first
  position_2: "WRAP_HEADER"
  position_3: "PAC_REFERENCE"
  position_4: "RUNTIME_ACTIVATION_ACK"   # Optional, for context
  position_5: "AGENT_ACTIVATION_ACK"     # Optional, for context
  position_N_minus_2: "BENSON_TRAINING_SIGNAL"
  position_N_minus_1: "FINAL_STATE"
  position_N: "GOLD_STANDARD_WRAP_CHECKLIST"  # MUST be terminal
```

---

## 7. WRAP Validation Rules

```yaml
WRAP_VALIDATION_RULES:
  # These rules apply ONLY to WRAPs
  
  WRAP_MUST_HAVE:
    - "WRAP_INGESTION_PREAMBLE as first block"
    - "BENSON_TRAINING_SIGNAL block"
    - "FINAL_STATE block"
    - "Reference to authorizing PAC"
    
  WRAP_MUST_NOT_HAVE:
    - "BENSON_SELF_REVIEW_GATE"
    - "REVIEW_GATE with enforcement"
    - "PAG-01 control blocks"
    
  WRAP_DOES_NOT_TRIGGER:
    - "PAC validation gates"
    - "Persona activation validation"
    - "Review gate enforcement"
    - "BSRG validation"
```

---

## 8. Gate Separation Matrix

```yaml
GATE_SEPARATION_MATRIX:
  # Which gates apply to which artifacts
  
  PAC_ARTIFACTS:
    PAG01: ENFORCED
    REVIEW_GATE: ENFORCED
    BSRG: ENFORCED
    GOLD_STANDARD_CHECKLIST: ENFORCED
    
  WRAP_ARTIFACTS:
    PAG01: DISABLED
    REVIEW_GATE: DISABLED
    BSRG: DISABLED
    WRAP_INGESTION_PREAMBLE: REQUIRED
    BENSON_TRAINING_SIGNAL: REQUIRED
    GOLD_STANDARD_WRAP_CHECKLIST: ENFORCED
```

---

## 9. Gold Standard WRAP Checklist

```yaml
GOLD_STANDARD_WRAP_CHECKLIST:
  # This checklist applies to WRAPs only
  
  wrap_ingestion_preamble_present: "[true/false]"
  wrap_ingestion_preamble_first: "[true/false]"
  wrap_header_present: "[true/false]"
  pac_reference_present: "[true/false]"
  benson_training_signal_present: "[true/false]"
  final_state_present: "[true/false]"
  no_forbidden_pac_blocks: "[true/false]"
  checklist_terminal: "[true/false]"
```

---

## 10. Schema Immutability

```yaml
SCHEMA_IMMUTABILITY:
  schema_frozen: true
  version_locked: "1.1.0"
  modifications_allowed: false
  supersession_requires: "PAC from BENSON (GID-00) with explicit authority"
```

---

## 11. Security Hardening (v1.1.0)

```yaml
SECURITY_HARDENING:
  authority: "PAC-SAM-P31-GOVERNANCE-SECURITY-GATE-HARDENING-AND-WRAP-INGESTION-01"
  effective_date: "2025-12-24"
  
  THREAT_MODEL:
    authority_spoofing:
      description: "WRAP attempts to assert authorization authority"
      mitigation: "Forbidden block detection with HARD_FAIL"
      error_code: "WRP_004"
      
    gate_confusion:
      description: "WRAP triggers PAC validation gates incorrectly"
      mitigation: "Explicit WRAP_INGESTION_PREAMBLE as first block"
      error_code: "WRP_001"
      
    schema_poisoning:
      description: "Malformed WRAP corrupts schema validation"
      mitigation: "Strict schema version validation"
      error_code: "WRP_007"
      
    prompt_injection_via_replay:
      description: "WRAP content replayed to inject commands"
      mitigation: "Training signal content validation and isolation"
      error_code: "WRP_009"
      
    identity_escalation:
      description: "WRAP claims higher authority than source PAC"
      mitigation: "PAC_REFERENCE validation against ledger"
      error_code: "WRP_010"
      
  ENFORCEMENT_RULES:
    - "WRAP_INGESTION_PREAMBLE must be first block (HARD_FAIL)"
    - "No PAC control blocks allowed in WRAP (HARD_FAIL)"
    - "No mixed artifact semantics (HARD_FAIL)"
    - "No legacy exceptions for security enforcement"
    - "Fail-closed on ambiguity"
    
  NEW_ERROR_CODES:
    WRP_008: "WRAP artifact_type mismatch or mixed semantics"
    WRP_009: "WRAP training signal contains forbidden patterns"
    WRP_010: "WRAP PAC_REFERENCE validation failed"
    WRP_011: "WRAP preamble fields incomplete or invalid"
```

---

# ═══════════════════════════════════════════════════════════════════════════════
# END CHAINBRIDGE_CANONICAL_WRAP_SCHEMA v1.1.0
# STATUS: FROZEN | SECURITY_HARDENED
# ENFORCEMENT: HARD_FAIL
# ═══════════════════════════════════════════════════════════════════════════════
