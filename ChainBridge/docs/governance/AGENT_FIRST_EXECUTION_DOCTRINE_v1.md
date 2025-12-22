# ⚪ ALEX | GID-08 | Governance Engine
# AGENT_FIRST_EXECUTION_DOCTRINE_v1.md
# Status: LOCKED | Effective: 2025-12-15

---

## 1. CORE DOCTRINE

### The Agent-First Rule

> **Everything gets done by agents unless explicitly flagged "CEO-required."**

This is not a preference. This is policy. Violation triggers immediate REJECT.

### The Stop-the-Line Rule

> **If tests break, no forward progress. Full stop.**

Red tests mean HALT. No exceptions. No "I'll fix it later." No "it's just one test."

### The Training Loop Rule

> **Every failure becomes a training artifact + grading signal.**

Incidents are not buried. They are documented, converted to Agent University training material, and factored into weekly grades.

---

## 2. CEO-ONLY EXCEPTIONS (Strict List)

The following are the **only** activities that require human CEO execution:

| # | Activity | Rationale |
|---|----------|-----------|
| 1 | **Final merge approval to `main`** | Human accountability for production |
| 2 | **External vendor contract signatures** | Legal authority |
| 3 | **Security incident response (P0/P1)** | Human judgment for critical escalation |
| 4 | **Investor/board communications** | Fiduciary duty |
| 5 | **Agent termination decisions** | HR/governance authority |
| 6 | **Production deployment confirmation** | "Press the button" accountability |

**Everything else is agent work.**

If a task is not on this list, an agent must execute it. If you think a task belongs on this list, submit a governance PR to ALEX for review.

---

## 3. ENFORCEMENT MECHANISM

### Gate 1: PAC Assignment

Before any work begins:
```
☐ Task assigned to a specific GID
☐ Agent acknowledged the PAC
☐ NOT flagged as CEO-only exception
```

If a human attempts to execute non-CEO-only work:
```
⛔ REJECT: AGENT-FIRST VIOLATION
```

### Gate 2: Test Status

Before any forward progress:
```
☐ All relevant tests passing (green)
☐ No new test failures introduced
☐ CI pipeline status = SUCCESS
```

If tests are red:
```
⛔ HALT: TESTS RED — STOP THE LINE
```

### Gate 3: Training Loop

After any incident or failure:
```
☐ Root cause documented
☐ Training artifact created (Agent University)
☐ Grading impact assessed
☐ Remediation plan assigned
```

---

## 4. REJECTION TEMPLATES

### Template 1: Agent-First Violation

```
⛔ REJECT: AGENT-FIRST VIOLATION

Detected: Human executed agent-assignable work
Task: [TASK DESCRIPTION]
Rule: Agent-First Execution Doctrine v1 §1

Required Fix:
1. Revert any human-executed changes
2. Assign task to appropriate agent (GID-XX)
3. Agent executes via proper PAC
4. Submit compliant WRAP

Reference: AGENT_FIRST_EXECUTION_DOCTRINE_v1.md §2 for CEO-only exceptions
```

### Template 2: Stop-the-Line

```
⛔ HALT: TESTS RED — STOP THE LINE

Detected: Test failure(s) blocking forward progress
Failing Tests: [LIST TESTS]
Pipeline Status: FAILED

Required Actions:
1. STOP all new development immediately
2. Identify root cause of failure
3. Fix tests (not skip them)
4. Achieve GREEN status
5. Resume only after CI = SUCCESS

Rule: Agent-First Execution Doctrine v1 §1
Governance Maxim: No green, no go.
```

### Template 3: Missing Training Artifact

```
⛔ REJECT: TRAINING LOOP VIOLATION

Detected: Incident without training artifact
Incident: [INCIDENT DESCRIPTION]
Date: [DATE]

Required Fix:
1. Create training artifact in docs/agent_university/
2. Document: What happened, why, how to prevent
3. Update relevant agent's grading record
4. Submit evidence of completion

Rule: Agent-First Execution Doctrine v1 §1
Governance Maxim: Every failure is a lesson—document it.
```

---

## 5. GRADING IMPACT

### Compliance Multiplier

Agents are graded weekly. Agent-First compliance affects the score:

| Compliance Level | Multiplier | Effect |
|------------------|------------|--------|
| Full compliance | 1.0x | Score unchanged |
| Minor violation (1 instance) | 0.9x | 10% penalty |
| Major violation (2+ instances) | 0.7x | 30% penalty |
| Stop-the-line ignored | 0.5x | 50% penalty |

**Example:**
- Agent scores 85 points this week
- But ignored a stop-the-line once
- Final score: 85 × 0.5 = 42.5 → L1 (not L2)

### Violation Escalation

| Violation | First | Second | Third |
|-----------|-------|--------|-------|
| Agent-First bypass | WARN | REJECT | BLOCK |
| Tests ignored | REJECT | BLOCK | RETRAIN |
| Missing training artifact | WARN | WARN | REJECT |

---

## 6. WORKFLOW INTEGRATION

### Pre-Round Checklist Addition

Before starting any round:
```
☐ All tasks assigned to agents (not humans)
☐ CI pipeline is GREEN
☐ No outstanding training artifacts missing
```

### WRAP Linter Addition

When reviewing WRAPs:
```
☐ Was this executed by an agent? (YES = pass, NO = REJECT)
☐ If tests failed, did we stop the line? (YES = pass, NO = REJECT)
```

### PAC Standard Addition

Every PAC must include:
```
Agent-First Confirmation: ☐ This work is assigned to an agent
Test Gate: ☐ Tests were green before starting
```

---

## 7. DEFINITIONS

| Term | Definition |
|------|------------|
| **Agent-First** | Default assumption that agents execute all work unless CEO exception applies |
| **Stop-the-Line** | Immediate halt to all forward progress when tests fail |
| **Training Loop** | Mandatory process of converting failures into learning artifacts |
| **CEO-Only** | The 6 tasks that require human execution (see §2) |
| **Green** | All tests passing, CI pipeline SUCCESS |
| **Red** | Any test failing, CI pipeline FAILED |

---

## 8. DOCUMENT GOVERNANCE

- **Owner:** ALEX (GID-08)
- **Reviewers:** BENSON (GID-00)
- **Modification:** Requires ALEX + BENSON dual approval
- **Review Cycle:** Quarterly or upon policy change
- **Enforcement:** Immediate upon document lock

---

## 9. REFERENCES

- [PAC_STANDARD.md](./PAC_STANDARD.md)
- [ROUND_OPERATOR_CHECKLIST.md](./ROUND_OPERATOR_CHECKLIST.md)
- [WRAP_LINTER_CHECKLIST.md](./WRAP_LINTER_CHECKLIST.md)
- [MONDAY_GRADING_RITUAL_v1.md](./MONDAY_GRADING_RITUAL_v1.md)
- [VIOLATION_ESCALATION_v1.md](./VIOLATION_ESCALATION_v1.md)

---

**Document Hash:** `AGENT-FIRST-v1-20251215`
**Status:** LOCKED
