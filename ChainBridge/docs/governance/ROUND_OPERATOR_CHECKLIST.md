# Round Operator Checklist v1.0

> **Governance Document** — AU07.A
> **Version:** 1.0.0
> **Effective Date:** 2025-12-15
> **Owner:** BENSON (GID-00)
> **User:** Alex (Human CEO)

---

## Purpose

The 12-step checklist for running any ChainBridge execution round. Follow in order. No skipping.

---

## Pre-Round (Steps 1-3)

### Step 1: Verify Prior Round Lock
```
☐ Previous round status = LOCKED
☐ All prior WRAPs accepted
☐ No outstanding rejections
```
**If not locked:** Do not start new round. Resolve first.

### Step 2: Define Round Scope
```
☐ Round number assigned (e.g., R-07)
☐ Mission statement written (1-2 sentences)
☐ Doctrine alignment confirmed (Trust > Tracking)
```

### Step 3: Issue PACs
```
☐ Each PAC has: Agent, Scope, Acceptance Criteria
☐ PAC uses correct template
☐ Agents acknowledged receipt
```

### Step 3.5: Agent-First Gate ⚪ NEW
```
☐ All tasks assigned to agents (not humans)
☐ No CEO-only exception claimed without justification
☐ CI pipeline is GREEN before starting
☐ No outstanding training artifacts missing
```
**If human attempts non-CEO-only work:** Issue `⛔ REJECT: AGENT-FIRST VIOLATION`
**If tests are RED:** Issue `⛔ HALT: TESTS RED — STOP THE LINE`

Reference: [AGENT_FIRST_EXECUTION_DOCTRINE_v1.md](./AGENT_FIRST_EXECUTION_DOCTRINE_v1.md)

---

## Execution (Steps 4-7)

### Step 4: Monitor Execution
```
☐ Agents working on assigned PACs
☐ No scope creep detected
☐ No unauthorized cross-agent work
```
**If violation:** Issue `⛔ HALT` immediately.

### Step 4.5: Reset Step (If Drift Detected) ⚪ NEW
```
☐ Drift or format violation detected?
☐ Issue appropriate RESET command (see AGENT_RESET_PIPELINE_v1.md)
☐ Wait for valid BOXED RESET-ACK (max 5 minutes)
    - **Check 1:** Is it a BOXED RESET-ACK with correct top+bottom emoji banners (matches CANON_REGISTRY_v1.md)?
    - **Check 2:** Are all 6 parts present?
    - **Check 3:** Is the Status exactly "READY — awaiting RESUME"?
☐ If valid: Issue `RESUME` command.
☐ If invalid: Re-issue RESET (Escalate severity).
```
**If RESET-ACK is not boxed:** Treat as `DRIFT_FORMAT` and re-issue RESET immediately (no negotiation).
**If narration/logs appear between RESET-ACK and RESUME:** Escalate to **HARD_RESET** on the next command.
**If no RESET-ACK within 5 min:** Escalate to HARD RESET or BLOCK
**Reference:** [AGENT_RESET_PIPELINE_v1.md](./AGENT_RESET_PIPELINE_v1.md)

### Step 5: Receive WRAPs
```
☐ WRAP received from each PAC
☐ No partial logs or streaming output
☐ Single agent per WRAP
```

### Step 5.5: Resume Gate (After Reset) ⚪ NEW
```
☐ If reset was issued: RESET-ACK validated
☐ Issue RESUME command to cleared agent(s)
☐ Confirm agent acknowledged RESUME
☐ Heightened monitoring active (30 min post-reset)
```
**Do NOT accept WRAPs from reset agents until RESUME issued.**
**If output appears before RESUME after a reset:** Trigger HARD_RESET immediately.
**Reference:** [RESET_PACKET_TEMPLATES_v1.md](./RESET_PACKET_TEMPLATES_v1.md)

### Step 6: Lint Each WRAP
```
☐ Run WRAP_LINTER_CHECKLIST.md (14 checks) ← Updated from 12
☐ All checks pass = ACCEPT
☐ Any check fails = REJECT with template
```
**Do not negotiate.** Binary decision only.

### Step 7: Handle Rejections
```
☐ Rejection issued with specific fix request
☐ Agent resubmits corrected WRAP
☐ Re-lint from Step 6
```
**Loop until all WRAPs accepted or round halted.**

---

## Post-Round (Steps 8-10)

### Step 8: Security Gate
```
☐ SAM (GID-06) reviews security-impacting changes
☐ No security objections
☐ Clear to merge
```
**If SAM objects:** Resolve before proceeding.

### Step 9: Lock Round
```
☐ All WRAPs accepted
☐ All acceptance criteria met
☐ Declare: "Round R-XX: ✅ LOCKED"
```

### Step 10: Commit/Merge
```
☐ Stage all round artifacts
☐ Commit with round reference
☐ Push to branch
```

---

## Governance (Steps 11-12)

### Step 11: Update Logs
```
☐ Round logged in AGENT_ACTIVITY_LOG.md
☐ Any violations noted
☐ Any escalations recorded
```

### Step 12: Prepare Next Round
```
☐ Identify next mission
☐ Note any carryover items
☐ Ready for next round kickoff
```

---

## Quick Reference Card

| Step | Action | Gate |
|------|--------|------|
| 1 | Verify prior lock | Cannot start if unlocked |
| 2 | Define scope | Must have mission |
| 3 | Issue PACs | Must have acceptance criteria |
| 4 | Monitor | Halt on violation |
| 4.5 | Reset (if needed) | Valid BOXED RESET-ACK required ⚪ NEW |
| 5 | Receive WRAPs | No partials |
| 5.5 | Resume Gate | RESUME before continue ⚪ NEW |
| 6 | Lint WRAPs | 14-check pass |
| 7 | Handle rejections | Loop until clean |
| 8 | Security gate | SAM approval |
| 9 | Lock round | Explicit declaration |
| 10 | Merge | Commit with reference |
| 11 | Update logs | Activity tracked |
| 12 | Prepare next | Continuous flow |

---

## Emergency Procedures

### Mid-Round Halt
```
⛔ HALT — Round R-XX

Reason: [Specific issue]
Action: [What needs to happen]
Resume: After [condition]
```

### Round Abandonment
```
❌ ABANDON — Round R-XX

Reason: [Why round cannot complete]
Carryover: [What moves to next round]
Post-mortem: Required within 24h
```

---

## Time Expectations

| Phase | Expected Duration |
|-------|-------------------|
| Pre-Round (1-3) | 5-10 minutes |
| Execution (4-7) | Variable (agent work) |
| WRAP Review (per WRAP) | <60 seconds |
| Post-Round (8-12) | 5-10 minutes |

---

## Enforcement

- **Alex (CEO)** is the operator
- **BENSON (GID-00)** assists execution
- **ALEX (GID-08)** handles governance escalations
- **SAM (GID-06)** handles security escalations

**This checklist is mandatory for every round.**
