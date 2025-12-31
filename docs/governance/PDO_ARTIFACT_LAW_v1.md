# PDO Artifact Law v1

**Governance Document: PDO_ARTIFACT_LAW_v1**  
**Effective Date:** 2025-12-26  
**PAC Reference:** PAC-BENSON-EXEC-GOVERNANCE-PDO-ARTIFACT-ENGINE-020  
**Status:** ACTIVE  
**Authority:** GID-00 (ORCHESTRATION_ENGINE)

---

## 1. Purpose

This law establishes the **PDO Artifact** as the canonical, immutable, machine-verifiable
object representing every completed execution loop in the ChainBridge governance system.

PDO formalizes **Proof → Decision → Outcome** as a concrete, auditable object—not a narrative.

---

## 2. Definitions

### 2.1 PDO (Proof → Decision → Outcome)

The atomic unit of execution completion in ChainBridge governance.

| Component  | Description                                        | Source           |
|------------|----------------------------------------------------|------------------|
| **Proof**  | Evidence that work was performed (WRAP artifact)   | Agent (GID-01+)  |
| **Decision** | Evaluation of proof (BER artifact)               | GID-00           |
| **Outcome** | Final state (ACCEPTED/CORRECTIVE/REJECTED)        | GID-00           |

### 2.2 PDOArtifact

An immutable, frozen dataclass containing:

```python
@dataclass(frozen=True)
class PDOArtifact:
    # Identity
    pdo_id: str              # Unique PDO identifier
    pac_id: str              # Source PAC identifier
    
    # Component IDs
    wrap_id: str             # WRAP artifact reference
    ber_id: str              # BER artifact reference
    
    # Authority
    issuer: str              # Always "GID-00"
    
    # Hash Chain (Proof → Decision → Outcome)
    proof_hash: str          # SHA-256 of proof data
    decision_hash: str       # SHA-256 of decision data
    outcome_hash: str        # SHA-256 of outcome data
    pdo_hash: str            # SHA-256 of entire PDO (chain binding)
    
    # Timestamps
    proof_at: str            # When proof was received
    decision_at: str         # When decision was made
    outcome_at: str          # When outcome was finalized
    created_at: str          # PDO creation timestamp
    
    # Status
    outcome_status: str      # ACCEPTED / CORRECTIVE / REJECTED
```

---

## 3. Invariants

### INV-PDO-001: One-to-One Mapping

Every PAC execution produces **exactly one** PDO:

```
PAC → WRAP → BER → PDO (1:1:1:1)
```

Violations:
- Multiple PDOs for same PAC = GOVERNANCE FAILURE
- BER without PDO = GOVERNANCE FAILURE
- PDO without BER = IMPOSSIBLE (mechanically prevented)

### INV-PDO-002: Authority Restriction

**Only ORCHESTRATION_ENGINE (GID-00) may create PDOArtifact.**

| Actor                | PDO Creation | Reason                        |
|----------------------|--------------|-------------------------------|
| GID-00 (Benson)      | ✅ ALLOWED   | Sole BER authority            |
| GID-01+ (Agents)     | ❌ FORBIDDEN | Proof providers, not judges   |
| Drafting Surface     | ❌ FORBIDDEN | Instruction-only              |

### INV-PDO-003: Immutability

PDOArtifact is frozen at creation. No field may be modified after instantiation.

- `@dataclass(frozen=True)` enforces this at runtime
- Hash binding prevents tampering detection
- All timestamps are UTC ISO-8601

### INV-PDO-004: Hash Chain Integrity

The PDO hash chain binds Proof → Decision → Outcome:

```
proof_hash     = SHA256(wrap_data)
decision_hash  = SHA256(proof_hash + ber_data)
outcome_hash   = SHA256(decision_hash + outcome_data)
pdo_hash       = SHA256(outcome_hash + metadata)
```

Tamper detection: Any modification breaks the chain.

### INV-PDO-005: Synchronous Emission

PDO must be emitted **synchronously** with BER:

```
BER_ISSUED → PDO_CREATED → BER_EMITTED → PDO_EMITTED
```

No async or deferred PDO creation allowed.

### INV-PDO-006: Completeness Requirement

PDO cannot be created with missing components:

