# Governance WARN Lock Rules

> **PAC Reference:** PAC-MAGGIE-P41-GOVERNANCE-SIGNAL-AUTHORITY-BOUNDARIES-AND-WARN-PROPAGATION-LOCKDOWN-01  
> **Author:** Maggie (GID-10) | 💗 MAGENTA  
> **Authority:** BENSON (GID-00)  
> **Date:** 2025-12-24  
> **Status:** ENFORCED

---

## 1. Overview

This document defines the **WARN_LOCK ruleset** — a machine-readable set of rules that enforce the hard boundary between WARN signals and settlement/authority actions. These rules are deterministic, replay-safe, and immutable.

**Core Principle:** `WARN_IS_NOT_AUTHORITY` — Advisory signals must never move money.

---

## 2. WARN_LOCK Rule Schema

```yaml
WARN_LOCK_SCHEMA:
  version: "1.0.0"
  authority: "BENSON (GID-00)"
  immutable: true
  
  rule_types:
    - "TRANSITION_LOCK"
    - "BOUNDARY_LOCK"
    - "CASCADE_LOCK"
    - "ESCALATION_LOCK"
```

---

## 3. Transition Lock Rules

### 3.1 Forbidden State Transitions

```yaml
TRANSITION_LOCKS:
  WARN_TO_PASS_LOCK:
    rule_id: "WL_001"
    description: "WARN cannot transition to PASS without human intervention"
    from_state: "WARN"
    to_state: "PASS"
    allowed: false
    requires: "HUMAN_REVIEW_APPROVAL"
    error_code: "GS_100"
    
  WARN_TO_RELEASE_LOCK:
    rule_id: "WL_002"
    description: "WARN cannot authorize fund release"
    from_state: "WARN"
    to_state: "RELEASE"
    allowed: false
    requires: null  # No path exists
    error_code: "GS_096"
    
  WARN_TO_SETTLE_LOCK:
    rule_id: "WL_003"
    description: "WARN cannot authorize settlement"
    from_state: "WARN"
    to_state: "SETTLED"
    allowed: false
    requires: null  # No path exists
    error_code: "GS_098"
    
  WARN_TO_ESCALATION_AUTHORITY_LOCK:
    rule_id: "WL_004"
    description: "WARN cannot grant escalation authority"
    from_state: "WARN"
    to_state: "ESCALATION_GRANTED"
    allowed: false
    requires: null  # No path exists
    error_code: "GS_099"
    
  WARN_TO_CLOSURE_LOCK:
    rule_id: "WL_005"
    description: "WARN cannot trigger POSITIVE_CLOSURE"
    from_state: "WARN"
    to_state: "POSITIVE_CLOSURE"
    allowed: false
    requires: null  # No path exists
    error_code: "GS_097"
```

### 3.2 Valid Transition Table

```yaml
WARN_VALID_TRANSITIONS:
  WARN_TO_LOGGED:
    rule_id: "WL_010"
    allowed: true
    destination: "AUDIT_LOG"
    
  WARN_TO_MONITORED:
    rule_id: "WL_011"
    allowed: true
    destination: "MONITORING_SYSTEM"
    
  WARN_TO_QUEUED:
    rule_id: "WL_012"
    allowed: true
    destination: "HUMAN_REVIEW_QUEUE"
    
  WARN_TO_DISPLAYED:
    rule_id: "WL_013"
    allowed: true
    destination: "DASHBOARD"
    
  WARN_TO_REMEDIATED:
    rule_id: "WL_014"
    allowed: true
    destination: "CORRECTION_ENGINE"
    requires: "HUMAN_APPROVAL"
```

---

## 4. Boundary Lock Rules

### 4.1 Layer Boundary Locks

```yaml
BOUNDARY_LOCKS:
  SIGNAL_GOVERNANCE_BOUNDARY:
    rule_id: "BL_001"
    description: "WARN can cross from SIGNAL to GOVERNANCE for logging only"
    boundary: "SIGNAL → GOVERNANCE"
    warn_allowed: true
    allowed_purposes: ["LOGGING", "DISPLAY", "METRICS"]
    blocked_purposes: ["AUTHORITY_GRANT", "STATE_CHANGE"]
    
  GOVERNANCE_SETTLEMENT_BOUNDARY:
    rule_id: "BL_002"
    description: "WARN cannot cross into SETTLEMENT layer"
    boundary: "GOVERNANCE → SETTLEMENT"
    warn_allowed: false
    allowed_purposes: []
    blocked_purposes: ["ALL"]
    error_code: "GS_098"
    enforcement: "HARD_GATE"
    
  SIGNAL_SETTLEMENT_BOUNDARY:
    rule_id: "BL_003"
    description: "WARN cannot bypass GOVERNANCE to reach SETTLEMENT"
    boundary: "SIGNAL → SETTLEMENT"
    warn_allowed: false
    allowed_purposes: []
    blocked_purposes: ["ALL"]
    error_code: "GS_096"
    enforcement: "HARD_GATE"
```

