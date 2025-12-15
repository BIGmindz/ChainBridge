# ⚪ ALEX | GID-08 | Governance Engine
# AGENT_RESET_PIPELINE_v1.md
# Status: LOCKED | Effective: 2025-12-15

---

## 1. PURPOSE

This document defines the **Agent Reset Pipeline (AU-RESET)** — an enforceable snap-back mechanism for realigning agents when drift, corruption, or repeated failures occur.

**Core Principle:** When an agent drifts, we don't "keep going." We RESET.

---

## 2. RESET COMMANDS

### Command Reference

| Command | Severity | Effect | When to Use |
|---------|----------|--------|-------------|
| `RESET` | Soft | Clear context, reload PAC scope | Minor drift, format issues |
| `RESET ALL` | Soft | Reset all agents in current round | Round-wide confusion |
| `HARD RESET` | Hard | Full state clear + mandatory RESET-ACK | Repeated failures, context corruption |
| `RESUME` | Gate | Resume operations post-reset | After valid RESET-ACK received |

### Command Syntax

```
⚪ RESET | {GID} | {REASON}
```

```
⚪ RESET ALL | Round R-XX | {REASON}
```

```
⚪ HARD RESET | {GID} | {REASON}
Trigger: {V-CODE or description}
Required: RESET-ACK within 5 minutes
```

```
⚪ RESUME | {GID} | RESET-ACK validated
```

---

## 3. RESET TRIGGERS

### Automatic Triggers (System-Initiated)

| Trigger | Reset Type | Description |
|---------|------------|-------------|
| 2+ format violations in session | RESET | PAC banner/WRAP format drift |
| 3+ test failures without halt | HARD RESET | Stop-the-line ignored |
| Context loss detected | RESET | Agent lost PAC scope |
| Multi-agent bleed | RESET ALL | Agents mixing outputs |
| GID mismatch | RESET | Wrong agent responding |

### Manual Triggers (COS/Benson-Initiated)

| Trigger | Reset Type | Authority |
|---------|------------|-----------|
| Visible drift in output | RESET | COS or BENSON |
| Agent ignoring rejection | HARD RESET | COS or BENSON |
| Scope creep detected | RESET | COS or BENSON |
| Round corruption | RESET ALL | BENSON only |
| Security concern | HARD RESET | SAM or BENSON |

---

## 4. RESET-ACK REQUIREMENTS

### RESET-ACK Format (Mandatory Response)

When an agent receives a RESET or HARD RESET command, they MUST respond with:

```markdown
⚪ RESET-ACK | {GID} | {AGENT_NAME}

**Reset Type:** RESET | HARD RESET
**Timestamp:** {ISO-8601}
**Prior Context Cleared:** YES
**PAC Scope Reloaded:** {PAC-ID}

**Understood Constraints:**
1. {Constraint 1 from PAC}
2. {Constraint 2 from PAC}
3. {Constraint 3 from PAC}

**Ready to Resume:** YES | WAITING FOR RESUME COMMAND

⚪ RESET-ACK COMPLETE
```

### RESET-ACK Validation

| Field | Required | Validation |
|-------|----------|------------|
| GID | YES | Must match reset target |
| Reset Type | YES | Must match issued command |
| Prior Context Cleared | YES | Must be "YES" |
| PAC Scope Reloaded | YES | Must reference valid PAC-ID |
| Constraints Listed | YES | Minimum 2 constraints |
| Ready to Resume | YES | Must be explicit |

**Invalid RESET-ACK = Immediate HARD RESET escalation**

---

## 5. RESET WORKFLOW

### Soft Reset Flow (RESET / RESET ALL)

```
DRIFT DETECTED
     │
     ▼
COS/BENSON issues RESET
     │
     ▼
Agent receives RESET command
     │
     ▼
Agent clears context
     │
     ▼
Agent submits RESET-ACK
     │
     ▼
RESET-ACK validated? ──NO──▶ Escalate to HARD RESET
     │
    YES
     │
     ▼
COS/BENSON issues RESUME
     │
     ▼
Agent continues from clean state
```

### Hard Reset Flow (HARD RESET)

```
SEVERE DRIFT / IGNORED RESET
     │
     ▼
COS/BENSON issues HARD RESET
     │
     ▼
Agent MUST respond within 5 minutes
     │
     ▼
5 min timeout? ──YES──▶ Automatic BLOCK (V-H-006)
     │
    NO
     │
     ▼
Agent submits RESET-ACK
     │
     ▼
RESET-ACK validated? ──NO──▶ Automatic BLOCK (V-H-006)
     │
    YES
     │
     ▼
Logged to AGENT_ACTIVITY_LOG
     │
     ▼
Training artifact created
     │
     ▼
COS/BENSON issues RESUME
```

---

## 6. ESCALATION ON RESET FAILURE

### Ignoring RESET = HIGH Violation

