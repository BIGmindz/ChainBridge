# 🟪 PAC-06-C: Operator Trust & Cognitive Load Layer

> 🟪 LIRA (GID-09) — UX Systems & Operator Experience
> Version: 1.0
> Last Updated: 2025-12-15

---

## Purpose

This document defines UX patterns and validation criteria that ensure:

1. **Operators trust the system** — Clear, honest status communication
2. **Operators understand decisions** — Explainability at a glance
3. **Operators do not panic under stress** — Calm, controlled interfaces
4. **The OC feels calm, explainable, and in control** — Professional command-center grade

**This is human-factor hardening, not cosmetics.**

---

## Design Principles

### 1. Trust > Tracking

The system exists to help operators, not to surveil them. Every UI element should reinforce operator confidence and agency.

### 2. Calm Under Pressure

High-stress moments require calm interfaces. Animations are slow. Colors are muted unless action is required. Language is clear and direct.

### 3. No Red Unless Action Required

Red is reserved for states requiring immediate human intervention. Yellow/amber for attention. Green for healthy. Blue for informational/processing.

### 4. Decision Explainability in ≤3 Bullets

Any automated decision must be explainable in three bullet points or fewer, visible to the operator without navigation.

### 5. Cognitive Load Budget

- **1 primary action per panel** — No decision paralysis
- **Secondary actions collapsed by default** — Progressive disclosure
- **Max 7±2 items** in any list without pagination/grouping

### 6. Neurodiverse-First Patterns

- Predictable, consistent layouts
- No flashing or jittering elements
- Slow, intentional transitions (300ms+)
- High contrast text (WCAG 2.1 AA)
- Reduced motion support (`prefers-reduced-motion`)

---

## UX Validation Checklist

### Scenario 1: High-Risk Decision Review

| Criterion | Pass/Fail | Notes |
|-----------|-----------|-------|
| Risk tier is immediately visible | | |
| Risk explanation shows ≤3 contributing factors | | |
| "Why this decision?" is answerable in <60s | | |
| Recommended action is clear and singular | | |
| Override option is visible but not prominent | | |
| Audit trail is accessible (1 click) | | |

### Scenario 2: Escalation Flow

| Criterion | Pass/Fail | Notes |
|-----------|-----------|-------|
| Escalation state is visually distinct but not alarming | | |
| Escalation reason is visible | | |
| Time-in-queue is displayed | | |
| Primary action (Approve/Reject) is clear | | |
| Secondary actions are collapsed | | |
| Escalation history is accessible | | |

### Scenario 3: Override Review

| Criterion | Pass/Fail | Notes |
|-----------|-----------|-------|
| Override request is clearly labeled | | |
| Original decision is visible for comparison | | |
| Override justification field is prominent | | |
| Approver accountability is clear | | |
| Confirmation step prevents accidental approval | | |
| Audit event is logged | | |

### Scenario 4: All-Clear / No Activity

| Criterion | Pass/Fail | Notes |
|-----------|-----------|-------|
| System state is visibly "healthy" | | |
| No red or alarming indicators | | |
| Last-checked timestamp is visible | | |
| Operator knows "nothing requires attention" | | |
| System heartbeat/activity indicator present | | |

---

## Component Library: Calm UX Primitives

Located in: `chainboard-ui/src/components/ui/CalmUX.tsx`

### All Clear States

| Component | Use Case |
|-----------|----------|
| `AllClearBadge` | Compact inline "all systems operational" |
| `AllClearCard` | Dashboard card when no alerts present |
| `AllClearStrip` | Banner confirmation at page/section level |

### Operator Reassurance

| Component | Use Case |
|-----------|----------|
| `ReassuranceMessage` | Contextual confidence-building message paired with risk data |
| `ConfidenceIndicator` | System confidence/trust score visualization |

### Calm Transitions

| Component | Use Case |
|-----------|----------|
| `CalmTransition` | Smooth entry/exit animations for appearing content |
| `CalmPulse` | Subtle pulsing for status indicators (non-alarming) |

### Cognitive Load Reducers

| Component | Use Case |
|-----------|----------|
| `ProgressiveDisclosure` | Show summary with optional expand |
| `QuietLoading` | Non-intrusive background refresh indicator |
| `StatusHeartbeat` | Visual "system alive" pulse |

### Visual Hierarchy

| Component | Use Case |
|-----------|----------|
| `SectionDivider` | Clean visual separator with optional label |
| `ImportanceHint` | Visual weight indicator for content priority |

---

## Animation System

All animations support `prefers-reduced-motion` media query.

| Animation Class | Duration | Use Case |
|-----------------|----------|----------|
| `animate-calm-pulse` | 3s | Standard status pulsing |
| `animate-calm-pulse-subtle` | 4s | Background element pulsing |
| `animate-calm-pulse-strong` | 2s | Important status (not alarming) |
| `animate-calm-breathe` | 4s | Positive status glow |
| `animate-calm-fade-in` | 0.5s | Content entry |
| `animate-calm-glow` | 3s | Success celebration |
| `animate-calm-spin` | 2s | Non-urgent loading |
| `animate-calm-bounce` | 2s | Gentle attention |

---

## Copy Standards

### Alert Language

| Instead of... | Use... |
|---------------|--------|
| "ERROR: System failure" | "Service temporarily unavailable" |
| "CRITICAL: Immediate action required" | "Requires attention" |
| "WARNING: You must..." | "Consider reviewing..." |
| "Failed" | "Unable to complete" |
| "Invalid" | "Needs correction" |

### Status Language

| State | Label | Tone |
|-------|-------|------|
| Healthy | "All systems operational" | Calm, confident |
| Degraded | "Operating with limitations" | Honest, not alarming |
| Attention | "Review recommended" | Professional, neutral |
| Action Required | "Action required" | Clear, not urgent |
| Critical | "Immediate attention needed" | Serious but controlled |

---

## Security & Correctness Guarantees

- [ ] UX does not obscure risk — Risk tier always visible
- [ ] UX does not auto-approve critical actions — Human confirmation required
- [ ] UX surfaces human accountability — Approver/actor identity shown
- [ ] UX avoids dark patterns or coercive urgency — No fake timers, no panic language
- [ ] UX supports audit & explainability requirements — All decisions traceable

---

## Alignment with Governance

This PAC aligns with:

- [DECISION_EXPLAINABILITY_POLICY.md](./DECISION_EXPLAINABILITY_POLICY.md) — Explainability requirements
- [OVERRIDE_GOVERNANCE_POLICY.md](./OVERRIDE_GOVERNANCE_POLICY.md) — Override flow requirements
- [AGENT_ACTIVITY_LOG.md](./AGENT_ACTIVITY_LOG.md) — Audit trail requirements

---

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Operator can explain a decision in <60 seconds | ✅ |
| Operator knows when NOT to act | ✅ |
| System state is visible at a glance | ✅ |
| Escalations feel serious but not chaotic | ✅ |
| UX aligns with Trust > Tracking doctrine | ✅ |

---

## Open Issues

None at activation.

---

🟪🟪🟪 LIRA (GID-09) — PAC-06-C Complete 🟪🟪🟪
