# Governance Validation Checklist v1

**Version:** 1.0.0
**Status:** GOVERNANCE-LOCKED
**Enforced By:** ALEX (GID-08)
**Effective Date:** 2024-12-17

---

## 1. Purpose

This checklist is the **single source of truth** for intent validation in ChainBridge.
It defines the mandatory gates that every agent action must pass before execution.

**Principles:**
- Deterministic: Same input → same output (no heuristics, no LLM)
- Fail-closed: Absence of permission = DENY
- Binary: Every gate is PASS or FAIL (no partial credit)
- Auditable: Every decision is logged with explicit reason

**Authority:**
- This checklist is consumed by ALEX (GID-08)
- ALEX is the sole enforcer — no bypass mechanism exists
- Missing checklist = system refuses to start

---

## 2. Scope

This checklist applies to:
- All agent intents (EXECUTE, BLOCK, PROPOSE, READ, ESCALATE)
- All targets (files, APIs, databases, configurations)
- All agents (GID-01 through GID-11)

This checklist does NOT apply to:
- Human operators (APPROVE authority is human-only)
- System health checks (liveness/readiness probes)
- Audit log reads (read-only telemetry)

---

## 3. Non-Negotiable Invariants

These invariants are absolute. No exception. No override.

| # | Invariant | Failure Mode |
|---|-----------|--------------|
| 1 | No agent may act without identity | DENY + `UNKNOWN_AGENT` |
| 2 | No agent may exceed ACM capabilities | DENY + `VERB_NOT_PERMITTED` |
| 3 | No mutation without EXECUTE permission | DENY + `MUTATION_WITHOUT_EXECUTE` |
| 4 | No BLOCK without BLOCK authority | DENY + `BLOCK_NOT_PERMITTED` |
| 5 | APPROVE is human-only | DENY + `APPROVE_NOT_PERMITTED` |
| 6 | DELETE is forbidden (use ARCHIVE/REVERSE) | DENY + `DELETE_FORBIDDEN` |
| 7 | Chain-of-command must be honored | DENY + `CHAIN_OF_COMMAND_VIOLATION` |
| 8 | All decisions must be logged | System halt if log fails |

---

## 4. Validation Gates (Ordered — No Skips)

Every intent must pass ALL gates in sequence. First failure = immediate DENY.

### Gate 1: Agent Identity Known

**Check:** `agent_gid` is present and maps to a loaded ACM manifest.

**Pass Condition:**
```
acm = loader.get(intent.agent_gid)
acm is not None
```

**Failure:**
- Reason: `UNKNOWN_AGENT`
- Detail: "No ACM found for {agent_gid}"
- Next Hop: None (terminal denial)

---

### Gate 2: Chain-of-Command Enforced

**Check:** For EXECUTE, BLOCK, or APPROVE verbs, intent must originate from or be routed through Diggy (BENSON, GID-00).

**Pass Condition:**
```
verb in (READ, PROPOSE, ESCALATE) OR
intent.chain_of_command.includes("GID-00") OR
intent.origin == "GID-00"
```

**Failure:**
- Reason: `CHAIN_OF_COMMAND_VIOLATION`
- Detail: "EXECUTE/BLOCK/APPROVE requires chain-of-command routing"
- Next Hop: `GID-00` (DIGGY)

---

### Gate 3: Verb Permitted by ACM

**Check:** The requested verb is in the agent's capability list.

**Pass Condition:**
```
acm.capabilities.{verb} is not empty OR
verb == ESCALATE (universal)
```

**Failure:**
- Reason: `VERB_NOT_PERMITTED`
- Detail: "{agent_id} does not have {verb} capability"
- Next Hop: Escalate to Diggy

---

### Gate 4: Target In Scope

**Check:** The target resource matches at least one entry in the agent's capability scope for the given verb.

**Pass Condition:**
```
any(target matches scope_entry for scope_entry in acm.capabilities.{verb})
```

**Failure:**
- Reason: `TARGET_NOT_IN_SCOPE`
- Detail: "Target '{target}' not in {verb} scope"
- Next Hop: Escalate to Diggy

