# ChainBridge PAC Standard

**Owner:** GID-08 ALEX — Governance & Alignment Engine

## Visual Agent Legend (Canonical Color Map)

| GID | Agent | Role | Color | Emoji | Hex |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GID-01** | **CODY** | Backend Engineering | Blue | 🔵 | `#0066CC` |
| **GID-02** | **MAGGIE** | ML Engineering | Purple | 🟣 | `#9933FF` |
| **GID-03** | **SONNY** | UI Engineering | Green | 🟢 | `#00CC66` |
| **GID-04** | **DAN** | DevOps & CI/CD | Orange | 🟠 | `#FF6600` |
| **GID-05** | **ATLAS** | Repository Management | Brown | 🟤 | `#8B4513` |
| **GID-06** | **SAM** | Security Engineering | Red | 🔴 | `#CC0000` |
| **GID-07** | **DANA** | Data Engineering | Yellow | 🟡 | `#FFCC00` |
| **GID-08** | **ALEX** | Governance & Alignment | White | ⚪ | `#FFFFFF` |
| **GID-09** | **CINDY** | Backend Expansion | Diamond Blue | 🔷 | `#1E90FF` |
| **GID-10** | **PAX** | Tokenization & Settlement | Gold | 💰 | `#FFD700` |
| **GID-11** | **LIRA** | UX Design | Pink | 🩷 | `#FF69B4` |

> **Source of Truth:** `.github/agents/colors.json` — Colors are **governance-locked** and immutable.

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

## Color Logic
- **🔵 Blue (CODY):** Stability, logic, "blue chip" reliability (Backend Engineering).
- **🟣 Purple (MAGGIE):** Wisdom, deep ML intelligence, AI-driven insight.
- **🟢 Green (SONNY):** Growth, user-facing, "go" signal (Frontend/UI).
- **🟠 Orange (DAN):** Construction, safety gear, infrastructure (DevOps).
- **🟤 Brown (ATLAS):** Solid foundation, structure (Repository Management).
- **🔴 Red (SAM):** Alert, critical defense, stop signal (Security).
- **🟡 Yellow (DANA):** Data flow, analytics, ETL pipelines.
- **⚪ White (ALEX):** Neutrality, blank slate, pure governance truth.
- **🔷 Diamond Blue (CINDY):** Distinct but related to Blue; backend expansion.
- **💰 Gold (PAX):** Value, finance, settlement, currency (Tokenization).
- **🩷 Pink (LIRA):** Creativity, human-centered design (UX).

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
Copy the skeleton below and replace the placeholder text with the specifics for the current PAC.
**IMPORTANT:** Replace the ⚪ emojis with YOUR agent's specific color emoji.

````markdown
██████████████████████████████████████████████████████████████████
🔵🔵🔵 GID-01 // CODY – BACKEND MIGRATION 🔵🔵🔵
Title: <Concise PAC title>
Target: <System/component impacted>
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

### Mandatory Sections (1–8)
All PACs **MUST** include these eight sections in order:

| # | Section | Purpose |
|---|---------|---------|
| 1 | **AGENT HEADER** | Agent name, GID, role, authority |
| 2 | **CONTEXT & GOAL** | Current reality, desired outcome, success definition |
| 3 | **CONSTRAINTS** | Technical, governance, or timeline constraints |
| 4 | **TASKS** | Numbered tasks, owners, sequencing |
| 5 | **FILE TARGETS** | Exact paths to be added/edited |
| 6 | **CLI** | Shell commands for setup/validation |
| 7 | **ACCEPTANCE** | Objective tests, linting, reviews for sign-off |
| 8 | **HANDOFF** | How work is handed to next agent or supervisor |

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
Every PAC concludes with a WRAP block that must include:
- **Files touched:** Explicit list of paths (docs/, src/, scripts/, etc.).
- **Tests / commands run:** Name the command(s) and whether they passed (e.g., `python benson_rsi_bot.py --test ✔`).
- **Outcome summary:** Short paragraph that states completion status, partials, or blockers.
- **Follow-ups:** Link to the next PAC or TODO items if work remains.

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
- `docs/governance/PAC_STANDARD.md` (this file)
- `docs/governance/AGENT_ACTIVITY_LOG.md`
- `docs/product/AGENT_REGISTRY.md`
- Related domain specs (API contracts, architecture docs, dashboards) as referenced per PAC.
