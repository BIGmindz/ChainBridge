# GOVERNANCE RULE REGISTRY — v1.0

> **Authority:** PAC-BENSON-P51-GOVERNANCE-DOCTRINE-V1-EXECUTION-INTELLIGENCE-FOUNDATION-01  
> **Owner:** BENSON (GID-00)  
> **Status:** 🔒 CANONICAL  
> **Version:** 1.0.0  

---

## 0. REGISTRY PREAMBLE

```yaml
REGISTRY_PREAMBLE:
  registry_name: "CHAINBRIDGE_GOVERNANCE_RULE_REGISTRY"
  version: "1.0.0"
  authority: "BENSON (GID-00)"
  human_authority: "ALEX (HUMAN-IN-THE-LOOP)"
  purpose: "Machine-enforceable governance law"
  data_file: "governance_rules.json"
  immutable: false
  self_modification_allowed: false
  human_amendment_required: true
```

The Governance Rule Registry is the machine-readable law of the ChainBridge governance system. Rules defined here are automatically enforced by the BensonExecutionEngine and gate_pack.py validation.

---

## 1. RULE STRUCTURE

Each governance rule follows a canonical structure:

```yaml
RULE_STRUCTURE:
  required_fields:
    rule_id:
      type: "string"
      format: "GR-{NNN}"
      description: "Unique rule identifier"
      
    scope:
      type: "string"
      enum:
        - "AUTHORITY"
        - "EXECUTION"
        - "SEQUENTIAL"
        - "DRIFT"
        - "DOCTRINE"
        - "LEARNING"
      description: "Category of governance this rule covers"
      
    trigger:
      type: "string"
      description: "Condition that activates this rule"
      
    enforcement:
      type: "string"
      enum:
        - "HARD_BLOCK"
        - "ESCALATE"
        - "ADVISORY"
        - "LOG_ONLY"
      description: "How the rule is enforced"
      
    error_code:
      type: "string"
      format: "GS_{XXX}"
      description: "Error code emitted on violation"
      
    description:
      type: "string"
      description: "Human-readable explanation"
      
  optional_fields:
    training_signal:
      type: "object"
      properties:
        pattern: "string"
        lesson: "string"
      description: "Learning signal emitted on violation"
      
    recovery:
      type: "string"
      description: "Recommended recovery action"
      
    escalation:
      type: "string"
      description: "Escalation path if enforcement is ESCALATE"
      
    notes:
      type: "string"
      description: "Additional context or planned changes"
```

---

## 2. SCOPE DEFINITIONS

### 2.1 AUTHORITY Scope

Rules governing **who** can perform actions.

| Rule ID | Error Code | Trigger | Enforcement |
|---------|------------|---------|-------------|
| GR-001 | GS_120 | Non-Benson WRAP_ACCEPTED | HARD_BLOCK |
| GR-002 | GS_121 | Agent direct WRAP emission | HARD_BLOCK |
| GR-003 | GS_122 | Agent POSITIVE_CLOSURE | HARD_BLOCK |
| GR-005 | GS_124 | Agent self-closure | HARD_BLOCK |
| GR-006 | GS_125 | Non-Benson WRAP generation | HARD_BLOCK |
| GR-009 | GS_117 | Agent self-activation | HARD_BLOCK |

### 2.2 EXECUTION Scope

Rules governing **how** actions are performed.

| Rule ID | Error Code | Trigger | Enforcement |
|---------|------------|---------|-------------|
| GR-004 | GS_123 | Runtime bypass | HARD_BLOCK |
| GR-007 | GS_131 | Forbidden fields in EXECUTION_RESULT | HARD_BLOCK |
| GR-008 | GS_130 | Missing required fields | HARD_BLOCK |
| GR-010 | GS_118 | Identity mismatch | HARD_BLOCK |
| GR-016 | GS_064 | Scope boundary violation | HARD_BLOCK |
| GR-017 | GS_092 | Lane boundary violation | HARD_BLOCK |

### 2.3 SEQUENTIAL Scope

Rules governing **ordering** and dependencies.

