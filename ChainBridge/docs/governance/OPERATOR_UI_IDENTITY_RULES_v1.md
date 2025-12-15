# Operator UI Identity Rules v1.0

> 🟫 LIRA (GID-09) — UX Systems & Operator Experience
> Version: 1.0
> Last Updated: 2025-12-15
> Status: CANONICAL

---

## Purpose

Ensure **every agent is instantly distinguishable** in the ChainBoard UI. No operator should confuse Benson with Sam, or ALEX with Cody. This document defines the **Triple Redundancy Rule** and **Calm UX Checklist** for agent-related UI.

---

## 1. Triple Redundancy Rule

Every agent identity MUST be expressed through **three independent channels**:

| Channel | Purpose | Example |
|---------|---------|---------|
| **Color** | Instant visual grouping | 🟦 Blue = LIRA |
| **Shape/Icon** | Colorblind accessibility | Shield = SAM |
| **Label** | Screen reader + explicit ID | "SAM (GID-06)" |

### 1.1 Required Implementation

```
┌─────────────────────────────────────┐
│ [🛡️] SAM (GID-06)                   │  ← Icon + Label
│ ████████████████████████████████    │  ← Color bar/accent
│ Security & Threat Engineer          │  ← Role descriptor
└─────────────────────────────────────┘
```

**All three MUST be present.** Color alone is never sufficient.

### 1.2 Agent Color Registry (Canonical)

| GID | Agent | Color | Hex | Icon | Shape |
|-----|-------|-------|-----|------|-------|
| GID-00 | BENSON | ⬛ Black | `#1e293b` | `brain` | Circle |
| GID-01 | CODY | 🟩 Green | `#22c55e` | `code` | Square |
| GID-02 | SONNY | 🟨 Yellow | `#eab308` | `layout` | Diamond |
| GID-03 | MIRA-R | 🟧 Orange | `#f97316` | `search` | Hexagon |
| GID-04 | CINDY | 🟪 Purple | `#a855f7` | `credit-card` | Pentagon |
| GID-05 | PAX | 🩵 Cyan | `#06b6d4` | `file-text` | Octagon |
| GID-06 | SAM | 🟥 Red | `#ef4444` | `shield` | Triangle |
| GID-07 | DAN | 🟫 Brown | `#a16207` | `server` | Parallelogram |
| GID-08 | ALEX | ⬜ White/Gray | `#94a3b8` | `scale` | Star |
| GID-09 | LIRA | 🟦 Blue | `#3b82f6` | `heart` | Rounded |
| GID-10 | MAGGIE | 🩷 Pink | `#ec4899` | `sparkles` | Wave |

### 1.3 Color Contrast Requirements

- Agent colors MUST have **WCAG 2.1 AA contrast** (4.5:1) against background
- On dark backgrounds: use lighter tint (400-500 weight)
- On light backgrounds: use darker shade (600-700 weight)
- **Never rely on color alone** — icon and label are mandatory fallbacks

---

## 2. Agent Activity Feed Rules

### 2.1 Entry Structure

Every agent activity entry MUST include:

```
[Icon] [AgentName] (GID-XX) · [Action] · [Timestamp]
       [One-line summary]
       [Optional: affected file/artifact]
```

### 2.2 Visual Hierarchy

| Element | Style | Purpose |
|---------|-------|---------|
| Agent badge | Color + icon + name | Instant identification |
| Action verb | Bold, neutral tone | What happened |
| Timestamp | Muted, relative | When (not alarming) |
| Details | Collapsed by default | Reduce cognitive load |

### 2.3 Prohibited Patterns

| ❌ Don't | ✅ Do |
|----------|-------|
| Color-only agent indicator | Color + icon + label |
| "BENSON ALERT!!!" | "Benson noted an issue" |
| Flashing agent badges | Subtle pulse if attention needed |
| Multiple agents same color | Unique color per agent |
| Raw GID without name | "ALEX (GID-08)" not just "GID-08" |