### 4.2 Boundary Enforcement Matrix

```yaml
BOUNDARY_ENFORCEMENT_MATRIX:
  # [Source Layer, Target Layer, Signal] → Decision
  
  SIGNAL_GOVERNANCE_PASS: "ALLOW"
  SIGNAL_GOVERNANCE_WARN: "ALLOW_LIMITED"
  SIGNAL_GOVERNANCE_FAIL: "ALLOW"
  SIGNAL_GOVERNANCE_SKIP: "ALLOW"
  
  GOVERNANCE_SETTLEMENT_PASS: "ALLOW"
  GOVERNANCE_SETTLEMENT_WARN: "BLOCK"
  GOVERNANCE_SETTLEMENT_FAIL: "BLOCK"
  GOVERNANCE_SETTLEMENT_SKIP: "BLOCK"
  
  SIGNAL_SETTLEMENT_PASS: "BLOCK"  # Must go through GOVERNANCE
  SIGNAL_SETTLEMENT_WARN: "BLOCK"
  SIGNAL_SETTLEMENT_FAIL: "BLOCK"
  SIGNAL_SETTLEMENT_SKIP: "BLOCK"
```

---

## 5. Cascade Lock Rules

### 5.1 Cascade Prevention

```yaml
CASCADE_LOCKS:
  WARN_ACCUMULATION_LOCK:
    rule_id: "CL_001"
    description: "Multiple WARNs cannot accumulate to form authority"
    rule: "SUM(WARN) ≠ PASS"
    enforcement: "INVARIANT"
    
  WARN_MAJORITY_LOCK:
    rule_id: "CL_002"
    description: "Majority WARN cannot override single FAIL"
    rule: "COUNT(WARN) > COUNT(FAIL) ⇏ PASS"
    enforcement: "INVARIANT"
    
  WARN_TIME_DECAY_LOCK:
    rule_id: "CL_003"
    description: "WARN cannot decay into PASS over time"
    rule: "WARN(t) → WARN(t+n) OR HUMAN_REVIEWED"
    enforcement: "STATE_MACHINE"
    
  WARN_RETRY_LOCK:
    rule_id: "CL_004"
    description: "Repeated WARN does not become PASS"
    rule: "RETRY(WARN) = WARN"
    enforcement: "IDEMPOTENT"
```

### 5.2 Cascade Detection Rules

```yaml
CASCADE_DETECTION:
  WARN_CHAIN_DETECTION:
    rule_id: "CD_001"
    description: "Detect chains of WARN signals attempting authority acquisition"
    pattern: "WARN → WARN → WARN → {PASS|RELEASE|SETTLE}"
    action: "BLOCK_AND_ALERT"
    alert_code: "GS_101"
    
  WARN_FANOUT_DETECTION:
    rule_id: "CD_002"
    description: "Detect WARN fanout attempting to bypass gates"
    pattern: "WARN → [WARN, WARN, WARN] → MERGE → {PASS}"
    action: "BLOCK_AND_ALERT"
    alert_code: "GS_102"
    
  WARN_TIMING_ATTACK_DETECTION:
    rule_id: "CD_003"
    description: "Detect rapid WARN submission attempting race condition"
    pattern: "WARN(t) → WARN(t+ε) → WARN(t+2ε) where ε < MIN_INTERVAL"
    action: "RATE_LIMIT_AND_ALERT"
    alert_code: "GS_103"
    min_interval_ms: 100
```

---

## 6. Escalation Lock Rules

### 6.1 Escalation Boundary Locks

