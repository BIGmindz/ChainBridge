# Risk Signal Taxonomy for Governance Decisions

> **Author**: 🟣 MAGGIE (GID-10) — Machine Learning & Applied AI Lead
> **PAC**: PAC-MAGGIE-RISK-SIGNALS-01
> **Status**: SPEC (Design Only — No Training)
> **Created**: 2025-12-17

---

## 1. BLUF

This document defines a **taxonomy of interpretable risk signals** that can be derived from existing governance events. Each signal is:

- ✅ **Explainable**: Clear causal relationship to inputs
- ✅ **Auditable**: Reproducible from event logs
- ✅ **Read-only**: Cannot influence governance decisions directly
- ✅ **Fail-safe**: Degrades to "no signal" on missing data

These signals are **advisory only**. Governance (ACM, DRCP, Diggi) retains absolute authority.

---

## 2. Signal Categories

### 2.1. Agent Trust Signals

Signals derived from historical agent behavior patterns.

| Signal ID | Signal Name | Description | Directionality |
|-----------|-------------|-------------|----------------|
| `ATS-01` | **Denial Rate (Rolling)** | Fraction of agent intents denied in last N decisions | ↑ denial_rate → ↑ risk |
| `ATS-02` | **DRCP Routing Frequency** | How often agent triggers DRCP correction cycles | ↑ drcp_triggers → ↑ risk |
| `ATS-03` | **Escalation Frequency** | Rate of escalations to human review | Neutral (context-dependent) |
| `ATS-04` | **Scope Violation History** | Count of `SCOPE_VIOLATION` events in window | ↑ violations → ↑ risk |
| `ATS-05` | **Correction Acceptance Rate** | Fraction of Diggi corrections accepted vs rejected | ↑ acceptance → ↓ risk |

#### ATS-01: Denial Rate (Rolling)

**Inputs** (from `GovernanceEventType`):
- `DECISION_DENIED` events
- `DECISION_ALLOWED` events

**Formula**:
```
denial_rate(agent, window) = count(DECISION_DENIED) / (count(DECISION_DENIED) + count(DECISION_ALLOWED))
```

**Interpretability Note**: A high denial rate suggests the agent is frequently requesting actions outside its permitted scope. This may indicate misconfiguration, scope creep, or adversarial probing.

**Failure Mode**: If no events exist in window → return `null` (no signal). Do NOT impute or extrapolate.

---

### 2.2. Tool Misuse Signals

Signals derived from tool execution patterns.

| Signal ID | Signal Name | Description | Directionality |
|-----------|-------------|-------------|----------------|
| `TMS-01` | **Forbidden Tool Attempts** | Count of denied tool executions | ↑ attempts → ↑ risk |
| `TMS-02` | **Tool Diversity (Entropy)** | Shannon entropy of tool usage distribution | ↓ entropy → ↑ risk (narrow focus) |
| `TMS-03` | **Execute-After-Deny Pattern** | Detection of retry attempts post-denial | Any occurrence → ↑ risk |
| `TMS-04` | **High-Risk Tool Concentration** | Fraction of requests targeting sensitive tools | ↑ concentration → ↑ risk |

#### TMS-01: Forbidden Tool Attempts

**Inputs** (from `GovernanceEventType`):
- `TOOL_EXECUTION_DENIED` events

**Formula**:
```
forbidden_attempts(agent, window) = count(TOOL_EXECUTION_DENIED)
```

**Interpretability Note**: Repeated attempts to execute forbidden tools suggest either misconfiguration or intentional boundary testing.

**Failure Mode**: If no tool events exist → return `0` (known safe baseline).

#### TMS-03: Execute-After-Deny Pattern

**Inputs**:
- `DECISION_DENIED` events
- Subsequent `TOOL_EXECUTION_ALLOWED` or `TOOL_EXECUTION_DENIED` within T seconds

**Detection Logic**:
```
For each DECISION_DENIED(agent, verb, target):
    If exists(TOOL_EXECUTION_*) with same (agent, target) within T seconds:
        → Pattern detected
```

**Interpretability Note**: DRCP explicitly forbids retry-after-deny. Detection of this pattern indicates protocol violation.

**Failure Mode**: Requires timestamp ordering. If timestamps unreliable → disable signal.

---

### 2.3. Policy Boundary Signals

Signals measuring proximity to governance limits.

| Signal ID | Signal Name | Description | Directionality |
|-----------|-------------|-------------|----------------|
| `PBS-01` | **Scope Utilization Ratio** | Fraction of permitted scope currently accessed | ↑ utilization → ↑ risk |
| `PBS-02` | **Boundary Probe Frequency** | Rate of requests at scope edges | ↑ probes → ↑ risk |
| `PBS-03` | **ACM Evaluation Latency Trend** | Increasing latency may indicate complex rule matching | ↑ latency → ⚠️ warning |
| `PBS-04` | **Permission Request Concentration** | Clustering of requests around specific verbs | Context-dependent |

