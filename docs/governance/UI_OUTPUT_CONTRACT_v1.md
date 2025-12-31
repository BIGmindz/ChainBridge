# UI Output Contract v1

**Document ID:** UI-OUTPUT-CONTRACT-LAW-001  
**Version:** 1.0.0  
**Status:** ACTIVE  
**Effective:** 2025-12-26  
**Author:** Agent GID-01 (Cody)  
**PAC Reference:** PAC-JEFFREY-DRAFT-GOVERNANCE-UI-OUTPUT-CONTRACT-025

---

## 1. Purpose

This document establishes the **UI Output Contract** — a formal specification
defining what the orchestration engine MAY and MAY NOT emit to the user interface.

The contract creates a **hard separation** between:
- **Execution Telemetry** — Internal operational data (unbounded, machine-readable)
- **UI Signals** — Human-facing checkpoints (bounded, predictable)

---

## 2. Core Principle

> **UI bandwidth is finite; governance is not.**

The orchestration engine processes unlimited internal telemetry, but emits only
bounded, deterministic signals to the UI. This ensures:

1. No output saturation under high agent concurrency (4–8+ agents)
2. Predictable UI behavior regardless of task complexity
3. Human-readable progress without cognitive overload
4. Full auditability preserved in internal logs

---

## 3. Allowed UI Emissions (STRICT ENUM)

Only the following emission types are permitted:

| Emission Type        | Symbol | Description                              |
|----------------------|--------|------------------------------------------|
| PAC_RECEIVED         | 🟦     | PAC validated and accepted               |
| AGENTS_DISPATCHED    | 🚀     | N agents dispatched in parallel          |
| CHECKPOINT_REACHED   | ⏳     | Named checkpoint reached                 |
| WRAP_HASH_RECEIVED   | 📦     | WRAP hash received from agent            |
| BER_ISSUED           | 🟩     | Benson Execution Report issued           |
| PDO_EMITTED          | 🧿     | Proof-Decision-Outcome emitted           |
| ERROR_SIGNAL         | 🔴     | Critical error requiring attention       |
| WARNING_SIGNAL       | 🟡     | Non-fatal warning                        |

### 3.1 Emission Format

All UI emissions MUST follow this format:

```
{SYMBOL} {EMISSION_TYPE}: {BRIEF_MESSAGE} [{HASH_REF}]
```

Examples:
```
🟦 PAC_RECEIVED: PAC-025 validated
🚀 AGENTS_DISPATCHED: 4 agents (GID-01, GID-02, GID-07, GID-10)
📦 WRAP_HASH_RECEIVED: GID-01 [sha256:abc123...]
🟩 BER_ISSUED: APPROVE [BER-025]
🧿 PDO_EMITTED: PDO-025 [sha256:def456...]
```

### 3.2 Maximum Emission Length

- **Single emission:** ≤ 120 characters
- **Hash references:** Truncated to 12 characters + "..."
- **Agent lists:** Maximum 8 GIDs, then "+N more"

---

## 4. Forbidden UI Emissions

The following are **STRICTLY FORBIDDEN** from UI output:

| Forbidden Type       | Reason                                    |
|----------------------|-------------------------------------------|
| Task logs            | Unbounded, verbose                        |
| Todo list updates    | Internal state, not signals               |
| File listings        | Can be arbitrarily long                   |
| Diff outputs         | Unbounded, often massive                  |
| Full WRAP payloads   | Hash-only references required             |
| Full PDO payloads    | Hash-only references required             |
| Agent narration      | Internal execution detail                 |
| Progress percentages | Misleading for non-linear work            |
| Intermediate results | Only checkpoints matter                   |
| Stack traces         | Internal telemetry only                   |
| Debug logs           | Never in UI                               |

### 4.1 Invariant: INV-UI-001

**No unbounded output may reach the UI.**

Any emission that cannot be bounded to ≤120 characters MUST be:
1. Replaced with a hash reference
2. Or omitted entirely
3. Or converted to a checkpoint signal

---

## 5. UI vs Telemetry Boundary

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATION ENGINE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    EXECUTION TELEMETRY                           │   │
│  │  (Unbounded, Full Detail, Machine-Readable)                      │   │
│  │                                                                   │   │
│  │  • Agent task logs                                               │   │
│  │  • File operations                                               │   │
│  │  • Test output                                                   │   │
│  │  • Full WRAP payloads                                            │   │
│  │  • Performance metrics                                           │   │
│  │  • Error details                                                 │   │
│  └──────────────────────────┬──────────────────────────────────────┘   │
│                              │                                          │
│                              │ validate_ui_emission()                   │
│                              │ reject_unbounded_output()                │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                       UI SIGNALS                                 │   │
│  │  (Bounded, Checkpoint-Only, Human-Readable)                      │   │
│  │                                                                   │   │
│  │  • PAC_RECEIVED                                                  │   │
│  │  • AGENTS_DISPATCHED                                             │   │
│  │  • CHECKPOINT_REACHED                                            │   │
│  │  • WRAP_HASH_RECEIVED                                            │   │
│  │  • BER_ISSUED                                                    │   │
│  │  • PDO_EMITTED                                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Invariants

### INV-UI-001 — Bounded Output
No UI emission may exceed 120 characters.

### INV-UI-002 — Checkpoint-Only
Only enumerated checkpoint types may be emitted.

### INV-UI-003 — Hash-Only References
WRAPs, PDOs, and artifacts MUST be referenced by hash only.

### INV-UI-004 — No Agent Narration
Agents do not emit directly to UI. Only GID-00 emits.

### INV-UI-005 — Deterministic Ordering
UI emissions follow deterministic order based on governance events.

### INV-UI-006 — Fail-Closed
Invalid emissions are rejected, not truncated or modified.

---

## 7. Enforcement

### 7.1 Validation Function

```python
def validate_ui_emission(emission: UIEmission) -> bool:
    """
    Validate emission against UI Output Contract.
    
    Returns True if valid, raises UIContractViolation if not.
    """
    # Check emission type is allowed
    if emission.emission_type not in ALLOWED_EMISSION_TYPES:
        raise UIContractViolation("Forbidden emission type")
    
    # Check length bound
    if len(emission.render()) > MAX_EMISSION_LENGTH:
        raise UIContractViolation("Emission exceeds length bound")
    
    # Check no forbidden content
    if contains_forbidden_content(emission):
        raise UIContractViolation("Contains forbidden content")
    
    return True
```

### 7.2 Rejection Function

```python
def reject_unbounded_output(output: Any) -> NoReturn:
    """
    Reject any attempt to emit unbounded output.
    
    FAIL-CLOSED: Does not truncate, does not modify.
    """
    raise UIContractViolation(
        f"Unbounded output rejected: {type(output).__name__}"
    )
```

---

## 8. Rationale

### 8.1 Why Separate Signals from Telemetry?

**Human signal ≠ Execution data**

- Humans need progress indicators, not logs
- Machines need full telemetry, not summaries
- Mixing them creates cognitive overload and output saturation

### 8.2 Why Hash-Only?

- Hashes are fixed-length (bounded)
- Full payloads can be arbitrarily large
- Verification happens internally, not in UI

### 8.3 Why Fail-Closed?

- Truncation hides information unpredictably
- Modification changes semantics
- Rejection is explicit and auditable

---

## 9. Changelog

| Version | Date       | Author  | Changes                        |
|---------|------------|---------|--------------------------------|
| 1.0.0   | 2025-12-26 | GID-01  | Initial specification          |

---

**END OF DOCUMENT — UI_OUTPUT_CONTRACT_v1.md**
