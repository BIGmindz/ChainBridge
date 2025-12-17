# Agent Capability Manifest (ACM) v1

## Canonical Specification

**Version:** 1.0.0
**Status:** GOVERNANCE-LOCKED
**Owner:** Benson CTO (GID-00)

---

## Purpose

The Agent Capability Manifest (ACM) defines **positive authority** for ChainBridge agents.

It complements **negative authority** (defined in agent personas) by explicitly enumerating what each agent MAY do, rather than only what they MUST NOT do.

Together, positive and negative authority create a complete, enforceable boundary for agent behavior.

---

## Default-Deny Principle

All agent capabilities operate under **default-deny**.

- If a capability is not explicitly granted, it is forbidden.
- Silence is denial.
- Ambiguity is denial.
- Implied permissions do not exist.

An agent may only perform actions explicitly listed in their ACM manifest.

---

## Capability Taxonomy

The following capabilities are the only valid capability types in ACM v1:

| Capability | Definition | Agent-Grantable |
|------------|------------|-----------------|
| `READ` | Access and inspect resources without modification | Yes |
| `PROPOSE` | Suggest changes for review; no direct execution | Yes |
| `EXECUTE` | Perform actions that modify state | Yes (restricted) |
| `APPROVE` | Authorize proposed changes for execution | **No — Human-only** |
| `BLOCK` | Halt or reject operations that violate policy | Yes (governance agents) |
| `ESCALATE` | Transfer decision authority to higher level | Yes |

### Capability Rules

1. **APPROVE** is never granted to agents. All approvals require human authorization.
2. **EXECUTE** on production or financial systems requires explicit escalation and human approval.
3. **BLOCK** is reserved for governance and security agents (ALEX, SAM).
4. **ESCALATE** is mandatory when scope boundaries are reached.

---

## Forbidden Operations

The following operations are **permanently forbidden** for all agents:

| Operation | Status | Alternative |
|-----------|--------|-------------|
| `DELETE` | **FORBIDDEN** | Use `ARCHIVE` or `REVERSE` |
| Direct production deployment | **FORBIDDEN** | Requires human APPROVE |
| Financial transaction execution | **FORBIDDEN** | Requires human APPROVE |
| Governance rule modification | **FORBIDDEN** | Requires Benson CTO authorization |

Data is never destroyed. It is archived or reversed.

---

## Enforcement Layers

ACM is enforced at three layers:

### 1. Gateway (Runtime)

- API gateway validates agent identity and capability before execution
- Unauthorized actions are rejected with explicit denial
- All attempts are logged for audit

### 2. CI/CD (Build Time)

- Capability manifests are validated during CI
- Code changes that exceed agent authority fail build
- Drift detection blocks unauthorized capability expansion

### 3. Prompt Injection (Context Only)

- ACM rules are injected into agent prompts for awareness
- Prompt injection is **non-authoritative** — it provides context only
- Runtime enforcement is the source of truth

---

## Versioning Rules

ACM manifests follow semantic versioning:

- **MAJOR:** Breaking changes to capability structure
- **MINOR:** New capabilities added (backward compatible)
- **PATCH:** Clarifications, no functional change

Version changes require:
1. Documented rationale
2. Governance review
3. Benson CTO approval

---

## Drift Policy

Capability drift is prohibited.

- All ACM changes require governance approval
- Unauthorized capability expansion is a governance violation
- ALEX monitors for drift and blocks non-compliant behavior
- Drift detection failures block deployment

Changes to ACM manifests are tracked in version control and require explicit approval workflow.

---

## Manifest Structure

All ACM manifests MUST follow this structure:

```yaml
agent_id: "<NAME>"
gid: "<GID-XX>"
role: "<ROLE>"
color: "<COLOR>"
version: "1.0.0"

constraints:
  # Negative authority (aligned with persona)
  - <constraint>

capabilities:
  # Positive authority
  read:
    - <resource>
  propose:
    - <action>
  execute:
    - <action>
  block:
    - <condition>
  escalate:
    - <trigger>

escalation_triggers:
  - <condition>

invariants:
  - <rule that must always hold>
```

---

## Canonical Close

This specification is governance-locked.

No modifications without Benson CTO (GID-00) authorization.

---

**Agent:** ACM Specification
**GID:** N/A (System Document)
**Role:** Governance Standard
**Color:** Grey ⚪
**Version:** 1.0.0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END OF ACM — GOVERNANCE LOCKED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
