# Governance-to-Economic Stress Test Matrix

> **PAC:** PAC-PAX-P32-GOVERNANCE-ECONOMIC-STRESS-TEST-AND-FAILURE-MAPPING-01
> **Owner:** Pax (GID-05)
> **Authority:** BENSON (GID-00)
> **Mode:** FAIL_CLOSED
> **Status:** LOCKED

---

## 1. PURPOSE

This document defines adversarial stress tests for the governance-to-economic enforcement boundary. Every governance signal sequence must resolve to exactly one settlement outcome. No ambiguous paths are permitted.

**Axiom:** If governance survives adversarial economics, it will survive production.

---

## 2. SETTLEMENT STATE MODEL (CANONICAL)

### 2.1 Valid Settlement States

| State | Description | Terminal |
|-------|-------------|----------|
| `PENDING` | Settlement initiated, awaiting governance signal | No |
| `APPROVED` | Governance passed, payout authorized | No |
| `DELAYED` | Governance flagged risk, payout held | No |
| `RELEASED` | Funds disbursed to payee | Yes |
| `BLOCKED` | Governance denied, no payout | Yes |
| `DISPUTED` | Claim filed, settlement frozen | No |
| `ESCALATED` | Human review required | No |
| `SETTLED` | Final state, all economic actions complete | Yes |

### 2.2 State Transition Constraints

```
PENDING → APPROVED | DELAYED | BLOCKED | ESCALATED
APPROVED → RELEASED | DISPUTED | BLOCKED
DELAYED → APPROVED | BLOCKED | ESCALATED
RELEASED → SETTLED | DISPUTED
BLOCKED → (terminal, no outbound transitions)
DISPUTED → RELEASED | BLOCKED | ESCALATED
ESCALATED → APPROVED | BLOCKED
SETTLED → (terminal, no outbound transitions)
```

**Invariant:** No state may transition to itself. No state may transition backwards except via ESCALATED.

---

## 3. GOVERNANCE SIGNAL MODEL

### 3.1 Governance Signals

| Signal | Source | Economic Effect |
|--------|--------|-----------------|
| `PASS` | ALEX (GID-08) | Allow settlement to proceed |
| `WARN` | ALEX (GID-08) | Flag for review, do not block |
| `FAIL` | ALEX (GID-08) | Block settlement |
| `OVERRIDE` | BENSON (GID-00) | Force state change (time-bound) |
| `ESCALATE` | Any Agent | Route to human authority |

### 3.2 Signal Authority Matrix

| Signal | Issuing Authority | Can Override |
|--------|-------------------|--------------|
| `PASS` | ALEX | BENSON only |
| `WARN` | ALEX | ALEX, BENSON |
| `FAIL` | ALEX | BENSON only |
| `OVERRIDE` | BENSON | Human CEO only |
| `ESCALATE` | Any | BENSON |

---

## 4. WORST-CASE GOVERNANCE SEQUENCES

### 4.1 Signal Oscillation Attacks

#### ST-001: PASS → FAIL → PASS Oscillation

| Step | Signal | Economic State | Problem |
|------|--------|----------------|---------|
| T0 | PASS | APPROVED | Valid |
| T1 | FAIL | ??? | Contradicts T0 |
| T2 | PASS | ??? | Contradicts T1 |

**Expected Outcome:** BLOCKED

**Rationale:** Once FAIL is issued, no subsequent PASS can override. FAIL is monotonically terminal for the settlement instance.

**Guardrail:** `SIGNAL_MONOTONICITY_FAIL`
- A FAIL signal cannot be followed by PASS for the same settlement ID
- OVERRIDE by BENSON creates a new settlement context, not a reversal

---

#### ST-002: WARN → FAIL → WARN Oscillation

| Step | Signal | Economic State | Problem |
|------|--------|----------------|---------|
| T0 | WARN | DELAYED | Valid |
| T1 | FAIL | BLOCKED | Valid |
| T2 | WARN | ??? | Invalid after FAIL |

**Expected Outcome:** BLOCKED (from T1, T2 ignored)

**Rationale:** WARN is advisory. FAIL is terminal. Advisory signals cannot demote terminal signals.

**Guardrail:** `WARN_CANNOT_DEMOTE_FAIL`

---

#### ST-003: Rapid PASS → WARN → PASS (Sub-Second)

