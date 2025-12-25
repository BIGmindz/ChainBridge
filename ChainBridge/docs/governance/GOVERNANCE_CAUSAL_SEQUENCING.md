# GOVERNANCE_CAUSAL_SEQUENCING.md

> **Version:** 1.0.0  
> **Authority:** PAC-BENSON-P42-SEQUENTIAL-PAC-WRAP-GATING-AND-CAUSAL-ADVANCEMENT-ENFORCEMENT-01  
> **Status:** ACTIVE  
> **Mode:** FAIL_CLOSED  
> **Last Updated:** 2025-12-24

---

## 1. Purpose

This document defines the **causal sequencing rules** for PACs and WRAPs in the ChainBridge governance system. These rules ensure:

1. **Accountability** — Every PAC must produce a WRAP documenting its execution
2. **Sequence Integrity** — PAC numbers advance monotonically with no gaps
3. **Causal Binding** — PAC and WRAP are treated as a causally bound pair
4. **Progress Verification** — No new work begins until prior work is documented

---

## 2. Fundamental Invariants

### 2.1 PAC↔WRAP Binding

Every PAC **MUST** have a corresponding WRAP. This is not optional.

```
PAC-AGENT-Pn-DESCRIPTOR-01 ⟹ WRAP-AGENT-Pn-DESCRIPTOR-01
```

**Constraint:** Same agent, same P##, same descriptor root.

### 2.2 Sequential Advancement

PAC numbers must advance strictly incrementally:

```
P(n) → P(n+1) → P(n+2) → ...
```

**Violations:**
- Skipping: P40 → P42 (❌ GS_097)
- Regression: P42 → P40 (❌ GS_097)
- Duplicate: P42 → P42 (❌ GS_097)

### 2.3 Causal Gating

A new PAC may **NOT** be issued if any prior PAC lacks a WRAP:

```
IF PAC-Pn has no WRAP THEN
  BLOCK(PAC-P(n+1))
  ERROR: GS_096
```

**Pattern:** CAUSALITY_OVER_CONVENIENCE  
**Lesson:** Progress without proof is not progress.

---

## 3. PAC States

A PAC transitions through the following states:

| State | Description | Next State |
|-------|-------------|------------|
| ISSUED | PAC created and recorded | EXECUTED |
| EXECUTED | PAC tasks completed | CLOSED |
| CLOSED | WRAP submitted and bound | — (terminal) |
| BLOCKED | Cannot advance due to missing WRAP | EXECUTED (after WRAP) |

### State Transitions

```
ISSUED → EXECUTED → CLOSED
           ↓
        BLOCKED (if next PAC attempted)
```

---

## 4. Error Codes

| Code | Condition | Action |
|------|-----------|--------|
| **GS_096** | Missing WRAP for prior PAC | BLOCK new PAC issuance |
| **GS_097** | PAC number out of sequence | REJECT artifact |
| **GS_098** | WRAP/PAC number mismatch | REJECT WRAP binding |
| **GS_099** | PAC↔WRAP coupling violation (file-based) | WARN or BLOCK |

---

## 5. Ledger Tracking

The Governance Ledger tracks PAC↔WRAP binding:

### 5.1 PAC Issuance

```json
{
  "entry_type": "PAC_ISSUED",
  "artifact_id": "PAC-BENSON-P42-...",
  "artifact_status": "ISSUED"
}
```

### 5.2 WRAP Submission

```json
{
  "entry_type": "WRAP_SUBMITTED",
  "artifact_id": "WRAP-BENSON-P42-...",
  "parent_artifact": "PAC-BENSON-P42-...",
  "artifact_status": "ISSUED"
}
```

### 5.3 Querying Open PACs

```python
ledger = GovernanceLedger()
open_pacs = ledger.get_pacs_awaiting_wrap(agent_gid="GID-00")

# Returns: ["PAC-BENSON-P41-..."] (if P41 has no WRAP)
```