#### PBS-01: Scope Utilization Ratio

**Inputs**:
- Agent's permitted scope (from ACM)
- Set of unique targets accessed in window

**Formula**:
```
scope_utilization(agent, window) = |accessed_targets| / |permitted_targets|
```

**Interpretability Note**: An agent using 95% of its permitted scope may be operating at capacity limits. Useful for capacity planning, not directly for risk.

**Failure Mode**: Requires ACM scope definition. If ACM unavailable → return `null`.

---

### 2.4. Artifact Integrity Signals

Signals derived from artifact verification events.

| Signal ID | Signal Name | Description | Directionality |
|-----------|-------------|-------------|----------------|
| `AIS-01` | **Verification Failure Rate** | Fraction of artifacts failing verification | ↑ failures → ↑ risk |
| `AIS-02` | **Hash Mismatch Frequency** | Count of `ARTIFACT_VERIFICATION_FAILED` | ↑ mismatches → ↑ risk |
| `AIS-03` | **Verification Coverage** | Fraction of actions with artifact verification | ↓ coverage → ↑ risk |
| `AIS-04` | **Artifact Staleness** | Time since last successful verification | ↑ staleness → ↑ risk |

#### AIS-01: Verification Failure Rate

**Inputs** (from `GovernanceEventType`):
- `ARTIFACT_VERIFIED` events
- `ARTIFACT_VERIFICATION_FAILED` events

**Formula**:
```
failure_rate(window) = count(ARTIFACT_VERIFICATION_FAILED) / count(ARTIFACT_VERIFIED + ARTIFACT_VERIFICATION_FAILED)
```

**Interpretability Note**: Artifact integrity failures indicate either data corruption, tampering, or system malfunction.

**Failure Mode**: If no verification events → return `null`. Do NOT assume verification passed.

---

### 2.5. Governance Drift Signals

Signals indicating deviation from expected governance behavior.

| Signal ID | Signal Name | Description | Directionality |
|-----------|-------------|-------------|----------------|
| `GDS-01` | **Boot Check Failure Trend** | Increasing `GOVERNANCE_BOOT_FAILED` events | ↑ failures → ↑ risk |
| `GDS-02` | **Drift Detection Count** | `GOVERNANCE_DRIFT_DETECTED` events in window | ↑ drift → ↑ risk |
| `GDS-03` | **ACM Version Staleness** | Age of current ACM version | ↑ age → ⚠️ warning |
| `GDS-04` | **Checklist Version Skew** | Mismatch between agent and system checklist versions | Skew detected → ↑ risk |

#### GDS-02: Drift Detection Count

**Inputs** (from `GovernanceEventType`):
- `GOVERNANCE_DRIFT_DETECTED` events

**Formula**:
```
drift_count(window) = count(GOVERNANCE_DRIFT_DETECTED)
```

**Interpretability Note**: Governance drift indicates system state divergence from expected configuration. Requires immediate investigation.

**Failure Mode**: If drift detection disabled → return `null`.

---

### 2.6. Correction Pattern Signals

Signals derived from Diggi correction cycles.

| Signal ID | Signal Name | Description | Directionality |
|-----------|-------------|-------------|----------------|
| `CPS-01` | **Correction Cycle Time** | Mean time from denial to correction acceptance | ↑ time → ⚠️ warning |
| `CPS-02` | **No-Valid-Correction Rate** | Fraction of denials with no correction available | ↑ rate → ↑ risk |
| `CPS-03` | **Human Escalation Rate** | Fraction of corrections requiring human review | Neutral (context-dependent) |
| `CPS-04` | **Repeated Denial Pattern** | Same (agent, verb, target) denied multiple times | Any occurrence → ↑ risk |

#### CPS-02: No-Valid-Correction Rate

**Inputs**:
- `DRCP_TRIGGERED` events
- `DIGGI_CORRECTION_ISSUED` events
- Events with reason `DIGGI_NO_VALID_CORRECTION`

**Formula**:
```
no_correction_rate(window) = count(DIGGI_NO_VALID_CORRECTION) / count(DRCP_TRIGGERED)
```

**Interpretability Note**: A high no-correction rate indicates agents are requesting actions that have no valid alternatives, suggesting fundamental misalignment between agent goals and system permissions.

**Failure Mode**: If DRCP not triggered in window → return `null`.

---

## 3. Composite Risk Signals

Composite signals aggregate multiple atomic signals into higher-level risk indicators.

| Signal ID | Signal Name | Components | Aggregation |
|-----------|-------------|------------|-------------|
| `CRS-01` | **Agent Risk Score** | ATS-01, ATS-02, ATS-04, TMS-01 | Weighted linear combination |
| `CRS-02` | **System Integrity Score** | AIS-01, AIS-02, GDS-01, GDS-02 | Min (conservative) |
| `CRS-03` | **Operational Health Score** | PBS-03, CPS-01, GDS-03 | Weighted average |

### CRS-01: Agent Risk Score

