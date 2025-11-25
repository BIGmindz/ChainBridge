# Agent Health Observability PRD

## Problem Statement

- ChainBridge now operates dozens of autonomous agents across AGENTS/, but there is no single view that indicates whether each prompt set is valid and deployable. When an agent silently loses required metadata or an env var, downstream demos fail without warning.
- Leadership needs an auditable signal that the AI workforce is ready for investor demos, customer pilots, and 24/7 operations. Today this assurance requires combing through CI logs and manual scripts.
- Without proactive visibility, shipping velocity slows, support escalations rise, and teams learn too late that an agent is missing credentials or violates the readiness checklist.

## Goals & Non-Goals

### Goals

1. Deliver a canonical status API and UI card that reports `{ total, valid, invalid, invalid_roles[] }` in real time.
2. Provide a single pane inside ChainBoard so operators can confirm agent readiness alongside other Control Tower metrics.
3. Preserve CI evidence by exporting the full agent prompt set as a JSON artifact on every run for audit and historical diffing.

### Non-Goals

- Measuring model accuracy or LLM performance; quality evaluation is handled elsewhere.
- Replacing deeper observability for individual microservices or runtime telemetry.
- Performing automated remediation. This release is read-only visibility.

## Users & Use Cases

- **Benson (CTO):** Needs an immediate yes/no signal before board demos: "Are all 28 agents valid?".
- **Internal developers:** Investigate why a feature branch fails readiness: "Which roles are invalid and what folder should I inspect?".
- **Operators / BizDev:** Validate readiness before investor walk-throughs without touching the repo.
- **Potential investors:** Review export artifacts that prove ChainBridge can govern agent prompts with change history.

Typical flows:

1. Operator loads Control Tower Overview, glances at Agent Health card to confirm `invalid = 0`.
2. Developer sees `invalid = 3`, expands the list of `invalidRoles`, opens AGENTS/<role> to fix prompts, reruns validation, and confirms green state.
3. Compliance audits CI for the `agent-prompts-json` artifact to prove agents were validated for a given release tag.

## Functional Requirements

1. Backend `GET /api/agents/status` endpoint (already implemented in S1) returns totals and invalid roles.
2. ChainBoard UI consumes the endpoint via `useAgentHealth` hook and surfaces counts in the dashboard without extra navigation.
3. CI workflow (`agent_ci.yml`) exports `agents_export.json` and uploads as `agent-prompts-json` artifact on every run.
4. System is read-only: no mutation endpoints or destructive controls in this scope.
5. Responses are cached client-side with refresh to avoid hammering the API yet remain near-real-time (<=30s stale).

## UX Requirements

- Present Agent Health inside the Overview/Control Tower grid using the existing card pattern (rounded border, Tailwind theme).
- Display clear state labels: **Healthy (green)** when `invalid === 0`, **Attention Needed (amber)** otherwise.
- Include a list of invalid roles with human-readable IDs; when empty, show an affirmative "All agents valid" message.
- Dedicated loading skeleton and explicit error panel with retry CTA.
- Layout stays glanceable on desktop 1440px and collapses cleanly on tablet widths.

## Metrics & KPIs

- `% Valid Agents = valid / total * 100` target ≥ 95% for production readiness.
- **Mean Time To Detect (MTTD)** a broken agent: target < 5 minutes between CI failure and UI signal.
- **CI Pass Rate** for agent readiness pipeline: number of runs with `invalid = 0` per release train.
- **Operator Confirmation Time:** time from opening dashboard to determining readiness should be under 10 seconds.

## Risks & Open Questions

- **Misconfiguration Risk:** If validation rules drift or the endpoint fails silently, UI could show false green; need monitoring on the API itself.
- **Over-Reliance on Counts:** Even with `invalid = 0`, prompt quality might be poor; future work may need qualitative scoring.
- **Artifact Exposure:** `agents_export.json` contains proprietary prompts—requires proper access controls.
- **Scaling Question:** Do we need per-agent metadata (e.g., last validation timestamp) in the response for future automation?
- **Performance Consideration:** When AGENTS/ scales to hundreds of roles, do we paginate invalid listings or provide filters?