---

## 6. Enforcement Points

### 6.1 Gate Pack Validation

`gate_pack.py` enforces causal sequencing at validation time:

```python
# In validate_pac_sequence_and_reservations()
causal_result = ledger.validate_causal_advancement(pac_id, agent_gid)

if not causal_result.get("valid"):
    errors.append(ValidationError(
        ErrorCode.GS_096,
        causal_result.get("message"),
    ))
```

### 6.2 CI Integration

CI mode (`--mode ci`) validates:

1. All PACs have sequential numbers
2. All executed PACs have corresponding WRAPs
3. No gaps in P## sequence per agent

### 6.3 Ledger Writer

`ledger_writer.py` provides:

- `get_pacs_awaiting_wrap(agent_gid)` — List PACs without WRAPs
- `validate_causal_advancement(pac_id, agent_gid)` — Check advancement rules
- `bind_wrap_to_pac(wrap_id, pac_id)` — Record WRAP↔PAC binding

---

## 7. Examples

### 7.1 Valid Sequence

```
PAC-BENSON-P40-FEATURE-A → WRAP-BENSON-P40-FEATURE-A ✅
PAC-BENSON-P41-FEATURE-B → WRAP-BENSON-P41-FEATURE-B ✅
PAC-BENSON-P42-FEATURE-C → (in progress)
```

### 7.2 Blocked Sequence

```
PAC-BENSON-P40-FEATURE-A → WRAP-BENSON-P40-FEATURE-A ✅
PAC-BENSON-P41-FEATURE-B → (no WRAP) ❌ OPEN
PAC-BENSON-P42-FEATURE-C → BLOCKED (GS_096)
```

**Resolution:** Submit WRAP-BENSON-P41-FEATURE-B first.

### 7.3 Number Mismatch

```
PAC-BENSON-P42-FEATURE-X
WRAP-BENSON-P41-FEATURE-X → GS_098 (P## mismatch)
```

---

## 8. Exceptions

### 8.1 ISSUED_NOT_EXECUTED Status

PACs with `artifact_status: ISSUED_NOT_EXECUTED` do not require WRAPs yet:

```yaml
artifact_status: ISSUED_NOT_EXECUTED
```

These PACs are "planned but not executed" and don't block advancement.

### 8.2 Cross-Agent Independence

Agents' PAC sequences are independent:

- BENSON P42 does NOT block ATLAS P10
- Each agent maintains their own sequence

### 8.3 Legacy Grandfathering

PACs issued before this enforcement (P01-P41) may be grandfathered.

---

## 9. Implementation Checklist

| Component | File | Status |
|-----------|------|--------|
| Error codes GS_096-098 | `gate_pack.py` | ✅ |
| Causal advancement validation | `gate_pack.py` | ✅ |
| `get_pacs_awaiting_wrap()` | `ledger_writer.py` | ✅ |
| `validate_causal_advancement()` | `ledger_writer.py` | ✅ |
| `bind_wrap_to_pac()` | `ledger_writer.py` | ✅ |
| CI integration | `gate_pack.py --mode ci` | ✅ |
| Regression tests | `test_sequential_pac_wrap_enforcement.py` | ✅ |

---

## 10. Training Signal

```yaml
TRAINING_SIGNAL:
  pattern: CAUSALITY_OVER_CONVENIENCE
  lesson: "Progress without proof is not progress."
  mandatory: true
  propagate: true
```

---

## 11. References

- [GOVERNANCE_SCHEMA.md](./GOVERNANCE_SCHEMA.md) — PAC/WRAP schema
- [AGENT_REGISTRY.md](./AGENT_REGISTRY.md) — Agent definitions
- [ledger_writer.py](../../tools/governance/ledger_writer.py) — Ledger implementation
- [gate_pack.py](../../tools/governance/gate_pack.py) — Validation engine

---

**END OF DOCUMENT**
