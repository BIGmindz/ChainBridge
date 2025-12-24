# GOVERNANCE TO ECONOMIC EFFECTS

**Document ID:** GOVERNANCE_TO_ECONOMIC_EFFECTS  
**Authority:** PAC-ALEX-P31-GOVERNANCE-TO-ECONOMIC-ENFORCEMENT-MAPPING-01  
**Agent:** ALEX (GID-08) | ⚪ WHITE  
**Status:** CANONICAL  
**Version:** 1.0.0  
**Date:** 2025-12-24  

---

## 1. PURPOSE

This document defines the **authoritative mapping** between ChainBridge governance signals and their economic effects on settlement operations.

**Core Principle:**
> If a governance signal has no economic effect, it is not governance—it is advisory theater.

Every governance evaluation must resolve to a deterministic economic outcome.

---

## 2. SIGNAL TAXONOMY

### 2.1 Signal Classes

| Class | Severity | Description |
|-------|----------|-------------|
| **FAIL** | CRITICAL | Fundamental violation; system integrity at risk |
| **FAIL** | STRUCTURAL | Schema or contract violation; correctable |
| **WARN** | DRIFT | Deviation from baseline; within tolerance |
| **WARN** | LATENCY | Timing constraint exceeded; may self-resolve |
| **PASS** | OK | All constraints satisfied |
| **SKIP** | LEGACY | Not evaluated; technical debt marker |

### 2.2 Signal Code Prefixes

| Prefix | Domain | Authority |
|--------|--------|-----------|
| `PAG_` | Protocol Action Governance | BENSON (GID-00) |
| `RG_` | Registry Governance | System |
| `BSRG_` | Benson System Registry Governance | BENSON (GID-00) |
| `GS_` | Gold Standard Compliance | System |
| `WRP_` | Wrapper/Legacy Integration | System |
| `PDO_` | Provable Decision Object | Trust Layer |

---

## 3. SETTLEMENT CONTROL STATES

Every governance evaluation resolves to exactly one settlement state:

```yaml
SETTLEMENT_STATES:
  BLOCKED:
    description: "Settlement cannot proceed"
    reversible: false
    requires: "Governance resolution"
    
  DELAYED:
    description: "Settlement paused pending condition"
    reversible: true
    requires: "Condition satisfaction or timeout"
    
  CONDITIONAL:
    description: "Settlement proceeds with constraints"
    reversible: false
    requires: "Constraint acknowledgment"
    
  PROCEED:
    description: "Settlement authorized"
    reversible: false
    requires: "None"
    
  OVERRIDDEN:
    description: "Governance bypassed with authority"
    reversible: false
    requires: "Override justification + authority"
```

### 3.1 State Transitions

```
┌─────────────────────────────────────────────────────────────┐
│                    GOVERNANCE EVALUATION                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │   Signal Classification  │
              └─────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
   ┌─────────┐        ┌─────────┐        ┌─────────┐
   │  FAIL   │        │  WARN   │        │  PASS   │
   └────┬────┘        └────┬────┘        └────┬────┘
        │                   │                   │
        ▼                   ▼                   ▼
   ┌─────────┐        ┌─────────┐        ┌─────────┐
   │ BLOCKED │        │ DELAYED │        │ PROCEED │
   │   or    │        │   or    │        └─────────┘
   │CONDITIONAL│      │CONDITIONAL│
   └────┬────┘        └────┬────┘
        │                   │
        ▼                   ▼
   ┌─────────────────────────────┐
   │  OVERRIDE EVALUATION        │
   │  (if authority present)     │
   └──────────────┬──────────────┘
                  │
                  ▼
            ┌───────────┐
            │ OVERRIDDEN│
            └───────────┘
```

---

## 4. SIGNAL → ECONOMIC EFFECT MAPPING

### 4.1 FAIL Signals (Critical)

| Code | Description | Economic Effect | Settlement State |
|------|-------------|-----------------|------------------|
| `PAG_001` | Missing PDO | Hard block | **BLOCKED** |
| `PAG_002` | Invalid PDO hash | Hard block | **BLOCKED** |
| `PAG_003` | PDO outcome DENIED | Hard block | **BLOCKED** |
| `RG_001` | Agent not registered | Hard block | **BLOCKED** |
| `RG_002` | Agent suspended | Hard block | **BLOCKED** |
| `RG_003` | Authority mismatch | Hard block | **BLOCKED** |
| `BSRG_001` | Benson override required | Escalation block | **BLOCKED** |
| `PDO_001` | Missing required field | Hard block | **BLOCKED** |
| `PDO_002` | Hash integrity failure | Hard block | **BLOCKED** |

**Policy:** FAIL (Critical) signals **always** result in BLOCKED state. No automatic recovery.

### 4.2 FAIL Signals (Structural)

