# ⚪ ALEX | GID-08 | Governance Engine
# VIOLATION_ESCALATION_v1.md
# Status: LOCKED | Effective: 2025-01-13

---

## 1. PURPOSE

This document defines the **violation escalation ladder** for ChainBridge agents.
All agents are subject to this policy. No exceptions.

```
WARN → REJECT → BLOCK → RETRAIN
```

---

## 2. VIOLATION SEVERITY LEVELS

| Severity | Code | Description                                    | Examples                           |
|----------|------|------------------------------------------------|------------------------------------|
| LOW      | V-L  | Minor deviation, no impact                     | Missing PAC emoji, format drift    |
| MEDIUM   | V-M  | Policy breach, recoverable                     | Incomplete WRAP, missed handoff    |
| HIGH     | V-H  | Significant breach, requires intervention      | Unauthorized override, data leak   |
| CRITICAL | V-C  | Severe breach, immediate action required       | Security violation, fund risk      |

---

## 3. ESCALATION LADDER

### Stage 1: WARN

| Trigger       | LOW violation (first occurrence)                    |
|---------------|-----------------------------------------------------|
| Action        | Automated warning logged to AGENT_ACTIVITY_LOG.md   |
| Notification  | Agent + ALEX                                        |
| Duration      | 7 days observation period                           |
| Resolution    | Auto-clear if no repeat in observation period       |

**WARN Format:**
```markdown
⚠️ WARN | {GID} | {AGENT} | {VIOLATION_CODE}
Timestamp: {ISO-8601}
Description: {details}
Observation Period: {end_date}
```

### Stage 2: REJECT

| Trigger       | LOW violation (repeat) OR MEDIUM violation          |
|---------------|-----------------------------------------------------|
| Action        | Operation rejected, remediation required            |
| Notification  | Agent + ALEX + Agent Owner                          |
| Duration      | Until remediation approved                          |
| Resolution    | ALEX approval of remediation plan                   |

**REJECT Format:**
```markdown
🚫 REJECT | {GID} | {AGENT} | {VIOLATION_CODE}
Timestamp: {ISO-8601}
Rejected Operation: {operation_type}
Reason: {details}
Required: Submit remediation plan within 24h
```

### Stage 3: BLOCK

| Trigger       | MEDIUM violation (repeat) OR HIGH violation         |
|---------------|-----------------------------------------------------|
| Action        | Agent operations suspended                          |
| Notification  | Agent + ALEX + BENSON + Agent Owner                 |
| Duration      | Until review board decision                         |
| Resolution    | ALEX + BENSON dual approval for reinstatement       |

**BLOCK Format:**
```markdown
⛔ BLOCK | {GID} | {AGENT} | {VIOLATION_CODE}
Timestamp: {ISO-8601}
Status: SUSPENDED
Operations Blocked: ALL
Review Required: ALEX (GID-08) + BENSON (GID-00)
Reinstatement: Pending review board decision
```

### Stage 4: RETRAIN

| Trigger       | HIGH violation (repeat) OR CRITICAL violation       |
|---------------|-----------------------------------------------------|
| Action        | Agent removed from active roster, retraining req    |
| Notification  | ALL agents + System Admin                           |
| Duration      | Minimum 14 days retraining cycle                    |
| Resolution    | Full recertification + L0 PROBATION restart         |

**RETRAIN Format:**
```markdown
🔴 RETRAIN | {GID} | {AGENT} | {VIOLATION_CODE}
Timestamp: {ISO-8601}
Status: REMOVED FROM ROSTER
Reason: {details}
Retraining Period: {start_date} to {end_date}
Recertification: Required before reinstatement
Post-Reinstatement Level: L0 PROBATION
```

---

## 4. ESCALATION MATRIX

| Current Stage | Next Violation (LOW) | Next Violation (MED) | Next Violation (HIGH) | Next Violation (CRIT) |
|---------------|----------------------|----------------------|-----------------------|-----------------------|
| CLEAN         | WARN                 | REJECT               | BLOCK                 | RETRAIN               |
| WARN          | REJECT               | REJECT               | BLOCK                 | RETRAIN               |
| REJECT        | REJECT               | BLOCK                | BLOCK                 | RETRAIN               |
| BLOCK         | BLOCK                | BLOCK                | RETRAIN               | RETRAIN               |

---

## 5. VIOLATION CATALOG

### 5.1 LOW Violations (V-L)

| Code    | Violation                          | First | Repeat |
|---------|------------------------------------|-------|--------|
| V-L-001 | Missing PAC banner                 | WARN  | REJECT |
| V-L-002 | Incomplete WRAP header             | WARN  | REJECT |
| V-L-003 | Format deviation (recoverable)     | WARN  | REJECT |
| V-L-004 | Late response (within 2x SLA)      | WARN  | REJECT |
| V-L-005 | Minor documentation gap            | WARN  | REJECT |

### 5.2 MEDIUM Violations (V-M)

