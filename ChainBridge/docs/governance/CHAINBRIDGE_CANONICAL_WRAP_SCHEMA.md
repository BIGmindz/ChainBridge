# ═══════════════════════════════════════════════════════════════════════════════
# CHAINBRIDGE CANONICAL WRAP SCHEMA v1.3.0
# Authority: PAC-BENSON-GOV-WRAP-BER-002
# Mode: FROZEN | Enforcement: HARD_FAIL
# ═══════════════════════════════════════════════════════════════════════════════

## Schema Metadata

```yaml
SCHEMA_METADATA:
  schema_id: "CHAINBRIDGE_CANONICAL_WRAP_SCHEMA"
  version: "1.4.0"
  authority: "PAC-JEFFREY-GOV-PDO-SPINE-ORCHESTRATION-001"
  previous_version: "1.3.0"
  status: "FROZEN"
  enforcement: "HARD_FAIL"
  mutable: false
  effective_date: "2025-12-30"
  security_hardened: true
  wrap_ber_separation: "ABSOLUTE"
  evaluative_language: "FORBIDDEN"
  pdo_spine_binding: "MANDATORY"
```

---

## 0.0.1 PDO SPINE BINDING (v1.4.0 — MANDATORY)

```yaml
PDO_SPINE_BINDING:
  authority: "PAC-JEFFREY-GOV-PDO-SPINE-ORCHESTRATION-001"
  enforcement: "HARD_FAIL"
  error_code: "WRP_PDO_001"
  
  BINDING_REQUIREMENT:
    description: "All execution WRAPs MUST reference a valid PDO_ID"
    scope: "ALL_EXECUTION_WRAPS"
    enforcement: "MANDATORY"
    
  WRAP_HEADER_PDO_FIELDS:
    pdo_id:
      required: true
      type: "string"
      pattern: "PDO-[A-Z0-9-]+"
      validation: "MUST_EXIST_IN_SPINE"
      description: "Root PDO for this execution"
      
    pdo_state_at_wrap:
      required: true
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
      description: "PDO state when WRAP was generated"
      
  WRAP_REJECTION:
    condition: |
      IF wrap_type = EXECUTION
      AND pdo_id IS NULL
      THEN REJECT
    error_code: "WRP_PDO_001"
    message: "WRAP rejected: PDO reference required"
    
  WRAP_PREAMBLE_UPDATE:
    # Add to WRAP_INGESTION_PREAMBLE:
    pdo_bound: true
    pdo_validation: "REQUIRED"
```

---

## 0. ABSOLUTE WRAP / BER SEPARATION (NON-NEGOTIABLE)

```yaml
WRAP_BER_SEPARATION:
  enforcement: "ABSOLUTE"
  authority: "PAC-BENSON-GOV-WRAP-BER-001"
  effective_date: "2025-12-30"
  
  WRAP_DEFINITION:
    artifact_class: "EXECUTION_REPORT"
    authority_level: "NONE"
    purpose: "Document completed work factually"
    issuer: "Execution Agent (any GID)"
    decision_authority: "NONE"
    
  BER_DEFINITION:
    artifact_class: "BINDING_DECISION"
    authority_level: "ORCHESTRATION_ENGINE"
    purpose: "Issue binding acceptance/rejection"
    issuer: "Benson (GID-00) ONLY"
    decision_authority: "EXCLUSIVE"
    
  SEPARATION_INVARIANTS:
    INV-WRAP-BER-001: "WRAP may NEVER contain decision language"
    INV-WRAP-BER-002: "Only Benson (GID-00) may issue BER"
    INV-WRAP-BER-003: "Execution agents have ZERO decision authority"
    INV-WRAP-BER-004: "No hybrid WRAP/BER artifacts permitted"
```

---

## 0.1 FORBIDDEN DECISION LANGUAGE IN WRAPs

