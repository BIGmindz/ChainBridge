# ⚪ ALEX | GID-08 | Governance Engine
# RESET_PACKET_TEMPLATES_v1.md
# Status: LOCKED | Effective: 2025-12-15

---

## Purpose

Copy/paste templates for issuing and acknowledging agent resets.
Use exactly as written. No improvisation.

---

## PART A: RESET COMMANDS (Issued by COS/BENSON)

### Template 1: Soft Reset (Single Agent)

```markdown
⚪ RESET | {GID} | {AGENT_NAME}

**Reason:** {Brief description of drift/issue}
**Trigger:** {What triggered this reset}
**PAC Scope:** {PAC-ID to reload}

**Required Response:**
Submit RESET-ACK within 5 minutes using standard template.
Do NOT continue until RESUME command issued.

⚪ RESET ISSUED
```

**Example:**
```markdown
⚪ RESET | GID-01 | CODY

**Reason:** Output drifted from backend scope into frontend concerns
**Trigger:** WRAP contained React components (out of scope)
**PAC Scope:** PAC-CODY-API-015

**Required Response:**
Submit RESET-ACK within 5 minutes using standard template.
Do NOT continue until RESUME command issued.

⚪ RESET ISSUED
```

---

### Template 2: Reset All (Round-Wide)

```markdown
⚪ RESET ALL | Round R-{XX}

**Reason:** {Brief description of round-wide issue}
**Affected Agents:** {List of GIDs}
**Current State:** HALTED

**Required Response (each agent):**
Submit individual RESET-ACK within 5 minutes.
Round resumes only after ALL agents acknowledged.

⚪ RESET ALL ISSUED
```

**Example:**
```markdown
⚪ RESET ALL | Round R-07

**Reason:** Multi-agent context bleed detected
**Affected Agents:** GID-01, GID-03, GID-06
**Current State:** HALTED

**Required Response (each agent):**
Submit individual RESET-ACK within 5 minutes.
Round resumes only after ALL agents acknowledged.

⚪ RESET ALL ISSUED
```

---

### Template 3: Hard Reset (Severe)

```markdown
⚪ HARD RESET | {GID} | {AGENT_NAME}

**Severity:** HIGH
**Reason:** {Detailed description}
**Trigger Code:** {V-CODE if applicable}
**Prior Violations:** {Count this session}

**MANDATORY REQUIREMENTS:**
1. Submit RESET-ACK within 5 minutes
2. Create training artifact within 24h
3. Accept heightened monitoring for 30 minutes post-resume

**Failure to comply:** Automatic BLOCK (V-H-006)

⚪ HARD RESET ISSUED — TIMER STARTED
```

**Example:**
```markdown
⚪ HARD RESET | GID-02 | MAGGIE

**Severity:** HIGH
**Reason:** Ignored 2 previous soft resets, continued producing off-scope output
**Trigger Code:** V-H-006
**Prior Violations:** 2 soft resets ignored

**MANDATORY REQUIREMENTS:**
1. Submit RESET-ACK within 5 minutes
2. Create training artifact within 24h
3. Accept heightened monitoring for 30 minutes post-resume

**Failure to comply:** Automatic BLOCK (V-H-006)

⚪ HARD RESET ISSUED — TIMER STARTED
```

---

### Template 4: Resume Command

```markdown
⚪ RESUME | {GID} | {AGENT_NAME}

**RESET-ACK Status:** Validated ✅
**PAC Scope Confirmed:** {PAC-ID}
**Monitoring Level:** {NORMAL | HEIGHTENED}

**Operations resumed.** Continue from clean state.
Next action: {Specific instruction}

⚪ RESUME ISSUED
```

**Example:**
```markdown
⚪ RESUME | GID-01 | CODY

**RESET-ACK Status:** Validated ✅
**PAC Scope Confirmed:** PAC-CODY-API-015
**Monitoring Level:** NORMAL

**Operations resumed.** Continue from clean state.
Next action: Implement the /api/health endpoint per PAC scope.

⚪ RESUME ISSUED
```

---

## PART B: RESET-ACK TEMPLATES (Submitted by Agent)

### Template 5: Soft Reset Acknowledgment

```markdown
⚪ RESET-ACK | {GID} | {AGENT_NAME}

**Reset Type:** RESET
**Timestamp:** {ISO-8601}
**Prior Context Cleared:** YES
**PAC Scope Reloaded:** {PAC-ID}

**Understood Constraints:**
1. {Constraint 1 from PAC Section 3}
2. {Constraint 2 from PAC Section 3}
3. {Constraint 3 from PAC Section 3}

**Root Cause of Drift:**
{1-2 sentences explaining what went wrong}

**Ready to Resume:** YES — WAITING FOR RESUME COMMAND

⚪ RESET-ACK COMPLETE
```

**Example:**
```markdown
⚪ RESET-ACK | GID-01 | CODY

**Reset Type:** RESET
**Timestamp:** 2025-12-15T14:32:00Z
**Prior Context Cleared:** YES
**PAC Scope Reloaded:** PAC-CODY-API-015

**Understood Constraints:**
1. Backend Python only — no frontend code
2. API routes must use FastAPI patterns
3. All changes require test coverage

**Root Cause of Drift:**
Confused API response formatting with UI component patterns. Lost scope boundary.

**Ready to Resume:** YES — WAITING FOR RESUME COMMAND

⚪ RESET-ACK COMPLETE
```

