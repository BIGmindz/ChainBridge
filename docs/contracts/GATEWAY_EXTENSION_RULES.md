# ChainBridge Gateway Extension Rules Contract

**Document:** GATEWAY_EXTENSION_RULES.md
**Version:** 1.0
**Status:** LOCKED
**Classification:** CONTRACT (Integration Discipline Document)

**Contract Owner:** BENSON (GID-00)
**PAC Reference:** PAC-BENSON-GATEWAY-INTEGRATION-DISCIPLINE-01
**Effective Date:** 2025-12-18
**Alignment:** GATEWAY_CAPABILITY_CONTRACT.md, GATEWAY_INTEGRATION_PATTERNS.md

---

## 1. Purpose

This document defines the **extension rules** for the ChainBridge Gateway:

- What may be extended
- What may never be extended
- Required artifacts for extension
- Mandatory review processes

**Extension is constrained, auditable, and reversible.** Unauthorized extension is forbidden.

---

## 2. Extension Definition

### 2.1 What Extension Means

| Term | Definition |
|------|------------|
| **Extension** | Adding new capability without modifying core Gateway behavior |
| **Core** | Gateway components that enforce invariants |
| **Peripheral** | Gateway components that can be extended without weakening guarantees |
| **Extension Point** | Designated location where extension is permitted |
| **Forbidden Zone** | Component that must never be extended |

### 2.2 Extension Principle

**Extensions must preserve all existing invariants.** An extension that weakens any invariant is forbidden.

---

## 3. What May Be Extended

### 3.1 Extensible Components

| Component | Extension Type | Extension Point | Constraints |
|-----------|---------------|-----------------|-------------|
| **Intent Schema** | New fields | `GatewayIntent` Pydantic model | Must be additive; existing fields frozen |
| **Envelope Metadata** | New metadata keys | `envelope.metadata` dict | Must not modify core fields |
| **ALEX Rules** | New rules | `.github/ALEX_RULES.json` | Must follow ALEX rule schema |
| **ACM Manifests** | New agents | `acm/manifests/*.yaml` | Must follow ACM schema |
| **Denial Reason Codes** | New codes | `denial_codes.py` | Must map to invariant violation |
| **Tool Registry** | New tools | `tool_registry.yaml` | Must have governance binding |
| **Evidence Types** | New evidence | `evidence_types.py` | Must implement Evidence protocol |

### 3.2 Extension Rules by Component

#### 3.2.1 EXT-SCHEMA: Intent Schema Extensions

**What is permitted:**

| Action | Permitted | Constraint |
|--------|-----------|------------|
| Add new optional field | ✓ | Must have default value |
| Add new required field | ✗ | Breaks existing intents |
| Modify existing field type | ✗ | Breaks existing intents |
| Remove existing field | ✗ | Breaks existing intents |
| Add field validation | ✓ | Must be additive (stricter OK) |

**Extension Invariants:**

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| EXT-SCHEMA-001 | Existing fields are frozen | Schema version lock |
| EXT-SCHEMA-002 | New fields must have defaults | Pydantic field definition |
| EXT-SCHEMA-003 | Schema version must increment | Version field in schema |

#### 3.2.2 EXT-ENVELOPE: Envelope Metadata Extensions

**What is permitted:**

| Action | Permitted | Constraint |
|--------|-----------|------------|
| Add metadata key | ✓ | Must not collide with reserved keys |
| Modify metadata value | ✓ | If envelope not frozen |
| Remove metadata key | ✗ | Breaks downstream consumers |
| Add reserved key | ✗ | Reserved keys are frozen |

**Reserved Keys (frozen):**

| Key | Purpose | Owner |
|-----|---------|-------|
| `decision` | ALLOW/DENY | Gateway |
| `audit_ref` | Governance log reference | Gateway |
| `version` | Envelope version | Gateway |
| `human_required` | Escalation flag | Gateway |
| `allowed_tools` | Tool scope | Gateway |
| `reason_code` | Denial reason | Gateway |