| Component    | Required | Validation                     |
|--------------|----------|--------------------------------|
| pac_id       | ✅       | Non-empty string               |
| wrap_id      | ✅       | Non-empty string               |
| ber_id       | ✅       | Non-empty string               |
| proof_hash   | ✅       | Valid SHA-256 (64 hex chars)   |
| decision_hash| ✅       | Valid SHA-256 (64 hex chars)   |
| outcome_hash | ✅       | Valid SHA-256 (64 hex chars)   |

Missing any component → PDO creation FAILS.

---

## 4. PDO Lifecycle

### 4.1 Creation Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                       PDO CREATION FLOW                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. PAC Received                                                    │
│     └─ pac_id assigned                                              │
│                                                                     │
│  2. WRAP Received (from Agent)                                      │
│     └─ wrap_id assigned                                             │
│     └─ proof_hash = SHA256(wrap_data)                               │
│     └─ proof_at = now()                                             │
│                                                                     │
│  3. BER Issued (by GID-00)                                          │
│     └─ ber_id assigned                                              │
│     └─ decision_hash = SHA256(proof_hash + ber_data)                │
│     └─ decision_at = now()                                          │
│                                                                     │
│  4. PDO Created (by GID-00)                                         │
│     └─ pdo_id assigned                                              │
│     └─ outcome_hash = SHA256(decision_hash + outcome_data)          │
│     └─ pdo_hash = SHA256(outcome_hash + metadata)                   │
│     └─ outcome_at = now()                                           │
│     └─ created_at = now()                                           │
│                                                                     │
│  5. PDO Emitted                                                     │
│     └─ PDO returned to caller                                       │
│     └─ Registered in PDO registry                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 State Transitions

```
PAC_RECEIVED
    │
    ▼
PAC_DISPATCHED
    │
    ▼
EXECUTING
    │
    ▼
WRAP_RECEIVED ────────────────────► 🧾 PROOF LOCKED
    │
    ▼
BER_REQUIRED
    │
    ▼
BER_ISSUED ───────────────────────► 🧠 DECISION ISSUED
    │
    ▼
PDO_CREATED ──────────────────────► 🧿 PDO EMITTED
    │
    ▼
BER_EMITTED
    │
    ▼
SESSION_COMPLETE
```

---

## 5. Forbidden States

### 5.1 Anti-Patterns

| Anti-Pattern                        | Status      | Prevention                    |
|-------------------------------------|-------------|-------------------------------|
| PDO without BER                     | IMPOSSIBLE  | Mechanical: PDO requires BER  |
| BER without PDO                     | FORBIDDEN   | Mechanical: BER emits PDO     |
| Agent creates PDO                   | FORBIDDEN   | Authority check at creation   |
| Drafting surface creates PDO        | FORBIDDEN   | Authority check at creation   |
| Partial PDO (missing components)    | FORBIDDEN   | Completeness validation       |
| Mutable PDO                         | FORBIDDEN   | frozen=True enforcement       |
| Multiple PDOs per PAC               | FORBIDDEN   | Registry uniqueness check     |
| Async PDO creation                  | FORBIDDEN   | Synchronous emission only     |

### 5.2 Error Types

```python
class PDOCreationError(Exception):
    """Base exception for PDO creation errors."""

class PDOAuthorityError(PDOCreationError):
    """Raised when non-GID-00 attempts PDO creation."""

class PDOIncompleteError(PDOCreationError):
    """Raised when PDO missing required components."""

class PDODuplicateError(PDOCreationError):
    """Raised when PDO already exists for PAC."""

class PDOHashMismatchError(PDOCreationError):
    """Raised when hash chain verification fails."""
```

---

## 6. PDO Relationship to Other Artifacts

