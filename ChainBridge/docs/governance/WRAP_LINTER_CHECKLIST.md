# WRAP Linter Checklist v1.0

> **Governance Document** — AU07.A
> **Version:** 1.0.0
> **Effective Date:** 2025-12-15
> **Owner:** BENSON (GID-00)
> **Usage:** Review every WRAP in <60 seconds

---

## Quick Reference

**Pass = All 10 checks YES**
**Fail = Any check NO → REJECT immediately**

---

## The 10-Point Check

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