**Extension Invariants:**

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| EXT-ENV-001 | Reserved keys are immutable | `@dataclass(frozen=True)` |
| EXT-ENV-002 | Metadata extensions must be documented | Extension registry |
| EXT-ENV-003 | Metadata keys must be namespaced | `{service}.{key}` format |

#### 3.2.3 EXT-ALEX: ALEX Rule Extensions

**What is permitted:**

| Action | Permitted | Constraint |
|--------|-----------|------------|
| Add new rule | ✓ | Must follow ALEX rule schema |
| Modify existing rule strictness (stricter) | ✓ | More restrictive is OK |
| Modify existing rule strictness (looser) | ✗ | Weakens governance |
| Remove existing rule | ✗ | Weakens governance |
| Add new denial code | ✓ | Must map to rule |

**Extension Invariants:**

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| EXT-ALEX-001 | Rules may only become stricter | Rule diff analysis |
| EXT-ALEX-002 | Rule removal is forbidden | ALEX rule registry immutability |
| EXT-ALEX-003 | New rules must have tests | CI gate |

#### 3.2.4 EXT-ACM: ACM Manifest Extensions

**What is permitted:**

| Action | Permitted | Constraint |
|--------|-----------|------------|
| Add new agent | ✓ | Must have GID, capabilities |
| Add capability to agent | ✓ | Must be within agent's domain |
| Remove capability from agent | ✓ | Revocation is permitted |
| Remove agent entirely | ✓ | Revocation is permitted |
| Modify agent's chain-of-command | ✗ | Requires BENSON approval |

**Extension Invariants:**

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| EXT-ACM-001 | New agents must have valid GID | ACM loader validation |
| EXT-ACM-002 | Chain-of-command changes require BENSON | Approval gate |
| EXT-ACM-003 | ACM changes must be versioned | Git history |

#### 3.2.5 EXT-TOOL: Tool Registry Extensions

**What is permitted:**

| Action | Permitted | Constraint |
|--------|-----------|------------|
| Add new tool | ✓ | Must have governance binding |
| Remove tool | ✓ | Revocation is permitted |
| Modify tool schema | ✓ | Must be backward compatible |
| Add tool without governance | ✗ | All tools must be governed |

**Extension Invariants:**

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| EXT-TOOL-001 | All tools must have ALEX rule binding | Tool registry validation |
| EXT-TOOL-002 | Tool removal is revocation, not deletion | Tool marked as `disabled` |
| EXT-TOOL-003 | Tool schema changes must be additive | Schema version check |

---

## 4. What May Never Be Extended

### 4.1 Forbidden Zones

| Component | Why Forbidden | Impact if Violated |
|-----------|---------------|-------------------|
| **Gateway Decision Logic** | Core enforcement | Authorization bypass |
| **Envelope Immutability** | Proof integrity | Proof forgery |
| **PDO State Machine** | Decision integrity | Invalid state transitions |
| **DRCP Routing Logic** | Denial handling | Denial swallowing |
| **Authority Hierarchy** | Chain-of-command | Authority escalation |
| **Verification Order** | Evaluation sequence | Bypass opportunity |

### 4.2 Forbidden Extension Actions

| ID | Action | Why Forbidden | Violated Invariant |
|----|--------|---------------|-------------------|
| FZ-001 | Modify `evaluate_intent()` logic | Core decision engine | INV-GW-L4-001 |
| FZ-002 | Remove `@dataclass(frozen=True)` from envelope | Enables mutation | INV-GW-L2-004 |
| FZ-003 | Add states to PDO FSM | Breaks terminal state guarantee | INV-GW-L3-003 |
| FZ-004 | Bypass DRCP for DENY decisions | Denial swallowing | ESC-001 |
| FZ-005 | Modify chain-of-command without BENSON | Authority violation | AUTH-002 |
| FZ-006 | Reorder Gateway layers | Creates bypass | INT-COMP-001 |
| FZ-007 | Add third decision type (not ALLOW/DENY) | Breaks binary decision | INV-GW-L2-003 |
| FZ-008 | Allow empty audit_ref | Breaks traceability | INV-GW-L2-005 |
| FZ-009 | Remove require_pdo() check | Enables ungoverned execution | INV-GW-L3-001 |
| FZ-010 | Modify evidence context scope | Evidence leak | INV-GW-L5-001 |

