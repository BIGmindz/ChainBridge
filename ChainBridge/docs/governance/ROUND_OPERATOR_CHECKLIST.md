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

---

## Execution (Steps 4-7)

### Step 4: Monitor Execution
```
☐ Agents working on assigned PACs
☐ No scope creep detected
☐ No unauthorized cross-agent work
```
**If violation:** Issue `⛔ HALT` immediately.

### Step 5: Receive WRAPs
```
☐ WRAP received from each PAC
☐ No partial logs or streaming output
☐ Single agent per WRAP
```

### Step 6: Lint Each WRAP
```
☐ Run WRAP_LINTER_CHECKLIST.md (10 checks)
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
| 5 | Receive WRAPs | No partials |
| 6 | Lint WRAPs | 10-check pass |
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
