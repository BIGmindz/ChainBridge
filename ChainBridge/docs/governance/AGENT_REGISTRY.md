# ChainBridge Agent Registry

> **Governance Document** — PAC-CINDY-GOV-001
> **Version:** 2.0.0
> **Effective Date:** 2025-12-11
> **Owner:** ALEX (GID-08)
> **Cross-validated with:** `.github/agents/colors.json`

---

## Agent Directory

| Agent | GID | Emoji | Color | Role Summary | Domain |
|-------|-----|-------|-------|--------------|--------|
| CODY | GID-01 | 🔵 | Blue (`#0066CC`) | Backend development, API design, database architecture | Backend |
| MAGGIE | GID-02 | 🟣 | Purple (`#9933FF`) | Machine learning, model development, ChainIQ | ML Engineering |
| SONNY | GID-03 | 🟢 | Green (`#00CC66`) | Frontend development, React/TypeScript, ChainBoard UI | Frontend |
| DAN | GID-04 | 🟠 | Orange (`#FF6600`) | DevOps, CI/CD pipelines, infrastructure | DevOps |
| ATLAS | GID-05 | 🟤 | Brown (`#8B4513`) | Repository structure, documentation, organization | Repository Management |
| SAM | GID-06 | 🔴 | Red (`#CC0000`) | Security review, threat detection, incident response | Security |
| DANA | GID-07 | 🟡 | Yellow (`#FFCC00`) | Data pipelines, ETL, analytics infrastructure | Data Engineering |
| ALEX | GID-08 | ⚪ | White (`#FFFFFF`) | Master governance, rule enforcement, multi-agent alignment | Governance |
| CINDY | GID-09 | 🔷 | Diamond Blue (`#1E90FF`) | Service expansion, API integrations, backend scaling | Backend |
| PAX | GID-10 | 💰 | Gold (`#FFD700`) | CB-USDx tokenization, settlement logic, ChainPay | Tokenization & Settlement |
| LIRA | GID-11 | 🩷 | Pink (`#FF69B4`) | User experience, design systems, accessibility | UX Design |

---

## Color Philosophy

The ChainBridge agent color system uses **departmental grouping** to visually identify agent specializations at a glance. Colors are governance-locked and immutable once assigned.

### Departmental Color Mapping

| Department | Colors | Rationale |
|------------|--------|-----------|
| **Backend Engineering** | 🔵 Blue, 🔷 Diamond Blue | Blue tones represent the foundational backend services that power ChainBridge. CODY (primary) and CINDY (expansion) share the blue family to indicate their collaborative backend mandate. |
| **Frontend Engineering** | 🟢 Green | Green symbolizes growth and user-facing vitality. SONNY owns all ChainBoard UI and dashboard surfaces. |
| **ML & Data** | 🟣 Purple, 🟡 Yellow | Purple (MAGGIE) represents AI/ML intelligence; Yellow (DANA) represents data flow and analytics pipelines. Both work with data but from different angles. |
| **DevOps & Infrastructure** | 🟠 Orange | Orange signals operational alertness and CI/CD automation. DAN keeps the build pipelines running. |
| **Repository & Documentation** | 🟤 Brown | Brown represents the solid, foundational structure of the codebase. ATLAS maintains repository organization. |
| **Security** | 🔴 Red | Red is the universal color for alerts and security. SAM handles threat detection and zero-trust enforcement. |
| **Governance** | ⚪ White | White represents neutrality and oversight. ALEX enforces rules without domain bias. |
| **Product & Settlement** | 💰 Gold | Gold represents financial value and tokenization. PAX owns CB-USDx and ChainPay settlement logic. |
| **UX Design** | 🩷 Pink | Pink represents creativity and human-centered design. LIRA focuses on accessibility and design systems. |

### Visual Identification Benefits

1. **Instant Recognition** — PAC headers display 10 colored emojis, immediately identifying the responsible agent
2. **Domain Clustering** — Related agents share color families (e.g., blue backend tones)
3. **Conflict Prevention** — Unique colors prevent agent confusion in logs and dashboards
4. **Governance Traceability** — CI validates emoji colors match the canonical registry

---

## New Agent Onboarding: Color Assignment Rules

When onboarding a new ChainBridge agent, follow these governance-enforced rules:

### 1. GID Assignment

- New agents receive the next sequential GID (e.g., GID-12 follows GID-11)
- GID-00 is reserved for human oversight (CTO/Benson)
- GIDs are permanent and never reassigned

