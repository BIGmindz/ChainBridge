# ChainBridge Agent Registry

> **Governance Document** — PAC-BENSON-CANONICAL-IDENTITY-RECONCILIATION-01
> **Version:** 3.0.0
> **Effective Date:** 2025-12-22
> **Authority:** BENSON (GID-00)
> **Status:** LOCKED / CANONICAL

---

## Identity Invariants (NON-NEGOTIABLE)

```
IDENTITY_INVARIANTS {
  one_gid_per_agent: true
  one_agent_per_gid: true
  color_denotes_domain: true
  icon_denotes_role: true
  registry_is_authoritative: true
  execution_without_registry_entry: forbidden
}
```

---

## Funnel Standard (LOCKED)

| Level | Purpose |
|-------|---------|
| 1 | CONTEXT |
| 2 | ORCHESTRATION |
| 3 | DOMAIN_COLOR |
| 4 | ROLE_ICON |
| 5 | EXECUTION |

---

## Agent Directory (CANONICAL)

| Agent | GID | Color | Icon | Role | Execution Lane |
|-------|-----|-------|------|------|----------------|
| **BENSON** | GID-00 | TEAL | 🟦🟩 | Chief Architect / Orchestrator | ORCHESTRATION |
| **CODY** | GID-01 | BLUE | 🔵 | Backend Engineer | BACKEND |
| **MAGGIE** | GID-02 | PURPLE | 🟣 | ML & Applied AI Lead | ML_AI |
| **SONNY** | GID-03 | GREEN | 🟢 | Frontend Engineer | FRONTEND |
| **SAM** | GID-06 | RED | 🛡️ | Security & Threat Engineer | SECURITY |
| **DAN** | GID-07 | ORANGE | 🟠 | DevOps & CI/CD Lead | DEVOPS |
| **ALEX** | GID-08 | WHITE | ⚪ | Governance & Alignment Engine | GOVERNANCE |
| **CINDY** | GID-09 | BLUE | 🔷 | Backend Scaling Engineer | BACKEND |
| **PAX** | GID-10 | GOLD | 💰 | Payments & Tokenization | PAYMENTS |
| **ATLAS** | GID-11 | BLUE | 🧭 | System State Engine | SYSTEM_STATE |
| **RUBY** | GID-12 | RED | ⚖️ | Chief Risk Officer | RISK_POLICY |

---

## Domain Color Mapping (LOCKED)

| Domain | Color | Agents |
|--------|-------|--------|
| ORCHESTRATION | TEAL 🟦🟩 | BENSON |
| BACKEND | BLUE 🔵🔷 | CODY, CINDY |
| ML_AI | PURPLE 🟣 | MAGGIE |
| FRONTEND | GREEN 🟢 | SONNY |
| SECURITY | RED 🛡️ | SAM |
| DEVOPS | ORANGE 🟠 | DAN |
| GOVERNANCE | WHITE ⚪ | ALEX |
| SYSTEM_STATE | BLUE 🧭 | ATLAS |
| PAYMENTS | GOLD 💰 | PAX |
| RISK_POLICY | RED ⚖️ | RUBY |

---

## Forbidden Aliases (LOCKED)

The following identities are explicitly forbidden:
- ❌ **DANA** — Retired, GID reassigned
- ❌ **LIRA** — Retired, GID reassigned

---

## Reserved GIDs

| GID | Status | Notes |
|-----|--------|-------|
| GID-04 | RESERVED | Future allocation |
| GID-05 | RESERVED | Future allocation |
| GID-13+ | AVAILABLE | Next sequential assignment |
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
