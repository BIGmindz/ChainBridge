# ChainBridge PAC Standard

**Owner:** GID-00 BENSON — Chief Architect & Orchestrator
**Version:** 4.2.0
**Last Updated:** 2025-12-22
**Canonical Templates:** [PAC_TEMPLATE_V1.md](PAC_TEMPLATE_V1.md), [WRAP_TEMPLATE_V1.md](WRAP_TEMPLATE_V1.md)
**CI Enforcement:** [pac-identity-gate.yml](../../.github/workflows/pac-identity-gate.yml)
**Amended By:** PAC-BENSON-IDENTITY-DRIFT-ELIMINATION-01

---

## Identity Drift Elimination — HARD INVARIANTS

**Authority:** PAC-BENSON-IDENTITY-DRIFT-ELIMINATION-01
**Drift Class Eliminated:** IDENTITY_PRESENTATION_DRIFT
**Enforcement:** HARD_FAIL

```yaml
INVARIANT_SET IDENTITY_RESOLUTION {
  INVARIANT_01: "AGENT_COLOR_MUST_MATCH_REGISTRY" → HARD_FAIL
  INVARIANT_02: "AGENT_ICON_MUST_MATCH_REGISTRY" → HARD_FAIL
  INVARIANT_03: "NO_FREE_TEXT_AGENT_IDENTITY_FIELDS" → HARD_FAIL
  INVARIANT_04: "AUTHORITY_DOES_NOT_IMPLY_NEW_COLOR" → HARD_FAIL
  INVARIANT_05: "BLACK_RESERVED_FOR_UI_ONLY" → HARD_FAIL
}

REGISTRY_BINDING {
  source_of_truth: "docs/governance/AGENT_REGISTRY.json"
  lookup_required: true
  cache_allowed: false
  mismatch_action: "EXECUTION_ABORT"
}
```

### FORBIDDEN — Will Cause HARD_FAIL

- ❌ Free-text color values (e.g., "Black", "Navy", "Aqua")
- ❌ Implied colors from authority level (ROOT ≠ BLACK)
- ❌ Runtime using agent identity fields
- ❌ Manual color/icon override
- ❌ Fallback identity when registry lookup fails
- ❌ BLACK for any agent (reserved for UI only)

---

## CI Enforcement — MANDATORY

**Authority:** PAC-BENSON-FUNNEL-ENFORCEMENT-CI-GATE-01
**Failure Mode:** FAIL_CLOSED

All PACs and WRAPs are validated by CI before merge. Non-compliant documents **cannot land**.

### CI-Enforced Invariants

```yaml
CI_INVARIANTS {
  pac_must_contain_blocks: [
    "RUNTIME_ACTIVATION_ACK",
    "AGENT_ACTIVATION_ACK"
  ]
  block_order_enforced: true
  agent_identity_required: [
    "gid",
    "color",
    "icon",
    "execution_lane"
  ]
  runtime_identity_constraints: {
    gid_forbidden: true
    agent_name_forbidden: true
  }
  wrap_identity_echo_required: true
  registry_source_of_truth: "docs/governance/AGENT_REGISTRY.json"
  failure_mode: "FAIL_CLOSED"
}
```

### Funnel Stage Declaration

Every PAC **MUST** include:

```
Funnel Stage: <STAGE>
```

**Allowed values:**
- `CANONICAL` — Canonical document creation/update
- `IDENTITY` — Identity reconciliation
- `TEMPLATE` — Template definition/lock
- `CI_ENFORCEMENT` — CI/Automation enforcement
- `EXECUTION` — Normal execution work

**Invalid or missing Funnel Stage → CI FAIL**

### Validator Location

- **Script:** `scripts/ci/validate_pac_identity.py`
- **Workflow:** `.github/workflows/pac-identity-gate.yml`

Governance maxim: **Drift is not a discussion — it's a blocked merge.**

---