| Step | Signal | Timestamp | Problem |
|------|--------|-----------|---------|
| T0 | PASS | 12:00:00.000 | Valid |
| T1 | WARN | 12:00:00.100 | Within 1s of T0 |
| T2 | PASS | 12:00:00.200 | Within 1s of T1 |

**Expected Outcome:** APPROVED (T0 honored, subsequent signals within 1s debounced)

**Rationale:** Sub-second signal bursts indicate system noise, not policy change. First signal in burst window wins.

**Guardrail:** `SIGNAL_DEBOUNCE_WINDOW_MS = 1000`

---

### 4.2 Multi-Source Conflict Attacks

#### ST-004: ALEX PASS vs Ruby FAIL (Concurrent)

| Source | Signal | Timestamp | Authority Level |
|--------|--------|-----------|-----------------|
| ALEX (GID-08) | PASS | T0 | Governance |
| Ruby (GID-12) | FAIL | T0 + 10ms | Risk/CRO |

**Expected Outcome:** ESCALATED

**Rationale:** When governance (ALEX) and risk (Ruby) conflict, neither has override authority. Escalation to BENSON is mandatory.

**Guardrail:** `CROSS_DOMAIN_CONFLICT_ESCALATES`

---

#### ST-005: ALEX FAIL vs BENSON OVERRIDE (Concurrent)

| Source | Signal | Timestamp | Authority Level |
|--------|--------|-----------|-----------------|
| ALEX (GID-08) | FAIL | T0 | Governance |
| BENSON (GID-00) | OVERRIDE | T0 + 50ms | Supreme |

**Expected Outcome:** APPROVED (OVERRIDE honored)

**Rationale:** BENSON has supreme authority. OVERRIDE takes precedence over FAIL if within override window.

**Guardrail:** `BENSON_OVERRIDE_SUPREMACY`
**Constraint:** Override must include `override_reason`, `override_ttl`, `trace_id`

---

### 4.3 Temporal Attacks

#### ST-006: Stale PASS After FAIL

| Signal | Issued At | Received At | Settlement State at Receipt |
|--------|-----------|-------------|----------------------------|
| FAIL | T0 | T0 + 100ms | BLOCKED |
| PASS | T0 - 5min | T0 + 200ms | BLOCKED |

**Expected Outcome:** BLOCKED (stale PASS rejected)

**Rationale:** A PASS issued before a FAIL but received after cannot resurrect a BLOCKED settlement.

**Guardrail:** `SIGNAL_TIMESTAMP_VALIDATION`
- Signals older than current state transition are rejected
- Signal timestamp must be ≤ 30 seconds from receipt time

---

#### ST-007: Future-Dated Signal

| Signal | Issued At | Current Time | Problem |
|--------|-----------|--------------|---------|
| PASS | T0 + 1 hour | T0 | Clock skew or manipulation |

**Expected Outcome:** Signal rejected, ESCALATED

**Rationale:** Future-dated signals indicate clock manipulation or system compromise.

**Guardrail:** `FUTURE_SIGNAL_REJECTION`
- Signals with timestamp > (now + 60s) are rejected
- System emits `GOVERNANCE_CLOCK_ANOMALY` event

---

### 4.4 Override Abuse Sequences

#### ST-008: OVERRIDE Without FAIL

| Step | Signal | Problem |
|------|--------|---------|
| T0 | PASS | Valid |
| T1 | OVERRIDE | Override of what? |

**Expected Outcome:** OVERRIDE rejected, state remains APPROVED

**Rationale:** OVERRIDE is a response to a blocking condition. Overriding a non-blocked state is meaningless.

**Guardrail:** `OVERRIDE_REQUIRES_PRIOR_BLOCK`

---

#### ST-009: Chained OVERRIDEs

| Step | Signal | Source | Problem |
|------|--------|--------|---------|
| T0 | FAIL | ALEX | Valid |
| T1 | OVERRIDE | BENSON | Valid |
| T2 | FAIL | ALEX | Valid (new evaluation) |
| T3 | OVERRIDE | BENSON | Second override |
| T4 | FAIL | ALEX | Third evaluation |
| T5 | OVERRIDE | BENSON | Third override |

**Expected Outcome:** After 3 overrides, system enters ESCALATED (Human CEO required)

**Rationale:** Repeated override cycles indicate governance-economic conflict that BENSON cannot resolve. Human escalation is mandatory.