| Rule ID | Error Code | Trigger | Enforcement |
|---------|------------|---------|-------------|
| GR-013 | GS_096 | PAC sequence violation | HARD_BLOCK |
| GR-014 | GS_111 | Missing prior WRAP | HARD_BLOCK |
| GR-015 | GS_112 | WRAP/PAC binding mismatch | HARD_BLOCK |

### 2.4 DRIFT Scope

Rules governing **deviation** from baselines.

| Rule ID | Error Code | Trigger | Enforcement |
|---------|------------|---------|-------------|
| GR-011 | GS_094 | Performance regression | HARD_BLOCK |
| GR-012 | GS_095 | Semantic drift | ESCALATE |

### 2.5 DOCTRINE Scope

Rules governing **adherence** to governance principles.

| Rule ID | Error Code | Trigger | Enforcement |
|---------|------------|---------|-------------|
| GR-018 | GS_140 | Missing doctrine reference | ADVISORY |
| GR-019 | GS_141 | Governance rule violation | HARD_BLOCK |

### 2.6 LEARNING Scope

Rules governing **training** and model updates.

| Rule ID | Error Code | Trigger | Enforcement |
|---------|------------|---------|-------------|
| GR-020 | GS_150 | Autonomous learning deployment | HARD_BLOCK |

---

## 3. ENFORCEMENT LEVELS

### 3.1 HARD_BLOCK

```yaml
HARD_BLOCK:
  behavior: "Execution halts immediately"
  bypass: "NONE"
  logging: "MANDATORY"
  ledger_entry: "BLOCK_ENFORCED"
  recovery: "CORRECTION_PACK or manual remediation"
  human_override: false
```

### 3.2 ESCALATE

```yaml
ESCALATE:
  behavior: "Execution paused, human decision required"
  bypass: "HUMAN_AUTHORIZATION_ONLY"
  logging: "MANDATORY"
  ledger_entry: "ESCALATION_TRIGGERED"
  timeout: "NO_AUTO_PROCEED"
  human_override: true
```

### 3.3 ADVISORY

```yaml
ADVISORY:
  behavior: "Warning logged, execution continues"
  bypass: "N/A"
  logging: "MANDATORY"
  ledger_entry: "ADVISORY_LOGGED"
  impact: "INFORMATIONAL"
  human_override: "N/A"
```

### 3.4 LOG_ONLY

```yaml
LOG_ONLY:
  behavior: "Observation recorded, no action taken"
  bypass: "N/A"
  logging: "MANDATORY"
  ledger_entry: "NONE"
  impact: "OBSERVATIONAL"
  human_override: "N/A"
```

---

## 4. RULE LOOKUP API

The governance rule registry is consumed by:
- **BensonExecutionEngine**: Validates rules during PAC execution
- **gate_pack.py**: Validates rules during artifact validation
- **ledger_writer.py**: References rules when recording violations

### 4.1 Lookup by Error Code

```python
def get_rule_by_error_code(error_code: str) -> dict:
    """
    Retrieve governance rule by error code.
    
    Args:
        error_code: e.g., "GS_120"
    
    Returns:
        Rule definition or None
    """
    rules = load_governance_rules()
    for rule in rules["rules"]:
        if rule["error_code"] == error_code:
            return rule
    return None
```

### 4.2 Lookup by Scope

```python
def get_rules_by_scope(scope: str) -> list:
    """
    Retrieve all rules in a scope.
    
    Args:
        scope: e.g., "AUTHORITY"
    
    Returns:
        List of matching rules
    """
    rules = load_governance_rules()
    return [r for r in rules["rules"] if r["scope"] == scope]
```

### 4.3 Validate Against Rule

```python
def check_rule_violation(rule_id: str, context: dict) -> dict:
    """
    Check if a rule is violated given context.
    
    Args:
        rule_id: e.g., "GR-001"
        context: Execution context
    
    Returns:
        {"violated": bool, "enforcement": str, "error_code": str}
    """
    # Implementation in benson_execution.py
    pass
```

---

## 5. RULE AMENDMENT PROCESS