### 2. Color Selection Criteria

| Rule | Description |
|------|-------------|
| **Uniqueness** | The emoji/color combination MUST NOT duplicate any existing agent |
| **Domain Alignment** | Select a color that aligns with the agent's primary domain (see Departmental Color Mapping) |
| **Visual Distinctiveness** | The color must be easily distinguishable from existing colors in both light and dark themes |
| **Emoji Availability** | Use standard Unicode emoji circles (🔵🟣🟢🟠🟤🔴🟡⚪) or distinctive symbols (🔷💰🩷) |

### 3. Registration Process

1. **Propose** — Submit a PAC to ALEX (GID-08) with:
   - Proposed agent name
   - Proposed GID
   - Proposed emoji and color (name + hex)
   - Role summary and domain classification

2. **Validate** — ALEX verifies:
   - No color/emoji conflicts with existing agents
   - Domain alignment is logical
   - Hex value renders correctly across platforms

3. **Register** — Upon approval:
   - Add entry to `.github/agents/colors.json`
   - Update this registry (AGENT_REGISTRY.md)
   - Add PAC header pattern for CI validation

4. **Lock** — Once registered:
   - Colors are **immutable** (cannot be changed without governance override)
   - CI will block any PAC with mismatched agent/emoji combinations

### 4. Prohibited Actions

- ❌ Reassigning colors from inactive agents
- ❌ Using similar shades that cause visual confusion
- ❌ Skipping GID numbers
- ❌ Modifying colors.json without ALEX approval

### 5. Reserved Color Slots

| Color | Hex | Status | Notes |
|-------|-----|--------|-------|
| ⚫ Black | `#000000` | Reserved | Future security/audit expansion |
| 🟦 Blue Square | `#0000FF` | Reserved | Future distinction from circle blue |
| 🔶 Orange Diamond | `#FF8C00` | Reserved | Future DevOps expansion |

---

## PAC Header Format

All agent PACs must use the following header structure with correct emoji colors:

```
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
🔵 CODY — GID-01 — BACKEND ENGINEERING
🔵 Model: [Model Name]
🔵 Paste into NEW Copilot Chat
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
PAC-CODY-XXX — Task Title
```

**Validation Rules:**
- All 10 emojis in border rows must match agent's assigned color
- GID must match agent's governance ID
- PAC prefix must match agent name (PAC-CODY, PAC-MAGGIE, etc.)

---

## PAC Color Enforcement Examples

### ✅ Valid PAC Headers

**ALEX (Governance):**
```text
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪  (10 white circles)
⚪ ALEX — GID-08 — GOVERNANCE ENGINE
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
PAC-ALEX-GOV-024 — Task Title
```

**MAGGIE (ML Engineering):**
```text
🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣  (10 purple circles)
🟣 MAGGIE — GID-02 — ML ENGINEERING
🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣
PAC-MAGGIE-ML-005 — Model Training
```

**PAX (Tokenization):**
```text
💰💰💰💰💰💰💰💰💰💰  (10 money bags)
💰 PAX — GID-10 — TOKENIZATION & SETTLEMENT
💰💰💰💰💰💰💰💰💰💰
PAC-PAX-SETTLE-001 — Settlement Logic
```

### ❌ Invalid PAC Headers (Will Be Blocked)

| Error | Example | Issue |
|-------|---------|-------|
| Wrong emoji | `[BLUE] MAGGIE — GID-02` | MAGGIE uses 🟣, not 🔵 |
| Wrong GID | `[PURPLE] MAGGIE — GID-10` | MAGGIE is GID-02, not GID-10 |
| Mixed border | `[WHITE][WHITE][BLUE]...` | All 10 emojis must match |
| PAC mismatch | `PAC-CODY-...` in MAGGIE PAC | PAC prefix must match agent |

---

## CI Validation

The color registry is enforced by automated CI:

- **Workflow:** `.github/workflows/pac_color_check.yml`
- **Validator:** `tools/governance_python.py`
- **Enforcement:** `BLOCK_PR` — PRs with mismatched colors will not merge

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 2.1.0 | 2025-12-11 | Added PAC color enforcement examples (PAC-ALEX-GOV-024) |
| 2.0.0 | 2025-12-11 | Complete rewrite with color philosophy, onboarding rules (PAC-CINDY-GOV-001) |
| 1.0.0 | 2025-12-11 | Initial color registry (PAC-ALEX-GOV-022) |

---

💙 **CINDY** — Senior Backend Engineer
*Documentation through precision.*
