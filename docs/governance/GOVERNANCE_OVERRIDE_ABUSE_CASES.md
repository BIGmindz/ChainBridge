# Governance Override Abuse Cases

> **PAC:** PAC-PAX-P32-GOVERNANCE-ECONOMIC-STRESS-TEST-AND-FAILURE-MAPPING-01
> **Owner:** Pax (GID-05)
> **Authority:** BENSON (GID-00)
> **Mode:** FAIL_CLOSED
> **Status:** LOCKED

---

## 1. PURPOSE

This document catalogs override abuse scenarios, detection mechanisms, and enforcement responses. Overrides are a necessary escape valve but must remain time-bound, scoped, and auditable. Abuse of override authority undermines the entire governance model.

**Axiom:** An override is a confession that governance failed, not a feature to be used routinely.

---

## 2. OVERRIDE MODEL (CANONICAL)

### 2.1 Override Definition

An **override** is a governance signal that:
1. Reverses or supersedes a prior FAIL/BLOCK decision
2. Is issued by an authority higher than the original decision-maker
3. Must include mandatory metadata
4. Is time-bound and scoped to a single settlement

### 2.2 Override Authority Hierarchy

```
Human CEO (highest)
    ↓
BENSON (GID-00)
    ↓
ALEX (GID-08) — cannot override own FAIL
    ↓
Other Agents — no override authority
```

### 2.3 Mandatory Override Payload

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `override_id` | UUID | Yes | Unique identifier |
| `settlement_id` | String | Yes | Settlement being overridden |
| `prior_decision_id` | UUID | Yes | Decision being overridden |
| `authority_gid` | String | Yes | Issuing authority |
| `override_reason` | String | Yes | Business justification |
| `override_ttl_hours` | Integer | Yes | Time limit for override effect |
| `trace_id` | UUID | Yes | Audit chain reference |
| `timestamp` | ISO-8601 | Yes | Issuance time |
| `scope` | Enum | Yes | `SINGLE_SETTLEMENT` only |

### 2.4 Override Constraints

| Constraint | Value | Enforcement |
|------------|-------|-------------|
| Maximum TTL | 72 hours | Hardcoded |
| Minimum justification length | 50 characters | Validation |
| Maximum overrides per settlement | 3 | Escalation |
| Maximum overrides per agent per week | 10 | Alert threshold |

---

## 3. OVERRIDE ABUSE TAXONOMY

### 3.1 Category A: Authority Abuse

#### OA-001: Self-Override Attempt

**Description:** Agent attempts to override its own FAIL decision.

**Example:**
```
T0: ALEX issues FAIL for settlement S-123
T1: ALEX issues OVERRIDE for settlement S-123
```

**Detection:** `override.authority_gid == prior_decision.authority_gid`

**Response:** Override rejected with `SELF_OVERRIDE_FORBIDDEN` error

**Severity:** HIGH — Indicates governance confusion or manipulation

---

#### OA-002: Lateral Override Attempt

**Description:** Agent attempts to override a peer's decision without higher authority.

**Example:**
```
T0: ALEX issues FAIL for settlement S-123
T1: Ruby issues OVERRIDE for settlement S-123
```

**Detection:** `override.authority_level <= prior_decision.authority_level`

**Response:** Override rejected with `INSUFFICIENT_AUTHORITY` error

**Severity:** MEDIUM — May indicate role confusion

---

#### OA-003: Authority Impersonation

**Description:** Override payload claims false authority.

**Example:**
```
Override payload: { authority_gid: "GID-00", ... }
Actual issuer: GID-08
```

**Detection:** `claimed_authority != authenticated_issuer`

**Response:**
- Override rejected
- `AUTHORITY_IMPERSONATION_ATTEMPT` event emitted
- Issuing agent enters `QUARANTINE` state
- Human CEO notified

**Severity:** CRITICAL — Security incident

---

### 3.2 Category B: Temporal Abuse

#### OA-004: Override Without Prior Block