### 5.1 Adding New Rules

1. **Proposal**: Submit rule proposal with full structure
2. **Review**: Benson validates against existing rules
3. **Conflict Check**: Ensure no contradictions
4. **Human Approval**: Explicit authorization required
5. **Registration**: Add to governance_rules.json
6. **Publication**: Update this documentation

### 5.2 Modifying Existing Rules

1. **Justification**: Document reason for modification
2. **Impact Analysis**: Assess downstream effects
3. **Deprecation Notice**: If changing enforcement level
4. **Human Approval**: Explicit authorization required
5. **Version Bump**: Increment registry version

### 5.3 Deprecating Rules

1. **Notice Period**: Mark as deprecated for one version
2. **Migration Path**: Document alternative rules
3. **Human Approval**: Explicit authorization required
4. **Removal**: Remove in subsequent version

**No autonomous rule modification is permitted.**

---

## 6. ERROR CODE REFERENCE

### 6.1 GS_120-GS_129: Authority Violations

| Code | Rule | Description |
|------|------|-------------|
| GS_120 | GR-001 | WRAP_AUTHORITY_VIOLATION |
| GS_121 | GR-002 | AGENT_WRAP_EMISSION_BLOCKED |
| GS_122 | GR-003 | POSITIVE_CLOSURE_AUTHORITY_BLOCKED |
| GS_123 | GR-004 | EXECUTION_RUNTIME_BYPASS |
| GS_124 | GR-005 | AGENT_SELF_CLOSURE_BLOCKED |
| GS_125 | GR-006 | WRAP_GENERATION_AUTHORITY_VIOLATION |

### 6.2 GS_130-GS_139: Execution Violations

| Code | Rule | Description |
|------|------|-------------|
| GS_130 | GR-008 | EXECUTION_RESULT_INCOMPLETE |
| GS_131 | GR-007 | EXECUTION_RESULT_FORBIDDEN_FIELDS |
| GS_132 | — | CLOSURE_CLAIM_IN_RESULT |
| GS_133 | — | AUTHORITY_CLAIM_IN_RESULT |
| GS_134 | — | PAC_REFERENCE_INVALID |

### 6.3 GS_140-GS_149: Doctrine Violations

| Code | Rule | Description |
|------|------|-------------|
| GS_140 | GR-018 | DOCTRINE_REFERENCE_MISSING |
| GS_141 | GR-019 | GOVERNANCE_RULE_VIOLATION |

### 6.4 GS_150-GS_159: Learning Violations

| Code | Rule | Description |
|------|------|-------------|
| GS_150 | GR-020 | AUTONOMOUS_LEARNING_BLOCKED |

---

## 7. INTEGRATION CHECKLIST

### 7.1 BensonExecutionEngine Integration

- [ ] Load governance_rules.json on initialization
- [ ] Check AUTHORITY rules before WRAP generation
- [ ] Check EXECUTION rules during validation
- [ ] Emit training signals from rule definitions
- [ ] Log rule violations to ledger

### 7.2 gate_pack.py Integration

- [ ] Load governance_rules.json on initialization
- [ ] Validate PAC structure against DOCTRINE rules
- [ ] Validate WRAP structure against AUTHORITY rules
- [ ] Reference error codes from rule registry

### 7.3 ledger_writer.py Integration

- [ ] Reference rule_id in BLOCK_ENFORCED entries
- [ ] Include training_signal from rule definition
- [ ] Track rule violation statistics

---

## 8. ATTESTATION

```yaml
REGISTRY_ATTESTATION:
  registry_id: "GOVERNANCE_RULE_REGISTRY"
  version: "1.0.0"
  rules_count: 20
  created_by: "BENSON (GID-00)"
  created_at: "2025-12-26"
  authority: "PAC-BENSON-P51"
  status: "CANONICAL"
  data_file: "governance_rules.json"
```

---

**END GOVERNANCE RULE REGISTRY — v1.0**

> 🟦🟩 **BENSON (GID-00)** — Registry Authority  
> 🔒 **CANONICAL** — Machine-enforceable law