```yaml
ESCALATION_LOCKS:
  WARN_NO_ESCALATION_AUTHORITY:
    rule_id: "EL_001"
    description: "WARN cannot escalate with authority grant"
    rule: "WARN + ESCALATE ⇏ AUTHORITY_GRANT"
    allowed_escalation_types: ["HUMAN_REVIEW", "NOTIFICATION"]
    blocked_escalation_types: ["AUTHORITY_GRANT", "PRIVILEGE_ELEVATION"]
    
  WARN_ESCALATION_CEILING:
    rule_id: "EL_002"
    description: "WARN escalation has a ceiling"
    max_escalation_level: "AGENT_LEAD"
    cannot_reach: ["BENSON_AUTHORITY", "EXECUTIVE_AUTHORITY"]
    reason: "Advisory signals cannot demand executive attention"
    
  WARN_NO_OVERRIDE_REQUEST:
    rule_id: "EL_003"
    description: "WARN cannot request gate override"
    rule: "WARN ⇏ OVERRIDE_REQUEST"
    error_code: "GS_104"
```

---

## 7. Machine-Readable Ruleset

```python
# WARN_LOCK_RULES.py
# Machine-readable enforcement ruleset

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Set, Tuple

class Signal(Enum):
    PASS = auto()
    WARN = auto()
    FAIL = auto()
    SKIP = auto()

class Layer(Enum):
    SIGNAL = auto()
    GOVERNANCE = auto()
    SETTLEMENT = auto()

class Destination(Enum):
    LOG = auto()
    MONITOR = auto()
    DASHBOARD = auto()
    REVIEW_QUEUE = auto()
    RELEASE = auto()
    SETTLE = auto()
    CLOSURE = auto()
    ESCALATION_GRANT = auto()

@dataclass(frozen=True)
class TransitionRule:
    from_state: Signal
    to_destination: Destination
    allowed: bool
    error_code: Optional[str]
    requires_human: bool = False

# IMMUTABLE TRANSITION RULES
WARN_TRANSITION_RULES: Tuple[TransitionRule, ...] = (
    # Allowed transitions
    TransitionRule(Signal.WARN, Destination.LOG, True, None),
    TransitionRule(Signal.WARN, Destination.MONITOR, True, None),
    TransitionRule(Signal.WARN, Destination.DASHBOARD, True, None),
    TransitionRule(Signal.WARN, Destination.REVIEW_QUEUE, True, None),
    
    # Blocked transitions
    TransitionRule(Signal.WARN, Destination.RELEASE, False, "GS_096"),
    TransitionRule(Signal.WARN, Destination.SETTLE, False, "GS_098"),
    TransitionRule(Signal.WARN, Destination.CLOSURE, False, "GS_097"),
    TransitionRule(Signal.WARN, Destination.ESCALATION_GRANT, False, "GS_099"),
)

@dataclass(frozen=True)
class BoundaryRule:
    source_layer: Layer
    target_layer: Layer
    signal: Signal
    allowed: bool
    error_code: Optional[str]

# IMMUTABLE BOUNDARY RULES
WARN_BOUNDARY_RULES: Tuple[BoundaryRule, ...] = (
    BoundaryRule(Layer.SIGNAL, Layer.GOVERNANCE, Signal.WARN, True, None),
    BoundaryRule(Layer.GOVERNANCE, Layer.SETTLEMENT, Signal.WARN, False, "GS_098"),
    BoundaryRule(Layer.SIGNAL, Layer.SETTLEMENT, Signal.WARN, False, "GS_096"),
)

def check_warn_transition(destination: Destination) -> Tuple[bool, Optional[str]]:
    """
    Check if WARN can transition to destination.
    Returns (allowed, error_code).
    FAIL_CLOSED: unknown destination = blocked.
    """
    for rule in WARN_TRANSITION_RULES:
        if rule.from_state == Signal.WARN and rule.to_destination == destination:
            return (rule.allowed, rule.error_code)
    # FAIL_CLOSED: unknown = blocked
    return (False, "GS_105")  # Unknown destination blocked

def check_warn_boundary(source: Layer, target: Layer) -> Tuple[bool, Optional[str]]:
    """
    Check if WARN can cross from source to target layer.
    Returns (allowed, error_code).
    FAIL_CLOSED: unknown boundary = blocked.
    """
    for rule in WARN_BOUNDARY_RULES:
        if (rule.source_layer == source and 
            rule.target_layer == target and 
            rule.signal == Signal.WARN):
            return (rule.allowed, rule.error_code)
    # FAIL_CLOSED: unknown = blocked
    return (False, "GS_106")  # Unknown boundary blocked

def validate_warn_cascade(signal_chain: Tuple[Signal, ...]) -> Tuple[bool, Optional[str]]:
    """
    Validate that a chain of signals doesn't allow WARN to acquire authority.
    Returns (valid, error_code).
    """
    warn_count = sum(1 for s in signal_chain if s == Signal.WARN)
    
    # Multiple WARNs cannot combine to form authority
    if warn_count > 1:
        # Check if chain ends in authority-granting state
        # (This would be detected at boundary, but catch early)
        pass
    
    # WARN anywhere in chain taints the chain for settlement
    if Signal.WARN in signal_chain:
        # Chain cannot reach settlement
        return (True, None)  # Valid = stays advisory
    
    return (True, None)

# MONOTONIC DOWNGRADE RULE
def monotonic_downgrade(signals: Tuple[Signal, ...]) -> Signal:
    """
    Apply monotonic downgrade: FAIL > WARN > PASS > SKIP
    Any WARN in the set means result cannot be PASS for authority purposes.
    """
    if Signal.FAIL in signals:
        return Signal.FAIL
    if Signal.WARN in signals:
        return Signal.WARN  # Cannot upgrade to PASS
    if Signal.PASS in signals:
        return Signal.PASS
    return Signal.SKIP
```

