# WRAP Linter Checklist v1.0

> **Governance Document** — AU07.A
> **Version:** 1.0.0
> **Effective Date:** 2025-12-15
> **Owner:** BENSON (GID-00)
> **Usage:** Review every WRAP in <60 seconds

---

## Quick Reference

**Pass = All 14 checks YES** ← Updated from 12
**Fail = Any check NO → REJECT immediately**

---

## The 14-Point Check

| # | Check | YES/NO |
|---|-------|--------|
| 1 | **Color Block Present?** — START banner has correct emoji for GID | ☐ |
| 2 | **GID Valid?** — Agent GID exists in CANON_REGISTRY_v1.md | ☐ |
| 3 | **Role Matches?** — Role in header matches registry | ☐ |
| 4 | **END Block Present?** — Matching END banner with same GID | ☐ |
| 5 | **Single Agent?** — Only one agent authored this WRAP | ☐ |
| 6 | **All Sections Present?** — Has: Scope, Implementation, Guarantees, Tests, Checklist, Open Issues | ☐ |
| 7 | **No Partial Logs?** — No mid-execution commentary, only final output | ☐ |
| 8 | **Tests Included?** — Evidence of validation (commands, output, or explicit skip reason) | ☐ |
| 9 | **Scope Matches PAC?** — Work done matches the assigned PAC scope | ☐ |
| 10 | **Acceptance Criteria Met?** — All criteria from PAC are checked off | ☐ |
| 11 | **Agent-First Compliance?** — Was this executed by an agent (not human)? | ☐ |
| 12 | **Stop-the-Line Compliance?** — If tests failed, did we halt before proceeding? | ☐ |
| 13 | **Reset Compliance?** — If RESET issued this session, was valid RESET-ACK submitted? ⚪ NEW | ☐ |
| 14 | **Resume Gate Passed?** — If reset occurred, did agent wait for RESUME before continuing? ⚪ NEW | ☐ |

---

## Decision Tree

```
START
  │
  ▼
Check 1-4 (Format) ──NO──▶ 🔁 REJECT "Format violation"
  │
  YES
  │
  ▼
Check 5 (Single Agent) ──NO──▶ 🔁 REJECT "Multi-agent bleed"
  │
  YES
  │
  ▼
Check 6-7 (Content) ──NO──▶ 🔁 REJECT "Missing sections / partial logs"
  │
  YES
  │
  ▼
Check 8-10 (Quality) ──NO──▶ 🔁 REJECT "Incomplete work"
  │
  YES
  │
  ▼
Check 11 (Agent-First) ──NO──▶ ⛔ REJECT "Human executed agent work"
  │
  YES
  │
  ▼
Check 12 (Stop-the-Line) ──NO──▶ ⛔ HALT "Tests red — stop the line"
  │
  YES
  │
  ▼
Check 13 (Reset Compliance) ──NO──▶ ⛔ BLOCK "Ignored RESET command"
  │
  YES
  │
  ▼
Check 14 (Resume Gate) ──NO──▶ ⛔ BLOCK "Continued without RESUME"
  │
  YES
  │
  ▼
✅ ACCEPT
```

---

## Rejection Templates

### Format Violation (Checks 1-4)
```
🔁 REJECT — [PAC-XX-NAME]

Violation: Format non-compliant
Details: [Missing START block / Wrong emoji / Missing END / etc.]
Fix: Resubmit with correct WRAP format per CANON_REGISTRY_v1.md
```

### Multi-Agent Bleed (Check 5)
```
🔁 REJECT — [PAC-XX-NAME]

Violation: Multiple agents in single WRAP
Details: Found [AGENT-A] and [AGENT-B] content mixed
Fix: One WRAP per agent. Credit collaborators in text, don't merge blocks.
```

### Missing Sections (Check 6)
```
🔁 REJECT — [PAC-XX-NAME]

Violation: Missing required sections
Missing: [List missing sections]
Fix: Include all 6 required sections per WRAP standard
```

### Partial Logs (Check 7)
```
🔁 REJECT — [PAC-XX-NAME]

Violation: Partial/streaming output detected
Details: WRAP contains mid-execution logs instead of final summary
Fix: Resubmit with final WRAP only, no running commentary
```

### Incomplete Work (Checks 8-10)
```
🔁 REJECT — [PAC-XX-NAME]

Violation: Acceptance criteria not met
Missing: [List unmet criteria]
Fix: Complete work, add evidence, resubmit
```

### Agent-First Violation (Check 11) ⚪ NEW
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

### Stop-the-Line Violation (Check 12) ⚪ NEW
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

### Reset Non-Compliance (Check 13) ⚪ NEW
```
⛔ BLOCK: IGNORED RESET COMMAND

Detected: RESET issued but no valid RESET-ACK received
Reset Command: {RESET | HARD RESET}
Time Since Reset: {minutes}

Required Actions:
1. Submit valid RESET-ACK immediately
2. Clear all prior context
3. Reload PAC scope
4. Wait for RESUME command

Violation: V-H-006
Reference: AGENT_RESET_PIPELINE_v1.md §4
```

### Resume Gate Violation (Check 14) ⚪ NEW
```
⛔ BLOCK: CONTINUED WITHOUT RESUME

Detected: Agent continued operations after reset without RESUME command
Last Command: RESET / HARD RESET
RESUME Issued: NO

Required Actions:
1. STOP all operations immediately
2. Wait for explicit RESUME command
3. Do not generate any output until resumed

Violation: V-H-007
Reference: AGENT_RESET_PIPELINE_v1.md §7
```

---

## Speed Tips for Reviewers

1. **Scan format first** — 5 seconds to check color blocks
2. **Ctrl+F for sections** — Search for "Scope", "Implementation", "Tests"
3. **Check checklist** — Are all boxes checked?
4. **Trust but verify** — Spot-check one test command
5. **No negotiation** — If it fails, reject immediately

---

## Common Mistakes (Auto-Reject)

| Mistake | Why It's Wrong |
|---------|----------------|
| `🔵 START — BENSON` | Wrong color for BENSON (should be 🟦🟩) |
| No END block | Incomplete WRAP format |
| "I'm going to..." | Narration, not final output |
| Missing GID | Can't verify agent identity |
| Two agents in one WRAP | Violates single-authorship rule |
| "Tests: TODO" | No evidence of validation |
| Human executed task | Agent-First violation (Check 11) |
| Ignored red tests | Stop-the-Line violation (Check 12) |
| No RESET-ACK after reset | Reset non-compliance (Check 13) ⚪ NEW |
| Continued without RESUME | Resume gate violation (Check 14) ⚪ NEW |

---

## Enforcement

- **BENSON (GID-00)** runs this checklist on every WRAP
- **Rejection is immediate** — no "let me check with..."
- **Pattern tracking** — Repeated failures logged per agent
- **Escalation** — 3+ failures in one round → ALEX review

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2025-12-15 | Initial release |
