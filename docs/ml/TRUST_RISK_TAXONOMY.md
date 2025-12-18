# Trust-Weighted Risk Signal Taxonomy

> **Author**: 🟣 MAGGIE (GID-10) — Machine Learning & Applied AI Lead
> **PAC**: PAC-MAGGIE-RISK-TRUST-01
> **Status**: SPEC (Design Only — No Training, No Code)
> **Created**: 2025-12-17

---

## 1. BLUF

This taxonomy defines **three risk domains** that answer the commercial question:

> "How risky is this operator / integration / workflow right now?"

Each signal maps 1:1 to existing `GovernanceEventType` events. No synthetic signals. No black-box inference.

**Purpose**: Quantify operational risk for Trust Center, audit bundles, and procurement reviews.

---

## 2. Risk Domain Overview

| Domain | What It Measures | Commercial Value |
|--------|------------------|------------------|
| **Governance Integrity Risk** | Are agents behaving within bounds? | Confidence in access controls |
| **Operational Discipline Risk** | How often do things go wrong? | Operational maturity signal |
| **System Drift Risk** | Is the system staying stable? | Change management confidence |

Each domain produces a sub-score in [0.0, 1.0]. The composite **Trust Risk Index (TRI)** aggregates them.

---

## 3. Domain 1: Governance Integrity Risk

Measures whether agents are operating within their authorized boundaries.

### 3.1 Signal Mapping

| Signal ID | Signal Name | Source Event | Direction |
|-----------|-------------|--------------|-----------|
| GI-01 | Denial Rate | `DECISION_DENIED` / total decisions | ↑ risk |
| GI-02 | Scope Violation Count | `SCOPE_VIOLATION` | ↑ risk |
| GI-03 | Forbidden Verb Attempt Rate | `DECISION_DENIED` with reason `*_FORBIDDEN` | ↑ risk |
| GI-04 | Unknown Agent Attempt Rate | `DECISION_DENIED` with reason `UNKNOWN_AGENT` | ↑ risk |
| GI-05 | Tool Denial Rate | `TOOL_EXECUTION_DENIED` / total tool events | ↑ risk |

### 3.2 Signal Definitions

#### GI-01: Denial Rate

**What**: Fraction of governance decisions that result in denial.

**Source Events**:
- `DECISION_ALLOWED` (denominator)
- `DECISION_DENIED` (numerator)

**Interpretation**: High denial rate indicates agents frequently requesting unauthorized actions.

**Commercial Relevance**: Customers want to know: "Are your agents under control?"

---

#### GI-02: Scope Violation Count

**What**: Absolute count of scope boundary violations.

**Source Events**:
- `SCOPE_VIOLATION`

**Interpretation**: Any scope violation indicates a file or pattern that should not exist. Zero is expected.

**Commercial Relevance**: Auditors ask: "Can forbidden files appear in your repo?"

---

#### GI-03: Forbidden Verb Attempt Rate

**What**: Rate of attempts to use forbidden verbs (EXECUTE, BLOCK, APPROVE by unauthorized agents).

**Source Events**:
- `DECISION_DENIED` with `reason_code` in:
  - `EXECUTE_NOT_PERMITTED`
  - `BLOCK_NOT_PERMITTED`
  - `APPROVE_NOT_PERMITTED`
  - `DIGGY_EXECUTE_FORBIDDEN`
  - `DIGGY_BLOCK_FORBIDDEN`
  - `DIGGY_APPROVE_FORBIDDEN`

**Interpretation**: Forbidden verb attempts suggest either misconfiguration or probing behavior.

**Commercial Relevance**: Demonstrates that privilege boundaries are actively enforced.

---

#### GI-04: Unknown Agent Attempt Rate

**What**: Rate of requests from unrecognized agent identities.

**Source Events**:
- `DECISION_DENIED` with `reason_code` in:
  - `UNKNOWN_AGENT`
  - `MALFORMED_GID`

**Interpretation**: Unknown agent attempts could indicate forged identities or integration errors.

**Commercial Relevance**: "Do you detect unauthorized actors?"

---

#### GI-05: Tool Denial Rate

**What**: Fraction of tool execution requests that are denied.

**Source Events**:
- `TOOL_EXECUTION_ALLOWED` (denominator)
- `TOOL_EXECUTION_DENIED` (numerator)

**Interpretation**: Tools are the execution boundary. High tool denial rate indicates control pressure.

**Commercial Relevance**: "Are tools executing without proper authorization?"

---

## 4. Domain 2: Operational Discipline Risk