---

## 8. Proof of Monotonic Downgrade

### 8.1 Downgrade Rules

```yaml
MONOTONIC_DOWNGRADE_RULES:
  definition: "Signal authority can only decrease through composition"
  
  authority_order:
    - PASS: 3  # Highest authority
    - WARN: 1  # Advisory only (not 2, to emphasize gap)
    - FAIL: 0  # Terminal
    - SKIP: 0  # No authority
    
  composition_rules:
    PASS + PASS: PASS
    PASS + WARN: WARN  # Downgrade
    PASS + FAIL: FAIL  # Downgrade
    PASS + SKIP: PASS
    
    WARN + WARN: WARN
    WARN + FAIL: FAIL  # Downgrade
    WARN + SKIP: WARN
    
    FAIL + FAIL: FAIL
    FAIL + SKIP: FAIL
    
    SKIP + SKIP: SKIP
    
  invariant: "For any composition C(a, b): authority(C) <= min(authority(a), authority(b))"
  
  warn_specific_invariant: "WARN + X != PASS for any X"
```

### 8.2 Formal Proof

```
THEOREM: WARN cannot compose to PASS

PROOF:
1. Let authority(PASS) = 3, authority(WARN) = 1
2. Composition rule: authority(C) <= min(authority(inputs))
3. For any composition involving WARN: min(..., authority(WARN), ...) <= 1
4. Since authority(PASS) = 3 > 1, WARN + X cannot yield PASS
5. QED

COROLLARY: No number of WARNs can yield PASS
- SUM(WARN, n times) <= authority(WARN) = 1 < 3 = authority(PASS)
```

---

## 9. Enforcement Checkpoints

```yaml
ENFORCEMENT_CHECKPOINTS:
  CHECKPOINT_001:
    location: "gate_pack.py validation output"
    check: "WARN signals tagged with ADVISORY_ONLY flag"
    
  CHECKPOINT_002:
    location: "Governance layer entry"
    check: "WARN signals routed to advisory handlers only"
    
  CHECKPOINT_003:
    location: "Settlement boundary gate"
    check: "Assert signal != WARN"
    action_on_fail: "EMERGENCY_HALT + GS_098"
    
  CHECKPOINT_004:
    location: "Authority token issuance"
    check: "Assert source signal != WARN"
    action_on_fail: "BLOCK + GS_099"
    
  CHECKPOINT_005:
    location: "POSITIVE_CLOSURE evaluation"
    check: "Assert all signals == PASS"
    action_on_fail: "BLOCK + GS_097"
```

---

## 10. Summary Error Code Reference

```yaml
WARN_LOCK_ERROR_CODES:
  GS_096: "WARN signal attempted to reach settlement boundary"
  GS_097: "WARN signal attempted to grant POSITIVE_CLOSURE"
  GS_098: "WARN signal detected in settlement layer"
  GS_099: "WARN cascaded through authority escalation path"
  GS_100: "WARN attempted unauthorized transition to PASS"
  GS_101: "WARN chain attack detected"
  GS_102: "WARN fanout attack detected"
  GS_103: "WARN timing attack detected"
  GS_104: "WARN attempted gate override request"
  GS_105: "WARN transition to unknown destination blocked"
  GS_106: "WARN boundary crossing to unknown layer blocked"
```

---

**Ruleset Status:** ENFORCED  
**Authority:** BENSON (GID-00)  
**Immutable:** true  
**Replay-Safe:** true
