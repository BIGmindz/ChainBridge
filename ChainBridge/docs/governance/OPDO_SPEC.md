# O-PDO Specification

> **Orchestrated PDO (O-PDO) — Composite Finality Specification**  
> Version: 1.0.0  
> Status: CANONICAL  
> PAC Reference: PAC-BENSON-P69-ORCHESTRATED-PDO-COMPOSITE-FINALITY-01

---

## 1. Overview

The Orchestrated PDO (O-PDO) is the settlement-grade composite decision artifact that binds multiple agent PDOs into a single, verifiable record with irreversible finality semantics.

### 1.1 Purpose

In multi-agent orchestration, each agent (CODY, SONNY, GERRY, etc.) produces an individual PDO after their work is validated through BER. The O-PDO aggregates these child PDOs into a single governance record that:

1. **Binds** all child PDOs with dependency relationships
2. **Proves** integrity via merkle tree construction
3. **Finalizes** with irreversibility guarantee
4. **Enables** WRAP emission for orchestrated executions

### 1.2 Position in Governance Pipeline

```
PAC-ORCH → Sub-PACs → Agent Execution → Individual BERs → Agent PDOs
                                                              ↓
Human Review → Child PDO Validation → O-PDO Composition → WRAP
```

---

## 2. O-PDO Structure

### 2.1 Schema Definition

```python
@dataclass
class OrchestratedPDO:
    opdo_id: str              # Unique identifier (OPDO-{AGENT}-{TIMESTAMP})
    pac_orch_id: str          # Source PAC-ORCH reference
    orchestrator_agent: str   # Always "BENSON"
    orchestrator_gid: str     # Always "GID-00"
    
    child_pdos: List[ChildPDO]           # Bound agent PDOs
    composite_proof: CompositeProof      # Merkle proof
    
    state: OPDOState                     # Finality state
    state_history: List[StateTransition] # Audit trail
    
    created_at: str                      # Creation timestamp
    sealed_at: Optional[str]             # Seal timestamp
    finalized_at: Optional[str]          # Finality timestamp
    
    human_review_ber_id: Optional[str]   # Human review binding
    final_hash: Optional[str]            # Immutable final hash
```

### 2.2 Child PDO Schema

```python
@dataclass
class ChildPDO:
    pdo_id: str           # PDO-{AGENT}-{PAC}-{TIMESTAMP}
    agent_name: str       # Agent name (CODY, SONNY, etc.)
    agent_gid: str        # Agent GID (GID-02, GID-03, etc.)
    sub_pac_id: str       # Sub-PAC reference
    ber_id: str           # BER that validated this PDO
    status: str           # Must be "VALIDATED"
    pdo_hash: str         # Content hash
    task_count: int       # Number of tasks completed
    quality_score: float  # 0.0 - 1.0
    created_at: str       # Timestamp
    dependencies: List[str]  # Dependency PDO IDs
```

---

## 3. Finality State Machine

### 3.1 State Diagram

```
     ┌─────────┐
     │  DRAFT  │ ← Initial state (mutable)
     └────┬────┘
          │ seal()
          │ (requires: composite_proof)
          ▼
     ┌─────────┐
     │ SEALED  │ ← Proof generated (immutable, pending review)
     └────┬────┘
          │ finalize()
          │ (requires: human_review_ber_id)
          ▼
     ┌─────────┐
     │  FINAL  │ ← Irreversibly committed (no transitions)
     └─────────┘
```

### 3.2 State Definitions

| State | Description | Mutable | Next State |
|-------|-------------|---------|------------|
| `DRAFT` | Initial state, child PDOs can be modified | Yes | SEALED |
| `SEALED` | Proof generated, awaiting human review | No | FINAL |
| `FINAL` | Irreversibly committed to governance record | No | None |

### 3.3 Transition Requirements

#### DRAFT → SEALED
- All child PDOs must be bound
- All child PDOs must have status="VALIDATED"
- Composite proof must be generated
- Merkle root must be computed

#### SEALED → FINAL
- Human review BER must be provided
- Human review must be genuine (cognitive friction verified)
- Final hash is computed and locked

---

## 4. Composite Proof

### 4.1 Merkle Tree Construction

The composite proof uses a binary merkle tree:

```
                    MERKLE_ROOT
                    /          \
                H(A+B)        H(C+D)
               /     \        /     \
           H(PDO-A) H(PDO-B) H(PDO-C) H(PDO-D)
```