```yaml
FORBIDDEN_WRAP_LANGUAGE:
  enforcement: "HARD_FAIL"
  error_code: "WRP_012"
  
  # These words/phrases are ABSOLUTELY FORBIDDEN in WRAP artifacts
  # when used in an authoritative/decision context:
  
  FORBIDDEN_TERMS:
    decision_terms:
      - "Decision:"          # As a field label implying authority
      - "decision:"
      - "DECISION:"
      - "BER_DECISION"       # BER-only block
      - "ber_decision"
      
    acceptance_terms:
      - "ACCEPTED"           # As outcome status (BER-only)
      - "Accepted"
      - "accepted"
      - "REJECTED"           # As outcome status (BER-only)
      - "Rejected"
      - "rejected"
      
    issuance_terms:
      - "ISSUED"             # Implies authority
      - "Issued"
      - "issued"
      - "hereby issue"
      - "hereby ISSUE"
      
    approval_terms:
      - "APPROVED"           # Implies authority
      - "Approved"
      - "approved"
      - "hereby approve"
      
    finality_terms:
      - "FINAL"              # As binding state
      - "Final"
      - "final decision"
      - "binding"
      - "BINDING"
      
  PERMITTED_CONTEXTS:
    # These contexts are permitted even with similar words:
    - "task status: completed"      # Task completion, not decision
    - "criteria satisfied"          # Factual observation
    - "verification passed"         # Test result
    - "attestation"                 # Agent observation
    - "handoff to BER"              # Proper sequencing
    - "pending Benson review"       # Proper authority chain
    
  REQUIRED_DISCLAIMERS:
    # Every WRAP must include these in WRAP_HEADER:
    authority_disclaimer: "Authority: EXECUTION ONLY — No decision authority"
    decision_disclaimer: "Decision Authority: NONE — Awaits Benson (GID-00) BER"
```

---

## 0.1.1 FORBIDDEN EVALUATIVE LANGUAGE IN WRAPs (v1.3.0)

```yaml
FORBIDDEN_EVALUATIVE_LANGUAGE:
  authority: "PAC-BENSON-GOV-WRAP-BER-002"
  enforcement: "HARD_FAIL"
  error_code: "WRP_016"
  
  # These words/phrases imply completion, success, or acceptance
  # and are FORBIDDEN in WRAP summaries and status fields:
  
  FORBIDDEN_STATUS_TERMS:
    completion_claims:
      - "EXECUTION_COMPLETE"
      - "Execution Complete"
      - "execution complete"
      - "COMPLETE"
      - "Complete"
      - "COMPLETED"
      - "Completed"
      
    success_claims:
      - "SUCCESS"
      - "Success"
      - "Successful"
      - "SUCCESSFUL"
      - "PASSED"
      - "Passed"
      
    accomplishment_claims:
      - "DONE"
      - "Done"
      - "FINISHED"
      - "Finished"
      - "ACHIEVED"
      - "Achieved"
      
    evaluative_markers:
      - "✓ COMPLETE"
      - "✓ Complete"
      - "✓ DONE"
      - "✓ Done"
      - "✓ SUCCESS"
      - "✓ Successful"
      - "[x]"              # As completion marker in summaries
      
  PERMITTED_NEUTRAL_TERMS:
    # Use these instead:
    status_terms:
      - "TASKS_EXECUTED"
      - "EXECUTION_REPORTED"
      - "AWAITING_REVIEW"
      - "PENDING_BER"
      
    task_terms:
      - "Executed"         # Neutral factual state
      - "Ran"
      - "Performed"
      - "Documented"
      
    marker_terms:
      - "•"                # Bullet, not checkmark
      - "—"                # Dash
      - "T1:"              # Task reference without evaluation
      
  WRAP_TITLE_CONSTRAINTS:
    forbidden_patterns:
      - "Execution Complete"
      - "— Complete"
      - "— Done"
      - "— Success"
    required_pattern: "Factual title without evaluative suffix"
    
  WRAP_SUMMARY_CONSTRAINTS:
    forbidden: "Summary language implying completion, success, or acceptance"
    required: "Neutral, factual execution reporting"
    mandatory_statement: "This WRAP does not express any decision"
```

---

## 0.2 WRAP AUTHORITY DISCLAIMER (MANDATORY)

```yaml
WRAP_AUTHORITY_DISCLAIMER:
  required: true
  enforcement: "HARD_FAIL"
  error_code: "WRP_013"
  
  MANDATORY_HEADER_FIELDS:
    execution_authority: "EXECUTION ONLY"
    decision_authority: "NONE"
    ber_issuance_authority: "NONE — Reserved for Benson (GID-00)"
    
  MANDATORY_FINAL_STATE_FIELDS:
    awaits_ber: true  # or false if BER not required
    decision_pending: true  # until BER issued
    execution_only_attestation: |
      This WRAP documents execution only. 
      No decision authority is claimed or implied.
      Binding decisions require BER from Benson (GID-00).
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
  schema_version: "1.2.0"
  pac_gates_disabled: true
  pag01_required: false
  review_gate_required: false
  bsrg_required: false
  mode: "REPORT_ONLY"
  
  # MANDATORY AUTHORITY DISCLAIMERS (v1.2.0)
  execution_authority: "EXECUTION ONLY"
  decision_authority: "NONE"
  ber_issuance_authority: "NONE — Reserved for Benson (GID-00)"
  
  authority_attestation: |
    This WRAP is an execution report only.
    No decision authority is claimed or implied.
    Binding decisions require BER issuance by Benson (GID-00).
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
    WRP_012: "WRAP contains forbidden decision language"
    WRP_013: "WRAP missing mandatory authority disclaimers"
    WRP_014: "WRAP claims decision/issuance authority"
    WRP_015: "WRAP/BER hybrid artifact detected"
    WRP_016: "WRAP contains evaluative summary/status language"
    WRP_017: "WRAP missing mandatory neutrality statement"
```

