# ChainBridge Constitution: Lock Lifecycle

**Document:** LOCK_LIFECYCLE.md
**Version:** 1.0
**Status:** LOCKED
**Classification:** CONTRACT (Constitution Document)

**Contract Owner:** BENSON (GID-00)
**PAC Reference:** PAC-BENSON-CONSTITUTION-ENGINE-01
**Effective Date:** 2025-12-18
**Alignment:** LOCK_REGISTRY.yaml

---

## 1. Purpose

This document defines the **lock lifecycle** for the ChainBridge Constitution:

- How locks are created
- What can and cannot be done to existing locks
- How locks are superseded
- Why locks cannot be bypassed or disabled

**Locks are constitutional law.** They outrank PACs. PACs outrank agents.

---

## 2. Lock Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                     CONSTITUTIONAL HIERARCHY                     │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                        LOCKS                            │   │
│   │          (Immutable machine-enforced law)               │   │
│   └────────────────────────┬────────────────────────────────┘   │
│                            │                                    │
│                            │ outranks                           │
│                            ▼                                    │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                        PACs                             │   │
│   │          (Scoped agent directives)                      │   │
│   └────────────────────────┬────────────────────────────────┘   │
│                            │                                    │
│                            │ outranks                           │
│                            ▼                                    │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                       AGENTS                            │   │
│   │          (Executors, not lawmakers)                     │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Lock Lifecycle States

```
┌──────────────┐
│   PROPOSED   │───▶ PAC submitted
└──────┬───────┘
       │
       │ PAC approved + enforcement verified
       ▼
┌──────────────┐
│    ACTIVE    │───▶ In LOCK_REGISTRY.yaml, CI-enforced
└──────┬───────┘
       │
       │ (ONLY via supersession)
       ▼
┌──────────────┐
│  SUPERSEDED  │───▶ Replaced by stricter lock
└──────────────┘
       │
       │ Never
       ▼
┌──────────────────────────────────────────────────────────────┐
│   MODIFIED / BYPASSED / DISABLED  ─────────▶  IMPOSSIBLE     │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Lifecycle Actions

### 4.1 Action Matrix

| Action | Allowed | Mechanism | Result |
|--------|---------|-----------|--------|
| **Create lock** | ✓ | New PAC with enforcement | Lock added to registry |
| **Modify lock** | ✗ | N/A | Forbidden |
| **Supersede lock** | ✓ | New stricter lock + explicit deprecation | Old lock marked SUPERSEDED |
| **Bypass lock** | ✗ | N/A | Impossible — enforcement is mechanical |
| **Disable lock** | ✗ | N/A | Impossible — no disable mechanism exists |
| **Delete lock** | ✗ | N/A | Forbidden |

### 4.2 Create Lock

**Preconditions:**
1. PAC must exist with lock specification
2. Lock must map to existing invariants OR define new invariant
3. At least one enforcement mechanism must be specified
4. Enforcement mechanism must exist and pass

**Process:**

```yaml
# New lock in PAC
lock_proposal:
  lock_id: LOCK-{DOMAIN}-{TYPE}-{NNN}
  description: Clear description
  scope: [affected_domains]
  type: invariant | constraint | boundary | gate
  source_invariants: [existing INV-* IDs]
  enforcement:
    - test_required: path/to/test.py
    - runtime_assert: "description of assertion"
    - ci_workflow: workflow_name.yml
    - pac_gate: true
  severity: CRITICAL | HIGH | MEDIUM
  violation_policy:
    action: HARD_FAIL | SOFT_FAIL
    telemetry: REQUIRED | OPTIONAL
```

**Acceptance:**
- PAC approved by authorized agent (BENSON/ALEX)
- All enforcement tests pass
- CI workflow exists (if specified)
- Lock added to LOCK_REGISTRY.yaml

### 4.3 Supersede Lock

**When to supersede:**
- Existing lock needs to be stricter
- New invariant replaces old invariant
- Scope needs to expand

**Process:**

```yaml
# Supersession in PAC
lock_supersession:
  old_lock_id: LOCK-GW-EXAMPLE-001
  new_lock_id: LOCK-GW-EXAMPLE-002
  reason: "Expanding scope to include OCC domain"
  strictness_comparison: NEW_IS_STRICTER

  new_lock:
    lock_id: LOCK-GW-EXAMPLE-002
    description: Updated description
    scope: [original_domains, new_domains]  # Can only expand
    # ... rest of lock specification