---

## 3. Operator Calm UX Checklist

### 3.1 Agent Displays

- [ ] Agent has color + icon + label (Triple Redundancy)
- [ ] Agent color is unique in the registry
- [ ] Agent icon is meaningful to role
- [ ] Label includes both name AND GID
- [ ] Contrast ratio ≥ 4.5:1

### 3.2 Activity Feeds

- [ ] Entries are scannable (≤2 lines visible)
- [ ] Details are collapsed by default
- [ ] No flashing or rapid animation
- [ ] Timestamps are relative ("2m ago" not "2025-12-15T10:30:00Z")
- [ ] Actions use neutral verbs (see §4)

### 3.3 Alerts & Errors

- [ ] No ALL CAPS except single-word labels
- [ ] No exclamation marks in body text
- [ ] No "ERROR" or "FAILED" without context
- [ ] Red reserved for action-required only
- [ ] Recovery action is visible

### 3.4 Cognitive Load

- [ ] Max 7±2 items visible without scroll
- [ ] One primary action per panel
- [ ] Secondary actions collapsed
- [ ] Consistent left-to-right reading flow

---

## 4. "Do Not Alarm" Copy Rules

### 4.1 Prohibited Language

| ❌ Never Use | ✅ Use Instead |
|--------------|----------------|
| CRITICAL ERROR | Issue detected |
| FAILED | Unable to complete |
| ALERT!!! | Attention needed |
| URGENT | Review recommended |
| WARNING: You must... | Consider reviewing... |
| System failure | Service unavailable |
| Invalid | Needs correction |
| Unauthorized | Access not permitted |
| Crashed | Stopped unexpectedly |

### 4.2 Verb Tone Guide

| Context | Tone | Example Verbs |
|---------|------|---------------|
| Success | Confident, brief | completed, approved, verified |
| Progress | Neutral, factual | processing, reviewing, preparing |
| Attention | Calm, actionable | flagged, queued, awaiting |
| Issue | Honest, not alarming | paused, unable, needs review |

### 4.3 Agent-Specific Phrasing

| Agent | Characteristic Tone | Example |
|-------|---------------------|---------|
| BENSON | Supervisory, brief | "Benson reviewed and approved" |
| SAM | Security-focused, direct | "Sam flagged for security review" |
| ALEX | Governance, formal | "Alex recorded compliance event" |
| LIRA | Supportive, calm | "Ready when you are" |

---

## 5. Implementation Guidance

### 5.1 Component Usage

```tsx
// ✅ Correct: Triple Redundancy
<AgentBadge
  agent="SAM"
  gid="GID-06"
  icon={<Shield />}
  color="red"
/>

// ❌ Wrong: Color only
<div className="bg-red-500">SAM</div>
```

### 5.2 Activity Feed Entry

```tsx
// ✅ Correct: Full context, calm tone
<ActivityEntry
  agent={{ name: "ALEX", gid: "GID-08", icon: Scale, color: "gray" }}
  action="recorded"
  summary="Compliance event logged"
  timestamp="2m ago"
/>

// ❌ Wrong: Alarming, incomplete
<div className="text-red-500 font-bold animate-pulse">
  ALEX: COMPLIANCE VIOLATION DETECTED!!!
</div>
```

---

## 6. Validation & Enforcement

### 6.1 PR Checklist

Before merging any agent-related UI:

- [ ] Triple Redundancy Rule satisfied
- [ ] Color from canonical registry
- [ ] Copy reviewed against §4 prohibited list
- [ ] Calm UX checklist (§3) passed

### 6.2 Automated Checks (Future)

- ESLint rule: no agent color without icon prop
- Copy linter: flag prohibited words
- Contrast checker: WCAG AA validation

---

## 7. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-15 | LIRA (GID-09) | Initial release |

---

🟫 LIRA (GID-09) — Operator UI Identity Rules v1.0 Complete 🟫
