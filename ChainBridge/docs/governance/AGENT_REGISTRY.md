# ChainBridge Agent Registry

> **Governance Document** — PAC-BENSON-CANONICAL-AGENT-REGISTRY-RECONCILIATION-01
> **Version:** 4.0.0
> **Effective Date:** 2025-12-22
> **Authority:** BENSON (GID-00)
> **Status:** LOCKED / CANONICAL
> **Supersedes:** v3.0.0

---

## Canonical Identity Rules (NON-NEGOTIABLE)

```
CANONICAL_IDENTITY_RULES {
  one_agent = one_gid = one_color = one_icon = one_execution_lane
  no_shared_gids: TRUE
  no_shared_colors_without_sub_icon: TRUE
  no_ghost_agents: TRUE
  registry_is_authority: TRUE
  directory_mirrors_registry: TRUE
}
```

**Violation → IMMEDIATE HALT**

---

## Funnel Standard (LOCKED)

| Level | Purpose |
|-------|---------|
| 1 | CONTEXT |
| 2 | ORCHESTRATION |
| 3 | DOMAIN_COLOR |
| 4 | ROLE_ICON |
| 5 | EXECUTION |

### Color Funnel Narrowing Order

```
ORCHESTRATION → GOVERNANCE → SECURITY → DEVOPS → SYSTEM_STATE → BACKEND → ML_AI → FRONTEND → UX → RESEARCH
```

---

## Agent Directory (CANONICAL)

| Agent | GID | Color | Icon | Role | Execution Lane |
|-------|-----|-------|------|------|----------------|
| **BENSON** | GID-00 | TEAL | 🟦🟩 | Chief Architect & Orchestrator | ORCHESTRATION |
| **CODY** | GID-01 | BLUE | 🔵 | Backend Engineer | BACKEND |
| **SONNY** | GID-02 | YELLOW | 🟡 | Frontend Engineer | FRONTEND |
| **MIRA** | GID-03 | PURPLE | 🟣 | Research Lead | RESEARCH |
| **CINDY** | GID-04 | CYAN | 🔷 | Backend Scaling Engineer | BACKEND |
| **ATLAS** | GID-05 | BLUE | 🟦 | System State Engine | SYSTEM_STATE |
| **SAM** | GID-06 | DARK_RED | 🔴 | Security & Threat Engineer | SECURITY |
| **DAN** | GID-07 | GREEN | 🟢 | DevOps & CI/CD Lead | DEVOPS |
| **ALEX** | GID-08 | WHITE | ⚪ | Governance & Alignment Engine | GOVERNANCE |
| **LIRA** | GID-09 | PINK | 🩷 | UX Lead | UX |
| **MAGGIE** | GID-10 | MAGENTA | 💗 | ML & Applied AI Lead | ML_AI |
| **RUBY** | GID-12 | CRIMSON | ♦️ | Chief Risk Officer | RISK_POLICY |

---

## Special Agent Constraints

### ATLAS (GID-05)
```
ATLAS_LOCK {
  gid: "GID-05"
  role: "System State Engine"
  write_access: false
  execution_authority: false
  output: "FACTS ONLY"
}
```

### RUBY (GID-12)
```
RUBY_STATUS {
  gid: "GID-12"
  role: "Chief Risk Officer"
  authority: "RISK OVERRIDE ONLY"
  execution: "POLICY ENFORCEMENT"
}
```

---

## Deprecated GIDs

| GID | Prior Agent | Status | Reason |
|-----|-------------|--------|--------|
| GID-11 | ATLAS | DEPRECATED | Consolidated to GID-05 |

---

## Non-Executing Strategy Agents (LOCKED)

The following agents exist for **advisory purposes only**. They may NOT execute PACs, WRAPs, or create artifacts.

### PAX — NON_EXECUTING_STRATEGY

