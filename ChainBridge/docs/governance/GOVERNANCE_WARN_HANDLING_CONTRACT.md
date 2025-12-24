# Governance WARN Handling Contract

> **PAC Reference:** PAC-MAGGIE-P41-GOVERNANCE-SIGNAL-AUTHORITY-BOUNDARIES-AND-WARN-PROPAGATION-LOCKDOWN-01  
> **Author:** Maggie (GID-10) | 💗 MAGENTA  
> **Authority:** BENSON (GID-00)  
> **Date:** 2025-12-24  
> **Status:** ENFORCED

---

## 1. Overview

This document defines the **explicit handling contract** for WARN signals within the ChainBridge governance system. WARN is an advisory signal — it must **never** propagate to settlement layer actions that move money, release funds, or authorize execution.

**Core Principle:** `WARN_IS_NOT_AUTHORITY` — Advisory signals must never move money.

---

## 2. WARN Signal Definition

### 2.1 What WARN Represents

```yaml
WARN_SIGNAL_DEFINITION:
  signal_type: "ADVISORY"
  authority_level: "NONE"
  
  semantics:
    description: "Input has deficiencies but is not fundamentally invalid"
    action_required: "Human review or automated remediation"
    blocking: false
    
  key_properties:
    - "WARN is NOT approval"
    - "WARN is NOT rejection"
    - "WARN is NOT deferral"
    - "WARN is OBSERVATION ONLY"
    
  cannot_authorize:
    - "Cash release"
    - "Fund transfer"
    - "Settlement execution"
    - "Authority escalation grant"
    - "Privilege elevation"
    - "Bypass of any gate"
```

### 2.2 WARN vs Other Signals

```yaml
SIGNAL_AUTHORITY_HIERARCHY:
  PASS:
    authority: "FULL"
    can_authorize: ["settlement", "release", "execution"]
    propagates_to: ["SETTLEMENT", "ECONOMIC_ACTIONS"]
    
  WARN:
    authority: "NONE"
    can_authorize: []
    propagates_to: ["LOGGING", "MONITORING", "HUMAN_REVIEW"]
    
  FAIL:
    authority: "TERMINAL_BLOCK"
    can_authorize: []
    propagates_to: ["HALT", "REJECTION", "AUDIT"]
    
  SKIP:
    authority: "NONE"
    can_authorize: []
    propagates_to: ["LOGGING"]
```

---

## 3. WARN Ingress Path Mapping

### 3.1 All WARN Sources

```yaml
WARN_INGRESS_PATHS:
  SIGNAL_LAYER:
    sources:
      - "gate_pack.py validation with non-blocking issues"
      - "BSRG partial checklist compliance"
      - "Gold Standard checklist with optional items missing"
      - "Schema validation with deprecated fields"
      - "Agent registry lookup with soft mismatches"
      
    allowed_consumers:
      - "LOGGING_SUBSYSTEM"
      - "MONITORING_DASHBOARD"
      - "AUDIT_TRAIL"
      - "HUMAN_REVIEW_QUEUE"
      
    forbidden_consumers:
      - "SETTLEMENT_ENGINE"
      - "FUND_RELEASE_GATE"
      - "AUTHORITY_ESCALATION_SERVICE"
      - "PRIVILEGE_MANAGER"
      
  GOVERNANCE_LAYER:
    sources:
      - "PAC validation with advisory warnings"
      - "WRAP validation with non-critical issues"
      - "Ledger entries with optional metadata missing"
      - "Sequence checks with soft ordering issues"
      
    allowed_consumers:
      - "GOVERNANCE_DASHBOARD"
      - "AGENT_NOTIFICATION_SERVICE"
      - "CORRECTION_SUGGESTION_ENGINE"
      
    forbidden_consumers:
      - "POSITIVE_CLOSURE_GRANT"
      - "AUTHORITY_TOKEN_ISSUER"
      - "SETTLEMENT_BRIDGE"
```

### 3.2 WARN Egress Boundaries