| Code | Description | Economic Effect | Settlement State |
|------|-------------|-----------------|------------------|
| `GS_010` | PAC schema violation | Block until corrected | **BLOCKED** |
| `GS_011` | Missing closure | Block until corrected | **BLOCKED** |
| `GS_012` | Invalid agent color | Block until corrected | **BLOCKED** |
| `GS_013` | Execution lane mismatch | Block until corrected | **BLOCKED** |
| `WRP_001` | Wrapper contract invalid | Block until corrected | **BLOCKED** |

**Policy:** FAIL (Structural) signals result in BLOCKED state but are correctable without authority escalation.

### 4.3 WARN Signals (Drift)

| Code | Description | Economic Effect | Settlement State |
|------|-------------|-----------------|------------------|
| `GS_021` | Minor schema deviation | Allow, flag audit | **CONDITIONAL** |
| `GS_022` | Non-canonical naming | Allow, flag audit | **CONDITIONAL** |
| `GS_023` | Missing optional field | Allow, flag audit | **PROCEED** |
| `GS_024` | Deprecated pattern used | Allow, flag audit | **CONDITIONAL** |

**Policy:** WARN (Drift) signals allow settlement but require audit flag. Accumulated drift may trigger review.

### 4.4 WARN Signals (Latency)

| Code | Description | Economic Effect | Settlement State |
|------|-------------|-----------------|------------------|
| `GS_031` | Evaluation timeout | Delay, retry | **DELAYED** |
| `GS_032` | External service slow | Delay, notify | **DELAYED** |
| `GS_033` | Chain confirmation pending | Delay, wait | **DELAYED** |
| `GS_034` | Rate limit approached | Delay, throttle | **DELAYED** |

**Policy:** WARN (Latency) signals result in DELAYED state with automatic retry. Max delay: 300 seconds.

### 4.5 PASS Signals

| Code | Description | Economic Effect | Settlement State |
|------|-------------|-----------------|------------------|
| `GS_OK` | All checks passed | Proceed normally | **PROCEED** |
| `PAG_OK` | PDO validated | Proceed normally | **PROCEED** |
| `RG_OK` | Agent authorized | Proceed normally | **PROCEED** |

**Policy:** PASS signals result in PROCEED state. No additional action required.

### 4.6 SKIP Signals

| Code | Description | Economic Effect | Settlement State |
|------|-------------|-----------------|------------------|
| `WRP_004` | Legacy system bypass | Allow, mark debt | **CONDITIONAL** |
| `GS_SKIP` | Check not applicable | Allow, log reason | **PROCEED** |
| `LEGACY_001` | Pre-governance artifact | Allow, mark migration | **CONDITIONAL** |

**Policy:** SKIP signals allow settlement but accumulate technical debt. Debt threshold triggers mandatory review.

---

## 5. OVERRIDE POLICY

### 5.1 Override Requirements

```yaml
OVERRIDE_REQUIREMENTS:
  authority:
    primary: "BENSON (GID-00)"
    delegated:
      - "ALEX (GID-08) for orchestration scope"
      - "RUBY (GID-03) for risk scope"
    
  justification:
    required: true
    min_length: 50 characters
    must_reference: "specific signal code"
    
  scope:
    types:
      - SHIPMENT: "single shipment ID"
      - INVOICE: "single invoice ID"
      - TIME_WINDOW: "bounded time range"
      - TRANSACTION: "single transaction hash"
    max_duration: "24 hours"
    
  expiration:
    mandatory: true
    auto_revert: true
    notification: "1 hour before expiry"
    
  audit_log:
    immutable: true
    includes:
      - override_id
      - authority
      - justification
      - scope
      - timestamp
      - expiration
      - affected_signals
```

### 5.2 Override Constraints

| Constraint | Requirement |
|------------|-------------|
| **No Blanket Overrides** | Every override must specify exact scope |
| **No Permanent Overrides** | Maximum duration: 24 hours |
| **No Silent Overrides** | All overrides logged and notified |
| **No Cascading Overrides** | Override applies to specified scope only |
| **No Self-Override** | Agent cannot override its own signals |

### 5.3 Override Audit Record

```yaml
OVERRIDE_RECORD:
  override_id: "OVR-2025-12-24-001"
  authority: "BENSON (GID-00)"
  timestamp: "2025-12-24T10:30:00Z"
  expiration: "2025-12-24T18:30:00Z"
  
  affected_signal:
    code: "GS_010"
    original_state: "BLOCKED"
    override_state: "PROCEED"
    
  scope:
    type: "INVOICE"
    identifier: "INV-2025-001234"
    
  justification: |
    Schema violation is cosmetic (missing optional metadata field).
    Invoice contents verified manually. Settlement required before
    EOD for contractual obligation. Correction scheduled for next cycle.
    
  audit_hash: "sha256:a1b2c3d4..."
```