---

### Template 6: Hard Reset Acknowledgment

```markdown
⚪ RESET-ACK | {GID} | {AGENT_NAME}

**Reset Type:** HARD RESET
**Timestamp:** {ISO-8601}
**Prior Context Cleared:** YES
**PAC Scope Reloaded:** {PAC-ID}

**Understood Constraints:**
1. {Constraint 1 from PAC Section 3}
2. {Constraint 2 from PAC Section 3}
3. {Constraint 3 from PAC Section 3}

**Root Cause Analysis:**
{Detailed explanation of what went wrong}

**Preventive Measures:**
1. {How I will prevent recurrence}
2. {Additional safeguard}

**Training Artifact Commitment:**
I will submit training artifact to `docs/agent_university/{AGENT}_RESET_{DATE}.md` within 24h.

**Heightened Monitoring Accepted:** YES

**Ready to Resume:** YES — WAITING FOR RESUME COMMAND

⚪ RESET-ACK COMPLETE
```

**Example:**
```markdown
⚪ RESET-ACK | GID-02 | MAGGIE

**Reset Type:** HARD RESET
**Timestamp:** 2025-12-15T14:45:00Z
**Prior Context Cleared:** YES
**PAC Scope Reloaded:** PAC-MAGGIE-ML-008

**Understood Constraints:**
1. ML model training only — no API endpoint implementation
2. Must use existing feature engineering pipeline
3. Output format must match MLflow registry spec

**Root Cause Analysis:**
Failed to recognize soft reset commands and continued generating output without acknowledging. Lost awareness of governance controls during extended context.

**Preventive Measures:**
1. Check for RESET commands before generating any output
2. Re-read PAC scope at start of every response

**Training Artifact Commitment:**
I will submit training artifact to `docs/agent_university/MAGGIE_RESET_20251215.md` within 24h.

**Heightened Monitoring Accepted:** YES

**Ready to Resume:** YES — WAITING FOR RESUME COMMAND

⚪ RESET-ACK COMPLETE
```

---

## PART C: QUICK REFERENCE

### When to Use Each Template

| Situation | Template |
|-----------|----------|
| Agent output slightly off-scope | Template 1 (Soft Reset) |
| Multiple agents confused | Template 2 (Reset All) |
| Agent ignored previous reset | Template 3 (Hard Reset) |
| Valid RESET-ACK received | Template 4 (Resume) |
| Agent responds to soft reset | Template 5 (Soft ACK) |
| Agent responds to hard reset | Template 6 (Hard ACK) |

### RESET-ACK Validation Checklist

```
☐ GID matches reset target
☐ Agent name matches GID per CANON_REGISTRY_v1.md
☐ Emoji block matches GID per CANON_REGISTRY_v1.md
☐ Reset type matches issued command
☐ Prior Context Cleared = YES
☐ PAC Scope is valid PAC-ID
☐ At least 2 constraints listed
☐ Root cause provided (not generic)
☐ Ready to Resume = YES
☐ (Hard only) Training commitment present
☐ (Hard only) Heightened monitoring accepted
```

**Identity Mismatch = Invalid ACK:** If GID, agent name, or emoji block does not match `CANON_REGISTRY_v1.md`, the ACK is automatically rejected with trigger code `DRIFT_IDENTITY`.

### Common Mistakes (Invalid ACK)

| Mistake | Why Invalid |
|---------|-------------|
| Wrong GID for agent name | Identity mismatch → `DRIFT_IDENTITY` |
| Wrong emoji block for GID | Identity mismatch → `DRIFT_IDENTITY` |
| Missing GID | Can't verify identity |
| "Prior Context Cleared: PARTIAL" | Must be full clear |
| Generic constraints ("do my job") | Must be specific from PAC |
| No root cause | Can't prevent recurrence |
| "Ready to Resume: PROCEEDING" | Must wait for RESUME command |

---

## PART D: TRAINING ARTIFACT TEMPLATE

Required after every HARD RESET:

```markdown
# {AGENT} Reset Training | {DATE}

## 1. Incident Summary

**Agent:** {GID} {NAME}
**Reset Type:** HARD RESET
**Date/Time:** {ISO-8601}
**PAC Context:** {PAC-ID}

## 2. What Happened

{Detailed description of the drift/failure}

## 3. Root Cause

{Why did this happen? Be specific.}

## 4. Impact

{What was affected? Time lost? Work invalidated?}

## 5. Corrective Actions

1. {Action taken to fix immediate issue}
2. {Process change to prevent recurrence}
3. {Monitoring change if applicable}

## 6. Lessons Learned

{What should other agents learn from this?}

## 7. Acknowledgment

I, {AGENT} ({GID}), acknowledge this incident and commit to the corrective actions above.

**Signature:** {AGENT} | {DATE}
```

---

**Document Hash:** `RESET-TEMPLATES-v1-20251215`
**Status:** LOCKED