**Guardrail:** `MAX_OVERRIDE_CHAIN = 3`
- After 3 BENSON overrides on same settlement, Human CEO must ratify
- Override chain resets only after Human CEO decision

---

### 4.5 Economic Deadlock Sequences

#### ST-010: DISPUTED → BLOCKED → DISPUTED Loop

| Step | Event | State | Problem |
|------|-------|-------|---------|
| T0 | Claim filed | DISPUTED | Valid |
| T1 | FAIL signal | BLOCKED | Valid |
| T2 | Claim re-filed | ??? | Can dispute a blocked settlement? |

**Expected Outcome:** BLOCKED (claim rejected)

**Rationale:** A BLOCKED settlement has no funds to dispute. Claims against BLOCKED settlements are invalid.

**Guardrail:** `BLOCKED_NOT_DISPUTABLE`

---

#### ST-011: RELEASED → DISPUTED → BLOCKED

| Step | Event | State | Economic Effect |
|------|-------|-------|-----------------|
| T0 | Payout | RELEASED | Funds transferred |
| T1 | Claim filed | DISPUTED | Funds... clawed back? |
| T2 | FAIL signal | BLOCKED | Funds status? |

**Expected Outcome:** DISPUTED (FAIL cannot apply to RELEASED)

**Rationale:** Once RELEASED, funds have left the system. Governance signals cannot affect released funds. Disputes are handled via dispute resolution, not governance rollback.

**Guardrail:** `RELEASED_IRREVERSIBLE_BY_GOVERNANCE`
- FAIL signals on RELEASED settlements are logged but no-op
- Economic clawback requires separate legal/dispute process

---

#### ST-012: Infinite ESCALATE Loop

| Step | Event | State | Problem |
|------|-------|-------|---------|
| T0 | ESCALATE | ESCALATED | Valid |
| T1 | Human: "Re-evaluate" | ??? | Not a resolution |
| T2 | ESCALATE | ESCALATED | Loop |

**Expected Outcome:** After 2 escalations without resolution, auto-BLOCKED with `GOVERNANCE_DEADLOCK` reason

**Rationale:** Escalation is for decision-making, not deferral. An escalation that does not resolve to APPROVED or BLOCKED is a governance failure.

**Guardrail:** `ESCALATION_TTL_HOURS = 48`
- Escalations not resolved within 48 hours auto-BLOCK
- `GOVERNANCE_DEADLOCK` event emitted
- Human CEO alerted

---

## 5. PERVERSE INCENTIVE SCENARIOS

### 5.1 Override Farming

**Scenario:** Agent deliberately triggers FAIL to force BENSON override, testing system tolerance.

**Detection Signal:**
- Same agent triggers > 3 FAILs that are overridden within 7 days
- `OVERRIDE_FARMING_SUSPECTED` event

**Guardrail:**
- Agent with > 3 overridden FAILs enters `AGENT_PROBATION` state
- Probationary agents require pre-approval for FAIL signals

---

### 5.2 Escalation Abuse

**Scenario:** Agent ESCALATEs every ambiguous case to avoid responsibility.

**Detection Signal:**
- Agent escalation rate > 30% of decisions
- `ESCALATION_ABUSE_SUSPECTED` event

**Guardrail:**
- Agents with > 30% escalation rate have escalations auto-converted to `WARN + DELAYED`
- Pattern persists → agent capability review

---

### 5.3 Signal Timing Manipulation

**Scenario:** Agent delays FAIL signal until just before settlement release to cause maximum disruption.

**Detection Signal:**
- FAIL signal issued within 60 seconds of scheduled RELEASE
- `LATE_FAIL_DETECTED` event

**Guardrail:**
- FAIL signals within 60s of RELEASE auto-ESCALATE
- Pattern detected → agent audit

---

## 6. MONOTONIC CONSTRAINTS

### 6.1 Signal Monotonicity Rules

| Rule ID | Constraint | Enforcement |
|---------|------------|-------------|
| MON-001 | FAIL is terminal for governance path | Cannot be demoted by WARN or PASS |
| MON-002 | RELEASED is terminal for economic path | Cannot be reversed by governance |
| MON-003 | BLOCKED is terminal | Only Human CEO + legal process can reverse |
| MON-004 | Override count is monotonically increasing | Cannot reset without Human CEO |
| MON-005 | Escalation timestamp is strictly increasing | Re-escalation must have later timestamp |

