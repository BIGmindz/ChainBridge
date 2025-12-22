# Canonical Agent Registry v1.0

> **Governance Document** — AU07.A
> **Version:** 1.0.0
> **Effective Date:** 2025-12-15
> **Owner:** BENSON (GID-00)
> **Status:** 🔒 LOCKED — Changes require ALEX (GID-08) + BENSON (GID-00) dual approval

---

## Purpose

This is the **single source of truth** for all ChainBridge agents. Any agent not listed here is unauthorized. Any color/emoji mismatch triggers automatic WRAP rejection.

---

## Canonical Agent Table

| GID | Agent | Role | Hex | Emoji Block | Domain |
|-----|-------|------|-----|-------------|--------|
| GID-00 | **BENSON** | Command & Orchestration | `#00B8A9` | 🟦🟩 | Execution CTO |
| GID-01 | **CODY** | Backend Engineering | `#0066CC` | 🔵🔵 | APIs, DB, Services |
| GID-02 | **MAGGIE** | ML Engineering | `#9933FF` | 🟣🟣 | ChainIQ, Risk Models |
| GID-03 | **SONNY** | Frontend Engineering | `#00CC66` | 🟢🟢 | ChainBoard UI |
| GID-04 | **DAN** | DevOps & Infrastructure | `#FF6600` | 🟠🟠 | CI/CD, Deploy |
| GID-05 | **ATLAS** | Repository Management | `#8B4513` | 🟤🟤 | Structure, Docs |
| GID-06 | **SAM** | Security | `#CC0000` | 🔴🔴 | Threat Detection |
| GID-07 | **DANA** | Data Engineering | `#FFCC00` | 🟡🟡 | ETL, Pipelines |
| GID-08 | **ALEX** | Governance | `#FFFFFF` | ⚪⚪ | Rule Enforcement |
| GID-09 | **CINDY** | Backend Expansion | `#1E90FF` | 🔷🔷 | API Integrations |
| GID-10 | **PAX** | Tokenization & Settlement | `#FFD700` | 💰💰 | CB-USDx, ChainPay |
| GID-11 | **LIRA** | UX Design | `#FF69B4` | 🩷🩷 | Accessibility, Design |

---

## Color Uniqueness Guarantee

**All hex values are unique. All emoji blocks are unique.**

| Check | Status |
|-------|--------|
| No duplicate hex codes | ✅ Verified |
| No duplicate emoji blocks | ✅ Verified |
| GID-00 reserved for human/CTO | ✅ Enforced |
| Sequential GID assignment | ✅ Enforced |

---

## WRAP Header Format

Every WRAP must use this exact format:

```
[EMOJI][EMOJI] START — [AGENT] (GID-XX) — [Role] [EMOJI][EMOJI]

... content ...

[EMOJI][EMOJI] END — [AGENT] (GID-XX) [EMOJI][EMOJI]
```

### Examples (Correct)

```
🟦🟩🟦🟩 START — BENSON (GID-00) — Command & Orchestration 🟦🟩🟦🟩
🔵🔵🔵🔵 START — CODY (GID-01) — Backend Engineering 🔵🔵🔵🔵
🟣🟣🟣🟣 START — MAGGIE (GID-02) — ML Engineering 🟣🟣🟣🟣
⚪⚪⚪⚪ START — ALEX (GID-08) — Governance ⚪⚪⚪⚪
```

### Rejection Triggers

| Violation | Result |
|-----------|--------|
| Wrong emoji for GID | 🔁 REJECT |
| Missing START/END | 🔁 REJECT |
| GID not in registry | 🔁 REJECT |
| Role mismatch | 🔁 REJECT |

---

## Reserved GIDs

| GID | Status | Notes |
|-----|--------|-------|
| GID-00 | ACTIVE | BENSON — Human/CTO orchestration |
| GID-12+ | RESERVED | Future agent onboarding |

---

## Modification Rules

1. **No unilateral changes** — Registry updates require:
   - PAC submission to ALEX (GID-08)
   - BENSON (GID-00) approval
   - 24-hour review window

2. **Immutable fields** — Once assigned:
   - GID cannot be reassigned
   - Hex code cannot be changed
   - Emoji block cannot be changed

3. **Addition only** — Agents can be added, never removed (only marked INACTIVE)

---

## Enforcement

This registry is enforced by:
- WRAP_LINTER_CHECKLIST.md (manual)
- CI validation (automated, future)
- BENSON (GID-00) review gate

**Any WRAP with non-canonical agent data is automatically rejected.**
