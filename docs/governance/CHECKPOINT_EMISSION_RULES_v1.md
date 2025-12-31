# Checkpoint Emission Rules v1

**Document ID:** CHECKPOINT-EMISSION-LAW-001  
**Version:** 1.0.0  
**Status:** ACTIVE  
**Effective:** 2025-12-26  
**Author:** Agent GID-01 (Cody)  
**PAC Reference:** PAC-JEFFREY-DRAFT-GOVERNANCE-UI-OUTPUT-CONTRACT-025

---

## 1. Purpose

This document defines the **Checkpoint Emission Rules** — the canonical set of
checkpoints that may be emitted to the UI during orchestration execution.

No intermediate chatter is allowed. Only these checkpoints signal progress.

---

## 2. Core Principle

> **Checkpoints are governance events, not task updates.**

A checkpoint represents a significant state transition in the governance loop,
not incremental progress within a task.

---

## 3. Canonical Checkpoints

### 3.1 Checkpoint Definitions

| Checkpoint           | Symbol | Trigger Condition                        |
|----------------------|--------|------------------------------------------|
| PAC_RECEIVED         | 🟦     | PAC validated and snapshot locked        |
| AGENTS_DISPATCHED    | 🚀     | All agents dispatched (parallel start)   |
| AGENT_STARTED        | ⏳     | Individual agent began execution         |
| AGENT_COMPLETED      | ✓      | Individual agent returned WRAP           |
| WRAP_HASH_RECEIVED   | 📦     | WRAP hash verified and recorded          |
| ALL_WRAPS_RECEIVED   | 📦📦   | All expected WRAPs collected             |
| BER_ISSUED           | 🟩     | Benson Execution Report issued           |
| PDO_EMITTED          | 🧿     | Proof-Decision-Outcome emitted           |
| ERROR_CHECKPOINT     | 🔴     | Critical failure detected                |

### 3.2 Checkpoint Sequence (Normal Flow)

```
1. 🟦 PAC_RECEIVED
2. 🚀 AGENTS_DISPATCHED
3. ⏳ AGENT_STARTED (×N, parallel)
4. ✓  AGENT_COMPLETED (×N, as they finish)
5. 📦 WRAP_HASH_RECEIVED (×N)
6. 📦📦 ALL_WRAPS_RECEIVED
7. 🟩 BER_ISSUED
8. 🧿 PDO_EMITTED
```

---

## 4. Emission Rules

### Rule 1: One Emission Per Checkpoint

Each checkpoint emits exactly ONE UI signal. No repeats, no duplicates.

### Rule 2: No Intermediate Chatter

Between checkpoints, no UI emissions occur. Internal processing is silent.

### Rule 3: Checkpoint Ordering is Deterministic

Checkpoints follow the governance loop order. No out-of-order emissions.

### Rule 4: Agent Checkpoints May Interleave

`AGENT_STARTED` and `AGENT_COMPLETED` may interleave across agents in parallel
execution, but each agent's sequence is ordered.

### Rule 5: Aggregation Before Final Checkpoints

Before `BER_ISSUED`, all individual `WRAP_HASH_RECEIVED` must complete.

---

## 5. Checkpoint Format

### 5.1 Standard Format

```
{SYMBOL} {CHECKPOINT_NAME}: {CONTEXT} [{REF}]
```

### 5.2 Examples

```
🟦 PAC_RECEIVED: PAC-GOVERNANCE-UI-CONTRACT-025 validated
🚀 AGENTS_DISPATCHED: 4 agents (GID-01, GID-02, GID-07, GID-10)
⏳ AGENT_STARTED: GID-01 (Cody) — GOVERNANCE lane
✓  AGENT_COMPLETED: GID-01 — 45 tests passed
📦 WRAP_HASH_RECEIVED: GID-01 [sha256:a1b2c3d4...]
📦📦 ALL_WRAPS_RECEIVED: 4/4 WRAPs verified
🟩 BER_ISSUED: APPROVE — all invariants satisfied [BER-025]
🧿 PDO_EMITTED: PDO-025 [sha256:e5f6g7h8...]
```

