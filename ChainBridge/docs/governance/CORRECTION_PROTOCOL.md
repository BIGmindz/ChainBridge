# Correction Protocol — G0.2.0

> **Governance Document** — PAC-BENSON-G0-GOVERNANCE-CORRECTION-02
> **Version:** G0.2.0
> **Effective Date:** 2025-12-22
> **Authority:** Benson (GID-00)
> **Status:** LOCKED / MANDATORY / MACHINE-ENFORCED

---

## Purpose

This document defines the **mandatory correction protocol** when any agent produces an invalid or non-compliant PAC/WRAP artifact.

```
Governance is physics, not policy.
"Close enough" is impossible.
```

---

## Correction Protocol (5 Steps)

```
┌─────────────────────────────────────────────────────────────────┐
│                    CORRECTION PROTOCOL                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   STEP 1: AGENT BLOCKED                                         │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ Agent's artifact failed validation                      │   │
│   │ Agent cannot proceed with new work                      │   │
│   │ Status: BLOCKED                                         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                          ▼                                      │
│   STEP 2: AGENT ACKNOWLEDGES DEFICIENCIES                       │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ Agent must explicitly ACK each deficiency               │   │
│   │ Format: "I acknowledge [specific issue]"                │   │
│   │ No generic acknowledgments accepted                     │   │
│   └─────────────────────────────────────────────────────────┘   │
│                          ▼                                      │
│   STEP 3: AGENT REISSUES CORRECTED ARTIFACT                     │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ Agent produces new PAC/WRAP with all corrections        │   │
│   │ Must pass all gates (Emission → Pre-Commit → CI)        │   │
│   │ No "partial fixes" allowed                              │   │
│   └─────────────────────────────────────────────────────────┘   │
│                          ▼                                      │
│   STEP 4: BENSON VALIDATES                                      │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ Benson (GID-00) reviews corrected artifact              │   │
│   │ Validates against Gold Standard template                │   │
│   │ Confirms all deficiencies addressed                     │   │
│   └─────────────────────────────────────────────────────────┘   │
│                          ▼                                      │
│   STEP 5: AGENT UNBLOCKED                                       │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ Only after validation passes                            │   │
│   │ Agent may resume normal work                            │   │
│   │ Status: ACTIVE                                          │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Acknowledgment Format (MANDATORY)

When an agent acknowledges deficiencies, they MUST use this format:

```yaml
CORRECTION_ACK:
  agent: "<Name>"
  gid: "GID-XX"
  original_artifact: "<PAC/WRAP-ID>"
  deficiencies_acknowledged:
    - "<Specific deficiency 1>"
    - "<Specific deficiency 2>"
    - "<Specific deficiency N>"
  corrective_action: "<What agent will do>"
  reissue_id: "<New PAC/WRAP-ID>"
```

**Validation Rules:**
- Agent name and GID must match registry
- Each deficiency must be specific (not generic)
- Corrective action must address all deficiencies
- Reissue ID must follow naming convention

---

## Blocked States

| State | Meaning | Can Agent Work? |
|-------|---------|-----------------|
| `ACTIVE` | Normal operation | ✅ Yes |
| `BLOCKED` | Failed validation | ❌ No |
| `PENDING_ACK` | Awaiting acknowledgment | ❌ No |
| `PENDING_REISSUE` | Awaiting corrected artifact | ❌ No |
| `PENDING_VALIDATION` | Awaiting Benson review | ❌ No |

---

## What Triggers a Block?

An agent is BLOCKED when any of the following occur:

1. **Gate 1 Failure** — Pack emission validation fails
2. **Gate 2 Failure** — Pre-commit hook rejects artifact
3. **Gate 3 Failure** — CI merge blocker triggers
4. **Gate 4 Failure** — WRAP references invalid PAC
5. **Registry Violation** — GID, color, role, or lane mismatch
6. **Template Violation** — Missing mandatory sections
7. **Training Signal Invalid** — Missing or malformed TRAINING_SIGNAL
8. **FINAL_STATE Invalid** — Missing or malformed FINAL_STATE
9. **Bypass Attempt** — Any attempt to circumvent gates

---

## Prohibited During Block

While BLOCKED, the agent CANNOT:

- Issue new PACs
- Issue new WRAPs
- Execute existing PACs
- Approve other agents' work
- Modify governance artifacts
- Request unblocking without ACK + reissue

---

## Escalation Path

If an agent disputes a block:

1. Agent documents dispute reason
2. Benson (GID-00) reviews
3. If valid concern → Benson issues governance clarification PAC
4. If invalid → Block remains until correction protocol completed
5. No appeals beyond Benson

---

## Training Integration

Every correction is a **learning opportunity**:

```yaml
CORRECTION_TRAINING_SIGNAL:
  program: "Agent University"
  level: "REMEDIAL"
  domain: "Governance Compliance"
  competencies:
    - Identifying template violations
    - Understanding gate failures
    - Proper acknowledgment format
    - Complete correction process
  evaluation: "BINARY"
  retention: "PERMANENT"
  outcome: "REQUIRED_PASS"
```

---

## Example Correction Flow

### Original Failed Artifact

```
PAC-CODY-A6-FEATURE-01 → VALIDATION FAILED
  [G0_001] Missing RUNTIME_ACTIVATION_ACK block
  [G0_011] Missing FORBIDDEN_ACTIONS section
```

### Agent Acknowledgment

```yaml
CORRECTION_ACK:
  agent: "Cody"
  gid: "GID-01"
  original_artifact: "PAC-CODY-A6-FEATURE-01"
  deficiencies_acknowledged:
    - "Missing RUNTIME_ACTIVATION_ACK block (G0_001)"
    - "Missing FORBIDDEN_ACTIONS section (G0_011)"
  corrective_action: "Reissue PAC with all mandatory blocks per G0.2.0 template"
  reissue_id: "PAC-CODY-A6-FEATURE-02"
```

### Corrected Artifact

```
PAC-CODY-A6-FEATURE-02 → VALIDATION PASSED
  ✓ All 13 required blocks present
  ✓ Block order correct
  ✓ Registry identity verified
  ✓ FORBIDDEN_ACTIONS included
  ✓ TRAINING_SIGNAL valid
  ✓ FINAL_STATE valid
```

### Unblock

```yaml
AGENT_UNBLOCK:
  agent: "Cody"
  gid: "GID-01"
  correction_artifact: "PAC-CODY-A6-FEATURE-02"
  validated_by: "Benson (GID-00)"
  status: "ACTIVE"
  timestamp: "2025-12-22T00:00:00Z"
```

---

## Lock Declaration

```yaml
CORRECTION_PROTOCOL_LOCK {
  version: "G0.2.0"
  status: "LOCKED"
  enforcement: "MANDATORY"
  override_allowed: false
  applies_to: "ALL_AGENTS"
  authority: "Benson (GID-00)"
}
```

---

🟦🟩 **BENSON (GID-00)** — Chief Architect & Orchestrator
