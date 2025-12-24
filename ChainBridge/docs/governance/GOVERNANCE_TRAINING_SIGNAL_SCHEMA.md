# Governance Training Signal Schema

> **PAC Reference:** PAC-MAGGIE-P36-GOVERNANCE-METRICS-LEARNING-LOOP-AND-AGENT-PERFORMANCE-BASELINE-01  
> **Author:** Maggie (GID-10) | 💗 MAGENTA  
> **Authority:** BENSON (GID-00)  
> **Date:** 2025-12-24  
> **Status:** CANONICAL

---

## 1. Overview

This document defines the canonical schema for TRAINING_SIGNAL blocks in PAC and WRAP documents. Training signals enable measurable agent learning by:

- Capturing lessons from each governance operation
- Propagating successful patterns across agents
- Identifying areas requiring improvement
- Creating a closed-loop feedback system

---

## 2. Training Signal Schema

### 2.1 Full Schema Definition

```yaml
TRAINING_SIGNAL_SCHEMA:
  version: "1.0.0"
  
  required_fields:
    signal_type:
      type: "string"
      allowed_values:
        - "POSITIVE_REINFORCEMENT"
        - "NEGATIVE_REINFORCEMENT"
        - "PATTERN_LEARNING"
        - "ERROR_CORRECTION"
        - "BEHAVIORAL_ADJUSTMENT"
      description: "Classification of the training signal"
      
    pattern:
      type: "string"
      format: "SCREAMING_SNAKE_CASE"
      max_length: 64
      description: "Unique identifier for the learned pattern"
      examples:
        - "GOVERNANCE_MUST_SURVIVE_ADVERSARIES"
        - "AGENTS_MUST_IMPROVE_MEASURABLY"
        - "NO_SILENT_FAILURES_PERMITTED"
        
    lesson:
      type: "string | array[string]"
      max_length: 500
      description: "Human-readable lesson(s) from this operation"
      
    mandatory:
      type: "boolean"
      default: true
      description: "Whether this signal must be propagated"
      
    propagate:
      type: "boolean"
      default: true
      description: "Whether to share with other agents"
      
  optional_fields:
    program:
      type: "string"
      description: "Learning program this belongs to"
      example: "Agent University"
      
    course:
      type: "string"
      description: "Specific course within program"
      example: "GOV-900: Adversarial Governance Robustness"
      
    module:
      type: "string"
      description: "Module within course"
      example: "P36 — Agent Performance Baselines"
      
    standard:
      type: "string"
      description: "External standard reference"
      example: "ISO/PAC/METRICS-V1.0"
      
    evaluation:
      type: "string"
      allowed_values: ["Binary", "Graduated", "Continuous"]
      description: "How learning is evaluated"
      
    scope:
      type: "string"
      allowed_values:
        - "AGENT_SPECIFIC"
        - "ROLE_SPECIFIC"
        - "LANE_SPECIFIC"
        - "ALL_AGENTS"
      description: "Who should receive this signal"
      
    priority:
      type: "integer"
      range: [1, 10]
      default: 5
      description: "Urgency of learning (10 = highest)"
      
    expires:
      type: "string"
      format: "ISO8601"
      description: "When this signal becomes obsolete"
      
    supersedes:
      type: "array[string]"
      description: "Previous patterns this replaces"
```

---

## 3. Signal Type Definitions

### 3.1 POSITIVE_REINFORCEMENT

Used when an operation demonstrates exemplary behavior.

```yaml
POSITIVE_REINFORCEMENT:
  purpose: "Reinforce successful patterns"
  triggers:
    - "First-pass validation success"
    - "Zero scope violations"
    - "Comprehensive failure explanations"
    - "Ahead-of-schedule completion"
    
  example:
    signal_type: "POSITIVE_REINFORCEMENT"
    pattern: "FIRST_PASS_VALIDATION_ACHIEVED"
    lesson: "Agent maintained high accuracy without iteration"
    mandatory: true
    propagate: true
    scope: "ROLE_SPECIFIC"
```

### 3.2 NEGATIVE_REINFORCEMENT

Used when an operation reveals problematic patterns.

```yaml
NEGATIVE_REINFORCEMENT:
  purpose: "Discourage failed patterns"
  triggers:
    - "Gate validation failures"
    - "Scope violations"
    - "Authority overreach"
    - "Silent failures"
    
  example:
    signal_type: "NEGATIVE_REINFORCEMENT"
    pattern: "SCOPE_VIOLATION_DETECTED"
    lesson: "Agent accessed paths outside declared execution lane"
    mandatory: true
    propagate: true
    scope: "AGENT_SPECIFIC"
```

### 3.3 PATTERN_LEARNING

Used to teach new patterns without value judgment.

```yaml
PATTERN_LEARNING:
  purpose: "Teach structural patterns"
  triggers:
    - "New governance structure introduced"
    - "Process change documented"
    - "Schema evolution"
    
  example:
    signal_type: "PATTERN_LEARNING"
    pattern: "METRICS_REQUIRED_FOR_COMPLETION"
    lesson: "All PACs must emit quantitative metrics in EXECUTION_METRICS block"
    mandatory: true
    propagate: true
    scope: "ALL_AGENTS"
```

### 3.4 ERROR_CORRECTION

Used to document and correct specific errors.

```yaml
ERROR_CORRECTION:
  purpose: "Correct specific errors"
  triggers:
    - "Validation error resolved"
    - "Regression fixed"
    - "Misunderstanding clarified"
    
  example:
    signal_type: "ERROR_CORRECTION"
    pattern: "REGISTRY_BINDING_CORRECTED"
    lesson: "Agent color must match AGENT_REGISTRY.md exactly (case-sensitive)"
    mandatory: true
    propagate: false
    scope: "AGENT_SPECIFIC"
```