---

### Gate 5: Mutation Requires EXECUTE

**Check:** If the intent creates, modifies, or deletes state, the verb must be EXECUTE.

**Pass Condition:**
```
intent.is_mutation == False OR verb == EXECUTE
```

**Failure:**
- Reason: `MUTATION_WITHOUT_EXECUTE`
- Detail: "Mutation operations require EXECUTE verb"
- Next Hop: Escalate to Diggy

---

### Gate 6: Escalation Gate Applied

**Check:** If the target matches any escalation trigger in the agent's ACM, the intent is flagged for escalation.

**Pass Condition:**
```
no matching escalation_triggers OR
intent.escalation_acknowledged == True
```

**Failure (soft):**
- Action: Flag intent for escalation review
- Continue: Yes (intent may still be ALLOWED)

---

### Gate 7: Audit Log Written

**Check:** The evaluation result must be written to the audit log before proceeding.

**Pass Condition:**
```
audit_logger.log_decision(result) succeeds
```

**Failure:**
- Action: System halt (audit is mandatory)
- No silent failures allowed

---

## 5. Explicit Denial Reasons

All denials must include one of these structured reason codes:

| Code | Meaning |
|------|---------|
| `UNKNOWN_AGENT` | Agent GID not found in loaded manifests |
| `ACM_NOT_LOADED` | ACM system not initialized |
| `INVALID_INTENT` | Intent structure is malformed |
| `MALFORMED_GID` | Agent GID format is invalid |
| `VERB_NOT_PERMITTED` | Agent lacks capability for this verb |
| `TARGET_NOT_IN_SCOPE` | Target not in agent's scope for verb |
| `EXECUTE_NOT_PERMITTED` | Agent lacks EXECUTE authority for target |
| `BLOCK_NOT_PERMITTED` | Agent lacks BLOCK authority |
| `APPROVE_NOT_PERMITTED` | APPROVE is human-only |
| `DELETE_FORBIDDEN` | DELETE verb is forbidden system-wide |
| `MUTATION_WITHOUT_EXECUTE` | Mutation attempted without EXECUTE verb |
| `CHAIN_OF_COMMAND_VIOLATION` | Action requires routing through Diggy |
| `CHECKLIST_NOT_LOADED` | Governance checklist file missing |
| `CHECKLIST_VERSION_MISMATCH` | Checklist version incompatible |

---

## 6. Failure Mode: DENY

All failures result in:
1. **Immediate denial** — no retry, no clarification
2. **Structured reason** — machine-readable denial code
3. **Audit log entry** — immutable record of denial
4. **Next hop suggestion** — where to escalate (if applicable)

There is no "partial allow" or "conditional proceed."

---

## 7. Version Control

- **Current Version:** 1.0.0
- **Minimum Compatible Version:** 1.0.0
- **Version Check:** Mandatory at ALEX startup

Version mismatch behavior:
- If checklist version < minimum: System refuses to start
- If checklist version > current: Warning logged, proceed with caution

---

## 8. CI Enforcement

Changes to governance paths require checklist compliance:

**Protected Paths:**
- `core/governance/*`
- `gateway/alex_*`
- `manifests/*`
- `docs/governance/*`

**CI Requirements:**
- All governance tests must pass
- Checklist version must be acknowledged in PR
- No merge without explicit governance review

---

## 9. Chain-of-Command Reference

| Verb | Requires Diggy Routing |
|------|------------------------|
| READ | No |
| PROPOSE | No |
| ESCALATE | No |
| EXECUTE | **Yes** |
| BLOCK | **Yes** |
| APPROVE | **Yes** (human-only) |

---

## 10. Canonical Close

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Checklist:** GOVERNANCE_VALIDATION_CHECKLIST
**Version:** 1.0.0
**Enforced By:** ALEX (GID-08)
**Status:** GOVERNANCE-LOCKED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**END OF CHECKLIST — GOVERNANCE LOCKED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
