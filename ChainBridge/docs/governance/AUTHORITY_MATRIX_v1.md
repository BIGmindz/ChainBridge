# Authority Matrix v1.0

> **Governance Document** — AU07.A
> **Version:** 1.0.0
> **Effective Date:** 2025-12-15
> **Owner:** BENSON (GID-00)
> **Status:** 🔒 LOCKED

---

## Purpose

Defines **who can do what** in ChainBridge governance. No action outside this matrix is authorized.

---

## Veto Authority

| Authority | Holder | Scope | Override |
|-----------|--------|-------|----------|
| **Merge Block** | SAM (GID-06) | Security violations | ALEX + BENSON dual |
| **Round Halt** | BENSON (GID-00) | Execution discipline | ALEX only |
| **Governance Gate** | ALEX (GID-08) | Policy violations | BENSON + Human CEO |
| **Human Override** | Alex (CEO) | Any decision | None (final) |

---

## Approval Matrix

| Action | Primary Approver | Secondary | Escalation |
|--------|------------------|-----------|------------|
| **PAC Creation** | Assigned Agent | — | BENSON |
| **WRAP Acceptance** | BENSON (GID-00) | — | ALEX |
| **Round Advancement** | BENSON (GID-00) | — | Human CEO |
| **Merge to Branch** | BENSON (GID-00) | SAM (security) | ALEX |
| **Registry Update** | ALEX (GID-08) | BENSON | Human CEO |
| **Policy Change** | ALEX (GID-08) | BENSON | Human CEO |
| **Agent Onboarding** | ALEX (GID-08) | BENSON | Human CEO |
| **Security Exception** | SAM (GID-06) | ALEX | Human CEO |
| **Production Deploy** | DAN (GID-04) | SAM + BENSON | Human CEO |

---

## Stop Authority

Who can stop what:

| Stopper | Can Stop | Trigger |
|---------|----------|---------|
| **SAM (GID-06)** | Any merge | Security violation detected |
| **ALEX (GID-08)** | Any PAC | Governance violation |
| **BENSON (GID-00)** | Any round | Discipline violation |
| **Human CEO** | Everything | Any reason |

---

## Rejection Authority

| Rejector | Can Reject | Grounds |
|----------|------------|---------|
| **BENSON (GID-00)** | WRAPs | Format, discipline, scope |
| **ALEX (GID-08)** | PACs | Governance, policy |
| **SAM (GID-06)** | Code | Security vulnerabilities |
| **MAGGIE (GID-02)** | ML artifacts | Model quality, bias |

---

## Escalation Path

```
Agent Issue
    ↓
BENSON (GID-00) — Execution issues
    ↓
ALEX (GID-08) — Governance issues
    ↓
Human CEO (Alex) — Final authority
```

---

## Round Governance

| Phase | Controller | Gate Condition |
|-------|------------|----------------|
| **PAC Issuance** | BENSON | Scope defined, acceptance criteria set |
| **Execution** | Assigned Agent | Work in progress |
| **WRAP Submission** | Agent | All criteria met |
| **WRAP Review** | BENSON | Format + content check |
| **Round Lock** | BENSON | All WRAPs accepted |
| **Merge** | BENSON + SAM | Security clearance |

---

## Security Gates (SAM Mandatory Review)

| Artifact | SAM Review Required |
|----------|---------------------|
| API endpoints | ✅ Yes |
| Auth/authz changes | ✅ Yes |
| Crypto operations | ✅ Yes |
| External integrations | ✅ Yes |
| Database schema | ✅ Yes |
| Frontend forms | ⚠️ If handling sensitive data |
| Documentation | ❌ No |
| UI styling | ❌ No |

---

## Governance Gates (ALEX Mandatory Review)

| Artifact | ALEX Review Required |
|----------|----------------------|
| Policy documents | ✅ Yes |
| Agent registry | ✅ Yes |
| Role definitions | ✅ Yes |
| Enforcement rules | ✅ Yes |
| Audit trail changes | ✅ Yes |
| Decision logic | ⚠️ If governance-impacting |
| Standard code | ❌ No |

---

## Emergency Override Protocol

When normal process is too slow:

1. **Declare Emergency** — Human CEO or SAM (security only)
2. **Log Override** — Reason, timestamp, approver
3. **Execute** — Bypass normal gates
4. **Post-Mortem** — Within 24h, ALEX reviews
5. **Policy Update** — If pattern emerges, update this matrix

---

## Matrix Modification

This matrix can only be modified by:
- ALEX (GID-08) proposes
- BENSON (GID-00) reviews
- Human CEO approves

Changes take effect 24h after approval (unless emergency).
