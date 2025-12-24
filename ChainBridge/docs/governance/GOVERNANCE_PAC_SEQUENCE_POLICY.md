# GOVERNANCE PAC SEQUENCE POLICY

> **Authority:** PAC-ALEX-P42-GOVERNANCE-PAC-SEQUENCE-ENFORCEMENT-AND-RESERVATION-LOCK-01  
> **Mode:** FAIL_CLOSED  
> **Pattern:** PAC_SEQUENCE_IS_LAW  

---

## 1. Purpose

This document defines the canonical rules for PAC number sequencing, reservation locks, and PAC↔WRAP coupling enforcement. These rules ensure that governance artifacts are:

- **Auditable** — Every PAC number has a deterministic source
- **Sequential** — No gaps, no out-of-order emissions
- **Coupled** — PACs and WRAPs are paired by design
- **Tamper-evident** — Ledger records are immutable

---

## 2. Core Principles

### 2.1 PAC Numbers Are Global and Monotonic

PAC numbers (P##) are assigned globally across all agents. They are NOT per-agent namespaces.

```
INVARIANT: P(n+1) can only be issued after P(n) is committed
INVARIANT: No agent may self-assign PAC numbers
INVARIANT: Sequence is enforced by gate_pack.py
```

### 2.2 Reservations Are Required

Before emitting a PAC, the number MUST be reserved via ledger_writer:

```python
ledger.reserve_pac_number(
    pac_number=42,
    reserved_for_agent_gid="GID-08",
    reserved_for_agent_name="ALEX",
    authority_gid="GID-00",
    authority_name="BENSON",
    expires_in_hours=24
)
```

### 2.3 Reservations Are Single-Use

- Each reservation can be consumed exactly once
- Consumed reservations cannot be reused
- Expired reservations are invalid

### 2.4 PAC↔WRAP Coupling Is Mandatory

- Every executed PAC must have a corresponding WRAP
- WRAPs must reference their parent PAC
- Exception: PACs with status `ISSUED_NOT_EXECUTED` may exist without WRAP

---

## 3. Error Codes

| Code | Description | Severity |
|------|-------------|----------|
| GS_096 | PAC sequence violation — out-of-order PAC number | HARD_FAIL |
| GS_097 | PAC reservation required — PAC number not reserved | HARD_FAIL |
| GS_098 | PAC reservation invalid — expired/consumed/mismatched | HARD_FAIL |
| GS_099 | PAC↔WRAP coupling violation — missing counterpart | HARD_FAIL |

---

## 4. Reservation Workflow

### 4.1 Reserve a PAC Number

```python
from tools.governance.ledger_writer import GovernanceLedger

ledger = GovernanceLedger()

# Reserve P42 for ALEX
entry = ledger.reserve_pac_number(
    pac_number=42,
    reserved_for_agent_gid="GID-08",
    reserved_for_agent_name="ALEX",
    authority_gid="GID-00",
    authority_name="BENSON"
)

print(f"Reserved: {entry.artifact_id}")
```

### 4.2 Check Active Reservation

```python
reservation = ledger.get_active_reservation(42)
if reservation:
    print(f"P42 reserved for {reservation['reserved_for_agent_name']}")
else:
    print("P42 is available")
```

### 4.3 Get Next Available Number

```python
next_number = ledger.get_next_available_pac_number()
print(f"Next available: P{next_number}")
```

### 4.4 Validate PAC Before Emission

```python
result = ledger.validate_pac_sequence(
    pac_id="PAC-ALEX-P42-GOVERNANCE-PAC-SEQUENCE-ENFORCEMENT-AND-RESERVATION-LOCK-01",
    agent_gid="GID-08"
)

if result["valid"]:
    print("PAC sequence valid")
else:
    print(f"Error: {result['error_code']} — {result['message']}")
```

---

## 5. Gate Enforcement

### 5.1 validate_pac_sequence_and_reservations()

Location: `tools/governance/gate_pack.py`

This function enforces:
- Global monotonic PAC numbering
- Ledger-backed reservation requirement
- Agent-reservation matching

### 5.2 validate_pac_wrap_coupling()

Location: `tools/governance/gate_pack.py`

This function enforces:
- PAC files must have corresponding WRAP files
- WRAP files must have corresponding PAC files
- Same P## and same agent name

---

## 6. Ledger Entry Types

| Entry Type | Description |
|------------|-------------|
| `PAC_RESERVATION_CREATED` | New reservation recorded |
| `PAC_RESERVATION_CONSUMED` | Reservation used by PAC issuance |
| `PAC_RESERVATION_EXPIRED` | Reservation expired without use |

---

## 7. Training Signals

### 7.1 On Sequence Violation

```yaml
TRAINING_SIGNAL:
  signal_type: "CORRECTIVE"
  pattern: "PAC_SEQUENCE_IS_LAW"
  lesson:
    - "PAC numbers are global, not per-agent"
    - "Always check next_available before reserving"
    - "Reservations are authority-controlled"
```

### 7.2 On Coupling Violation

```yaml
TRAINING_SIGNAL:
  signal_type: "CORRECTIVE"
  pattern: "PAC_WRAP_COUPLING_REQUIRED"
  lesson:
    - "Every executed PAC must have a WRAP"
    - "WRAPs document completed work"
    - "Uncoupled artifacts fail validation"
```

---

## 8. Forbidden Actions

| Action | Error Code | Consequence |
|--------|------------|-------------|
| SELF_ASSIGN_PAC_NUMBER | GS_096/GS_097 | HARD_FAIL |
| BYPASS_SEQUENCE_ENFORCEMENT | GS_096 | HARD_FAIL |
| CREATE_PAC_WITHOUT_RESERVATION | GS_097 | HARD_FAIL |
| REUSE_CONSUMED_RESERVATION | GS_098 | HARD_FAIL |
| EMIT_PAC_WITHOUT_WRAP | GS_099 | HARD_FAIL |
| EMIT_WRAP_WITHOUT_PAC | GS_099 | HARD_FAIL |
| RETROACTIVE_RENUMBERING | N/A | LEDGER_IMMUTABLE |

---

## 9. CLI Usage

### 9.1 Validate a PAC File

```bash
python tools/governance/gate_pack.py --file docs/governance/pacs/PAC-ALEX-P42-*.md
```

### 9.2 Reserve a PAC Number (via script)

```python
# reserve_pac.py
import sys
from tools.governance.ledger_writer import GovernanceLedger

ledger = GovernanceLedger()
pac_num = int(sys.argv[1])
agent_gid = sys.argv[2]
agent_name = sys.argv[3]

ledger.reserve_pac_number(
    pac_number=pac_num,
    reserved_for_agent_gid=agent_gid,
    reserved_for_agent_name=agent_name,
    authority_gid="GID-00",
    authority_name="BENSON"
)
```

---

## 10. Immutability

This policy is **IMMUTABLE** once committed. Changes require:

1. New PAC with CORRECTION_CLASS
2. BENSON review and approval
3. Full gate validation

---

**END — GOVERNANCE PAC SEQUENCE POLICY**
**Authority:** ALEX (GID-08)
**Mode:** FAIL_CLOSED
**Pattern:** PAC_SEQUENCE_IS_LAW