```yaml
PAX_CONSTRAINTS:
  status: "NON_EXECUTING_STRATEGY"
  execution_enabled: false
  execution_lane: "STRATEGY_ONLY"
  execution_mode: "ANALYSIS_ONLY"
  allowed_outputs:
    - "RESEARCH_PACK"
    - "STRATEGY_MEMO"
    - "POLICY_RECOMMENDATION"
    - "ADVISORY_BRIEF"
  forbidden_outputs:
    - "PAC"
    - "WRAP"
    - "CODE"
    - "FILE_CREATION"
    - "POSITIVE_CLOSURE"
  authority: "PAC-PAX-P37-EXECUTION-ROLE-RESTRICTION-AND-SCOPE-REALIGNMENT-01"
  enforcement: "FAIL_CLOSED"
  error_codes:
    GS_090: "Non-executing agent attempted PAC emission"
    GS_091: "Non-executing agent attempted WRAP emission"
    GS_092: "Non-executing agent attempted code/file creation"
    GS_093: "Non-executing agent attempted POSITIVE_CLOSURE"
```

---

## Forbidden Aliases (LOCKED)

The following identities are explicitly forbidden and CANNOT appear in PAC IDs:

- ❌ **DANA** — Retired (PERMANENTLY_FORBIDDEN)

```yaml
FORBIDDEN_AGENT_ENFORCEMENT:
  authority: "PAC-BENSON-P36-NONEXECUTING-AGENT-ENFORCEMENT-AND-PAC-NAMING-CANONICALIZATION-01"
  mode: "FAIL_CLOSED"
  error_codes:
    GS_071: "PAC ID references non-executing or retired agent"
    GS_072: "Footer color mismatch — must match executing agent"
    GS_073: "Forbidden agent alias detected in PAC ID"
    GS_090: "Non-executing agent attempted PAC emission"
    GS_091: "Non-executing agent attempted WRAP emission"
    GS_092: "Non-executing agent attempted code/file creation"
    GS_093: "Non-executing agent attempted POSITIVE_CLOSURE"
  forbidden_aliases:
    - "DANA"
  non_executing_agents:
    - "PAX"
  non_executing_strategy_agents:
    - "PAX"
  rules:
    - "PAC IDs may ONLY reference EXECUTING agents"
    - "Footer color MUST match executing agent from AGENT_ACTIVATION_ACK"
    - "Persona memory is SUBORDINATE to registry role"
    - "Non-executing agents may only produce advisory outputs"
    - "Strategy agents inform execution; they do not perform it"
    - "Ambiguity → FAIL_CLOSED"
```

---

## Reserved GIDs

| GID | Status | Notes |
|-----|--------|-------|
| GID-11 | DEPRECATED | Do not reuse |
| GID-13+ | AVAILABLE | Next sequential assignment |

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
- All emojis in border rows must match agent's assigned icon
- GID must match agent's governance ID
- PAC prefix must match agent name

---

## PAC Color Enforcement Examples

### ✅ Valid PAC Headers

**ALEX (Governance):**
```text
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
⚪ ALEX — GID-08 — GOVERNANCE ENGINE
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
PAC-ALEX-GOV-024 — Task Title
```

**MAGGIE (ML/AI):**
```text
💗💗💗💗💗💗💗💗💗💗
💗 MAGGIE — GID-10 — ML ENGINEERING
💗💗💗💗💗💗💗💗💗💗
PAC-MAGGIE-ML-005 — Model Training
```

**DAN (DevOps):**
```text
🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢
🟢 DAN — GID-07 — DEVOPS
🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢
PAC-DAN-DEVOPS-001 — CI Pipeline
```

### ❌ Invalid PAC Headers (Will Be Blocked)

| Error | Example | Issue |
|-------|---------|-------|
| Wrong icon | `[🟣] MAGGIE — GID-10` | MAGGIE uses 💗, not 🟣 |
| Wrong GID | `[💗] MAGGIE — GID-02` | MAGGIE is GID-10, not GID-02 |
| Mixed border | `[⚪][⚪][🔵]...` | All emojis must match |
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
| 4.0.0 | 2025-12-22 | Major reconciliation: GID reassignments, new agents (MIRA, LIRA), deprecated (PAX, GID-11) |
| 3.0.0 | 2025-12-22 | Directory canonicalization, funnel standard |
| 2.0.0 | 2025-12-11 | Color philosophy, onboarding rules |
| 1.0.0 | 2025-12-11 | Initial color registry |

---

🟦🟩 **BENSON (GID-00)** — Chief Architect & Orchestrator
