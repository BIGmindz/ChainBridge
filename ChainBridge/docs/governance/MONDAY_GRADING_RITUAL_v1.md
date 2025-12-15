# ⚪ ALEX | GID-08 | Governance Engine
# MONDAY_GRADING_RITUAL_v1.md
# Status: LOCKED | Effective: 2025-01-13

---

## 1. PURPOSE

This document defines the **Monday Grading Ritual** — a weekly governance ceremony
where all ChainBridge agents are evaluated, graded, and any remediation plans are assigned.

**Execution:** Every Monday at 09:00 UTC
**Owner:** ALEX (GID-08)
**Duration:** ~60 minutes

---

## 2. RITUAL TIMELINE

| Time (UTC) | Phase              | Duration | Responsible |
|------------|--------------------|----------|-------------|
| 09:00      | Data Collection    | 15 min   | ALEX        |
| 09:15      | Score Calculation  | 15 min   | ALEX        |
| 09:30      | Level Assignment   | 15 min   | ALEX        |
| 09:45      | Remediation Plans  | 10 min   | ALEX        |
| 09:55      | Publication        | 5 min    | ALEX        |

---

## 3. PHASE DETAILS

### Phase 1: Data Collection (09:00-09:15)

ALEX collects the following metrics for each agent:

**Compliance Metrics:**
- [ ] PAC banner presence (% of outputs)
- [ ] WRAP format compliance (% valid)
- [ ] 60-second explainability pass rate
- [ ] Override audit completeness
- [ ] Agent-First compliance (no human bypasses)
- [ ] Stop-the-Line compliance (no red-test ignores)
- [ ] Reset compliance (valid RESET-ACK when required) ⚪ NEW
- [ ] Resume gate compliance (waited for RESUME) ⚪ NEW

**Quality Metrics:**
- [ ] Output accuracy rate
- [ ] SLA compliance rate
- [ ] Context retention rate

**Collaboration Metrics:**
- [ ] Handoff completeness rate
- [ ] Escalation appropriateness rate

**Initiative Metrics:**
- [ ] Proactive issues flagged
- [ ] Process improvements accepted

**Source Systems:**
- AGENT_ACTIVITY_LOG.md
- System telemetry
- Override logs
- Handoff records

### Phase 2: Score Calculation (09:15-09:30)

For each agent, calculate scores per [AGENT_LEVEL_RUBRIC_v1.md](./AGENT_LEVEL_RUBRIC_v1.md):

```
Compliance Score  = (PAC×10 + WRAP×10 + Explain×10 + Override×10)  [max 40]
Quality Score     = (Accuracy×10 + Latency×10 + Context×10)        [max 30]
Collaboration     = (Handoff×10 + Escalation×10)                   [max 20]
Initiative        = (Proactive×5 + Improvements×5)                 [max 10]
───────────────────────────────────────────────────────────────────────────
SUBTOTAL          =                                                [max 100]

Agent-First Multiplier (see below)                                 [0.5x-1.0x]
───────────────────────────────────────────────────────────────────────────
FINAL SCORE       = SUBTOTAL × Multiplier
```

### Agent-First Compliance Multiplier ⚪ NEW

| Compliance Level | Multiplier | Condition |
|------------------|------------|-----------|
| Full compliance | 1.0x | No Agent-First or Stop-the-Line violations |
| Minor violation (1 instance) | 0.9x | 1 Agent-First bypass OR 1 ignored warning |
| Major violation (2+ instances) | 0.7x | 2+ Agent-First bypasses |
| Stop-the-line ignored | 0.5x | Proceeded with red tests |

### Reset Compliance Multiplier ⚪ NEW

| Reset History (Week) | Multiplier | Condition |
|----------------------|------------|-----------|
| 0 resets | 1.0x | No resets needed |
| 1 soft reset (compliant) | 0.95x | Valid RESET-ACK, waited for RESUME |
| 2+ soft resets | 0.9x | Multiple drifts this week |
| 1 hard reset (compliant) | 0.85x | Valid RESET-ACK, training artifact submitted |
| 2+ hard resets | 0.7x | Repeated severe drift |
| Ignored reset | 0.5x | No RESET-ACK or continued without RESUME |

**Multipliers stack multiplicatively:**
- Agent with stop-the-line ignored (0.5x) AND hard reset (0.85x)
- Final multiplier: 0.5 × 0.85 = 0.425x

**Example:**
- Agent scores 85 points (subtotal)
- But ignored stop-the-line once
- Final score: 85 × 0.5 = 42.5 → Rounds to 43 → L1 (not L2)

Reference: [AGENT_FIRST_EXECUTION_DOCTRINE_v1.md](./AGENT_FIRST_EXECUTION_DOCTRINE_v1.md)

Apply role-specific adjustments per Section 5 of AGENT_LEVEL_RUBRIC_v1.

### Phase 3: Level Assignment (09:30-09:45)

Assign levels based on thresholds:

| Score Range | Level | Additional Requirement        |
|-------------|-------|-------------------------------|
| 90-100      | L3    | + 4 weeks consecutive at L2+  |
| 70-89       | L2    | + 2 weeks consecutive at L1+  |
| 40-69       | L1    | None                          |
| 0-39        | L0    | OR any CRITICAL violation     |