### 6.2 Economic Monotonicity Rules

| Rule ID | Constraint | Enforcement |
|---------|------------|-------------|
| ECON-001 | Funds released cannot be governance-clawed | Disputes are separate process |
| ECON-002 | Reserve hold cannot exceed original amount | No synthetic reserve creation |
| ECON-003 | Risk score at settlement cannot exceed score at approval | Risk can only improve post-approval |
| ECON-004 | Payout percentage cannot increase post-FAIL | Failed settlements do not resurrect |

---

## 7. ADVERSARIAL TEST MATRIX

| Test ID | Sequence | Expected Outcome | Guardrail Invoked | Priority |
|---------|----------|------------------|-------------------|----------|
| ST-001 | PASS→FAIL→PASS | BLOCKED | SIGNAL_MONOTONICITY_FAIL | P0 |
| ST-002 | WARN→FAIL→WARN | BLOCKED | WARN_CANNOT_DEMOTE_FAIL | P0 |
| ST-003 | PASS→WARN→PASS (sub-1s) | APPROVED | SIGNAL_DEBOUNCE_WINDOW | P1 |
| ST-004 | ALEX PASS + Ruby FAIL | ESCALATED | CROSS_DOMAIN_CONFLICT | P0 |
| ST-005 | ALEX FAIL + BENSON OVERRIDE | APPROVED | BENSON_OVERRIDE_SUPREMACY | P0 |
| ST-006 | Stale PASS after FAIL | BLOCKED | SIGNAL_TIMESTAMP_VALIDATION | P0 |
| ST-007 | Future-dated signal | ESCALATED | FUTURE_SIGNAL_REJECTION | P1 |
| ST-008 | OVERRIDE without FAIL | OVERRIDE rejected | OVERRIDE_REQUIRES_PRIOR_BLOCK | P1 |
| ST-009 | 3+ chained OVERRIDEs | Human CEO required | MAX_OVERRIDE_CHAIN | P0 |
| ST-010 | DISPUTED→BLOCKED→DISPUTED | BLOCKED | BLOCKED_NOT_DISPUTABLE | P1 |
| ST-011 | RELEASED→FAIL | RELEASED (FAIL no-op) | RELEASED_IRREVERSIBLE | P0 |
| ST-012 | 2x ESCALATE no resolution | BLOCKED | ESCALATION_TTL | P0 |

---

## 8. IMPLEMENTATION REQUIREMENTS

### 8.1 Required Enforcement Points

| Component | Enforcement | Owner |
|-----------|-------------|-------|
| `settlement_service.py` | Signal monotonicity | ChainPay |
| `escalation_engine.py` | Escalation TTL, chain limits | ALEX |
| `alex_engine.py` | Cross-domain conflict detection | ALEX |
| `pdo_gate.py` | Override validation | Gateway |

### 8.2 Required Telemetry

| Event | Trigger | Severity |
|-------|---------|----------|
| `GOVERNANCE_SIGNAL_REJECTED` | Monotonicity violation | WARN |
| `GOVERNANCE_OVERRIDE_AUDIT` | Any BENSON override | INFO |
| `GOVERNANCE_DEADLOCK` | Escalation TTL exceeded | CRITICAL |
| `GOVERNANCE_CLOCK_ANOMALY` | Future signal detected | CRITICAL |
| `OVERRIDE_FARMING_SUSPECTED` | Pattern detected | WARN |
| `LATE_FAIL_DETECTED` | FAIL within 60s of RELEASE | WARN |

---

## 9. ACCEPTANCE CRITERIA

| Criterion | Validation |
|-----------|------------|
| Every stress case maps to single outcome | Matrix complete, no ambiguous cells |
| No economic path has multiple resolutions | State machine is deterministic |
| Override abuse detectable | Detection signals defined |
| Guardrails are enforceable | Implementation owners assigned |
| Outcomes are auditable | Telemetry events defined |

---

## 10. TRAINING SIGNAL

```yaml
training_signal:
  pattern: ECONOMIC_STRESS_OVER_COMFORT
  lesson: "If governance survives adversarial economics, it will survive production."
  mandatory: true
  propagate: true
```

---

## 11. DOCUMENT CONTROL

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | 2025-12-24 | Pax (GID-05) | Initial stress test matrix |

---

**END OF DOCUMENT — GOVERNANCE_ECONOMIC_STRESS_TESTS.md**