Measures how often the system requires correction or escalation.

### 4.1 Signal Mapping

| Signal ID | Signal Name | Source Event | Direction |
|-----------|-------------|--------------|-----------|
| OD-01 | DRCP Escalation Rate | `DRCP_TRIGGERED` / denials | ↑ risk |
| OD-02 | Diggi Correction Frequency | `DIGGI_CORRECTION_ISSUED` | Neutral (context) |
| OD-03 | Escalation to Human Rate | `DECISION_ESCALATED` / decisions | ↑ risk |
| OD-04 | Artifact Verification Failure Rate | `ARTIFACT_VERIFICATION_FAILED` / verifications | ↑ risk |
| OD-05 | Retry-After-Deny Rate | `DECISION_DENIED` with `RETRY_AFTER_DENY_FORBIDDEN` | ↑ risk |

### 4.2 Signal Definitions

#### OD-01: DRCP Escalation Rate

**What**: Fraction of denial events that trigger DRCP correction routing.

**Source Events**:
- `DRCP_TRIGGERED` (numerator)
- `DECISION_DENIED` (denominator)

**Interpretation**: High DRCP triggering indicates agents are hitting correction boundaries frequently.

**Commercial Relevance**: "How often do denied requests need remediation routing?"

---

#### OD-02: Diggi Correction Frequency

**What**: Count of correction plans issued by Diggi (bounded corrections).

**Source Events**:
- `DIGGI_CORRECTION_ISSUED`

**Interpretation**: Corrections indicate the system is actively providing remediation paths. High counts may indicate either good correction coverage or frequent boundary hits.

**Commercial Relevance**: "Do you have a correction mechanism?"

**Note**: This signal is **context-dependent** — corrections are not inherently bad.

---

#### OD-03: Escalation to Human Rate

**What**: Fraction of decisions requiring human escalation.

**Source Events**:
- `DECISION_ESCALATED` (numerator)
- Total decisions (denominator)

**Interpretation**: High escalation rate indicates automation cannot handle the workload confidently.

**Commercial Relevance**: "How much human intervention does your system require?"

---

#### OD-04: Artifact Verification Failure Rate

**What**: Fraction of artifact verifications that fail.

**Source Events**:
- `ARTIFACT_VERIFICATION_FAILED` (numerator)
- `ARTIFACT_VERIFIED` + `ARTIFACT_VERIFICATION_FAILED` (denominator)

**Interpretation**: Artifact failures indicate potential tampering, corruption, or build issues.

**Commercial Relevance**: "Can your system detect tampering?"

---

#### OD-05: Retry-After-Deny Rate

**What**: Rate of prohibited retry attempts after denial.

**Source Events**:
- `DECISION_DENIED` with `reason_code` = `RETRY_AFTER_DENY_FORBIDDEN`

**Interpretation**: Retry-after-deny violations indicate agents ignoring denial signals — a protocol violation.

**Commercial Relevance**: "Do your agents respect denial decisions?"

---

## 5. Domain 3: System Drift Risk

Measures stability of the governance configuration over time.

### 5.1 Signal Mapping

| Signal ID | Signal Name | Source Event | Direction |
|-----------|-------------|--------------|-----------|
| SD-01 | Governance Drift Detection Count | `GOVERNANCE_DRIFT_DETECTED` | ↑ risk |
| SD-02 | Boot Failure Rate | `GOVERNANCE_BOOT_FAILED` / boots | ↑ risk |
| SD-03 | Fingerprint Change Count | Governance fingerprint changes | ↑ risk |
| SD-04 | Freshness Violation Flag | Audit bundle age > threshold | ↑ risk |
| SD-05 | Gameday Coverage Gap | Missing gameday scenarios | ↑ risk |

### 5.2 Signal Definitions

#### SD-01: Governance Drift Detection Count

**What**: Count of detected governance configuration drift events.

**Source Events**:
- `GOVERNANCE_DRIFT_DETECTED`

**Interpretation**: Drift indicates runtime modification of governance files — always concerning.

**Commercial Relevance**: "Can configuration change without detection?"

---

#### SD-02: Boot Failure Rate

**What**: Fraction of boot attempts that fail governance checks.

**Source Events**:
- `GOVERNANCE_BOOT_PASSED` (denominator - success)
- `GOVERNANCE_BOOT_FAILED` (numerator)

**Interpretation**: Boot failures indicate the system refused to start due to governance issues.

**Commercial Relevance**: "Does your system fail safely?"

---