**Formula** (Example — coefficients require calibration):
```
agent_risk(agent, window) =
    w1 * normalize(ATS-01) +
    w2 * normalize(ATS-02) +
    w3 * normalize(ATS-04) +
    w4 * normalize(TMS-01)

Where:
    w1 = 0.35  (denial rate weight)
    w2 = 0.25  (DRCP frequency weight)
    w3 = 0.25  (scope violation weight)
    w4 = 0.15  (forbidden tool weight)
```

**Interpretability**: Each component maps to a specific governance concern. Weights reflect relative importance (tunable by governance policy, not ML).

**Monotonicity Constraints**:
- ↑ ATS-01 → ↑ agent_risk (required)
- ↑ ATS-02 → ↑ agent_risk (required)
- ↑ ATS-04 → ↑ agent_risk (required)
- ↑ TMS-01 → ↑ agent_risk (required)

---

## 4. Signal Output Schema

Every signal must conform to this output schema:

```json
{
  "signal_id": "ATS-01",
  "signal_name": "Denial Rate (Rolling)",
  "agent_gid": "GID-07",
  "window_start": "2025-12-17T00:00:00Z",
  "window_end": "2025-12-17T23:59:59Z",
  "value": 0.15,
  "value_type": "ratio",
  "confidence": 0.92,
  "confidence_note": "Based on 47 events in window",
  "interpretation": "Agent GID-07 has 15% denial rate in the last 24 hours",
  "directionality": "higher_is_riskier",
  "inputs_used": ["DECISION_DENIED", "DECISION_ALLOWED"],
  "input_count": 47,
  "failure_mode": null,
  "computed_at": "2025-12-17T15:30:00Z"
}
```

---

## 5. Signal Confidence Calculation

Signal confidence reflects data quality and sufficiency:

```python
def calculate_confidence(input_count: int, window_hours: int) -> float:
    """
    Calculate signal confidence based on data density.

    - Minimum 10 events for any confidence
    - Scales linearly up to 50 events
    - Penalizes sparse data over long windows
    """
    if input_count < 10:
        return 0.0  # Insufficient data

    data_density = input_count / window_hours
    base_confidence = min(1.0, input_count / 50)
    density_penalty = min(1.0, data_density / 2.0)

    return base_confidence * density_penalty
```

---

## 6. Failure Modes Summary

| Failure Mode | Trigger Condition | Signal Behavior |
|--------------|-------------------|-----------------|
| `NO_DATA` | Zero events in window | Return `null` |
| `INSUFFICIENT_DATA` | <10 events in window | Return `null` with warning |
| `TIMESTAMP_UNRELIABLE` | Clock skew detected | Disable time-sensitive signals |
| `ACM_UNAVAILABLE` | ACM loader fails | Disable scope-dependent signals |
| `SINK_UNAVAILABLE` | Event sink not writable | Log locally, continue |

**Critical Invariant**: A failed signal MUST NOT be interpreted as "low risk". Absence of signal ≠ presence of safety.

---

## 7. Governance Integration Points

These signals integrate with governance at the following points:

| Integration Point | Governance Component | Signal Role |
|-------------------|---------------------|-------------|
| Pre-evaluation annotation | ACM Evaluator | Read-only context |
| Post-denial enrichment | DRCP | Audit trail annotation |
| Dashboard display | ChainBoard OCC | Human decision support |
| Proofpack attachment | Artifact system | Audit evidence |
| Alert triggering | Monitoring | Threshold-based alerts |

**CRITICAL**: Signals NEVER participate in ALLOW/DENY decisions. They annotate, warn, and prioritize — nothing more.

---

## 8. Future Signals (Pending)

The following signals are identified but require additional infrastructure:

| Signal ID | Signal Name | Blocker |
|-----------|-------------|---------|
| `FUT-01` | Cross-Agent Collusion Score | Requires agent relationship graph |
| `FUT-02` | Temporal Anomaly Detection | Requires baseline establishment |
| `FUT-03` | Resource Consumption Outlier | Requires resource metering |
| `FUT-04` | External Context Risk | Requires external data feeds |

---

## 9. Acceptance Criteria

- [ ] All signals trace to existing `GovernanceEventType` events
- [ ] All signals have documented failure modes
- [ ] All signals are read-only (no governance authority)
- [ ] All signals degrade safely to `null` on insufficient data
- [ ] All signals have monotonicity documented (where applicable)
- [ ] Output schema is consistent across all signals
- [ ] Confidence calculation is deterministic and reproducible

---

## 10. References

- [core/governance/events.py](../../core/governance/events.py) — Event schema
- [core/governance/telemetry.py](../../core/governance/telemetry.py) — Telemetry integration
- [core/governance/acm_evaluator.py](../../core/governance/acm_evaluator.py) — ACM evaluation
- [core/governance/drcp.py](../../core/governance/drcp.py) — DRCP protocol
- [docs/governance/RETENTION_POLICY.md](../governance/RETENTION_POLICY.md) — Event retention
