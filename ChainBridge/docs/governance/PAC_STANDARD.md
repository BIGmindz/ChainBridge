# ChainBridge PAC Standard

**Owner:** GID-08 ALEX — Governance & Alignment Engine

## Purpose
This document defines the canonical Planning & Alignment Cycle (PAC) structure for every ChainBridge agent. It establishes the sections, WRAP requirements, and post-PAC logging discipline that Benson (GID-00) and the rest of the command stack rely on for governance truth.

## Header & Footer Convention
- Start every PAC with the colored banner block that declares the GID, PAC title, and intent (e.g., white/grey for governance, blue for backend, amber for product, etc.).
- End each PAC with a matching footer that repeats the GID, color tag, and "PAC END" marker.
- Within both banner and footer, include the `GID-XX // Agent Name – COLOR` line so agents can visually confirm ownership at a glance.

## PAC Section Order (Template)
Copy the skeleton below and replace the placeholder text with the specifics for the current PAC:

````markdown
██████████████████████████████████████████████████████████████████
⬜⬜⬜ GID-XX // AGENT NAME – TITLE ⬜⬜⬜
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
⬜⬜⬜ GID-XX // AGENT NAME – COLOR TAG ⬜⬜⬜
██████████████████████████████████████████████████████████████████
````

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