```yaml
WARN_EGRESS_BOUNDARIES:
  HARD_BOUNDARY_001:
    name: "SIGNAL_TO_GOVERNANCE"
    allows: ["WARN → GOVERNANCE_LOGGING"]
    blocks: ["WARN → AUTHORITY_DECISION"]
    enforcement: "COMPILE_TIME + RUNTIME"
    
  HARD_BOUNDARY_002:
    name: "GOVERNANCE_TO_SETTLEMENT"
    allows: ["PASS → SETTLEMENT"]
    blocks: ["WARN → SETTLEMENT", "FAIL → SETTLEMENT"]
    enforcement: "RUNTIME_INVARIANT"
    
  HARD_BOUNDARY_003:
    name: "WARN_TO_ECONOMIC"
    allows: []
    blocks: ["WARN → ANY_ECONOMIC_ACTION"]
    enforcement: "IMMUTABLE_GATE"
```

---

## 4. WARN Handling Contract

### 4.1 Explicit Actions per Context

```yaml
WARN_HANDLING_CONTRACT:
  context: "SIGNAL_VALIDATION"
  actions:
    ALLOW:
      - "Log warning to audit trail"
      - "Increment WARN counter in metrics"
      - "Add to human review queue"
      - "Continue validation pipeline (non-blocking)"
      
    BLOCK:
      - "Propagate to settlement layer"
      - "Issue authority tokens"
      - "Bypass any mandatory gate"
      - "Escalate with authority grant"
      
    ESCALATE:
      - "Route to designated reviewer if WARN count > threshold"
      - "Notify agent lead if WARN pattern detected"
      
  ---
  
  context: "GOVERNANCE_EVALUATION"
  actions:
    ALLOW:
      - "Display in governance dashboard"
      - "Include in PAC/WRAP status reports"
      - "Track in agent learning ledger"
      
    BLOCK:
      - "Grant POSITIVE_CLOSURE"
      - "Issue correction completion"
      - "Authorize PAC sequence advancement"
      
    ESCALATE:
      - "Flag for BENSON review if governance WARN threshold exceeded"
      
  ---
  
  context: "SETTLEMENT_BOUNDARY"
  actions:
    ALLOW: []  # NOTHING ALLOWED
    
    BLOCK:
      - "ANY action at settlement boundary"
      - "Fund release"
      - "Cash movement"
      - "Economic state change"
      
    ESCALATE:
      - "Emergency halt if WARN reaches settlement boundary"
      - "Emit GS_096: WARN_SETTLEMENT_BOUNDARY_VIOLATION"
```

### 4.2 Decision Matrix

```yaml
WARN_DECISION_MATRIX:
  # Signal → Context → Action
  
  WARN + SIGNAL_LAYER + LOGGING:
    decision: "ALLOW"
    reason: "Advisory logging is safe"
    
  WARN + SIGNAL_LAYER + MONITORING:
    decision: "ALLOW"
    reason: "Observability is safe"
    
  WARN + SIGNAL_LAYER + SETTLEMENT:
    decision: "BLOCK"
    reason: "WARN cannot authorize economic action"
    error_code: "GS_096"
    
  WARN + GOVERNANCE_LAYER + DASHBOARD:
    decision: "ALLOW"
    reason: "Display is safe"
    
  WARN + GOVERNANCE_LAYER + CLOSURE:
    decision: "BLOCK"
    reason: "WARN cannot grant closure"
    error_code: "GS_097"
    
  WARN + SETTLEMENT_LAYER + ANY:
    decision: "BLOCK"
    reason: "WARN cannot exist at settlement layer"
    error_code: "GS_098"
```

---

## 5. Error Codes

### 5.1 WARN Boundary Violation Codes