---

## 6. SMART CONTRACT INTERFACE

### 6.1 Contract Input Specification

Smart contracts receive **outcomes only**, never governance logic.

```yaml
CONTRACT_INPUT:
  settlement_state:
    type: ENUM
    values: [BLOCKED, DELAYED, CONDITIONAL, PROCEED, OVERRIDDEN]
    
  decision_hash:
    type: SHA256
    description: "Hash of full governance evaluation"
    
  timestamp:
    type: ISO8601
    description: "Time of governance decision"
    
  # OPTIONAL: For conditional settlements
  conditions:
    type: ARRAY
    items:
      condition_id: STRING
      acknowledged: BOOLEAN
```

### 6.2 Contract Behavior Rules

| Rule | Description |
|------|-------------|
| **No Governance Evaluation** | Contracts never interpret signals |
| **State Enforcement Only** | Contracts enforce the provided state |
| **Hash Verification** | Contracts may verify decision hash |
| **No Override Logic** | Override resolution happens off-chain |
| **Fail-Closed** | Unknown state = BLOCKED |

### 6.3 Contract Interface Example

```solidity
// GOVERNANCE OUTCOME STRUCT
struct GovernanceOutcome {
    SettlementState state;      // ENUM: BLOCKED, DELAYED, CONDITIONAL, PROCEED, OVERRIDDEN
    bytes32 decisionHash;       // SHA256 of off-chain evaluation
    uint256 timestamp;          // Unix timestamp of decision
    bool hasConditions;         // Whether conditions apply
}

// SETTLEMENT FUNCTION
function executeSettlement(
    GovernanceOutcome calldata outcome,
    bytes calldata settlementData
) external {
    // Contracts DO NOT evaluate governance
    // Contracts ONLY enforce the provided state
    
    require(
        outcome.state == SettlementState.PROCEED ||
        outcome.state == SettlementState.OVERRIDDEN ||
        outcome.state == SettlementState.CONDITIONAL,
        "Settlement blocked by governance"
    );
    
    // If conditional, verify conditions acknowledged
    if (outcome.state == SettlementState.CONDITIONAL) {
        require(conditionsAcknowledged[outcome.decisionHash], "Conditions not acknowledged");
    }
    
    // Proceed with settlement
    _executeSettlement(settlementData);
    
    // Emit audit event
    emit SettlementExecuted(outcome.decisionHash, outcome.state, block.timestamp);
}
```

### 6.4 Off-Chain / On-Chain Boundary

```
┌────────────────────────────────────────────────────────────────┐
│                      OFF-CHAIN (ChainBridge)                   │
│                                                                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │ Governance   │ →  │ Signal       │ →  │ Settlement   │     │
│  │ Evaluation   │    │ Resolution   │    │ State        │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│                                                │                │
│                                                ▼                │
│                                    ┌──────────────────┐        │
│                                    │ Decision Hash    │        │
│                                    │ + State + Time   │        │
│                                    └────────┬─────────┘        │
│                                             │                  │
└─────────────────────────────────────────────┼──────────────────┘
                                              │
══════════════════════════════════════════════╪══════════════════
                      BOUNDARY                │
══════════════════════════════════════════════╪══════════════════
                                              │
┌─────────────────────────────────────────────┼──────────────────┐
│                      ON-CHAIN (Contract)    │                  │
│                                             ▼                  │
│                                    ┌──────────────────┐        │
│                                    │ State Enforcement│        │
│                                    │ (No Logic)       │        │
│                                    └──────────────────┘        │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 7. AUDIT EXAMPLES

### 7.1 Example: Clean Settlement (PROCEED)

```yaml
AUDIT_RECORD:
  transaction_id: "TXN-2025-12-24-001"
  timestamp: "2025-12-24T14:30:00Z"
  
  governance_evaluation:
    signals:
      - code: "PAG_OK"
        class: "PASS"
        message: "PDO validated"
      - code: "RG_OK"
        class: "PASS"
        message: "Agent authorized"
      - code: "GS_OK"
        class: "PASS"
        message: "All checks passed"
        
  resolution:
    settlement_state: "PROCEED"
    decision_hash: "sha256:e3b0c44298fc..."
    
  outcome:
    settlement_executed: true
    execution_timestamp: "2025-12-24T14:30:01Z"
```

### 7.2 Example: Blocked Settlement (FAIL)

```yaml
AUDIT_RECORD:
  transaction_id: "TXN-2025-12-24-002"
  timestamp: "2025-12-24T15:00:00Z"
  
  governance_evaluation:
    signals:
      - code: "PAG_001"
        class: "FAIL"
        severity: "CRITICAL"
        message: "Missing PDO"
        
  resolution:
    settlement_state: "BLOCKED"
    decision_hash: "sha256:d4e5f6a7b8c9..."
    blocking_signal: "PAG_001"
    
  outcome:
    settlement_executed: false
    reason: "No valid PDO provided"
    required_action: "Submit valid PDO before retry"