```

**Rules:**
- New lock MUST be stricter or equal
- New lock scope MUST be superset of old scope
- Old lock marked as SUPERSEDED, not deleted
- Old lock remains in registry for audit trail

### 4.4 Modification (FORBIDDEN)

**Why modification is forbidden:**

1. **Proof Integrity:** Past proofs reference specific lock versions
2. **Audit Trail:** History must be immutable
3. **Trust:** Downstream systems depend on lock stability
4. **Drift Prevention:** Modification enables gradual weakening

**What happens if modification is attempted:**

```
Attempt to modify lock
         │
         ▼
┌──────────────────┐
│  CI Gate Check   │
│  (constitution   │
│   _check.yml)    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   HARD_FAIL      │
│   PR Blocked     │
│   Telemetry Emit │
└──────────────────┘
```

### 4.5 Bypass (IMPOSSIBLE)

**Why bypass is impossible:**

1. **Runtime Assertions:** Code-level guards cannot be circumvented without code change
2. **Code Changes Require CI:** CI enforces lock compliance
3. **CI Enforces Locks:** Constitution check blocks non-compliant changes
4. **No Bypass Flag:** No mechanism exists to disable enforcement

**Attempted bypass paths and why they fail:**

| Bypass Attempt | Why It Fails |
|----------------|--------------|
| Skip CI | Protected branches require CI pass |
| Modify runtime assert | Requires code change → CI → blocked |
| Comment out test | CI runs full test suite → test missing → fail |
| Direct merge | Protected branch rules prevent direct merge |
| Modify CI workflow | CODEOWNERS on .github/ → requires approval |
| Delete lock from registry | constitution_check.yml detects deletion → fail |

### 4.6 Disable (IMPOSSIBLE)

**Why disable is impossible:**

1. **No disable flag exists** in lock schema
2. **No disable command exists** in Constitution Engine
3. **Registry format doesn't support disabled state**
4. **CI doesn't check for disable state** (it doesn't exist)

---

## 5. Lock Enforcement Mechanisms

### 5.1 Enforcement Types

| Type | When Checked | What Happens on Violation |
|------|--------------|---------------------------|
| `test_required` | CI pytest run | Test failure → PR blocked |
| `runtime_assert` | Application runtime | Exception raised → operation blocked |
| `ci_workflow` | CI workflow run | Workflow failure → PR blocked |
| `lint_rule` | CI lint run | Lint error → PR blocked |
| `pac_gate` | PAC admission | Lock not acknowledged → PAC rejected |

### 5.2 Enforcement Layering

**Defense in depth:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENFORCEMENT LAYERS                           │
│                                                                 │
│   Layer 1: Development Time                                     │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  lint_rule: Static analysis catches patterns            │   │
│   └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│   Layer 2: Test Time                                            │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  test_required: Unit tests verify invariants            │   │
│   └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│   Layer 3: CI Time                                              │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  ci_workflow: Workflow validates compliance             │   │
│   └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│   Layer 4: Runtime                                              │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  runtime_assert: Code guards prevent violation          │   │
│   └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│   Layer 5: PAC Admission                                        │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  pac_gate: PAC must acknowledge all affected locks      │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. PAC Gate (Lock Acknowledgment)

### 6.1 What Is PAC Gate?

Every PAC must declare which locks it acknowledges:

```yaml
# In PAC header
locks_acknowledged:
  - LOCK-GW-IMMUTABILITY-001
  - LOCK-PDO-IMMUTABILITY-001
  - LOCK-VERIFY-SEMANTICS-001
