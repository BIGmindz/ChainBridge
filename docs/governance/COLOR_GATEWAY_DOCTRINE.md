# Color Gateway Doctrine

```
ARTIFACT TYPE:    Governance Doctrine
AUTHORITY LEVEL:  None (specification only)
BINDING EFFECT:   None (reference document)
ACCEPTANCE:       Not implied
FUNCTION:         Human-readable companion to color_gateway_spec.json
```

---

## WHAT THIS DOCUMENT IS NOT

- ❌ NOT an enforcement mechanism
- ❌ NOT an acceptance document
- ❌ NOT a policy override
- ❌ NOT authoritative for execution
- ❌ NOT a substitute for the JSON spec

---

## FORBIDDEN INTERPRETATIONS

- ❌ Does NOT grant authority to any agent
- ❌ Does NOT override Benson (GID-00) decisions
- ❌ Does NOT self-enforce
- ❌ Does NOT create binding rules
- ❌ Does NOT imply acceptance or approval
- ❌ ALEX is NOT the owner of this content

---

## Specification Reference

All enforcement tooling MUST reference:

```
docs/governance/color_gateway_spec.json
```

This document provides human context only.

---

## Lane Summary

| Lane | Emoji | Role | Execution |
|------|-------|------|-----------|
| TEAL | 🟦🟩 | Orchestration / Control Plane | No |
| BLUE | 🔵 | Backend / Systems | Yes |
| YELLOW | 🟡 | Frontend Engineering | Yes |
| PURPLE | 🟣 | Research | Yes |
| ORANGE | 🟠 | Product Strategy | Yes |
| DARK RED | 🔴 | Security | Yes |
| GREEN | 🟢 | DevOps / CI/CD | Yes |
| WHITE | ⚪ | Governance / Alignment | Yes |
| PINK | 🩷 | UX / ML | Yes |

---

## TEAL Lane Exclusivity

TEAL (🟦🟩) is reserved for:

- Agent: BENSON
- GID: GID-00
- Role: Orchestration / Control Plane

TEAL characteristics:

- Cannot appear as EXECUTING lane
- Reserved for command routing
- Reserved for acceptance decisions
- No implementation work permitted

---

## FORBIDDEN ACTIONS

### All Agents

- ❌ Execute outside declared lane
- ❌ Claim authority not granted
- ❌ Override Benson decisions
- ❌ Self-accept work

### TEAL Lane (BENSON)

- ❌ Execute implementation work
- ❌ Write code directly
- ❌ Modify files directly
- ❌ Appear as EXECUTING lane in PAC

### WHITE Lane (ALEX)

- ❌ Implement code changes
- ❌ Modify CI/CD
- ❌ Grant authority
- ❌ Accept work

---

## PAC Header Requirements

Every PAC MUST include:

| Field | Required |
|-------|----------|
| EXECUTING AGENT | Yes |
| EXECUTING GID | Yes |
| EXECUTING COLOR | Yes |

Validation rules per `color_gateway_spec.json`:

- Missing field → reject
- Color/agent mismatch → reject
- TEAL as executing → reject

---

## Cross-References

| Document | Purpose |
|----------|---------|
| [color_gateway_spec.json](./color_gateway_spec.json) | Machine-readable spec |
| [AGENT_REGISTRY.json](./AGENT_REGISTRY.json) | Agent identity source |
| [PAC_ENFORCEMENT.md](./PAC_ENFORCEMENT.md) | PAC validation rules |
| [STOP_THE_LINE.md](./STOP_THE_LINE.md) | Violation response |

---

**Prepared by:** ALEX (GID-08)
**Date:** 2025-12-19
**PAC Reference:** PAC-BENSON-COLOR-GATEWAY-CANONICAL-SPEC-01
**Classification:** Reference document. Non-authoritative.
