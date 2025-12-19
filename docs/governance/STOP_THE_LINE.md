# Stop-the-Line Protocol
**ALEX (GID-08) | PAC-ALEX-GOVERNANCE-LOCK-01**

---

## Purpose

This document defines the **mandatory stop-the-line criteria** for ChainBridge. When triggered, all work stops until resolution.

---

## Stop-the-Line Events

### STOP-01: Governance Invariant Violation

**Trigger:** Any violation of EXECUTION_SPINE_INVARIANTS.md

| Invariant | Example Violation |
|-----------|-------------------|
| INV-01 | Execution path skips Decision step |
| INV-02 | Execution completes without proof |
| INV-03 | Non-deterministic hash detected |
| INV-04 | Silent failure in spine code |
| INV-05 | Proof artifact modified or deleted |
| INV-06 | Decision function has side effects |
| INV-07 | Action missing traceability |

**Response:** IMMEDIATE STOP

---

### STOP-02: Ungoverned Code Merge

**Trigger:** Code merged to main without PAC ID

**Detection:**
```bash
git log --oneline | grep -v "PAC-" | head -5
```

**Response:** IMMEDIATE STOP + REVERT

---

### STOP-03: Security Constraint Breach

**Trigger:** Any of:
- Unauthorized file access
- Credential exposure
- Cryptographic downgrade
- Attack surface expansion

**Response:** IMMEDIATE STOP + SAM (GID-06) escalation

---

### STOP-04: Agent Scope Violation

**Trigger:** Agent modifies files outside authorized scope

| Agent | Authorized Scope |
|-------|------------------|
| ALEX (GID-08) | `docs/governance/*` only |
| ATLAS (GID-11) | Repo structure, migrations |
| SAM (GID-06) | Security files |
| DAN (GID-07) | CI/CD workflows |

**Response:** IMMEDIATE STOP + Benson escalation

---

### STOP-05: Proof Integrity Failure

**Trigger:** 
- Proof hash mismatch
- Proof artifact corruption
- Missing proof for completed execution

**Response:** IMMEDIATE STOP + AUDIT

---

### STOP-06: Cosmetic-Only Governance Correction

**Trigger:** Governance correction that:
- Fixes headers/colors/wording only
- Declares "acknowledged" without action
- Skips re-verification of original mandate
- Assumes work correctness without verification
- Agent self-asserts compliance

**Response:** IMMEDIATE STOP + Correction rejection + Re-issue required

---

## Governance Correction Routing

All governance violations MUST route to ALEX (GID-08).

### Correction Requirements

| Requirement | Mandatory |
|-------------|-----------|
| RE-AUDIT & ACTION section | Yes |
| Original mandate (verbatim) | Yes |
| PASS/FAIL per deliverable | Yes |
| Corrective steps if FAIL | Yes |
| Substance verification | Yes |

### Forbidden Correction Behaviors

- ❌ Format-only fixes
- ❌ Acknowledgment without action
- ❌ Skipping mandate re-verification
- ❌ Assuming correctness
- ❌ Self-asserted compliance

### Acceptance Authority

- ALEX issues corrections
- Benson (GID-00) retains sole acceptance authority
- No agent may self-accept corrections

**Reference:** [PAC_ENFORCEMENT.md](./PAC_ENFORCEMENT.md) — Governance Correction Requirements

---

## Response Protocol

### Immediate Actions (0-5 minutes)

1. **HALT** all in-progress work
2. **IDENTIFY** the violation
3. **NOTIFY** Benson (GID-00)
4. **LOG** the event with timestamp

### Triage (5-30 minutes)

| Severity | Escalation Path | SLA |
|----------|-----------------|-----|
| CRITICAL | Benson direct | 5 min |
| HIGH | Team channel | 15 min |
| MEDIUM | Next standup | 24h |

### Resolution

1. Root cause identified
2. Fix implemented
3. Regression test added
4. Post-mortem documented

---

## Escalation Matrix

```
┌─────────────────────────────────────────────────────┐
│                BENSON (GID-00)                      │
│                Wartime CTO                          │
│            Final Decision Authority                 │
└─────────────────────────────────────────────────────┘
                        ▲
        ┌───────────────┼───────────────┐
        │               │               │
   ┌────┴────┐    ┌─────┴─────┐   ┌─────┴─────┐
   │  ALEX   │    │    SAM    │   │    DAN    │
   │ GID-08  │    │  GID-06   │   │  GID-07   │
   │Governance│    │ Security  │   │   CI/CD   │
   └─────────┘    └───────────┘   └───────────┘
```

---

## Decision Authority

| Event Type | Primary | Backup |
|------------|---------|--------|
| Governance | ALEX (GID-08) | Benson |
| Security | SAM (GID-06) | Benson |
| CI/CD | DAN (GID-07) | Benson |
| Architecture | Benson | — |

---

## STOP Command Syntax

When invoking stop-the-line, use explicit format:

```
🛑 STOP-THE-LINE

Event: STOP-XX
Trigger: [description]
Evidence: [link or description]
Severity: CRITICAL | HIGH | MEDIUM
Agent: [GID]

Requested Action: [specific ask]
```

---

## Recovery Checklist

Before resuming work:

- [ ] Root cause identified
- [ ] Fix merged with PAC ID
- [ ] Test coverage added
- [ ] No other violations detected
- [ ] Benson sign-off (if CRITICAL)

---

## Audit Log Requirements

All STOP events MUST be logged to `logs/governance/stop_events.log`:

```json
{
  "timestamp": "ISO8601",
  "event": "STOP-XX",
  "trigger": "description",
  "severity": "CRITICAL|HIGH|MEDIUM",
  "agent": "GID-XX",
  "resolution": "pending|resolved",
  "resolution_timestamp": "ISO8601",
  "pac_id": "PAC-XXX"
}
```

---

## FORBIDDEN INTERPRETATIONS

- ❌ This document does NOT grant ALEX authority
- ❌ This document does NOT override Benson decisions
- ❌ This document does NOT self-enforce
- ❌ ALEX is NOT the owner of this content
- ❌ ALEX cannot accept changes to this document

---

**Prepared by:** ALEX (GID-08)  
**Date:** 2025-12-19  
**PAC Reference:** PAC-ALEX-GOVERNANCE-LOCK-01  
**Classification:** Reference document. Navigational aid only. Non-authoritative.