#### SD-03: Fingerprint Change Count

**What**: Number of governance fingerprint changes in the observation window.

**Source**: Governance fingerprint history (composite_hash changes)

**Interpretation**: Frequent fingerprint changes indicate governance configuration instability.

**Commercial Relevance**: "How stable is your governance configuration?"

---

#### SD-04: Freshness Violation Flag

**What**: Binary flag indicating whether audit bundle age exceeds acceptable threshold.

**Source**: Audit bundle timestamp vs. current time

**Threshold**: 24 hours (configurable)

**Interpretation**: Stale audit bundles cannot demonstrate current system state.

**Commercial Relevance**: "How current is your compliance evidence?"

---

#### SD-05: Gameday Coverage Gap

**What**: Fraction of defined threat scenarios without corresponding gameday tests.

**Source**: Comparison of THREAT_COVERAGE.md vs. gameday test inventory

**Interpretation**: Gaps in adversarial testing indicate untested failure modes.

**Commercial Relevance**: "Have you tested your controls?"

**Current State**: 109 gameday scenarios across 7 test files covering 6 threat classes.

---

## 6. Trust Weight Modifiers

Trust Weights penalize systems with weak evidence foundations.

### 6.1 Weight Definitions

| Weight ID | Weight Name | Source | Effect |
|-----------|-------------|--------|--------|
| TW-01 | Audit Bundle Freshness | Bundle age | Stale → ↑ risk |
| TW-02 | Gameday Coverage Completeness | Test coverage | Gaps → ↑ risk |
| TW-03 | Evidence Binding Success Rate | Artifact verification success | Low → ↑ risk |
| TW-04 | Observation Window Density | Events per hour | Sparse → ↓ confidence |

### 6.2 Weight Application

Trust Weights apply as **multipliers** to base risk scores:

```
effective_risk = base_risk × trust_weight_multiplier

Where:
    trust_weight_multiplier ∈ [1.0, 2.0]
    1.0 = full trust (fresh evidence, complete coverage)
    2.0 = maximum penalty (stale evidence, gaps)
```

**Key Insight**: A system with low base risk but stale evidence cannot appear "low risk."

---

## 7. Signal-to-Event Traceability Matrix

| Signal ID | GovernanceEventType | Field Used |
|-----------|---------------------|------------|
| GI-01 | `DECISION_ALLOWED`, `DECISION_DENIED` | event_type |
| GI-02 | `SCOPE_VIOLATION` | event_type |
| GI-03 | `DECISION_DENIED` | reason_code |
| GI-04 | `DECISION_DENIED` | reason_code |
| GI-05 | `TOOL_EXECUTION_ALLOWED`, `TOOL_EXECUTION_DENIED` | event_type |
| OD-01 | `DRCP_TRIGGERED`, `DECISION_DENIED` | event_type |
| OD-02 | `DIGGI_CORRECTION_ISSUED` | event_type |
| OD-03 | `DECISION_ESCALATED` | event_type |
| OD-04 | `ARTIFACT_VERIFIED`, `ARTIFACT_VERIFICATION_FAILED` | event_type |
| OD-05 | `DECISION_DENIED` | reason_code |
| SD-01 | `GOVERNANCE_DRIFT_DETECTED` | event_type |
| SD-02 | `GOVERNANCE_BOOT_PASSED`, `GOVERNANCE_BOOT_FAILED` | event_type |
| SD-03 | GovernanceFingerprint | composite_hash |
| SD-04 | AuditBundle | generated_at |
| SD-05 | GamedayTestInventory | coverage |

**All signals trace to verified, existing artifacts.**

---

## 8. Acceptance Criteria

- [x] Three risk domains defined
- [x] 15 signals mapped to existing events
- [x] All signals have directional interpretation
- [x] Trust weights defined for evidence quality
- [x] Traceability matrix complete
- [x] No synthetic or inferred signals
- [x] Commercial relevance documented per signal

---

## 9. References

- [core/governance/events.py](../../core/governance/events.py) — GovernanceEventType enum
- [core/governance/acm_evaluator.py](../../core/governance/acm_evaluator.py) — DenialReason enum
- [core/governance/governance_fingerprint.py](../../core/governance/governance_fingerprint.py) — Fingerprint schema
- [docs/trust/THREAT_COVERAGE.md](../trust/THREAT_COVERAGE.md) — Threat coverage map
- [docs/governance/AUDIT_BUNDLE_SCHEMA.md](../governance/AUDIT_BUNDLE_SCHEMA.md) — Audit bundle format