## Visual Agent Legend (Canonical Color Map v4.0.0)

**⚠️ ALL COLORS MUST BE RESOLVED FROM AGENT_REGISTRY.json — NO FREE TEXT**

| GID | Agent | Role | Color | Emoji |
| :--- | :--- | :--- | :--- | :--- |
| **GID-00** | **BENSON** | Chief Architect & Orchestrator | TEAL | 🟦🟩 |
| **GID-01** | **CODY** | Backend Engineer | BLUE | 🔵 |
| **GID-02** | **SONNY** | Frontend Engineer | YELLOW | 🟡 |
| **GID-03** | **MIRA** | Research Lead | PURPLE | 🟣 |
| **GID-04** | **CINDY** | Backend Scaling Engineer | CYAN | 🔷 |
| **GID-05** | **ATLAS** | System State Engine | BLUE | 🟦 |
| **GID-06** | **SAM** | Security & Threat Engineer | DARK_RED | 🔴 |
| **GID-07** | **DAN** | DevOps & CI/CD Lead | GREEN | 🟢 |
| **GID-08** | **ALEX** | Governance & Alignment Engine | WHITE | ⚪ |
| **GID-09** | **LIRA** | UX Lead | PINK | 🩷 |
| **GID-10** | **MAGGIE** | ML & Applied AI Lead | MAGENTA | 💗 |
| **GID-12** | **RUBY** | Chief Risk Officer | CRIMSON | ♦️ |

> **GID-11:** DEPRECATED — Do not use
> **Forbidden Aliases:** DANA, PAX — These are NOT agents
> **BLACK:** Reserved for UI only — NOT an agent color
>
> **Source of Truth:** `docs/governance/AGENT_REGISTRY.json` (v4.0.0) — Colors are **governance-locked** and immutable.

## Purpose
This document defines the canonical Planning & Alignment Cycle (PAC) structure for every ChainBridge agent. It establishes the sections, WRAP requirements, and post-PAC logging discipline that Benson (GID-00) and the rest of the command stack rely on for governance truth.

## Header & Footer Convention
- Start every PAC with the colored banner block that declares the GID, PAC title, and intent.
- End each PAC with a matching footer that repeats the GID, color tag, and "PAC END" marker.
- Within both banner and footer, include the `GID-XX // Agent Name – COLOR` line so agents can visually confirm ownership at a glance.

## PAC Drift Prevention
**Why Colors Matter:**
In a multi-agent environment, context switching is the primary risk. Colors provide an immediate visual anchor:
1.  **Visual Lock:** You instantly know if you are in a "Red" security context or a "Green" frontend context.
2.  **Drift Warning:** If a "Blue" backend agent starts discussing "Green" UI components, the visual mismatch triggers an immediate correction.
3.  **Session Hygiene:** Scrolling through a chat history becomes a color-coded map of the session's evolution.

## Color Logic — REGISTRY BOUND

**All colors MUST be resolved from AGENT_REGISTRY.json. No free-text interpretation.**

| Color | Agent | Semantic Meaning |
|-------|-------|------------------|
| **TEAL** | BENSON | Orchestration, executive authority |
| **BLUE** | CODY, ATLAS | Backend stability, system state |
| **YELLOW** | SONNY | Frontend, user-facing |
| **PURPLE** | MIRA | Research, analysis |
| **CYAN** | CINDY | Backend scaling |
| **DARK_RED** | SAM | Security, threat defense |
| **GREEN** | DAN | DevOps, CI/CD |
| **WHITE** | ALEX | Governance, neutrality |
| **PINK** | LIRA | UX, human-centered design |
| **MAGENTA** | MAGGIE | ML/AI intelligence |
| **CRIMSON** | RUBY | Risk, critical decisions |

### FORBIDDEN Colors

- **BLACK** — Reserved for UI only, not agent identity
- **GOLD** — No agent assigned (PAX is forbidden alias)
- **BROWN** — No agent currently uses (ATLAS is BLUE)