### 6.1 PAC → WRAP → BER → PDO Chain

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ARTIFACT CHAIN                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   PAC                   WRAP                  BER                   │
│   ┌─────────┐           ┌─────────┐           ┌─────────┐           │
│   │ pac_id  │───────────│ pac_id  │───────────│ pac_id  │           │
│   │ target  │           │ wrap_id │           │ ber_id  │           │
│   │ mode    │           │ status  │           │ status  │           │
│   │ ...     │           │ proof   │           │ decision│           │
│   └─────────┘           └─────────┘           └─────────┘           │
│        │                     │                     │                │
│        └─────────────────────┴─────────────────────┘                │
│                              │                                      │
│                              ▼                                      │
│                         ┌─────────────────────┐                     │
│                         │     PDOArtifact     │                     │
│                         ├─────────────────────┤                     │
│                         │ pdo_id              │                     │
│                         │ pac_id ─────────────┼──► PAC reference    │
│                         │ wrap_id ────────────┼──► WRAP reference   │
│                         │ ber_id ─────────────┼──► BER reference    │
│                         │                     │                     │
│                         │ proof_hash          │◄── WRAP data hash   │
│                         │ decision_hash       │◄── BER data hash    │
│                         │ outcome_hash        │◄── Final state hash │
│                         │ pdo_hash            │◄── Chain binding    │
│                         │                     │                     │
│                         │ outcome_status      │                     │
│                         └─────────────────────┘                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 BERArtifact vs PDOArtifact

| Aspect              | BERArtifact           | PDOArtifact                |
|---------------------|-----------------------|----------------------------|
| Purpose             | Decision notification | Complete execution record  |
| Scope               | BER emission proof    | Full PDO chain proof       |
| Components          | Decision only         | Proof + Decision + Outcome |
| Hash binding        | None                  | Full chain                 |
| Audit capability    | Partial               | Complete                   |
| Settlement ready    | No                    | Yes                        |

---

## 7. Terminal Emissions

### 7.1 Required Emissions

| Event         | Symbol | Emission                                    |
|---------------|--------|---------------------------------------------|
| Proof locked  | 🧾     | `emit_proof_locked(pac_id, proof_hash)`     |
| Decision made | 🧠     | `emit_decision_issued(pac_id, ber_status)`  |
| PDO emitted   | 🧿     | `emit_pdo_emitted(pdo_id, outcome_status)`  |

### 7.2 Emission Format

```
═══════════════════════════════════════════════════════════════════════
🧾 PROOF LOCKED
═══════════════════════════════════════════════════════════════════════
PAC:           PAC-XXX
WRAP_ID:       wrap_XXX
PROOF_HASH:    abc123...
LOCKED_AT:     2025-12-26T00:00:00Z
═══════════════════════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════════════════
🧠 DECISION ISSUED
═══════════════════════════════════════════════════════════════════════
PAC:           PAC-XXX
BER_ID:        ber_XXX
STATUS:        APPROVE
ISSUED_AT:     2025-12-26T00:00:00Z
═══════════════════════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════════════════
🧿 PDO EMITTED
═══════════════════════════════════════════════════════════════════════
PDO_ID:        pdo_XXX
PAC_ID:        PAC-XXX
OUTCOME:       ACCEPTED
PDO_HASH:      def456...
EMITTED_AT:    2025-12-26T00:00:00Z
═══════════════════════════════════════════════════════════════════════
```

---

## 8. Usage Guidelines

### 8.1 Creating PDO (GID-00 Only)

```python
from core.governance.pdo_artifact import PDOArtifactFactory

# Only ORCHESTRATION_ENGINE may call this
pdo = PDOArtifactFactory.create(
    pac_id="PAC-020",
    wrap_id="wrap_abc123",
    wrap_data=wrap_artifact,
    ber_id="ber_def456",
    ber_data=ber_artifact,
    outcome_status="ACCEPTED",
    issuer="GID-00",  # Required: must be GID-00
)
```

### 8.2 Verifying PDO

```python
from core.governance.pdo_artifact import verify_pdo_chain

# Verify hash chain integrity
is_valid = verify_pdo_chain(pdo)
assert is_valid, "PDO hash chain corrupted"
```

### 8.3 Retrieving PDO

```python
from core.governance.pdo_registry import get_pdo_registry

registry = get_pdo_registry()
pdo = registry.get(pac_id="PAC-020")
```

---

## 9. Compliance Requirements

### 9.1 Audit Trail

Every PDO must be:
- Registered in PDORegistry
- Immutable after creation
- Verifiable via hash chain
- Retrievable for audit

### 9.2 Settlement Readiness

PDO is the atomic unit for:
- Trust Center exposure
- Compliance reporting
- Settlement workflows
- Replay verification

---

## 10. Revision History

| Version | Date       | Author | Changes                          |
|---------|------------|--------|----------------------------------|
| v1      | 2025-12-26 | GID-00 | Initial law (PAC-020)            |

---

**END PDO_ARTIFACT_LAW_v1**
