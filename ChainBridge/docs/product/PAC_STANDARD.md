<!-- AUTO-GENERATED UNDER GID-07 DAN PAC-BOOT-INSTALL-02 -->
# ChainBridge PAC Standard

**Single source of truth for writing, executing, and closing Prompted Action Cycles (PACs).**

*Cross-refs:* [ChainBridge Agent Launch Center](CHAINBRIDGE_AGENT_LAUNCH_CENTER.md) · [ChainBridge Reality Baseline](CHAINBRIDGE_REALITY_BASELINE.md)

---

## 1. Mission Card

Every PAC begins with a concise mission card so any agent can join mid-stream.

- **PAC Code:** e.g. `PAC-DOCS-01` (domain prefix + focus)
- **Agent Owner:** GID assignment (must match [Agent Registry](AGENT_REGISTRY.md))
- **Phase & Mode:** Internal pilot, backtest, research, etc.
- **Objective:** One to two sentences describing the desired end-state
- **Source Docs:** Enumerate canonical references (Reality Baseline, specs, tickets)
- **Time Box:** Default to a single working session unless otherwise stated

> ✅ Copy/paste checklist
> - [ ] Mission card is present at the top of the PAC
> - [ ] All referenced files exist or are explicitly called out as missing
> - [ ] Objective is outcome-oriented (not a task list)

---

## 2. Context Intake

Before executing tasks, agents load the required context.

- Always load the Reality Baseline and relevant spec docs.
- Summarize unknowns or assumptions before acting.
- If dependencies are missing, raise them in the `Assumptions / Open Questions` block.

> ✅ Copy/paste checklist
> - [ ] Reality Baseline acknowledged
> - [ ] Supporting specs loaded (link paths)
> - [ ] Unknowns captured

---

## 3. Constraints & Guardrails

Document explicit boundaries so work stays compliant.

- Reference security, compliance, and platform limits.
- Restate required model tier (see Model Requirements below) when relevant.
- Note prohibitions (e.g., no network calls, no production secrets).

> ✅ Copy/paste checklist
> - [ ] Security / safety rules enumerated
> - [ ] Model tier stated
> - [ ] Non-negotiable constraints bolded for visibility

---

## 4. Tasks & Execution Plan

Break the mission into clear, sequential actions.

- Enumerate tasks as ordered steps (`Task A`, `Task B`, ...).
- Flag parallelizable work and dependencies.
- Encourage agents to propose a plan before code edits.

> ✅ Copy/paste checklist
> - [ ] Steps are actionable verbs
> - [ ] Dependencies identified
> - [ ] Plan reviewed before execution

---

## 5. Deliverables & Acceptance Criteria

Define exactly what “done” means before starting.

- Specify artifacts (files, services, dashboards).
- Capture expected validation (tests, linting, command output).
- Clarify formatting or documentation standards.

> ✅ Copy/paste checklist
> - [ ] Deliverables listed with paths
> - [ ] Acceptance criteria measurable
> - [ ] Validation commands documented

---

## 6. Validation & QA Rituals

No PAC is complete without verification.

- Prefer repo-native commands (`make test`, `python ... --test`).
- Note expected failures in restricted environments (document why).
- Capture actual command output in the WRAP when possible.

> ✅ Copy/paste checklist
> - [ ] Tests or linting executed (or explicit reason why not)
> - [ ] Results recorded
> - [ ] Follow-up validation tasks captured if needed

---

## 7. Communications, Updates & Escalation

Maintain transparency while work is in-flight.

- Provide status updates after major steps or blockers.
- Escalate missing dependencies to Benson CTO (GID-00) via the WRAP or inline notes.
- Keep language factual; avoid assumptions that contradict the Reality Baseline.

> ✅ Copy/paste checklist
> - [ ] Status updates logged when scope shifts
> - [ ] Blockers escalated with paths and owners
> - [ ] Reality Baseline cited when clarifying scope

---

## 8. Completion & Handoff

Close the PAC with a documented handoff.

- Summarize what changed (files, services, infra).
- List validation performed and remaining risks.
- Provide next-step suggestions or confirm completion.
- End with `!WRAP` SatRep format (see Launch Center).

> ✅ Copy/paste checklist
> - [ ] Handoff summary provided
> - [ ] Residual risks recorded
> - [ ] WRAP issued with status + next actions

---

## Universal Agent BOOT Block Standard

All ChainBridge BOOT blocks follow this convention:

```text
BOOT: <GID> <AGENT> — <Scope statement>. Load <canonical documents / directories>. Apply Model Requirements (<preferred models>). Enforce Reality Baseline. Await <domain> PAC instructions.
```

Guidelines:

- Keep BOOT text on a single line in backticks to avoid unintended hyperlinks.
- Only reference docs that exist under `docs/product/` or note gaps via HTML comments.
- Reuse exactly the canonical BOOT strings listed in [CHAINBRIDGE_AGENT_LAUNCH_CENTER.md](CHAINBRIDGE_AGENT_LAUNCH_CENTER.md) and [AGENT_REGISTRY.md](AGENT_REGISTRY.md).

---

## Model Requirements (VS Code + Copilot)

| Domain | Preferred Model(s) | Notes |
| --- | --- | --- |
| Backend, DevOps, ML code | GPT-5.1 Codex Preview | Primary coding model for Python/FastAPI/infra work. |
| Frontend & UI | GPT-5.1 Codex Preview · GPT-5.1 Preview | Use Codex when editing code, fall back to Preview for planning. |
| Governance & Security | GPT-5.1 Preview · Claude Opus | Choose based on availability; prioritize governance clarity. |
| Research & Market Analysis | Gemini 3 Pro Preview · Gemini 2.5 Pro | Non-coding research tasks. |

Agents must confirm model selection in their WRAP when deviating from these defaults.

---

## Copy/Paste Micro-Checklists

```
PAC STARTER CHECKLIST
- [ ] Mission card filled
- [ ] Context loaded + Reality Baseline reviewed
- [ ] Constraints captured
- [ ] Plan drafted and acknowledged

PAC WRAP CHECKLIST
- [ ] Deliverables summarized
- [ ] Validation steps reported
- [ ] Remaining risks logged
- [ ] Next actions assigned / confirmed complete
```