## PAC Color Enforcement Example

**Correct ALEX PAC Header:**
```
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
⚪ ALEX — GID-08 — GOVERNANCE ENGINE
⚪ Model: Claude Opus 4.5
⚪ Paste into NEW Copilot Chat
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
PAC-ALEX-GOV-024 — COLOR MAP UPDATE
```

**Correct CODY PAC Header:**
```
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
🔵 CODY — GID-01 — BACKEND ENGINEERING
🔵 Model: Claude Opus 4.5
🔵 Paste into NEW Copilot Chat
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
PAC-CODY-API-015 — API REFACTOR
```

**❌ INVALID — Wrong emoji for agent:**
```text
[GREEN][GREEN][GREEN]...[GREEN]  (10 green emojis)
[GREEN] CODY — GID-01 — BACKEND
>>> BLOCKED: CODY uses BLUE (🔵) not GREEN (🟢)
```

**❌ INVALID — Mixed emojis:**
```text
[WHITE][WHITE][BLUE][WHITE]...[WHITE]  (mixed emojis)
>>> BLOCKED: Border must be uniform (all same color)
```

**❌ INVALID — Wrong GID:**
```text
[PURPLE] MAGGIE — GID-10 — ML
>>> BLOCKED: MAGGIE is GID-02, not GID-10
```

## PAC Section Order (Template)

**CANONICAL TEMPLATE:** See [PAC_TEMPLATE_V1.md](PAC_TEMPLATE_V1.md) for the authoritative structure.

All PACs **MUST** use the locked template structure:

| Section | Name | Required |
|---------|------|----------|
| 0 | AGENT_ACTIVATION_ACK | ✅ MANDATORY FIRST |
| 1 | HEADER | ✅ |
| 2 | CONTEXT & GOAL | ✅ |
| 3 | CONSTRAINTS | ✅ |
| 4 | LOCKS ACKNOWLEDGED | ✅ |
| 5 | TASKS | ✅ |
| 6 | FILE TARGETS | ✅ |
| 7 | CLI | ✅ |
| 8 | ACCEPTANCE | ✅ |
| 9 | LOCK STATEMENT | ✅ |

**Section 0 is MANDATORY FIRST.** No exceptions.

---

## Runtime vs Agent Separation

**Critical Rule:** Runtimes (GitHub Copilot, ChatGPT, Claude, etc.) are NOT agents.

| Property | Agent | Runtime |
|----------|-------|---------|
| Has GID | ✅ Yes | ❌ No |
| Has Color | ✅ Yes | ❌ No |
| Has Authority | ✅ Yes | ❌ Delegated only |
| Identity | Unique | "Executing for Agent X" |
| Can self-identify | ✅ Yes | ❌ FORBIDDEN |

**Runtime MUST use:**
```
RUNTIME_ACTIVATION_ACK {
  runtime_name: "GitHub Copilot"
  gid: "N/A (RUNTIME)"
  executing_for_agent: "CODY (GID-01)"
  ...
}
```

**Runtime MUST NOT claim:**
- A GID
- A color
- Agent identity

---

## PAC Example (CODY)
██████████████████████████████████████████████████████████████████
1) AGENT HEADER
Agent: <Name + GID>
Role: <Scope, mandate, authority references>
Stack: <Primary code/doc surfaces>

2) CONTEXT & GOAL
Summarize the current reality, desired outcome, and success definition.

3) CONSTRAINTS & GUARDRAILS
List technical, governance, or timeline constraints that bind the PAC.

4) TASKS & PLAN
Outline the numbered tasks, owners, and sequencing.

5) FILE & CODE TARGETS
Enumerate exact paths that will be added or edited (docs/, src/, scripts/, etc.).

6) CLI / GIT COMMANDS
Document shell commands needed for setup, validation, or deployment.

7) QA & ACCEPTANCE CRITERIA
State the objective tests, linting, or doc reviews required for sign-off.