```

### 7.3 Example: Conditional Settlement (WARN)

```yaml
AUDIT_RECORD:
  transaction_id: "TXN-2025-12-24-003"
  timestamp: "2025-12-24T16:00:00Z"
  
  governance_evaluation:
    signals:
      - code: "PAG_OK"
        class: "PASS"
        message: "PDO validated"
      - code: "GS_021"
        class: "WARN"
        severity: "DRIFT"
        message: "Minor schema deviation detected"
        
  resolution:
    settlement_state: "CONDITIONAL"
    decision_hash: "sha256:a1b2c3d4e5f6..."
    conditions:
      - id: "COND-001"
        description: "Schema deviation acknowledged"
        acknowledged_by: "operator@example.com"
        acknowledged_at: "2025-12-24T16:01:00Z"
        
  outcome:
    settlement_executed: true
    execution_timestamp: "2025-12-24T16:01:05Z"
    audit_flags:
      - "GS_021: Schema deviation - scheduled for correction"
```

### 7.4 Example: Override Settlement

```yaml
AUDIT_RECORD:
  transaction_id: "TXN-2025-12-24-004"
  timestamp: "2025-12-24T17:00:00Z"
  
  governance_evaluation:
    signals:
      - code: "GS_010"
        class: "FAIL"
        severity: "STRUCTURAL"
        message: "PAC schema violation"
        
  initial_resolution:
    settlement_state: "BLOCKED"
    blocking_signal: "GS_010"
    
  override_applied:
    override_id: "OVR-2025-12-24-002"
    authority: "BENSON (GID-00)"
    justification: "Schema violation is in metadata only. Core data verified. EOD settlement required."
    scope:
      type: "TRANSACTION"
      identifier: "TXN-2025-12-24-004"
    expiration: "2025-12-24T23:59:59Z"
    
  final_resolution:
    settlement_state: "OVERRIDDEN"
    decision_hash: "sha256:f6e5d4c3b2a1..."
    
  outcome:
    settlement_executed: true
    execution_timestamp: "2025-12-24T17:00:30Z"
    audit_flags:
      - "OVERRIDE_APPLIED: GS_010 bypassed by BENSON authority"
      - "OVERRIDE_EXPIRES: 2025-12-24T23:59:59Z"
```

---

## 8. FAIL-CLOSED DEFAULT

### 8.1 Ambiguity Resolution

When governance evaluation produces ambiguous results:

| Condition | Resolution |
|-----------|------------|
| Unknown signal code | **BLOCKED** |
| Signal without mapping | **BLOCKED** |
| Evaluation timeout | **DELAYED** → **BLOCKED** after max delay |
| Contract receives invalid state | **BLOCKED** |
| Missing decision hash | **BLOCKED** |

### 8.2 Rationale

> **"When in doubt, block."**

Settlement is irreversible. Governance ambiguity must never result in unauthorized settlement. The cost of a false block is delay. The cost of a false allow is liability.

---

## 9. INTEGRATION POINTS

### 9.1 ChainPay Integration

```yaml
CHAINPAY_INTEGRATION:
  evaluation_point: "pre-settlement"
  
  flow:
    1. ChainPay receives settlement request
    2. ChainPay calls governance evaluation API
    3. Governance returns settlement_state + decision_hash
    4. ChainPay enforces state:
       - PROCEED: execute settlement
       - BLOCKED: reject with reason
       - DELAYED: queue for retry
       - CONDITIONAL: prompt for acknowledgment
       - OVERRIDDEN: execute with audit flag
```

### 9.2 Off-Chain Settlement Rails

```yaml
OFFCHAIN_INTEGRATION:
  evaluation_point: "pre-execution"
  
  enforcement:
    - Bank transfer: governance gate before initiation
    - Wire transfer: governance gate before submission
    - ACH batch: governance gate per item
    
  audit:
    - Every settlement includes decision_hash
    - Hash anchored to immutable log
    - Reconciliation verifies hash integrity
```

---

## 10. DOCUMENT GOVERNANCE

| Attribute | Value |
|-----------|-------|
| **Owner** | ALEX (GID-08) |
| **Authority** | BENSON (GID-00) |
| **Review Cycle** | Quarterly |
| **Change Process** | PAC required |
| **Immutability** | Signal mappings are immutable once published |

---

## 11. CHANGELOG

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0.0 | 2025-12-24 | PAX (GID-05) | Initial canonical specification |

---

**END OF DOCUMENT**

**Authority:** PAC-PAX-P31-GOVERNANCE-TO-ECONOMIC-ENFORCEMENT-MAPPING-01  
**Status:** CANONICAL  
**Hash:** `sha256:` _(computed at commit)_