### 4.2 Proof Schema

```python
@dataclass
class CompositeProof:
    merkle_root: str      # Root hash
    leaf_hashes: List[str] # Sorted child PDO hashes
    tree_height: int      # Tree depth
    proof_timestamp: str  # Generation timestamp
    nonce: str            # Uniqueness nonce
```

### 4.3 Determinism Guarantees

1. **Leaf ordering**: Child PDO hashes are sorted lexicographically
2. **Hash function**: SHA-256 only
3. **Canonical JSON**: `json.dumps(..., sort_keys=True)` for serialization
4. **Verification**: Root is recomputed twice to verify determinism

---

## 5. Error Codes

### 5.1 Child PDO Validation (GS_400-409)

| Code | Name | Description |
|------|------|-------------|
| GS_400 | EMPTY_CHILD_LIST | O-PDO requires at least one child PDO |
| GS_401 | INVALID_CHILD_PDO | Child PDO failed structural validation |
| GS_402 | CHILD_PDO_NOT_VALIDATED | Child PDO status is not VALIDATED |
| GS_403 | MISSING_AGENT_BER | Child PDO missing BER binding |
| GS_404 | DUPLICATE_AGENT | Same agent appears twice in child set |

### 5.2 Dependency Graph (GS_410-419)

| Code | Name | Description |
|------|------|-------------|
| GS_410 | CYCLE_DETECTED | Dependency graph contains cycle |
| GS_411 | MISSING_DEPENDENCY | Referenced dependency not found |
| GS_412 | ORPHAN_PDO | PDO has no dependency binding |

### 5.3 Composite Proof (GS_420-429)

| Code | Name | Description |
|------|------|-------------|
| GS_420 | PROOF_GENERATION_FAILED | Failed to generate proof |
| GS_421 | MERKLE_ROOT_MISMATCH | Root verification failed |
| GS_422 | HASH_COLLISION | Hash collision in proof |
| GS_423 | NON_DETERMINISTIC_HASH | Hash not deterministic |

### 5.4 Finality State Machine (GS_430-439)

| Code | Name | Description |
|------|------|-------------|
| GS_430 | INVALID_STATE_TRANSITION | Invalid transition attempted |
| GS_431 | ALREADY_FINALIZED | O-PDO already final |
| GS_432 | PREMATURE_FINALITY | Missing proof for finality |
| GS_433 | SEAL_REQUIRED | Must seal before finalize |
| GS_434 | HUMAN_REVIEW_REQUIRED | No human review provided |

### 5.5 O-PDO Structure (GS_440-449)

| Code | Name | Description |
|------|------|-------------|
| GS_440 | MISSING_ORCHESTRATOR | No orchestrator binding |
| GS_441 | INVALID_PAC_REF | Invalid PAC-ORCH reference |
| GS_442 | TIMESTAMP_DRIFT | Timestamp inconsistency |
| GS_443 | INTEGRITY_FAILED | Integrity check failed |

---

## 6. API Reference

### 6.1 Factory Function

```python
def create_opdo(
    pac_orch_id: str,
    child_pdos: List[ChildPDO],
    orchestrator_agent: str = "BENSON",
    orchestrator_gid: str = "GID-00"
) -> OrchestratedPDO
```

Creates an O-PDO with validated child PDOs. FAIL_CLOSED on any validation error.

### 6.2 Dependency Binder

```python
def bind_child_pdos(
    opdo: OrchestratedPDO,
    child_pdos: List[ChildPDO]
) -> OrchestratedPDO
```

Validates and binds child PDOs. Checks for:
- Valid PDO structure
- VALIDATED status
- BER binding
- No duplicate agents
- Acyclic dependency graph

### 6.3 Proof Generator

```python
def generate_composite_proof(opdo: OrchestratedPDO) -> CompositeProof
```

Generates merkle proof from child PDOs. Verifies determinism.

### 6.4 State Machine

```python
class OPDOFinalityStateMachine:
    def __init__(self, opdo: OrchestratedPDO): ...
    def can_transition(self, to_state: OPDOState) -> Tuple[bool, Optional[OPDOErrorCode]]: ...
    def transition(self, to_state: OPDOState, trigger: str, actor: str) -> OrchestratedPDO: ...
    def seal(self, actor: str = "BENSON") -> OrchestratedPDO: ...
    def finalize(self, human_review_ber_id: str, actor: str = "HUMAN_REVIEWER") -> OrchestratedPDO: ...
```