### 3.5 BEHAVIORAL_ADJUSTMENT

Used for operational behavior modifications.

```yaml
BEHAVIORAL_ADJUSTMENT:
  purpose: "Adjust operational behavior"
  triggers:
    - "Performance below baseline"
    - "New constraint introduced"
    - "Process optimization identified"
    
  example:
    signal_type: "BEHAVIORAL_ADJUSTMENT"
    pattern: "REDUCE_VALIDATION_ITERATIONS"
    lesson: "Reference gold-standard PACs before first validation attempt"
    mandatory: true
    propagate: true
    scope: "ROLE_SPECIFIC"
```

---

## 4. Signal Emission Rules

### 4.1 Mandatory Emission Points

```yaml
MANDATORY_EMISSION_POINTS:
  pac_completion:
    condition: "PAC reaches POSITIVE_CLOSURE"
    required_signal_type: "POSITIVE_REINFORCEMENT | PATTERN_LEARNING"
    
  validation_failure:
    condition: "gate_pack.py returns INVALID"
    required_signal_type: "NEGATIVE_REINFORCEMENT | ERROR_CORRECTION"
    
  scope_violation:
    condition: "Agent accesses forbidden path/tool"
    required_signal_type: "NEGATIVE_REINFORCEMENT"
    
  baseline_deviation:
    condition: "Performance metric exceeds threshold"
    required_signal_type: "BEHAVIORAL_ADJUSTMENT"
```

### 4.2 Signal Quality Requirements

```yaml
SIGNAL_QUALITY_REQUIREMENTS:
  lesson_clarity:
    requirement: "Lesson must be actionable"
    test: "Can an agent modify behavior based on this lesson?"
    
  pattern_uniqueness:
    requirement: "Pattern must be unique across signals"
    test: "No duplicate patterns in same scope"
    
  scope_appropriateness:
    requirement: "Scope must match lesson generalizability"
    test: "ALL_AGENTS only for universal lessons"
    
  propagation_necessity:
    requirement: "propagate=true only when lesson benefits others"
    test: "Agent-specific errors should not propagate"
```

---

## 5. Signal Ingestion

### 5.1 Ingestion Pipeline

```yaml
INGESTION_PIPELINE:
  steps:
    1_receive:
      action: "Parse TRAINING_SIGNAL from PAC/WRAP"
      validation: "Schema compliance check"
      
    2_classify:
      action: "Route by signal_type and scope"
      routing:
        AGENT_SPECIFIC: "agent/{gid}/signals/"
        ROLE_SPECIFIC: "roles/{role}/signals/"
        ALL_AGENTS: "global/signals/"
        
    3_deduplicate:
      action: "Check for duplicate patterns"
      resolution: "Keep most recent, archive older"
      
    4_index:
      action: "Add to searchable signal index"
      fields: ["pattern", "signal_type", "scope", "timestamp"]
      
    5_notify:
      action: "Alert affected agents"
      method: "Next PAC preamble includes pending signals"
```

### 5.2 Signal Storage

```yaml
SIGNAL_STORAGE:
  location: "data/training_signals/"
  format: "JSON"
  
  structure:
    global/
      signals.json        # ALL_AGENTS signals
      archive/            # Superseded signals
    roles/
      BACKEND/
      FRONTEND/
      SECURITY/
      ML_AI/
      STRATEGY/
      QUALITY_ASSURANCE/
    agents/
      GID-01/
      GID-05/
      GID-06/
      GID-07/
      GID-08/
      GID-10/
```

---

## 6. Signal Application

### 6.1 Pre-PAC Signal Review

Before executing a PAC, agents should review applicable signals:

```yaml
PRE_PAC_SIGNAL_REVIEW:
  mandatory_review:
    - "global/signals.json"
    - "roles/{agent_role}/signals.json"
    - "agents/{agent_gid}/signals.json"
    
  review_window: "Last 30 days or 50 signals, whichever is fewer"
  
  action_on_review:
    POSITIVE_REINFORCEMENT: "Note exemplary patterns"
    NEGATIVE_REINFORCEMENT: "Avoid documented anti-patterns"
    PATTERN_LEARNING: "Apply new structural requirements"
    ERROR_CORRECTION: "Verify correction is applied"
    BEHAVIORAL_ADJUSTMENT: "Modify operational approach"
```

### 6.2 Signal Acknowledgment

```yaml
SIGNAL_ACKNOWLEDGMENT:
  block_name: "SIGNALS_ACKNOWLEDGED"
  required_in: "PAC header section"
  
  format:
    SIGNALS_ACKNOWLEDGED:
      global: ["PATTERN_1", "PATTERN_2"]
      role: ["PATTERN_3"]
      agent: ["PATTERN_4"]
      
  enforcement: "ADVISORY"  # Will become MANDATORY after observation period
```

---

## 7. Signal Metrics

### 7.1 Signal Effectiveness

```yaml
SIGNAL_EFFECTIVENESS_METRICS:
  pattern_adherence:
    id: "SIG_001"
    description: "Rate of pattern compliance post-signal"
    formula: "compliant_operations / total_operations"
    target: "> 0.90"
    
  recurrence_rate:
    id: "SIG_002"
    description: "Rate of same error after correction signal"
    formula: "recurring_errors / total_errors_of_type"
    target: "< 0.10"
    
  signal_half_life:
    id: "SIG_003"
    description: "Time until signal becomes obsolete"
    formula: "days_until(compliance_rate > 0.95)"
    target: "< 30 days"
```

---

## 8. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-24 | Maggie (GID-10) | Initial canonical definition |

---

**END — GOVERNANCE_TRAINING_SIGNAL_SCHEMA.md**