8) OUTPUT / HANDOFF NOTES
Clarify how the work will be handed to the next agent or supervisor.

WRAP
Summarize results, blockers, and confirmations (see WRAP Requirements below).
██████████████████████████████████████████████████████████████████
🔵🔵🔵 GID-01 // CODY – BACKEND MIGRATION 🔵🔵🔵
██████████████████████████████████████████████████████████████████
````

## PAC Compliance Rule (Mandatory)

**Effective:** Round-1.2 (2025-12-13)
**Owner:** GID-08 ALEX — Governance & Alignment Engine

### Banner Requirements
Every PAC **MUST** include:

1. **START Banner** — Color-coded header block at the beginning:
   ```
   🩶🩶🩶 START — GID-XX AGENT_NAME — PAC TITLE 🩶🩶🩶
   Color Tag: <COLOR>
   ```

2. **END Banner** — Matching color-coded footer at the conclusion:
   ```
   🩶🩶🩶 END — GID-XX AGENT_NAME — PAC TITLE 🩶🩶🩶
   Color Tag: <COLOR>
   ```

### Mandatory Sections (1–9)
All PACs **MUST** include these nine sections in order:

| # | Section | Purpose |
|---|---------|---------|
| 1 | **AGENT HEADER** | Agent name, GID, role, authority |
| 2 | **CONTEXT & GOAL** | Current reality, desired outcome, success definition |
| 3 | **CONSTRAINTS** | Technical, governance, or timeline constraints |
| 4 | **LOCKS ACKNOWLEDGED** | Constitutional locks affected by this PAC (see below) |
| 5 | **TASKS** | Numbered tasks, owners, sequencing |
| 6 | **FILE TARGETS** | Exact paths to be added/edited |
| 7 | **CLI** | Shell commands for setup/validation |
| 8 | **ACCEPTANCE** | Objective tests, linting, reviews for sign-off |
| 9 | **HANDOFF** | How work is handed to next agent or supervisor |

### Lock Acknowledgment Requirement ⚪ NEW

**Effective:** 2025-12-18
**Owner:** GID-00 BENSON — Chief Architect & Orchestrator
**Reference:** PAC-BENSON-CONSTITUTION-ENGINE-01

Every PAC that touches governance-scoped code **MUST** declare which constitutional locks it acknowledges:

```yaml
locks_acknowledged:
  - LOCK-GW-IMMUTABILITY-001
  - LOCK-PDO-IMMUTABILITY-001
  - LOCK-VERIFY-SEMANTICS-001
```