### 4.3 Forbidden Zone Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| FZ-INV-001 | Forbidden zones cannot be modified | Code ownership + CI gate |
| FZ-INV-002 | Any forbidden zone change requires PAC | BENSON approval |
| FZ-INV-003 | Forbidden zone changes must have security review | Security team approval |

---

## 5. Extension Artifacts

### 5.1 Required Documentation

| Extension Type | Required Artifact | Content |
|----------------|-------------------|---------|
| Schema extension | Schema Change Request | Fields, types, defaults, rationale |
| ALEX rule extension | Rule Change Request | Rule definition, tests, impact |
| ACM extension | ACM Change Request | Agent definition, capabilities, domain |
| Tool extension | Tool Registration Request | Tool schema, governance binding, tests |

### 5.2 Extension Request Template

```yaml
extension_request:
  id: "EXT-{YYYY}-{NNN}"
  type: "schema|envelope|alex|acm|tool|evidence"
  requestor: "{GID}"
  date: "{YYYY-MM-DD}"

  description: |
    What is being extended and why.

  change:
    component: "{component_name}"
    action: "add|modify"
    details: |
      Specific changes being made.

  invariants_preserved:
    - "INV-* that remain valid"

  invariants_affected:
    - "INV-* that need attention"

  tests_added:
    - "Test name and purpose"

  rollback_plan: |
    How to revert if issues arise.

  approvals_required:
    - "{GID} for {reason}"
```

### 5.3 Extension Registry

All extensions must be registered in `docs/extensions/EXTENSION_REGISTRY.md`:

| Field | Description |
|-------|-------------|
| Extension ID | Unique identifier |
| Type | Component type extended |
| Date | When extension was approved |
| Requestor | Who requested |
| Approver | Who approved |
| Invariants Preserved | Which invariants remain valid |
| Tests | Test coverage for extension |

---

## 6. Mandatory Review Process

### 6.1 Review Requirements by Extension Type

| Extension Type | Required Reviews | Approvers |
|----------------|------------------|-----------|
| Schema extension | Code review + Contract review | ATLAS (GID-11) + BENSON (GID-00) |
| Envelope metadata | Code review | ATLAS (GID-11) |
| ALEX rule | Governance review | ALEX + BENSON (GID-00) |
| ACM manifest | Security review | ATLAS (GID-11) |
| Tool registry | Code review + Security review | ATLAS (GID-11) |
| Evidence type | Code review | ATLAS (GID-11) |

### 6.2 Review Checklist

| Check | Reviewer |
|-------|----------|
| Does extension preserve all existing invariants? | Contract reviewer |
| Does extension have test coverage? | Code reviewer |
| Does extension follow naming conventions? | Code reviewer |
| Is extension documented in registry? | Contract reviewer |
| Is rollback plan documented? | Code reviewer |
| Does extension avoid forbidden zones? | Security reviewer |

### 6.3 Review Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| REV-001 | All extensions require code review | PR gate |
| REV-002 | Schema extensions require contract review | CODEOWNERS |
| REV-003 | ALEX extensions require BENSON approval | CODEOWNERS |
| REV-004 | Forbidden zone changes blocked without PAC | CI gate |

---

## 7. Extension Versioning

### 7.1 Version Rules

| Rule | Description |
|------|-------------|
| Additive changes | Increment minor version |
| Breaking changes | Forbidden without PAC |
| Removal | Increment major version (revocation) |

### 7.2 Version Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| VER-001 | Schema version monotonically increases | Version check in CI |
| VER-002 | Breaking changes require major version bump | Semver enforcement |
| VER-003 | Version history must be preserved | Git history |

---

## 8. Extension Anti-Patterns

### 8.1 Forbidden Extension Patterns