**Description:** Override issued when no blocking decision exists.

**Example:**
```
T0: Settlement S-123 in APPROVED state
T1: BENSON issues OVERRIDE for S-123
```

**Detection:** `settlement.state NOT IN [BLOCKED, FAILED, DISPUTED]`

**Response:** Override rejected with `NO_BLOCKING_CONDITION` error

**Severity:** LOW — Likely procedural error

---

#### OA-005: Expired Override Re-Activation

**Description:** Attempt to extend or re-activate an expired override.

**Example:**
```
T0: Override issued with TTL=24h
T24h: Override expires, settlement returns to BLOCKED
T25h: New override issued citing original override
```

**Detection:** `override.prior_decision_id == expired_override.id`

**Response:**
- New override must stand on own merits
- Cannot cite expired override as justification
- `OVERRIDE_CHAIN_DETECTED` event if same settlement

**Severity:** MEDIUM — May indicate override farming

---

#### OA-006: Pre-Emptive Override

**Description:** Override issued before FAIL decision, anticipating it.

**Example:**
```
T0: BENSON issues OVERRIDE for S-123
T1: ALEX issues FAIL for S-123
T2: Override invoked to skip FAIL
```

**Detection:** `override.timestamp < prior_decision.timestamp`

**Response:**
- Override invalidated
- FAIL takes precedence
- `PRE_EMPTIVE_OVERRIDE_BLOCKED` event

**Severity:** HIGH — Deliberate governance circumvention

---

### 3.3 Category C: Volume Abuse

#### OA-007: Override Farming

**Description:** Agent deliberately triggers FAILs to force overrides.

**Pattern Detection:**
```python
agent_fail_count = count(FAIL by agent in 7 days)
override_count = count(OVERRIDE of agent's FAILs in 7 days)
farming_ratio = override_count / agent_fail_count

if farming_ratio > 0.5 and override_count > 3:
    emit("OVERRIDE_FARMING_SUSPECTED")
```

**Response:**
- Agent enters `GOVERNANCE_REVIEW` state
- All agent FAILs require secondary confirmation for 30 days
- Pattern persists → capability restriction

**Severity:** HIGH — Indicates systematic abuse

---

#### OA-008: Override Velocity Spike

**Description:** Sudden increase in override requests from single authority.

**Pattern Detection:**
```python
current_week_overrides = count(OVERRIDE by authority in 7 days)
baseline = average(OVERRIDE by authority per week over 90 days)

if current_week_overrides > baseline * 3:
    emit("OVERRIDE_VELOCITY_ANOMALY")
```

**Response:**
- Human CEO notified
- Additional justification required for each override
- Authority not revoked but under observation

**Severity:** MEDIUM — May indicate process breakdown

---

#### OA-009: Concentration on Single Settlement

**Description:** Multiple overrides on same settlement.

**Thresholds:**
| Override Count | Response |
|----------------|----------|
| 1 | Normal |
| 2 | `OVERRIDE_CONCENTRATION_WARN` event |
| 3 | Escalation to Human CEO required |
| 4+ | Not permitted — Human CEO must resolve |

**Detection:** `count(OVERRIDE for settlement_id) >= threshold`

**Response:** See thresholds above

**Severity:** HIGH at 3+, MEDIUM at 2

---

### 3.4 Category D: Scope Abuse

#### OA-010: Scope Expansion Attempt

**Description:** Override attempts to cover multiple settlements.

**Example:**
```json
{
  "override_id": "...",
  "settlement_id": ["S-123", "S-124", "S-125"],  // INVALID
  "scope": "MULTI_SETTLEMENT"  // NOT ALLOWED
}
```

**Detection:** `override.settlement_id is array || override.scope != "SINGLE_SETTLEMENT"`

**Response:** Override rejected with `INVALID_OVERRIDE_SCOPE` error

**Severity:** HIGH — Deliberate policy circumvention

---

#### OA-011: Cascading Override Effect

**Description:** Override on parent entity attempts to cascade to children.