```

### 6.2 Admission Logic

```
PAC Submitted
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│                   PAC ADMISSION GATE                          │
│                                                              │
│   Check 1: Lock acknowledgment present?                      │
│   ┌────────────────────────────────────────────────────────┐ │
│   │  Missing locks_acknowledged section → REJECT           │ │
│   └────────────────────────────────────────────────────────┘ │
│                            │                                 │
│                            ▼                                 │
│   Check 2: Scope matches acknowledged locks?                 │
│   ┌────────────────────────────────────────────────────────┐ │
│   │  PAC touches gateway but didn't ack gateway locks      │ │
│   │  → REJECT                                              │ │
│   └────────────────────────────────────────────────────────┘ │
│                            │                                 │
│                            ▼                                 │
│   Check 3: Forbidden zone touched?                           │
│   ┌────────────────────────────────────────────────────────┐ │
│   │  PAC modifies forbidden zone without supersession PAC  │ │
│   │  → REJECT                                              │ │
│   └────────────────────────────────────────────────────────┘ │
│                            │                                 │
│                            ▼                                 │
│                       ADMITTED                               │
└──────────────────────────────────────────────────────────────┘
```

### 6.3 Scope Mapping

| PAC Touches | Must Acknowledge |
|-------------|------------------|
| gateway/* | All LOCK-GW-* |
| occ/* | All LOCK-PDO-*, LOCK-INT-* |
| proofpack/* | All LOCK-PP-*, LOCK-VERIFY-* |
| governance/* | All LOCK-GOV-*, LOCK-AUTH-* |
| agents/* | All LOCK-AGENT-* |

---

## 7. Lock Versioning

### 7.1 Lock ID Format

```
LOCK-{DOMAIN}-{TYPE}-{NNN}

Where:
  DOMAIN: GW, PDO, VERIFY, AUTH, DENY, GOV, INT, EXT, PP, AGENT, META
  TYPE: Short descriptor (IMMUTABILITY, BINARY, GATE, etc.)
  NNN: Sequential number (001, 002, ...)
```

### 7.2 Version History

Each lock maintains implicit version history through Git:

- Initial creation: First commit adding lock
- Supersession: Commit marking lock as SUPERSEDED
- Audit trail: Full Git history preserved

### 7.3 No In-Place Updates

```
❌ WRONG (modification):
   - lock_id: LOCK-GW-IMMUTABILITY-001
     description: "Updated description"  # Changed!

✓ CORRECT (supersession):
   - lock_id: LOCK-GW-IMMUTABILITY-001
     status: SUPERSEDED
     superseded_by: LOCK-GW-IMMUTABILITY-002

   - lock_id: LOCK-GW-IMMUTABILITY-002
     description: "New stricter description"
```

---

## 8. Violation Response

### 8.1 Violation Severity Response

| Severity | CI Response | Runtime Response | Telemetry |
|----------|-------------|------------------|-----------|
| CRITICAL | HARD_FAIL, PR blocked | Exception, operation blocked | Required |
| HIGH | HARD_FAIL, PR blocked | Exception, operation blocked | Required |
| MEDIUM | SOFT_FAIL, warning | Warning logged | Optional |

### 8.2 Violation Telemetry

Every violation emits:

```json
{
  "event": "LOCK_VIOLATION",
  "lock_id": "LOCK-GW-IMMUTABILITY-001",
  "severity": "CRITICAL",
  "enforcement_type": "runtime_assert",
  "context": {
    "agent_gid": "GID-XX",
    "operation": "envelope_mutation_attempt",
    "timestamp": "2025-12-18T00:00:00Z"
  },
  "action_taken": "BLOCKED"
}
```

---

## 9. Lock Audit Trail

### 9.1 What Is Recorded

| Event | Recorded Data |
|-------|---------------|
| Lock creation | PAC reference, date, enforcement proof |
| Lock activation | CI run ID, test results |
| Lock supersession | Old lock, new lock, reason |
| Violation attempt | Full context, action taken |

### 9.2 Audit Immutability

Audit trail is immutable:
- Stored in Git history (commits are signed)
- Exported to governance audit log
- Cannot be modified retroactively

---

## 10. AI-Native Execution Model

### 10.1 Removed Human-Only Artifacts

| Removed | Reason |
|---------|--------|
| Manual review gates | Machine enforcement sufficient |
| Approval wait cycles | Locks are self-enforcing |
| Stepwise pacing | Full-bundle execution preferred |
| Rest-cycle assumptions | AI operates continuously |

### 10.2 Preserved Requirements

| Preserved | Reason |
|-----------|--------|
| PAC approval | Authority attribution required |
| Test passing | Machine verification required |
| Audit trail | Proof integrity required |

---

## 11. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-18 | BENSON (GID-00) | Initial contract |

---

## 12. References

- LOCK_REGISTRY.yaml — Lock definitions
- GOVERNANCE_INVARIANTS.md — Source invariants
- GATEWAY_CAPABILITY_CONTRACT.md — Gateway locks source
- constitution_engine.py — Runtime enforcement
- constitution_check.yml — CI enforcement
