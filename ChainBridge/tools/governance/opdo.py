#!/usr/bin/env python3
"""
opdo.py — Orchestrated PDO (O-PDO) Module

Defines the Orchestrated PDO schema, dependency binder, composite proof generator,
and finality state machine for multi-agent governance settlement.

Part of: ChainBridge Governance Infrastructure
PAC: PAC-BENSON-P69-ORCHESTRATED-PDO-COMPOSITE-FINALITY-01

FAIL_CLOSED semantics throughout.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum, auto
from datetime import datetime
import hashlib
import json
import secrets


# ═══════════════════════════════════════════════════════════════════════════════
# ERROR CODES (GS_4XX series for O-PDO)
# ═══════════════════════════════════════════════════════════════════════════════

class OPDOErrorCode(Enum):
    """O-PDO specific error codes."""
    # Child PDO Validation (GS_400-409)
    GS_400_EMPTY_CHILD_LIST = "GS_400: O-PDO requires at least one child PDO"
    GS_401_INVALID_CHILD_PDO = "GS_401: Child PDO failed validation"
    GS_402_CHILD_PDO_NOT_VALIDATED = "GS_402: Child PDO status is not VALIDATED"
    GS_403_MISSING_AGENT_BER = "GS_403: Child PDO missing agent BER binding"
    GS_404_DUPLICATE_AGENT = "GS_404: Duplicate agent in child PDO set"
    
    # Dependency Graph (GS_410-419)
    GS_410_CYCLE_DETECTED = "GS_410: Dependency graph contains cycle (DAG violated)"
    GS_411_MISSING_DEPENDENCY = "GS_411: Referenced dependency not found"
    GS_412_ORPHAN_PDO = "GS_412: PDO has no dependency binding"
    
    # Composite Proof (GS_420-429)
    GS_420_PROOF_GENERATION_FAILED = "GS_420: Failed to generate composite proof"
    GS_421_MERKLE_ROOT_MISMATCH = "GS_421: Merkle root verification failed"
    GS_422_HASH_COLLISION = "GS_422: Hash collision detected in proof"
    GS_423_NON_DETERMINISTIC_HASH = "GS_423: Non-deterministic hash detected"
    
    # Finality State Machine (GS_430-439)
    GS_430_INVALID_STATE_TRANSITION = "GS_430: Invalid state transition"
    GS_431_ALREADY_FINALIZED = "GS_431: O-PDO already finalized (irreversible)"
    GS_432_PREMATURE_FINALITY = "GS_432: Cannot finalize without complete proof"
    GS_433_SEAL_REQUIRED = "GS_433: Must be SEALED before finalization"
    GS_434_HUMAN_REVIEW_REQUIRED = "GS_434: Human review required before finalization"
    
    # O-PDO Structure (GS_440-449)
    GS_440_MISSING_ORCHESTRATOR = "GS_440: O-PDO requires orchestrator binding"
    GS_441_INVALID_PAC_REF = "GS_441: Invalid PAC-ORCH reference"
    GS_442_TIMESTAMP_DRIFT = "GS_442: Timestamp drift detected"
    GS_443_INTEGRITY_FAILED = "GS_443: O-PDO integrity check failed"


class OPDOError(Exception):
    """Exception raised for O-PDO errors."""
    def __init__(self, code: OPDOErrorCode, details: Optional[str] = None):
        self.code = code
        self.details = details
        super().__init__(f"{code.value}" + (f" | {details}" if details else ""))


# ═══════════════════════════════════════════════════════════════════════════════
# FINALITY STATE MACHINE
# ═══════════════════════════════════════════════════════════════════════════════

class OPDOState(Enum):
    """O-PDO finality states."""
    DRAFT = auto()      # Initial state, mutable
    SEALED = auto()     # Proof generated, immutable pending review
    FINAL = auto()      # Irreversibly committed


# Valid state transitions (from -> to)
VALID_TRANSITIONS: Dict[OPDOState, List[OPDOState]] = {
    OPDOState.DRAFT: [OPDOState.SEALED],
    OPDOState.SEALED: [OPDOState.FINAL],
    OPDOState.FINAL: [],  # No transitions from FINAL (irreversible)
}


@dataclass
class StateTransition:
    """Records a state transition."""
    from_state: OPDOState
    to_state: OPDOState
    timestamp: str
    trigger: str
    actor: str


# ═══════════════════════════════════════════════════════════════════════════════
# CHILD PDO SCHEMA
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ChildPDO:
    """Represents a child PDO from an individual agent."""
    pdo_id: str
    agent_name: str
    agent_gid: str
    sub_pac_id: str
    ber_id: str
    status: str  # Must be "VALIDATED"
    pdo_hash: str
    task_count: int
    quality_score: float
    created_at: str
    dependencies: List[str] = field(default_factory=list)
    
    def validate(self) -> Tuple[bool, Optional[OPDOErrorCode]]:
        """Validate child PDO structure."""
        if not self.pdo_id or not self.pdo_id.startswith("PDO-"):
            return False, OPDOErrorCode.GS_401_INVALID_CHILD_PDO
        if self.status != "VALIDATED":
            return False, OPDOErrorCode.GS_402_CHILD_PDO_NOT_VALIDATED
        if not self.ber_id or not self.ber_id.startswith("BER-"):
            return False, OPDOErrorCode.GS_403_MISSING_AGENT_BER
        return True, None
    
    def compute_hash(self) -> str:
        """Compute deterministic hash of child PDO."""
        canonical = json.dumps({
            "pdo_id": self.pdo_id,
            "agent_gid": self.agent_gid,
            "sub_pac_id": self.sub_pac_id,
            "ber_id": self.ber_id,
            "task_count": self.task_count,
            "quality_score": self.quality_score,
        }, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# COMPOSITE PROOF SCHEMA
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MerkleNode:
    """Node in the merkle tree."""
    hash: str
    left: Optional['MerkleNode'] = None
    right: Optional['MerkleNode'] = None
    leaf_data: Optional[str] = None  # For leaf nodes only


@dataclass
class CompositeProof:
    """Merkle proof binding all child PDOs."""
    merkle_root: str
    leaf_hashes: List[str]
    tree_height: int
    proof_timestamp: str
    nonce: str  # For uniqueness
    
    def verify(self, child_pdos: List[ChildPDO]) -> bool:
        """Verify the merkle root matches the child PDOs."""
        computed_leaves = sorted([p.compute_hash() for p in child_pdos])
        if computed_leaves != sorted(self.leaf_hashes):
            return False
        # Recompute root
        computed_root = self._compute_merkle_root(computed_leaves)
        return computed_root == self.merkle_root
    
    @staticmethod
    def _compute_merkle_root(leaves: List[str]) -> str:
        """Compute merkle root from leaves."""
        if not leaves:
            return hashlib.sha256(b"EMPTY").hexdigest()
        
        # Pad to power of 2
        while len(leaves) & (len(leaves) - 1) != 0:
            leaves.append(leaves[-1])
        
        current_level = leaves
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                combined = current_level[i] + current_level[i + 1]
                next_level.append(hashlib.sha256(combined.encode()).hexdigest())
            current_level = next_level
        
        return current_level[0]


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATED PDO (O-PDO) SCHEMA
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class OrchestratedPDO:
    """
    Orchestrated PDO (O-PDO) — Settlement-grade composite decision object.
    
    Binds multiple agent PDOs into a single verifiable artifact with
    irreversible finality semantics.
    """
    opdo_id: str
    pac_orch_id: str  # PAC-ORCH that spawned this O-PDO
    orchestrator_agent: str  # Always BENSON
    orchestrator_gid: str  # Always GID-00
    
    # Child PDO bindings
    child_pdos: List[ChildPDO]
    
    # Composite proof
    composite_proof: Optional[CompositeProof] = None
    
    # State machine
    state: OPDOState = OPDOState.DRAFT
    state_history: List[StateTransition] = field(default_factory=list)
    
    # Timestamps
    created_at: str = ""
    sealed_at: Optional[str] = None
    finalized_at: Optional[str] = None
    
    # Human review binding
    human_review_ber_id: Optional[str] = None
    human_review_timestamp: Optional[str] = None
    
    # Final hash (computed at finality)
    final_hash: Optional[str] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat() + "Z"


# ═══════════════════════════════════════════════════════════════════════════════
# PDO DEPENDENCY BINDER
# ═══════════════════════════════════════════════════════════════════════════════

def validate_child_pdos(child_pdos: List[ChildPDO]) -> List[Tuple[str, OPDOErrorCode]]:
    """
    Validate all child PDOs.
    
    Returns list of (pdo_id, error_code) for failures.
    """
    errors = []
    seen_agents = set()
    
    if not child_pdos:
        errors.append(("", OPDOErrorCode.GS_400_EMPTY_CHILD_LIST))
        return errors
    
    for pdo in child_pdos:
        # Validate structure
        valid, error = pdo.validate()
        if not valid and error:
            errors.append((pdo.pdo_id, error))
            continue
        
        # Check for duplicate agents
        if pdo.agent_gid in seen_agents:
            errors.append((pdo.pdo_id, OPDOErrorCode.GS_404_DUPLICATE_AGENT))
        seen_agents.add(pdo.agent_gid)
    
    return errors


def detect_cycles(child_pdos: List[ChildPDO]) -> Optional[List[str]]:
    """
    Detect cycles in dependency graph.
    
    Returns cycle path if found, None otherwise.
    """
    pdo_map = {p.pdo_id: p for p in child_pdos}
    visited = set()
    rec_stack = set()
    path = []
    
    def dfs(pdo_id: str) -> Optional[List[str]]:
        visited.add(pdo_id)
        rec_stack.add(pdo_id)
        path.append(pdo_id)
        
        pdo = pdo_map.get(pdo_id)
        if pdo:
            for dep in pdo.dependencies:
                if dep not in visited:
                    cycle = dfs(dep)
                    if cycle:
                        return cycle
                elif dep in rec_stack:
                    # Found cycle
                    cycle_start = path.index(dep)
                    return path[cycle_start:] + [dep]
        
        path.pop()
        rec_stack.discard(pdo_id)
        return None
    
    for pdo in child_pdos:
        if pdo.pdo_id not in visited:
            cycle = dfs(pdo.pdo_id)
            if cycle:
                return cycle
    
    return None


def bind_child_pdos(
    opdo: OrchestratedPDO,
    child_pdos: List[ChildPDO]
) -> OrchestratedPDO:
    """
    Bind child PDOs to O-PDO with validation.
    
    FAIL_CLOSED on any validation failure.
    """
    # Validate all child PDOs
    errors = validate_child_pdos(child_pdos)
    if errors:
        first_error = errors[0]
        raise OPDOError(first_error[1], f"PDO: {first_error[0]}")
    
    # Check for cycles
    cycle = detect_cycles(child_pdos)
    if cycle:
        raise OPDOError(
            OPDOErrorCode.GS_410_CYCLE_DETECTED,
            f"Cycle: {' -> '.join(cycle)}"
        )
    
    # Verify dependencies exist
    all_pdo_ids = {p.pdo_id for p in child_pdos}
    for pdo in child_pdos:
        for dep in pdo.dependencies:
            if dep not in all_pdo_ids:
                raise OPDOError(
                    OPDOErrorCode.GS_411_MISSING_DEPENDENCY,
                    f"PDO {pdo.pdo_id} references missing dependency {dep}"
                )
    
    # Bind
    opdo.child_pdos = child_pdos
    return opdo


# ═══════════════════════════════════════════════════════════════════════════════
# COMPOSITE PROOF GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def generate_composite_proof(opdo: OrchestratedPDO) -> CompositeProof:
    """
    Generate merkle proof for O-PDO child PDOs.
    
    Returns CompositeProof with merkle root and leaf hashes.
    """
    if not opdo.child_pdos:
        raise OPDOError(OPDOErrorCode.GS_400_EMPTY_CHILD_LIST)
    
    # Compute leaf hashes (sorted for determinism)
    leaf_hashes = sorted([pdo.compute_hash() for pdo in opdo.child_pdos])
    
    # Verify no collisions
    if len(leaf_hashes) != len(set(leaf_hashes)):
        raise OPDOError(OPDOErrorCode.GS_422_HASH_COLLISION)
    
    # Compute merkle root
    merkle_root = CompositeProof._compute_merkle_root(leaf_hashes.copy())
    
    # Verify determinism (compute twice)
    merkle_root_verify = CompositeProof._compute_merkle_root(leaf_hashes.copy())
    if merkle_root != merkle_root_verify:
        raise OPDOError(OPDOErrorCode.GS_423_NON_DETERMINISTIC_HASH)
    
    # Calculate tree height
    import math
    tree_height = math.ceil(math.log2(len(leaf_hashes))) if len(leaf_hashes) > 1 else 1
    
    return CompositeProof(
        merkle_root=merkle_root,
        leaf_hashes=leaf_hashes,
        tree_height=tree_height,
        proof_timestamp=datetime.utcnow().isoformat() + "Z",
        nonce=secrets.token_hex(16)
    )


# ═══════════════════════════════════════════════════════════════════════════════
# FINALITY STATE MACHINE
# ═══════════════════════════════════════════════════════════════════════════════

class OPDOFinalityStateMachine:
    """
    State machine for O-PDO finality.
    
    DRAFT → SEALED → FINAL
    
    - DRAFT: Mutable, can add/modify child PDOs
    - SEALED: Proof generated, immutable, pending human review
    - FINAL: Irreversibly committed to governance record
    """
    
    def __init__(self, opdo: OrchestratedPDO):
        self.opdo = opdo
    
    def can_transition(self, to_state: OPDOState) -> Tuple[bool, Optional[OPDOErrorCode]]:
        """Check if transition is valid."""
        if to_state not in VALID_TRANSITIONS.get(self.opdo.state, []):
            return False, OPDOErrorCode.GS_430_INVALID_STATE_TRANSITION
        
        if self.opdo.state == OPDOState.FINAL:
            return False, OPDOErrorCode.GS_431_ALREADY_FINALIZED
        
        # DRAFT → SEALED requires proof
        if self.opdo.state == OPDOState.DRAFT and to_state == OPDOState.SEALED:
            if not self.opdo.composite_proof:
                return False, OPDOErrorCode.GS_432_PREMATURE_FINALITY
        
        # SEALED → FINAL requires human review
        if self.opdo.state == OPDOState.SEALED and to_state == OPDOState.FINAL:
            if not self.opdo.human_review_ber_id:
                return False, OPDOErrorCode.GS_434_HUMAN_REVIEW_REQUIRED
        
        return True, None
    
    def transition(self, to_state: OPDOState, trigger: str, actor: str) -> OrchestratedPDO:
        """Execute state transition."""
        can, error = self.can_transition(to_state)
        if not can and error:
            raise OPDOError(error, f"Cannot transition from {self.opdo.state.name} to {to_state.name}")
        
        # Record transition
        transition = StateTransition(
            from_state=self.opdo.state,
            to_state=to_state,
            timestamp=datetime.utcnow().isoformat() + "Z",
            trigger=trigger,
            actor=actor
        )
        self.opdo.state_history.append(transition)
        
        # Update state and timestamps
        old_state = self.opdo.state
        self.opdo.state = to_state
        
        if to_state == OPDOState.SEALED:
            self.opdo.sealed_at = transition.timestamp
        elif to_state == OPDOState.FINAL:
            self.opdo.finalized_at = transition.timestamp
            self.opdo.final_hash = self._compute_final_hash()
        
        return self.opdo
    
    def _compute_final_hash(self) -> str:
        """Compute final immutable hash at finality."""
        canonical = json.dumps({
            "opdo_id": self.opdo.opdo_id,
            "pac_orch_id": self.opdo.pac_orch_id,
            "merkle_root": self.opdo.composite_proof.merkle_root if self.opdo.composite_proof else None,
            "child_count": len(self.opdo.child_pdos),
            "sealed_at": self.opdo.sealed_at,
            "human_review_ber_id": self.opdo.human_review_ber_id,
        }, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def seal(self, actor: str = "BENSON") -> OrchestratedPDO:
        """Seal O-PDO (generate proof and transition to SEALED)."""
        # Generate proof if not present
        if not self.opdo.composite_proof:
            self.opdo.composite_proof = generate_composite_proof(self.opdo)
        
        return self.transition(OPDOState.SEALED, "seal_opdo", actor)
    
    def finalize(self, human_review_ber_id: str, actor: str = "HUMAN_REVIEWER") -> OrchestratedPDO:
        """Finalize O-PDO (irreversible)."""
        if self.opdo.state != OPDOState.SEALED:
            raise OPDOError(
                OPDOErrorCode.GS_433_SEAL_REQUIRED,
                "O-PDO must be SEALED before finalization"
            )
        
        self.opdo.human_review_ber_id = human_review_ber_id
        self.opdo.human_review_timestamp = datetime.utcnow().isoformat() + "Z"
        
        return self.transition(OPDOState.FINAL, "human_review_approved", actor)


# ═══════════════════════════════════════════════════════════════════════════════
# O-PDO FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

def create_opdo(
    pac_orch_id: str,
    child_pdos: List[ChildPDO],
    orchestrator_agent: str = "BENSON",
    orchestrator_gid: str = "GID-00"
) -> OrchestratedPDO:
    """
    Factory function to create an O-PDO.
    
    FAIL_CLOSED on any validation failure.
    """
    # Validate PAC reference
    if not pac_orch_id or not pac_orch_id.startswith("PAC-"):
        raise OPDOError(OPDOErrorCode.GS_441_INVALID_PAC_REF, pac_orch_id)
    
    # Generate O-PDO ID
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    opdo_id = f"OPDO-{pac_orch_id.split('-')[1]}-{timestamp}"
    
    # Create O-PDO
    opdo = OrchestratedPDO(
        opdo_id=opdo_id,
        pac_orch_id=pac_orch_id,
        orchestrator_agent=orchestrator_agent,
        orchestrator_gid=orchestrator_gid,
        child_pdos=[]
    )
    
    # Bind child PDOs (validates)
    opdo = bind_child_pdos(opdo, child_pdos)
    
    return opdo


# ═══════════════════════════════════════════════════════════════════════════════
# SERIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def opdo_to_dict(opdo: OrchestratedPDO) -> Dict[str, Any]:
    """Serialize O-PDO to dictionary."""
    return {
        "opdo_id": opdo.opdo_id,
        "pac_orch_id": opdo.pac_orch_id,
        "orchestrator_agent": opdo.orchestrator_agent,
        "orchestrator_gid": opdo.orchestrator_gid,
        "state": opdo.state.name,
        "child_pdos": [
            {
                "pdo_id": p.pdo_id,
                "agent_name": p.agent_name,
                "agent_gid": p.agent_gid,
                "sub_pac_id": p.sub_pac_id,
                "ber_id": p.ber_id,
                "status": p.status,
                "pdo_hash": p.pdo_hash,
                "task_count": p.task_count,
                "quality_score": p.quality_score,
                "created_at": p.created_at,
                "dependencies": p.dependencies
            }
            for p in opdo.child_pdos
        ],
        "composite_proof": {
            "merkle_root": opdo.composite_proof.merkle_root,
            "leaf_hashes": opdo.composite_proof.leaf_hashes,
            "tree_height": opdo.composite_proof.tree_height,
            "proof_timestamp": opdo.composite_proof.proof_timestamp,
            "nonce": opdo.composite_proof.nonce
        } if opdo.composite_proof else None,
        "state_history": [
            {
                "from_state": t.from_state.name,
                "to_state": t.to_state.name,
                "timestamp": t.timestamp,
                "trigger": t.trigger,
                "actor": t.actor
            }
            for t in opdo.state_history
        ],
        "created_at": opdo.created_at,
        "sealed_at": opdo.sealed_at,
        "finalized_at": opdo.finalized_at,
        "human_review_ber_id": opdo.human_review_ber_id,
        "human_review_timestamp": opdo.human_review_timestamp,
        "final_hash": opdo.final_hash
    }


def opdo_to_json(opdo: OrchestratedPDO, indent: int = 2) -> str:
    """Serialize O-PDO to JSON string."""
    return json.dumps(opdo_to_dict(opdo), indent=indent)


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

def verify_opdo_integrity(opdo: OrchestratedPDO) -> Tuple[bool, List[str]]:
    """
    Verify O-PDO integrity.
    
    Returns (is_valid, list_of_issues).
    """
    issues = []
    
    # Check ID format
    if not opdo.opdo_id.startswith("OPDO-"):
        issues.append("Invalid O-PDO ID format")
    
    # Check orchestrator
    if opdo.orchestrator_agent != "BENSON" or opdo.orchestrator_gid != "GID-00":
        issues.append("Invalid orchestrator binding (must be BENSON/GID-00)")
    
    # Check child PDOs
    if not opdo.child_pdos:
        issues.append("No child PDOs bound")
    else:
        for pdo in opdo.child_pdos:
            valid, error = pdo.validate()
            if not valid:
                issues.append(f"Invalid child PDO {pdo.pdo_id}: {error}")
    
    # Check proof if sealed/final
    if opdo.state in [OPDOState.SEALED, OPDOState.FINAL]:
        if not opdo.composite_proof:
            issues.append("Missing composite proof for sealed/final O-PDO")
        elif not opdo.composite_proof.verify(opdo.child_pdos):
            issues.append("Composite proof verification failed")
    
    # Check human review if final
    if opdo.state == OPDOState.FINAL:
        if not opdo.human_review_ber_id:
            issues.append("Missing human review BER for final O-PDO")
        if not opdo.final_hash:
            issues.append("Missing final hash")
    
    return len(issues) == 0, issues


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("O-PDO MODULE TEST")
    print("=" * 70)
    
    # Test 1: Create child PDOs
    print("\n[Test 1] Creating child PDOs...")
    child1 = ChildPDO(
        pdo_id="PDO-CODY-P67R-20251226",
        agent_name="CODY",
        agent_gid="GID-02",
        sub_pac_id="Sub-PAC-CODY-P67R",
        ber_id="BER-CODY-P67R-DRILL",
        status="VALIDATED",
        pdo_hash="abc123",
        task_count=5,
        quality_score=0.95,
        created_at="2025-12-26T06:00:00Z"
    )
    
    child2 = ChildPDO(
        pdo_id="PDO-SONNY-P67R-20251226",
        agent_name="SONNY",
        agent_gid="GID-03",
        sub_pac_id="Sub-PAC-SONNY-P67R",
        ber_id="BER-SONNY-P67R-DRILL",
        status="VALIDATED",
        pdo_hash="def456",
        task_count=3,
        quality_score=0.92,
        created_at="2025-12-26T06:05:00Z"
    )
    print("✅ Child PDOs created")
    
    # Test 2: Create O-PDO
    print("\n[Test 2] Creating O-PDO...")
    opdo = create_opdo(
        pac_orch_id="PAC-BENSON-P67R-MULTI-AGENT-ORCHESTRATION-LIVE-EXECUTION-DRILL-01",
        child_pdos=[child1, child2]
    )
    print(f"✅ O-PDO created: {opdo.opdo_id}")
    print(f"   State: {opdo.state.name}")
    print(f"   Children: {len(opdo.child_pdos)}")
    
    # Test 3: Generate composite proof
    print("\n[Test 3] Generating composite proof...")
    proof = generate_composite_proof(opdo)
    opdo.composite_proof = proof
    print(f"✅ Proof generated")
    print(f"   Merkle root: {proof.merkle_root[:32]}...")
    print(f"   Tree height: {proof.tree_height}")
    print(f"   Leaf count: {len(proof.leaf_hashes)}")
    
    # Test 4: Seal O-PDO
    print("\n[Test 4] Sealing O-PDO...")
    fsm = OPDOFinalityStateMachine(opdo)
    opdo = fsm.seal()
    print(f"✅ O-PDO sealed")
    print(f"   State: {opdo.state.name}")
    print(f"   Sealed at: {opdo.sealed_at}")
    
    # Test 5: Attempt finalize without human review (should fail)
    print("\n[Test 5] Attempting premature finalization (before seal)...")
    opdo_test5 = create_opdo(
        pac_orch_id="PAC-TEST-P00",
        child_pdos=[child1, child2]
    )
    fsm_test5 = OPDOFinalityStateMachine(opdo_test5)
    try:
        fsm_test5.finalize("BER-TEST")
        print("❌ Should have failed!")
    except OPDOError as e:
        print(f"✅ Correctly rejected: {e.code.name}")
    
    # Test 6: Finalize with human review
    print("\n[Test 6] Finalizing with human review...")
    opdo = fsm.finalize("BER-HUMAN-REVIEW-P67R-APPROVED")
    print(f"✅ O-PDO finalized")
    print(f"   State: {opdo.state.name}")
    print(f"   Finalized at: {opdo.finalized_at}")
    print(f"   Final hash: {opdo.final_hash[:32]}...")
    
    # Test 7: Attempt further transition (should fail - irreversible)
    print("\n[Test 7] Attempting transition after finality...")
    try:
        fsm.transition(OPDOState.DRAFT, "test", "test")
        print("❌ Should have failed!")
    except OPDOError as e:
        print(f"✅ Correctly rejected: {e.code.name}")
    
    # Test 8: Verify integrity
    print("\n[Test 8] Verifying O-PDO integrity...")
    valid, issues = verify_opdo_integrity(opdo)
    if valid:
        print("✅ O-PDO integrity verified")
    else:
        print(f"❌ Issues found: {issues}")
    
    # Test 9: Serialize
    print("\n[Test 9] Serializing O-PDO...")
    json_output = opdo_to_json(opdo)
    print(f"✅ Serialized to JSON ({len(json_output)} bytes)")
    
    print("\n" + "=" * 70)
    print("ALL O-PDO TESTS PASSED")
    print("=" * 70)