| Anti-Pattern | Description | Why Forbidden |
|--------------|-------------|---------------|
| Backdoor extension | Adding capability through "metadata" to bypass review | Circumvents governance |
| Shadow schema | Defining unofficial schema alongside official | Creates confusion |
| Rule weakening | Making ALEX rule less strict | Weakens governance |
| Ungoverned tool | Adding tool without ALEX binding | Bypasses governance |
| Direct forbidden zone edit | Modifying core without PAC | Contract violation |

### 8.2 Detection

| Anti-Pattern | Detection Method |
|--------------|------------------|
| Backdoor extension | Metadata audit for undocumented keys |
| Shadow schema | Schema registry validation |
| Rule weakening | ALEX rule diff analysis |
| Ungoverned tool | Tool registry audit |
| Direct forbidden zone edit | CODEOWNERS + CI gate |

---

## 9. Agent University Binding

### 9.1 Extension Training Requirements

| Role | Required Knowledge |
|------|-------------------|
| All developers | Extensible vs forbidden components |
| Schema maintainers | EXT-SCHEMA rules |
| Governance engineers | EXT-ALEX rules |
| Security engineers | Forbidden zone boundaries |

### 9.2 Certification Criteria

| Criterion | Evidence |
|-----------|----------|
| Extension rules knowledge | Exam on this document |
| Review process knowledge | Participation in extension review |
| Forbidden zone awareness | No violations in 6 months |

---

## 10. Extension Governance Summary

### 10.1 Quick Reference

| I want to... | Is it allowed? | What do I need? |
|--------------|----------------|-----------------|
| Add new field to intent schema | ✓ | Schema Change Request, Code Review |
| Add metadata to envelope | ✓ | Namespaced key, Documentation |
| Add new ALEX rule | ✓ | Rule Change Request, BENSON approval |
| Make ALEX rule stricter | ✓ | Rule Change Request, Tests |
| Make ALEX rule looser | ✗ | Not allowed |
| Remove ALEX rule | ✗ | Not allowed |
| Add new agent to ACM | ✓ | ACM Change Request, Security Review |
| Modify chain-of-command | ✗* | PAC required (BENSON only) |
| Add new tool | ✓ | Tool Registration, Governance binding |
| Modify Gateway decision logic | ✗ | Not allowed (forbidden zone) |
| Add third decision type | ✗ | Not allowed (forbidden zone) |
| Remove PDO requirement | ✗ | Not allowed (forbidden zone) |

### 10.2 Extension Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Extension Request Flow                        │
│                                                                 │
│    Request ──▶ Is it in Forbidden Zone?                         │
│       │              │                                          │
│       │         ┌────┴────┐                                     │
│       │         │         │                                     │
│       │        Yes        No                                    │
│       │         │         │                                     │
│       │         ▼         ▼                                     │
│       │      BLOCKED   Is it Extensible Component?              │
│       │                    │                                    │
│       │              ┌─────┴─────┐                               │
│       │              │           │                              │
│       │             Yes          No                             │
│       │              │           │                              │
│       │              ▼           ▼                              │
│       │      Submit Request   BLOCKED                           │
│       │              │                                          │
│       │              ▼                                          │
│       │         Required Reviews                                │
│       │              │                                          │
│       │         ┌────┴────┐                                     │
│       │         │         │                                     │
│       │      Approved  Rejected                                 │
│       │         │         │                                     │
│       │         ▼         ▼                                     │
│       │     Implement  Feedback                                 │
│       │         │                                               │
│       │         ▼                                               │
│       │    Register in                                          │
│       │    Extension Registry                                   │
│       │         │                                               │
│       │         ▼                                               │
│       │       DONE                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 11. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-18 | BENSON (GID-00) | Initial contract |

---

## 12. References

- GATEWAY_INTEGRATION_PATTERNS.md — Approved integration patterns
- GATEWAY_ANTI_PATTERNS.md — Forbidden patterns
- GATEWAY_CAPABILITY_CONTRACT.md — Gateway layer definitions
- GATEWAY_AUTHORITY_BOUNDARY.md — Authority scope
- GOVERNANCE_INVARIANTS.md — System-wide governance invariants
