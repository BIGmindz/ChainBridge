# ORCHESTRATION_ENGINE_LAW_v1.md

## Canonical Orchestration Engine Definition

```
PAC Reference:  PAC-BENSON-EXEC-GOVERNANCE-ORCHESTRATION-ENGINE-RENAMING-017
Effective Date: 2025-12-26
Version:        1.0.0
Classification: HARD LAW — Non-Negotiable
```

---

## 1. Purpose

This document establishes the **Orchestration Engine** as a distinct, non-persona
system component within the ChainBridge governance framework.

The Orchestration Engine is the **sole authority** for:
- Validating PACs
- Dispatching execution to agents
- Reviewing WRAPs
- Issuing BERs (Benson Execution Reports)

---

## 2. Identity Boundary — HARD LAW

### 2.1. System Components vs. Agents

| Classification    | Entity Type        | Can Issue BER | Has Persona | Conversational |
|-------------------|--------------------|---------------|-------------|----------------|
| SYSTEM_ORCHESTRATOR | Orchestration Engine | ✅ YES       | ❌ NO       | ❌ NO          |
| SYSTEM_EXECUTION   | Execution Engine    | ❌ NO        | ❌ NO       | ❌ NO          |
| DRAFTING_SURFACE   | Human Interface     | ❌ NO        | ❌ NO       | ✅ YES         |
| AGENT             | GID-01 through GID-12 | ❌ NO      | ✅ YES      | ❌ NO (work only) |

### 2.2. The Orchestration Engine Is NOT:
- ❌ A persona (no "Benson" as speaker)
- ❌ An agent (no GID collision)
- ❌ A conversational entity
- ❌ A drafting surface
- ❌ An assistant

### 2.3. The Orchestration Engine IS:
- ✅ A deterministic governance system
- ✅ The sole BER issuer
- ✅ A non-persona execution governor
- ✅ Invisible to human conversation
- ✅ Code-enforced, not prompt-enforced

---

## 3. Execution Flow — Canonical

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HUMAN DRAFTING SURFACE                        │
│                     (Jeffrey / User Interface)                       │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼ PAC Emission
┌─────────────────────────────────────────────────────────────────────┐
│               🧠 ORCHESTRATION ENGINE (SYSTEM_ORCHESTRATOR)          │
│                                                                      │
│   PAG Gate Validation:                                               │
│   PAG-01 │ Scope Definition      │ ✅                               │
│   PAG-02 │ Agent Selection       │ ✅                               │
│   PAG-03 │ Execution Constraints │ ✅                               │
│   PAG-04 │ Required Outputs      │ ✅                               │
│   PAG-05 │ Governance Duty       │ ✅                               │
│   PAG-06 │ Terminal Visibility   │ ✅                               │
│   PAG-07 │ Attestation           │ ✅                               │
│                                                                      │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼ Dispatch
┌─────────────────────────────────────────────────────────────────────┐
│                    EXECUTION ENGINE (SYSTEM_EXECUTION)               │
│                                                                      │
│   Dispatches to Agent: GID-XX (e.g., GID-01 Cody)                   │
│   Mode: EXECUTION                                                    │
│   Lane: GOVERNANCE                                                   │
│                                                                      │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼ Work
┌─────────────────────────────────────────────────────────────────────┐
│                         AGENT (GID-01 Cody)                          │
│                                                                      │
│   - Executes deliverables                                            │
│   - Runs tests                                                       │
│   - Returns WRAP                                                     │
│                                                                      │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼ WRAP Return
┌─────────────────────────────────────────────────────────────────────┐
│               🧠 ORCHESTRATION ENGINE (SYSTEM_ORCHESTRATOR)          │
│                                                                      │
│   WRAP Review:                                                       │
│   - Validate proof blocks                                            │
│   - Check attestation                                                │
│   - Verify test passage                                              │
│                                                                      │
│   Issue BER:                                                         │
│   - APPROVED or CORRECTIVE                                           │
│   - Only orchestration engine may issue                              │
│                                                                      │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼ BER Returned
┌─────────────────────────────────────────────────────────────────────┐
│                        HUMAN DRAFTING SURFACE                        │
│                     (Jeffrey / User Interface)                       │
│                                                                      │
│   Receives: BER-XXXX-APPROVED or BER-XXXX-CORRECTIVE                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Authority Matrix — HARD LAW

### 4.1. Who May Do What