**Scope Mapping:**
| PAC Touches | Must Acknowledge |
|-------------|------------------|
| gateway/* | All LOCK-GW-* |
| occ/* | All LOCK-PDO-*, LOCK-INT-* |
| proofpack/* | All LOCK-PP-*, LOCK-VERIFY-* |
| governance/* | All LOCK-GOV-*, LOCK-AUTH-* |
| agents/* | All LOCK-AGENT-* |

**Enforcement:**
- Missing lock acknowledgment → PAC returned for correction
- Scope violation (touched area not acknowledged) → PAC rejected
- Forbidden zone touched without supersession → PAC blocked

**Reference:** See `docs/constitution/LOCK_REGISTRY.yaml` for all active locks

### Enforcement
- PACs missing START/END banners or any of sections 1–8 are **non-compliant**.
- Non-compliant PACs will be flagged by ALEX and returned for correction.
- Governance maxim: **No banner, no ship.**

---

## Agent-First Execution Mandate ⚪ NEW

**Effective:** 2025-12-15
**Owner:** GID-08 ALEX — Governance & Alignment Engine
**Reference:** [AGENT_FIRST_EXECUTION_DOCTRINE_v1.md](./AGENT_FIRST_EXECUTION_DOCTRINE_v1.md)

### Mandatory Agent-First Clause

Every PAC **MUST** be executed by an agent unless the task is explicitly CEO-only.

**CEO-Only Exceptions (Exhaustive List):**
1. Final merge approval to `main`
2. External vendor contract signatures
3. Security incident response (P0/P1)
4. Investor/board communications
5. Agent termination decisions
6. Production deployment confirmation

**Enforcement:**
- If a human executes non-CEO-only work → `⛔ REJECT: AGENT-FIRST VIOLATION`
- No exceptions. No "it was faster to do it myself."

### Mandatory Stop-the-Line Clause

Every PAC **MUST** halt if tests are red.

**Rule:** If CI pipeline shows FAILED or any test is red:
1. STOP all forward progress immediately
2. Fix the failing tests
3. Achieve GREEN status
4. Resume only after CI = SUCCESS

**Enforcement:**
- If forward progress continues with red tests → `⛔ HALT: TESTS RED — STOP THE LINE`
- No exceptions. No "I'll fix it later."

### Mandatory Training Artifact Clause

Every incident or failure **MUST** produce a training artifact.

**Required After:**
- Test failures that blocked a round
- Governance violations (any severity)
- Security incidents
- Production issues

**Artifact Location:** `docs/agent_university/`
**Format:** `{AGENT}_{INCIDENT_TYPE}_{DATE}.md`

**Enforcement:**
- If incident occurs without training artifact within 48h → `⛔ REJECT: TRAINING LOOP VIOLATION`
- Training artifacts factor into weekly grading

---

## WRAP Requirements

**CANONICAL TEMPLATE:** See [WRAP_TEMPLATE_V1.md](WRAP_TEMPLATE_V1.md) for the authoritative structure.

All WRAPs **MUST** include these sections in order:

| Section | Name | Required |
|---------|------|----------|
| 0 | AGENT_ACTIVATION_ACK | ✅ MANDATORY FIRST |
| 1 | EXECUTION_SUMMARY | ✅ |
| 2 | TASK_STATUS | ✅ (PASS/FAIL only) |
| 3 | ARTIFACTS_TOUCHED | ✅ |
| 4 | TESTS_RUN | ✅ |
| 5 | DEVIATIONS | ✅ (even if none) |
| 6 | TRAINING_SIGNAL | ✅ |
| 7 | FINAL_STATE | ✅ |

**Narrative prose is FORBIDDEN inside WRAPs.**
**Task status must be PASS or FAIL only — no partial, no ambiguous.**

---

## Activity Log Rule
After the WRAP is written, immediately update `docs/governance/AGENT_ACTIVITY_LOG.md` with a new bullet under your GID. Use the exact format below so Benson can parse updates programmatically:

```
YYYY-MM-DD – <Short description>; files: path1, path2; tests: <command(s)>
```

Governance maxim: **If work is not recorded in `AGENT_ACTIVITY_LOG.md`, it did not ship.**

## Supervisor Alignment
- Benson (GID-00) derives all SITREPs and roadmap calls from:
  1. This PAC standard.
  2. `docs/product/AGENT_REGISTRY.md`.
  3. `docs/governance/AGENT_ACTIVITY_LOG.md`.
- Failing to follow the standard or log updates means Benson will assume no progress occurred; such work may be reprioritized or reassigned.

## References
- [PAC_TEMPLATE_V1.md](PAC_TEMPLATE_V1.md) — Canonical PAC structure (LOCKED)
- [WRAP_TEMPLATE_V1.md](WRAP_TEMPLATE_V1.md) — Canonical WRAP structure (LOCKED)
- [AGENT_REGISTRY.json](AGENT_REGISTRY.json) — Canonical agent identities (v4.0.0)
- [AGENT_REGISTRY.md](AGENT_REGISTRY.md) — Human-readable registry
- `docs/governance/AGENT_ACTIVITY_LOG.md` — Activity tracking
- Related domain specs (API contracts, architecture docs, dashboards) as referenced per PAC.