```yaml
WARN_ERROR_CODES:
  GS_096:
    description: "WARN signal attempted to reach settlement boundary"
    severity: "CRITICAL"
    action: "EMERGENCY_HALT"
    
  GS_097:
    description: "WARN signal attempted to grant POSITIVE_CLOSURE"
    severity: "CRITICAL"
    action: "BLOCK_AND_AUDIT"
    
  GS_098:
    description: "WARN signal detected in settlement layer"
    severity: "CATASTROPHIC"
    action: "SYSTEM_LOCKDOWN"
    
  GS_099:
    description: "WARN cascaded through authority escalation path"
    severity: "CRITICAL"
    action: "ESCALATION_BLOCKED"
```

---

## 6. Contract Enforcement

### 6.1 Static Analysis

```yaml
STATIC_ENFORCEMENT:
  compile_time_checks:
    - "Type system prevents WARN → Settlement function calls"
    - "Lint rules flag any WARN in settlement code paths"
    - "Code review gate blocks WARN in economic modules"
    
  pattern_detection:
    forbidden_patterns:
      - "if signal == WARN: release_funds()"
      - "if signal == WARN: grant_authority()"
      - "if signal in [PASS, WARN]: settle()"
```

### 6.2 Runtime Enforcement

```yaml
RUNTIME_ENFORCEMENT:
  invariant_checks:
    - "Assert WARN never reaches SettlementEngine"
    - "Assert WARN never in AuthorityToken payload"
    - "Assert WARN count = 0 at settlement boundary"
    
  audit_logging:
    - "Log all WARN signals with full context"
    - "Log all WARN boundary approach events"
    - "Alert on any WARN within 1 hop of settlement"
```

---

## 7. Machine-Readable Contract

```python
# WARN_HANDLING_CONTRACT.py
# Machine-readable enforcement

from enum import Enum, auto
from typing import Set

class Signal(Enum):
    PASS = auto()
    WARN = auto()
    FAIL = auto()
    SKIP = auto()

class Layer(Enum):
    SIGNAL = auto()
    GOVERNANCE = auto()
    SETTLEMENT = auto()

class Action(Enum):
    LOG = auto()
    MONITOR = auto()
    DASHBOARD = auto()
    REVIEW = auto()
    CLOSURE = auto()
    RELEASE = auto()
    SETTLEMENT = auto()

# Immutable permission matrix
WARN_ALLOWED_ACTIONS: Set[Action] = frozenset({
    Action.LOG,
    Action.MONITOR,
    Action.DASHBOARD,
    Action.REVIEW,
})

WARN_BLOCKED_ACTIONS: Set[Action] = frozenset({
    Action.CLOSURE,
    Action.RELEASE,
    Action.SETTLEMENT,
})

def validate_warn_action(action: Action) -> bool:
    """
    Returns True if action is allowed for WARN signal.
    FAIL_CLOSED: Unknown actions are blocked.
    """
    if action in WARN_BLOCKED_ACTIONS:
        return False
    if action in WARN_ALLOWED_ACTIONS:
        return True
    # FAIL_CLOSED: unknown = blocked
    return False

def warn_can_reach_layer(layer: Layer) -> bool:
    """
    Returns True if WARN is allowed to propagate to layer.
    """
    return layer != Layer.SETTLEMENT
```

---

## 8. Training Signal

```yaml
TRAINING_SIGNAL:
  pattern: "WARN_IS_NOT_AUTHORITY"
  lesson: "Advisory signals must never move money."
  mandatory: true
  propagate: true
  
  reinforcement:
    - "WARN = observation, not permission"
    - "WARN = logging, not authorization"
    - "WARN = human review trigger, not automation trigger"
```

---

## 9. Audit Trail Requirements

```yaml
AUDIT_REQUIREMENTS:
  every_warn_must:
    - "Be logged with timestamp"
    - "Include source context"
    - "Include destination context"
    - "Be traceable in replay"
    
  warn_boundary_events_must:
    - "Emit dedicated boundary event"
    - "Include distance from settlement layer"
    - "Trigger alert if distance < 2 hops"
```

---

**Contract Status:** ENFORCED  
**Authority:** BENSON (GID-00)  
**Immutable:** true