| Action                | Orchestration Engine | Execution Engine | Drafting Surface | Agent |
|-----------------------|----------------------|------------------|------------------|-------|
| Emit PAC              | ❌ NO               | ❌ NO            | ✅ YES           | ❌ NO |
| Validate PAC          | ✅ YES              | ❌ NO            | ❌ NO            | ❌ NO |
| Dispatch to Agent     | ✅ YES              | ✅ YES           | ❌ NO            | ❌ NO |
| Execute Work          | ❌ NO               | ❌ NO            | ❌ NO            | ✅ YES |
| Return WRAP           | ❌ NO               | ❌ NO            | ❌ NO            | ✅ YES |
| Review WRAP           | ✅ YES              | ❌ NO            | ❌ NO            | ❌ NO |
| Issue BER             | ✅ YES              | ❌ NO            | ❌ NO            | ❌ NO |
| Self-Approve          | ❌ NO               | ❌ NO            | ❌ NO            | ❌ NO |
| Override BER          | ❌ NO               | ❌ NO            | ❌ NO            | ❌ NO |

### 4.2. Forbidden Actions — HARD FAIL

| Violation                          | Result           |
|------------------------------------|------------------|
| Drafting surface issues WRAP       | HARD FAIL        |
| Drafting surface issues BER        | HARD FAIL        |
| Agent issues BER                   | HARD FAIL        |
| Agent self-approves                | HARD FAIL        |
| Persona-based authority claim      | HARD FAIL        |
| Execution engine issues BER        | HARD FAIL        |

---

## 5. Invariants — MANDATORY

```python
INV-ORC-001: Only SYSTEM_ORCHESTRATOR may issue BER
INV-ORC-002: DRAFTING_SURFACE may never emit WRAP or BER
INV-ORC-003: AGENT may never self-approve
INV-ORC-004: Persona strings have zero authority weight
INV-ORC-005: System components have no persona
INV-ORC-006: All authority is code-enforced, not prompt-enforced
INV-ORC-007: GID-00 registry entry marked system=True
```

---

## 6. Terminal Emissions — Canonical

### 6.1. Orchestration Engine Engaged
```
════════════════════════════════════════════════════════════════════
🧠 ORCHESTRATION ENGINE ENGAGED
   MODE: ORCHESTRATION
   DISCIPLINE: GOLD_STANDARD · FAIL-CLOSED
════════════════════════════════════════════════════════════════════
```

### 6.2. Persona Authority Rejected
```
════════════════════════════════════════════════════════════════════
⛔ PERSONA AUTHORITY REJECTED
   CLAIMED_PERSONA: "Benson"
   REASON: Persona strings have zero authority weight
   ENFORCEMENT: CODE_ONLY
════════════════════════════════════════════════════════════════════
```

### 6.3. System Governance Decision Issued
```
════════════════════════════════════════════════════════════════════
🟩 SYSTEM GOVERNANCE DECISION ISSUED
   DECISION: BER_APPROVED / BER_CORRECTIVE
   ISSUER: ORCHESTRATION_ENGINE (not persona)
   AUTHORITY: SYSTEM_ORCHESTRATOR
════════════════════════════════════════════════════════════════════
```

---

## 7. Anti-Patterns — FORBIDDEN

### 7.1. ❌ Persona-Based Authority
```
# FORBIDDEN — Persona has no authority
"As Benson, I approve this WRAP..."
"Benson says this is acceptable..."
```

### 7.2. ❌ Drafting Surface Governance
```
# FORBIDDEN — Drafting surface cannot govern
User: "I approve this work"
# This has no governance weight
```

### 7.3. ❌ Agent Self-Approval
```
# FORBIDDEN — Agents cannot approve their own work
Agent: "WRAP complete, BER issued: APPROVED"
# HARD FAIL — Agent cannot issue BER
```

### 7.4. ❌ Conversational Forgiveness
```
# FORBIDDEN — No conversational shortcuts
"Let's skip the BER this time..."
"Just approve it informally..."
```

---

## 8. Code Enforcement Location

```
core/governance/system_identities.py     — Canonical identity definitions
core/governance/enforcement.py           — BER authority enforcement
core/governance/terminal_gates.py        — Terminal emission support
```

---

## 9. Changelog

| Version | Date       | PAC Reference | Description                        |
|---------|------------|---------------|------------------------------------|
| 1.0.0   | 2025-12-26 | PAC-017       | Initial orchestration engine law   |

---

## 10. Attestation

```
This document is HARD LAW.
Violations result in HARD FAIL.
No exceptions.
No conversational forgiveness.
Code-enforced.
```

---

**END ORCHESTRATION_ENGINE_LAW_v1.md**