---

## 12. Atlas Rejection Rules (v1.3.0)

```yaml
ATLAS_REJECTION_RULES:
  authority: "PAC-BENSON-GOV-WRAP-BER-002"
  agent: "Atlas (GID-11)"
  enforcement: "HARD_REJECT"
  
  REJECTION_TRIGGERS:
    # Atlas SHALL reject any WRAP containing:
    
    decision_language:
      trigger: "WRAP contains 'Decision:', 'ACCEPTED', 'REJECTED' as outcomes"
      action: "HARD_REJECT"
      error_code: "WRP_012"
      
    issuance_claims:
      trigger: "WRAP contains 'ISSUED', 'hereby issue', issuance language"
      action: "HARD_REJECT"
      error_code: "WRP_014"
      
    approval_claims:
      trigger: "WRAP contains 'APPROVED', 'hereby approve', approval language"
      action: "HARD_REJECT"
      error_code: "WRP_014"
      
    missing_disclaimers:
      trigger: "WRAP_INGESTION_PREAMBLE lacks authority disclaimers"
      action: "HARD_REJECT"
      error_code: "WRP_013"
      
    hybrid_artifact:
      trigger: "Artifact contains both WRAP and BER blocks"
      action: "HARD_REJECT"
      error_code: "WRP_015"
      
    # NEW in v1.3.0: Evaluative language rejection
    evaluative_status:
      trigger: "WRAP status contains 'EXECUTION_COMPLETE', 'COMPLETE', 'SUCCESS'"
      action: "HARD_REJECT"
      error_code: "WRP_016"
      
    evaluative_summary:
      trigger: "WRAP summary uses '✓ COMPLETE', 'Done', 'Finished', 'Success'"
      action: "HARD_REJECT"
      error_code: "WRP_016"
      
    evaluative_title:
      trigger: "WRAP section titles contain '— Complete', '— Done', '— Success'"
      action: "HARD_REJECT"
      error_code: "WRP_016"
      
    missing_neutrality_statement:
      trigger: "WRAP lacks mandatory statement: 'This WRAP does not express any decision'"
      action: "HARD_REJECT"
      error_code: "WRP_017"
      
  ATLAS_ATTESTATION_TEMPLATE: |
    I, Atlas (GID-11), attest that this WRAP:
    [ ] Contains no forbidden decision language
    [ ] Contains no evaluative summary language (v1.3.0)
    [ ] Includes mandatory authority disclaimers
    [ ] Includes mandatory neutrality statement (v1.3.0)
    [ ] Does not claim decision/issuance authority
    [ ] Is properly separated from BER concerns
    [ ] Complies with CHAINBRIDGE_CANONICAL_WRAP_SCHEMA v1.3.0
```

---

## 13. Proper WRAP vs BER Workflow

```yaml
WRAP_BER_WORKFLOW:
  description: "Correct sequencing of WRAP and BER artifacts"
  
  STEP_1_EXECUTION:
    actor: "Execution Agent (any GID)"
    action: "Complete PAC tasks"
    output: "Work artifacts"
    
  STEP_2_WRAP:
    actor: "Execution Agent (any GID)"
    action: "Document execution in WRAP"
    output: "WRAP artifact"
    constraints:
      - "No decision language"
      - "Includes authority disclaimers"
      - "Reports facts only"
      
  STEP_3_REVIEW:
    actor: "Benson (GID-00)"
    action: "Review WRAP"
    input: "WRAP artifact"
    
  STEP_4_BER:
    actor: "Benson (GID-00) ONLY"
    action: "Issue BER with decision"
    output: "BER artifact"
    authority: "EXCLUSIVE"
    permitted_language:
      - "Decision: ACCEPTED"
      - "Decision: REJECTED"
      - "ISSUED"
      - "APPROVED"
      
  INVARIANT: |
    WRAP precedes BER.
    WRAP contains no decisions.
    BER contains binding decision.
    Only Benson issues BER.

---

# ═══════════════════════════════════════════════════════════════════════════════
# END CHAINBRIDGE_CANONICAL_WRAP_SCHEMA v1.1.0
# STATUS: FROZEN | SECURITY_HARDENED
# ENFORCEMENT: HARD_FAIL
# ═══════════════════════════════════════════════════════════════════════════════