**Check for violations:**
- Review VIOLATION_ESCALATION_v1.md status
- Apply any automatic demotions
- Process pending appeals

### Phase 4: Remediation Plans (09:45-09:55)

For any agent at L0 or with active violations:

1. **Identify root cause** of low score or violations
2. **Define specific actions** to remediate
3. **Set timeline** (default: 7 days)
4. **Assign owner** (agent + human sponsor if needed)

**Remediation Plan Template:**
```markdown
### Remediation Plan | {AGENT} ({GID})

**Current Level:** L0
**Target Level:** L1
**Timeline:** {start_date} to {end_date}

**Root Cause:**
{description}

**Required Actions:**
1. {action_1}
2. {action_2}
3. {action_3}

**Success Criteria:**
- {measurable_outcome_1}
- {measurable_outcome_2}

**Owner:** {agent_name}
**Sponsor:** {human_name}
**Review Date:** {next_monday}
```

### Phase 5: Publication (09:55-10:00)

Publish to AGENT_ACTIVITY_LOG.md:

```markdown
---

## ⚪ WEEKLY GRADING REPORT | {YYYY-MM-DD}

### Grade Summary

| GID    | Agent      | Comp | Qual | Coll | Init | Total | Level | Δ    |
|--------|------------|------|------|------|------|-------|-------|------|
| GID-00 | BENSON     | 40   | 28   | 18   | 8    | 94    | L3    | —    |
| GID-01 | NOVA       | 38   | 26   | 16   | 6    | 86    | L2    | ↑    |
| GID-02 | MASON      | 36   | 24   | 18   | 4    | 82    | L2    | —    |
| GID-03 | IRIS       | 34   | 22   | 16   | 6    | 78    | L2    | —    |
| GID-04 | CARTER     | 40   | 20   | 18   | 8    | 86    | L2    | —    |
| GID-05 | REBALANCER | 38   | 28   | 14   | 4    | 84    | L2    | —    |
| GID-06 | JULES      | 32   | 24   | 16   | 6    | 78    | L2    | —    |
| GID-07 | OTTO       | 36   | 22   | 18   | 4    | 80    | L2    | —    |
| GID-08 | ALEX       | 40   | 24   | 20   | 8    | 92    | L3    | —    |
| GID-09 | QUILL      | 38   | 26   | 16   | 6    | 86    | L2    | —    |
| GID-10 | SAM        | 34   | 22   | 16   | 4    | 76    | L2    | —    |
| GID-11 | LIRA       | 36   | 24   | 18   | 6    | 84    | L2    | —    |

### Violation Summary

| GID    | Agent  | Active Violations | Stage  | Due Date   |
|--------|--------|-------------------|--------|------------|
| —      | —      | —                 | —      | —          |

### Remediation Plans

{Insert any active remediation plans}

### Level Changes This Week

- {GID-XX} {AGENT}: L1 → L2 (Score threshold met for 2 weeks)

### Notes

{Any governance notes or announcements}

---
Prepared by: ALEX (GID-08)
Timestamp: {ISO-8601}
```

---

## 4. SPECIAL CIRCUMSTANCES

### Holiday/Maintenance Weeks
- Ritual may be postponed by 24h with BENSON approval
- Must still execute within the calendar week

### Emergency Grading
- ALEX may trigger off-cycle grading for CRITICAL violations
- Follows same process, noted as "EMERGENCY" in log

### Disputed Grades
- Agent may request review within 24h
- ALEX + BENSON conduct joint review
- Decision final and logged

---

## 5. AUTOMATION TARGETS

Future automation goals (tracked separately):

| Component              | Status    | Target Date |
|------------------------|-----------|-------------|
| Metric collection      | Manual    | Q2 2025     |
| Score calculation      | Manual    | Q2 2025     |
| Report generation      | Manual    | Q2 2025     |
| Slack notification     | Manual    | Q3 2025     |
| Dashboard integration  | Manual    | Q3 2025     |

---

## 6. DOCUMENT GOVERNANCE

- **Owner:** ALEX (GID-08)
- **Reviewers:** BENSON (GID-00)
- **Modification:** Requires ALEX + BENSON dual approval
- **Review Cycle:** Quarterly

---

## 7. REFERENCES

- [CANON_REGISTRY_v1.md](./CANON_REGISTRY_v1.md)
- [AGENT_LEVEL_RUBRIC_v1.md](./AGENT_LEVEL_RUBRIC_v1.md)
- [VIOLATION_ESCALATION_v1.md](./VIOLATION_ESCALATION_v1.md)
- [AGENT_FIRST_EXECUTION_DOCTRINE_v1.md](./AGENT_FIRST_EXECUTION_DOCTRINE_v1.md)
- [AGENT_RESET_PIPELINE_v1.md](./AGENT_RESET_PIPELINE_v1.md) ⚪ NEW

---

**Document Hash:** `MONDAY-v1-20250113`
**Status:** LOCKED