---

## 6. Maximum Emissions Per PAC

For a PAC with N agents:

| Checkpoint Type      | Count       |
|----------------------|-------------|
| PAC_RECEIVED         | 1           |
| AGENTS_DISPATCHED    | 1           |
| AGENT_STARTED        | N           |
| AGENT_COMPLETED      | N           |
| WRAP_HASH_RECEIVED   | N           |
| ALL_WRAPS_RECEIVED   | 1           |
| BER_ISSUED           | 1           |
| PDO_EMITTED          | 1           |
| **TOTAL**            | **4 + 3N**  |

For 4 agents: 4 + 12 = **16 checkpoints maximum**  
For 8 agents: 4 + 24 = **28 checkpoints maximum**

This is bounded and predictable.

---

## 7. Forbidden Between Checkpoints

The following MUST NOT be emitted between checkpoints:

- File creation notifications
- Test progress updates
- Todo list changes
- Intermediate results
- Thinking/reasoning output
- Code snippets
- Diff displays
- Error stack traces (use ERROR_CHECKPOINT summary only)

---

## 8. Error Checkpoint Rules

### 8.1 When to Emit ERROR_CHECKPOINT

- Agent fails to return WRAP
- Invariant violation detected
- Test failure blocks BER
- System error prevents completion

### 8.2 Error Format

```
🔴 ERROR_CHECKPOINT: {ERROR_TYPE} — {BRIEF_DESCRIPTION}
```

Examples:
```
🔴 ERROR_CHECKPOINT: WRAP_MISSING — GID-02 failed to return WRAP
🔴 ERROR_CHECKPOINT: INVARIANT_VIOLATION — INV-UI-003 violated
🔴 ERROR_CHECKPOINT: TEST_FAILURE — 3/47 tests failed in GID-01
```

### 8.3 Error Recovery

After ERROR_CHECKPOINT, the orchestration engine may:
1. Attempt retry (emit new AGENT_STARTED)
2. Issue CORRECTIVE BER
3. Halt execution

---

## 9. Checkpoint State Machine

```
                    ┌─────────────────┐
                    │   PAC_RECEIVED  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │AGENTS_DISPATCHED│
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌───────────┐  ┌───────────┐  ┌───────────┐
        │  AGENT_A  │  │  AGENT_B  │  │  AGENT_N  │
        │  STARTED  │  │  STARTED  │  │  STARTED  │
        └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
              │              │              │
              ▼              ▼              ▼
        ┌───────────┐  ┌───────────┐  ┌───────────┐
        │  AGENT_A  │  │  AGENT_B  │  │  AGENT_N  │
        │ COMPLETED │  │ COMPLETED │  │ COMPLETED │
        └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
              │              │              │
              ▼              ▼              ▼
        ┌───────────┐  ┌───────────┐  ┌───────────┐
        │   WRAP_A  │  │   WRAP_B  │  │   WRAP_N  │
        │  RECEIVED │  │  RECEIVED │  │  RECEIVED │
        └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ALL_WRAPS_RECEIVED│
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   BER_ISSUED    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   PDO_EMITTED   │
                    └─────────────────┘
```

---

## 10. Invariants

### INV-CKPT-001 — Checkpoint-Only Emissions
Only canonical checkpoints may be emitted to UI.

### INV-CKPT-002 — No Intermediate Chatter
No emissions between checkpoint transitions.

### INV-CKPT-003 — Deterministic Ordering
Checkpoint order follows governance loop state machine.

### INV-CKPT-004 — Bounded Total Emissions
Maximum emissions = 4 + 3N for N agents.

### INV-CKPT-005 — All Checkpoints Logged
Every emitted checkpoint is also logged to telemetry.

---

## 11. Changelog

| Version | Date       | Author  | Changes                        |
|---------|------------|---------|--------------------------------|
| 1.0.0   | 2025-12-26 | GID-01  | Initial specification          |

---

**END OF DOCUMENT — CHECKPOINT_EMISSION_RULES_v1.md**