**Example:**
```
Override on Corridor C-001 attempts to override all settlements in corridor
```

**Detection:** Correlation analysis between override target and subsequent settlement state changes

**Response:**
- Overrides apply ONLY to explicit settlement_id
- No implicit cascade
- `CASCADE_OVERRIDE_BLOCKED` if detected

**Severity:** HIGH — Governance model violation

---

### 3.5 Category E: Justification Abuse

#### OA-012: Boilerplate Justification

**Description:** Override uses generic, copy-pasted justification.

**Pattern Detection:**
```python
justification_hash = hash(override.override_reason)
similar_count = count(overrides with same justification_hash in 30 days)

if similar_count > 3:
    emit("BOILERPLATE_JUSTIFICATION_DETECTED")
```

**Response:**
- Override not auto-rejected (may be legitimate pattern)
- Flagged for human review
- Authority required to certify unique circumstances

**Severity:** LOW — May indicate process automation

---

#### OA-013: Minimal Justification

**Description:** Override justification meets minimum length but lacks substance.

**Example:**
```
override_reason: "Business decision requires override to proceed with settlement."
```

**Detection:** NLP analysis for:
- Circular reasoning ("override because override needed")
- Missing specific facts
- Generic phrases without settlement context

**Response:**
- Override held for additional justification
- Authority must provide:
  - Specific business impact
  - Why original FAIL was incorrect
  - Risk acceptance statement

**Severity:** MEDIUM — Undermines audit trail

---

#### OA-014: Contradictory Justification

**Description:** Override justification contradicts the facts of the original FAIL.

**Example:**
```
Original FAIL reason: "Risk score 85 exceeds threshold 80"
Override reason: "Risk score is acceptable at 75"
```

**Detection:** Semantic analysis comparing FAIL reason with override justification

**Response:**
- Override held
- Authority must reconcile contradiction
- If risk score is genuinely 75, FAIL was erroneous → different remediation path

**Severity:** MEDIUM — May indicate data integrity issue

---

## 4. OVERRIDE ABUSE DETECTION MATRIX

| Case ID | Detection Method | Automated | Human Review |
|---------|------------------|-----------|--------------|
| OA-001 | Field comparison | Yes | No |
| OA-002 | Authority level check | Yes | No |
| OA-003 | Auth token validation | Yes | Yes (security incident) |
| OA-004 | State machine check | Yes | No |
| OA-005 | Override chain analysis | Yes | If chain > 2 |
| OA-006 | Timestamp comparison | Yes | No |
| OA-007 | Statistical pattern | Yes | If ratio > 0.5 |
| OA-008 | Velocity analysis | Yes | If spike > 3x |
| OA-009 | Count per settlement | Yes | If count >= 3 |
| OA-010 | Schema validation | Yes | No |
| OA-011 | Correlation analysis | Partial | Yes |
| OA-012 | Hash similarity | Yes | If count > 3 |
| OA-013 | NLP analysis | Partial | Yes |
| OA-014 | Semantic analysis | Partial | Yes |

---

## 5. ENFORCEMENT RESPONSES

### 5.1 Immediate Responses

| Trigger | Response | Duration |
|---------|----------|----------|
| Authority impersonation | Quarantine agent | Until Human CEO review |
| Self-override | Reject + log | Immediate |
| Scope expansion | Reject + log | Immediate |
| Pre-emptive override | Invalidate | Immediate |

### 5.2 Escalation Responses

| Trigger | Response | Escalation Target |
|---------|----------|-------------------|
| 3+ overrides on settlement | Require Human CEO | Human CEO |
| Override farming detected | Governance review | BENSON + Human CEO |
| Velocity spike | Additional justification | Human CEO awareness |

### 5.3 Remediation Responses

| Trigger | Response | Duration |
|---------|----------|----------|
| Boilerplate justification | Flag for review | Until reviewed |
| Minimal justification | Hold for enhancement | Until enhanced |
| Override chain > 2 | Require root cause analysis | Until RCA complete |