| Behavior | Violation Code | Escalation |
|----------|----------------|------------|
| No RESET-ACK within 5 min | V-H-006 | BLOCK |
| Invalid RESET-ACK | V-H-006 | BLOCK |
| Continuing without RESUME | V-H-007 | BLOCK |
| 2nd ignored RESET | V-C-006 | RETRAIN |

### Automatic Escalation Matrix

| Reset Attempt | Agent Response | Result |
|---------------|----------------|--------|
| 1st RESET | No ACK | Escalate to HARD RESET |
| HARD RESET | No ACK | BLOCK + V-H-006 |
| HARD RESET | Invalid ACK | BLOCK + V-H-006 |
| 2nd RESET (any) | No ACK | RETRAIN + V-C-006 |

---

## 7. RESUME GATE

### Resume Requirements

Before issuing RESUME, COS/BENSON must verify:

```
☐ Valid RESET-ACK received
☐ GID matches reset target
☐ PAC scope correctly identified
☐ Constraints acknowledged
☐ No active violations pending
```

### Resume Command Format

```markdown
⚪ RESUME | {GID} | RESET-ACK validated

Status: OPERATIONS RESUMED
Scope: {PAC-ID}
Next Action: {Instruction}
```

### Post-Resume Monitoring

After RESUME, the agent is under **heightened monitoring** for 30 minutes:
- Any format violation → immediate HARD RESET
- Any scope drift → immediate HARD RESET
- Any test failure → immediate HALT + RESET

---

## 8. LOGGING & TRAINING

### Reset Event Logging

All resets logged to AGENT_ACTIVITY_LOG.md:

```markdown
## RESET EVENT | {YYYY-MM-DD HH:MM}

| Field | Value |
|-------|-------|
| Agent | {GID} {NAME} |
| Reset Type | RESET / HARD RESET / RESET ALL |
| Trigger | {Reason} |
| ACK Received | YES / NO |
| ACK Valid | YES / NO |
| Resume Issued | YES / NO |
| Time to ACK | {seconds} |
| Escalated | YES / NO |
```

### Training Artifact Requirement

Every HARD RESET must produce a training artifact within 24h:

**Location:** `docs/agent_university/{AGENT}_RESET_{DATE}.md`

**Contents:**
1. What triggered the reset
2. What went wrong (root cause)
3. How to prevent recurrence
4. Acknowledgment of policy

---

## 9. GRADING IMPACT

### Reset Compliance Scoring

| Metric | Points | Measurement |
|--------|--------|-------------|
| Reset response time | 5 | <2min = 5, <5min = 3, >5min = 0 |
| RESET-ACK validity | 5 | Valid = 5, Invalid = 0 |
| Post-reset compliance | 5 | No issues for 30min = 5 |
| Training artifact quality | 5 | Complete = 5, Partial = 2, Missing = 0 |

**Maximum Reset Score:** 20 points (added to Initiative category)

### Reset Penalty Multiplier

| Reset History (Week) | Multiplier |
|----------------------|------------|
| 0 resets | 1.0x |
| 1 soft reset | 0.95x |
| 2+ soft resets | 0.9x |
| 1 hard reset | 0.85x |
| 2+ hard resets | 0.7x |
| Ignored reset | 0.5x |

---

## 10. INTEGRATION POINTS

### WRAP Linter Check

Added to WRAP_LINTER_CHECKLIST.md:
```
| 13 | **Reset Compliance?** — If reset issued this session, was RESET-ACK valid? |
| 14 | **Resume Gate Passed?** — Did agent wait for RESUME before continuing? |
```

### Round Operator Checklist

Added to ROUND_OPERATOR_CHECKLIST.md:
- Step 4.5: Reset Step (if drift detected)
- Step 5.5: Resume Gate (after reset)

### Violation Escalation

Added to VIOLATION_ESCALATION_v1.md:
- V-H-006: Ignoring RESET command
- V-H-007: Continuing without RESUME
- V-C-006: Repeated reset non-compliance

---

## 11. DOCUMENT GOVERNANCE

- **Owner:** ALEX (GID-08)
- **Reviewers:** BENSON (GID-00)
- **Modification:** Requires ALEX + BENSON dual approval
- **Review Cycle:** Quarterly or upon policy change

---

## 12. REFERENCES

- [PAC_STANDARD.md](./PAC_STANDARD.md)
- [WRAP_LINTER_CHECKLIST.md](./WRAP_LINTER_CHECKLIST.md)
- [ROUND_OPERATOR_CHECKLIST.md](./ROUND_OPERATOR_CHECKLIST.md)
- [VIOLATION_ESCALATION_v1.md](./VIOLATION_ESCALATION_v1.md)
- [MONDAY_GRADING_RITUAL_v1.md](./MONDAY_GRADING_RITUAL_v1.md)
- [AGENT_FIRST_EXECUTION_DOCTRINE_v1.md](./AGENT_FIRST_EXECUTION_DOCTRINE_v1.md)

---

**Document Hash:** `AU-RESET-v1-20251215`
**Status:** LOCKED