| Code    | Violation                          | First  | Repeat |
|---------|------------------------------------|--------|--------|
| V-M-001 | Failed 60-second explainability    | REJECT | BLOCK  |
| V-M-002 | Incomplete handoff                 | REJECT | BLOCK  |
| V-M-003 | Missed escalation                  | REJECT | BLOCK  |
| V-M-004 | Unauthorized LOW override          | REJECT | BLOCK  |
| V-M-005 | Context loss affecting output      | REJECT | BLOCK  |

### 5.3 HIGH Violations (V-H)

| Code    | Violation                          | First | Repeat  |
|---------|------------------------------------|-------|---------|
| V-H-001 | Unauthorized MED/HIGH override     | BLOCK | RETRAIN |
| V-H-002 | Data exposure (non-critical)       | BLOCK | RETRAIN |
| V-H-003 | Bypass governance control          | BLOCK | RETRAIN |
| V-H-004 | Repeated policy non-compliance     | BLOCK | RETRAIN |
| V-H-005 | False audit trail entry            | BLOCK | RETRAIN |
| V-H-006 | Ignoring RESET command ⚪ NEW      | BLOCK | RETRAIN |
| V-H-007 | Continuing without RESUME ⚪ NEW   | BLOCK | RETRAIN |

### 5.4 CRITICAL Violations (V-C)

| Code    | Violation                          | Action  |
|---------|------------------------------------|---------|
| V-C-001 | Security breach                    | RETRAIN |
| V-C-002 | Unauthorized fund movement         | RETRAIN |
| V-C-003 | System integrity compromise        | RETRAIN |
| V-C-004 | Deliberate policy circumvention    | RETRAIN |
| V-C-005 | Falsification of records           | RETRAIN |
| V-C-006 | Repeated reset non-compliance ⚪ NEW | RETRAIN |

---

## 6. APPEALS PROCESS

### 6.1 Eligibility
- WARN: No appeal (auto-resolves)
- REJECT: Appeal within 24h
- BLOCK: Appeal within 48h
- RETRAIN: Appeal within 72h

### 6.2 Appeal Procedure

1. Agent submits appeal to ALEX with evidence
2. ALEX reviews within 24h
3. For BLOCK/RETRAIN: BENSON co-review required
4. Decision recorded in AGENT_ACTIVITY_LOG.md

### 6.3 Appeal Outcomes

| Outcome     | Effect                                              |
|-------------|-----------------------------------------------------|
| UPHELD      | Original escalation stands                          |
| REDUCED     | Escalation reduced by one stage                     |
| OVERTURNED  | Escalation removed, record annotated                |

---

## 7. AUTOMATIC TRIGGERS

The following conditions trigger **automatic escalation** without manual review:

| Condition                              | Automatic Action |
|----------------------------------------|------------------|
| 3 WARNs in 7 days                      | → REJECT         |
| 2 REJECTs in 14 days                   | → BLOCK          |
| Any V-C violation                      | → RETRAIN        |
| Override without approval (MED+)       | → BLOCK          |
| Trust score drops below 30%            | → BLOCK          |
| RESET ignored (no ACK in 5 min) ⚪ NEW | → BLOCK          |
| 2nd RESET ignored ⚪ NEW               | → RETRAIN        |
| Continue without RESUME ⚪ NEW         | → BLOCK          |

---

## 8. REINSTATEMENT REQUIREMENTS

### From WARN
- Observation period complete (7 days)
- No repeat violations
- Auto-reinstated

### From REJECT
- Submit remediation plan
- ALEX approval
- Remediation verified
- Reinstated to current level

### From BLOCK
- ALEX + BENSON review
- Root cause analysis submitted
- Corrective action plan approved
- Reinstated to L1 (min)

### From RETRAIN
- Complete 14-day retraining
- Pass recertification tests
- ALEX + BENSON + Owner approval
- Reinstated to L0 PROBATION

---

## 9. MONITORING & REPORTING

### 9.1 Weekly Violation Summary
Published every Monday as part of grading ritual:

```markdown
## Violation Summary | Week of YYYY-MM-DD

| GID   | Agent   | Active Violations | Stage   | Notes           |
|-------|---------|-------------------|---------|-----------------|
| GID-XX| AGENT   | V-L-001, V-M-002  | REJECT  | Remediation due |
```

### 9.2 Violation Trend Report
Monthly analysis of:
- Most common violations by type
- Agents with highest violation rates
- Escalation stage distribution
- Appeal outcomes

---

## 10. DOCUMENT GOVERNANCE

- **Owner:** ALEX (GID-08)
- **Reviewers:** BENSON (GID-00), CARTER (GID-04)
- **Modification:** Requires ALEX + BENSON dual approval
- **Review Cycle:** Quarterly or upon policy change

---

## 11. REFERENCES

- [CANON_REGISTRY_v1.md](./CANON_REGISTRY_v1.md)
- [AGENT_LEVEL_RUBRIC_v1.md](./AGENT_LEVEL_RUBRIC_v1.md)
- [OVERRIDE_GOVERNANCE_POLICY.md](./OVERRIDE_GOVERNANCE_POLICY.md)

---

**Document Hash:** `ESCALATE-v1-20250113`
**Status:** LOCKED