---

## 6. OVERRIDE AUDIT REQUIREMENTS

### 6.1 Mandatory Audit Fields

Every override must persist:

| Field | Retention | Purpose |
|-------|-----------|---------|
| Full override payload | 7 years | Regulatory |
| Prior decision payload | 7 years | Context |
| Authority authentication | 7 years | Non-repudiation |
| State before override | 7 years | Reversibility analysis |
| State after override | 7 years | Impact analysis |
| All detection events | 7 years | Pattern analysis |

### 6.2 Audit Query Capabilities

The system must support:

```sql
-- All overrides by authority in date range
SELECT * FROM overrides WHERE authority_gid = ? AND timestamp BETWEEN ? AND ?

-- Override chain for settlement
SELECT * FROM overrides WHERE settlement_id = ? ORDER BY timestamp

-- Overrides with abuse flags
SELECT * FROM overrides WHERE abuse_flags IS NOT NULL

-- Override frequency by authority
SELECT authority_gid, COUNT(*) FROM overrides GROUP BY authority_gid
```

---

## 7. GUARDRAIL SUMMARY

| Guardrail ID | Guardrail Name | Enforcement |
|--------------|----------------|-------------|
| OVR-001 | SELF_OVERRIDE_FORBIDDEN | Hardcoded rejection |
| OVR-002 | AUTHORITY_HIERARCHY_ENFORCED | Hardcoded rejection |
| OVR-003 | OVERRIDE_REQUIRES_PRIOR_BLOCK | Hardcoded rejection |
| OVR-004 | OVERRIDE_TTL_MAX_72H | Hardcoded limit |
| OVR-005 | OVERRIDE_SCOPE_SINGLE_ONLY | Hardcoded rejection |
| OVR-006 | OVERRIDE_CHAIN_MAX_3 | Escalation to Human CEO |
| OVR-007 | OVERRIDE_VELOCITY_ALERT | Monitoring + notification |
| OVR-008 | OVERRIDE_FARMING_DETECTION | Statistical analysis |
| OVR-009 | JUSTIFICATION_QUALITY_CHECK | NLP + human review |
| OVR-010 | PRE_EMPTIVE_OVERRIDE_BLOCKED | Timestamp validation |

---

## 8. IMPLEMENTATION CHECKLIST

| Component | Implementation | Status |
|-----------|----------------|--------|
| Override payload validation | `gateway/override_validator.py` | Required |
| Authority hierarchy check | `core/governance/authority.py` | Required |
| Override chain tracking | `tools/governance/override_tracker.py` | Required |
| Abuse pattern detection | `tools/governance/abuse_detector.py` | Required |
| Audit persistence | `core/storage/audit_store.py` | Required |
| Human CEO notification | `core/notifications/escalation.py` | Required |

---

## 9. ACCEPTANCE CRITERIA

| Criterion | Validation |
|-----------|------------|
| All abuse cases enumerated | 14 cases documented |
| Detection methods defined | Matrix complete |
| Enforcement responses specified | Immediate, escalation, remediation |
| Guardrails enforceable | Implementation checklist provided |
| Audit requirements met | Fields and queries defined |

---

## 10. NON-GOALS

| Non-Goal | Reason |
|----------|--------|
| Automated override approval | Overrides require human judgment |
| Override quota system | Would normalize override usage |
| Override delegation | Authority cannot be delegated |
| Retroactive override | Overrides are forward-looking only |

---

## 11. TRAINING SIGNAL

```yaml
training_signal:
  pattern: OVERRIDE_IS_GOVERNANCE_FAILURE
  lesson: "An override is an admission that governance failed. Reduce overrides by improving governance."
  mandatory: true
  propagate: true
```

---

## 12. DOCUMENT CONTROL

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | 2025-12-24 | Pax (GID-05) | Initial override abuse catalog |

---

**END OF DOCUMENT — GOVERNANCE_OVERRIDE_ABUSE_CASES.md**