### 6.5 Verification

```python
def verify_opdo_integrity(opdo: OrchestratedPDO) -> Tuple[bool, List[str]]
```

Verifies O-PDO structure, proof, and state consistency.

### 6.6 Serialization

```python
def opdo_to_dict(opdo: OrchestratedPDO) -> Dict[str, Any]
def opdo_to_json(opdo: OrchestratedPDO, indent: int = 2) -> str
```

---

## 7. Invariants

### 7.1 Structural Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| OI-01 | ALL_CHILD_PDOS_MUST_BE_VALIDATED | `bind_child_pdos()` |
| OI-02 | DEPENDENCY_DAG_MUST_BE_ACYCLIC | `detect_cycles()` |
| OI-03 | COMPOSITE_HASH_MUST_BE_DETERMINISTIC | `generate_composite_proof()` |
| OI-04 | ORCHESTRATOR_IS_BENSON | `create_opdo()` |

### 7.2 State Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| OI-05 | FINALITY_IS_IRREVERSIBLE | `VALID_TRANSITIONS[FINAL] = []` |
| OI-06 | SEAL_BEFORE_FINALIZE | `finalize()` checks state |
| OI-07 | HUMAN_REVIEW_FOR_FINALITY | `finalize()` requires BER |

---

## 8. Integration with WRAP

### 8.1 WRAP Eligibility

An O-PDO becomes WRAP-eligible when:

1. State is `FINAL`
2. All child PDOs are bound
3. Composite proof verified
4. Human review BER is valid
5. Final hash is computed

### 8.2 WRAP Binding

```yaml
WRAP_OPDO_BINDING:
  wrap_id: "WRAP-BENSON-P67R-..."
  opdo_id: "OPDO-BENSON-20251226..."
  opdo_final_hash: "abc123..."
  child_pdo_count: 3
  merkle_root: "def456..."
  human_review_ber: "BER-HUMAN-..."
```

---

## 9. Security Considerations

### 9.1 Attack Vectors Mitigated

| Vector | Mitigation |
|--------|------------|
| Child PDO tampering | Merkle proof invalidates |
| Rubber-stamp review | BER cognitive friction (P68) |
| State manipulation | Immutable after SEALED |
| Replay attack | Nonce in proof |
| Premature closure | State machine enforcement |

### 9.2 FAIL_CLOSED Enforcement

All operations fail closed:
- Missing child PDOs → GS_400
- Invalid child → GS_401
- Cycle detected → GS_410
- Invalid transition → GS_430

---

## 10. Examples

### 10.1 Complete O-PDO Lifecycle

```python
from tools.governance.opdo import (
    ChildPDO, create_opdo, OPDOFinalityStateMachine
)

# 1. Create child PDOs (from agent executions)
cody_pdo = ChildPDO(
    pdo_id="PDO-CODY-P67R-20251226",
    agent_name="CODY",
    agent_gid="GID-02",
    sub_pac_id="Sub-PAC-CODY-P67R",
    ber_id="BER-CODY-P67R-DRILL",
    status="VALIDATED",
    pdo_hash="...",
    task_count=5,
    quality_score=0.95,
    created_at="2025-12-26T06:00:00Z"
)

sonny_pdo = ChildPDO(
    pdo_id="PDO-SONNY-P67R-20251226",
    agent_name="SONNY",
    agent_gid="GID-03",
    sub_pac_id="Sub-PAC-SONNY-P67R",
    ber_id="BER-SONNY-P67R-DRILL",
    status="VALIDATED",
    pdo_hash="...",
    task_count=3,
    quality_score=0.92,
    created_at="2025-12-26T06:05:00Z"
)

# 2. Create O-PDO
opdo = create_opdo(
    pac_orch_id="PAC-BENSON-P67R-...",
    child_pdos=[cody_pdo, sonny_pdo]
)

# 3. Seal (generates proof)
fsm = OPDOFinalityStateMachine(opdo)
opdo = fsm.seal()

# 4. Finalize (after human review)
opdo = fsm.finalize("BER-HUMAN-REVIEW-APPROVED")

# 5. O-PDO is now FINAL and WRAP-eligible
assert opdo.state == OPDOState.FINAL
assert opdo.final_hash is not None
```

---

## 11. Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-26 | Initial specification |

---

🟦🟩 **BENSON (GID-00)** — O-PDO Specification v1.0.0
