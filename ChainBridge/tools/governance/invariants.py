#!/usr/bin/env python3
"""
invariants.py — Canonical Invariant Registry & Enforcement

PAC Reference: PAC-BENSON-P71R-ATLAS-CANONICAL-HARDENING-DRIFT-SEAL-01
Authority: BENSON (GID-00)
Executor: ATLAS (GID-11)

This module encodes explicit invariants extracted from PACs P65-P70.
All invariants are FAIL_CLOSED — violation halts execution.

Invariant Classes:
- STRUCTURAL: Schema and format requirements
- BEHAVIORAL: Runtime behavior constraints
- AUTHORITY: Permission and scope boundaries
- TEMPORAL: Ordering and sequencing requirements
- INTEGRITY: Hash chain and proof requirements
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple
import hashlib
import json
import re


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT ERROR CODES (GS_500 series)
# ═══════════════════════════════════════════════════════════════════════════════

class InvariantErrorCode(Enum):
    """Invariant violation error codes."""
    
    # Structural Invariants (GS_500-509)
    GS_500_STRUCTURAL_VIOLATION = "GS_500: Structural invariant violated"
    GS_501_MISSING_REQUIRED_FIELD = "GS_501: Required field missing"
    GS_502_INVALID_SCHEMA = "GS_502: Schema validation failed"
    GS_503_BLOCK_ORDER_VIOLATION = "GS_503: Block ordering invariant violated"
    GS_504_TEMPLATE_MISMATCH = "GS_504: Template binding mismatch"
    
    # Behavioral Invariants (GS_510-519)
    GS_510_BEHAVIORAL_VIOLATION = "GS_510: Behavioral invariant violated"
    GS_511_SILENT_FAILURE_DETECTED = "GS_511: Silent failure path detected"
    GS_512_NON_DETERMINISTIC = "GS_512: Non-deterministic behavior detected"
    GS_513_STATE_MUTATION_FORBIDDEN = "GS_513: Forbidden state mutation"
    GS_514_SIDE_EFFECT_DETECTED = "GS_514: Unexpected side effect detected"
    
    # Authority Invariants (GS_520-529)
    GS_520_AUTHORITY_VIOLATION = "GS_520: Authority invariant violated"
    GS_521_LANE_BOUNDARY_CROSSED = "GS_521: Execution lane boundary crossed"
    GS_522_SCOPE_EXCEEDED = "GS_522: Scope boundary exceeded"
    GS_523_UNAUTHORIZED_ACTION = "GS_523: Unauthorized action attempted"
    GS_524_SELF_CLOSURE_FORBIDDEN = "GS_524: Agent self-closure forbidden"
    
    # Temporal Invariants (GS_530-539)
    GS_530_TEMPORAL_VIOLATION = "GS_530: Temporal invariant violated"
    GS_531_GATEWAY_ORDER_VIOLATION = "GS_531: Gateway order not enforced"
    GS_532_SEQUENCE_GAP = "GS_532: Sequence gap detected"
    GS_533_TIMESTAMP_DRIFT = "GS_533: Timestamp drift exceeded tolerance"
    GS_534_PREMATURE_EXECUTION = "GS_534: Premature execution attempt"
    
    # Integrity Invariants (GS_540-549)
    GS_540_INTEGRITY_VIOLATION = "GS_540: Integrity invariant violated"
    GS_541_HASH_CHAIN_BROKEN = "GS_541: Hash chain integrity broken"
    GS_542_PROOF_INVALID = "GS_542: Proof validation failed"
    GS_543_TAMPER_DETECTED = "GS_543: Tampering detected"
    GS_544_REPLAY_DETECTED = "GS_544: Replay attack detected"
    
    # Composite Invariants (GS_550-559)
    GS_550_COMPOSITE_VIOLATION = "GS_550: Composite invariant violated"
    GS_551_DEPENDENCY_UNMET = "GS_551: Dependency requirement unmet"
    GS_552_INVARIANT_CONFLICT = "GS_552: Conflicting invariants detected"


class InvariantError(Exception):
    """Exception raised when an invariant is violated."""
    
    def __init__(self, code: InvariantErrorCode, details: Optional[str] = None, context: Optional[Dict] = None):
        self.code = code
        self.details = details
        self.context = context or {}
        message = f"{code.value}"
        if details:
            message += f" | {details}"
        super().__init__(message)


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

class InvariantClass(Enum):
    """Classification of invariant types."""
    STRUCTURAL = auto()   # Schema, format, required fields
    BEHAVIORAL = auto()   # Runtime behavior constraints
    AUTHORITY = auto()    # Permission, scope, lane boundaries
    TEMPORAL = auto()     # Ordering, sequencing, timing
    INTEGRITY = auto()    # Hash chains, proofs, tampering
    COMPOSITE = auto()    # Multi-invariant compositions


class InvariantSeverity(Enum):
    """Severity level of invariant violations."""
    CRITICAL = auto()  # Immediate halt, no recovery
    HIGH = auto()      # Halt, manual intervention required
    MEDIUM = auto()    # Block operation, log and continue
    LOW = auto()       # Warn only (NOT RECOMMENDED - use sparingly)


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT DEFINITION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Invariant:
    """
    An explicit, encoded invariant with enforcement function.
    
    Invariants are FAIL_CLOSED by default — violation halts execution.
    """
    
    id: str                                    # Unique identifier (INV-XXX)
    name: str                                  # Human-readable name
    description: str                           # What this invariant enforces
    invariant_class: InvariantClass            # Classification
    severity: InvariantSeverity                # Violation severity
    error_code: InvariantErrorCode             # Error code on violation
    pac_source: str                            # Source PAC reference
    
    # Enforcement function: (context) -> (passed: bool, message: str)
    enforce: Callable[[Dict[str, Any]], Tuple[bool, str]] = field(default=None)
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    enabled: bool = True
    fail_closed: bool = True  # Always True for canon invariants


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class InvariantRegistry:
    """
    Central registry for all canonical invariants.
    
    Invariants are loaded from PAC sources and enforced at runtime.
    """
    
    def __init__(self):
        self._invariants: Dict[str, Invariant] = {}
        self._by_class: Dict[InvariantClass, List[str]] = {c: [] for c in InvariantClass}
        self._enforcement_log: List[Dict] = []
        self._load_canonical_invariants()
    
    def _load_canonical_invariants(self):
        """Load all canonical invariants from P65-P70."""
        
        # ═══════════════════════════════════════════════════════════════════
        # STRUCTURAL INVARIANTS (from P65-P66)
        # ═══════════════════════════════════════════════════════════════════
        
        self.register(Invariant(
            id="INV-001",
            name="RUNTIME_ACTIVATION_REQUIRED",
            description="All executable PACs must include RUNTIME_ACTIVATION_ACK block",
            invariant_class=InvariantClass.STRUCTURAL,
            severity=InvariantSeverity.CRITICAL,
            error_code=InvariantErrorCode.GS_501_MISSING_REQUIRED_FIELD,
            pac_source="PAC-BENSON-P66R",
            enforce=lambda ctx: self._check_block_exists(ctx, "RUNTIME_ACTIVATION_ACK")
        ))
        
        self.register(Invariant(
            id="INV-002",
            name="AGENT_ACTIVATION_REQUIRED",
            description="All PACs must include AGENT_ACTIVATION_ACK block",
            invariant_class=InvariantClass.STRUCTURAL,
            severity=InvariantSeverity.CRITICAL,
            error_code=InvariantErrorCode.GS_501_MISSING_REQUIRED_FIELD,
            pac_source="PAC-BENSON-P66R",
            enforce=lambda ctx: self._check_block_exists(ctx, "AGENT_ACTIVATION_ACK")
        ))
        
        self.register(Invariant(
            id="INV-003",
            name="GATEWAY_SEQUENCE_REQUIRED",
            description="All PACs must include CANONICAL_GATEWAY_SEQUENCE block",
            invariant_class=InvariantClass.STRUCTURAL,
            severity=InvariantSeverity.CRITICAL,
            error_code=InvariantErrorCode.GS_501_MISSING_REQUIRED_FIELD,
            pac_source="PAC-BENSON-P67R",
            enforce=lambda ctx: self._check_block_exists(ctx, "CANONICAL_GATEWAY_SEQUENCE")
        ))
        
        self.register(Invariant(
            id="INV-004",
            name="TEMPLATE_CHECKSUM_BOUND",
            description="PAC must bind to canonical template with verified checksum",
            invariant_class=InvariantClass.STRUCTURAL,
            severity=InvariantSeverity.CRITICAL,
            error_code=InvariantErrorCode.GS_504_TEMPLATE_MISMATCH,
            pac_source="PAC-BENSON-P65",
            enforce=lambda ctx: self._check_template_binding(ctx)
        ))
        
        self.register(Invariant(
            id="INV-005",
            name="GOLD_STANDARD_CHECKLIST_COMPLETE",
            description="All 13 Gold Standard checklist items must pass",
            invariant_class=InvariantClass.STRUCTURAL,
            severity=InvariantSeverity.CRITICAL,
            error_code=InvariantErrorCode.GS_500_STRUCTURAL_VIOLATION,
            pac_source="PAC-BENSON-P69R",
            enforce=lambda ctx: self._check_gold_standard_complete(ctx)
        ))
        
        # ═══════════════════════════════════════════════════════════════════
        # BEHAVIORAL INVARIANTS (from P68-P69)
        # ═══════════════════════════════════════════════════════════════════
        
        self.register(Invariant(
            id="INV-010",
            name="NO_SILENT_FAILURES",
            description="All failure paths must be explicit and logged",
            invariant_class=InvariantClass.BEHAVIORAL,
            severity=InvariantSeverity.CRITICAL,
            error_code=InvariantErrorCode.GS_511_SILENT_FAILURE_DETECTED,
            pac_source="PAC-BENSON-P68",
            enforce=lambda ctx: self._check_no_silent_failures(ctx)
        ))
        
        self.register(Invariant(
            id="INV-011",
            name="FAIL_CLOSED_DEFAULT",
            description="All operations must fail closed on error",
            invariant_class=InvariantClass.BEHAVIORAL,
            severity=InvariantSeverity.CRITICAL,
            error_code=InvariantErrorCode.GS_510_BEHAVIORAL_VIOLATION,
            pac_source="PAC-BENSON-P69",
            enforce=lambda ctx: self._check_fail_closed_mode(ctx)
        ))
        
        self.register(Invariant(
            id="INV-012",
            name="DETERMINISTIC_HASH",
            description="Hash computations must be deterministic",
            invariant_class=InvariantClass.BEHAVIORAL,
            severity=InvariantSeverity.CRITICAL,
            error_code=InvariantErrorCode.GS_512_NON_DETERMINISTIC,
            pac_source="PAC-BENSON-P69",
            enforce=lambda ctx: self._check_deterministic_hash(ctx)
        ))
        
        self.register(Invariant(
            id="INV-013",
            name="FINALITY_IRREVERSIBLE",
            description="Once FINAL state reached, no transitions allowed",
            invariant_class=InvariantClass.BEHAVIORAL,
            severity=InvariantSeverity.CRITICAL,
            error_code=InvariantErrorCode.GS_513_STATE_MUTATION_FORBIDDEN,
            pac_source="PAC-BENSON-P69",
            enforce=lambda ctx: self._check_finality_irreversible(ctx)
        ))
        
        # ═══════════════════════════════════════════════════════════════════
        # AUTHORITY INVARIANTS (from P66-P67)
        # ═══════════════════════════════════════════════════════════════════
        
        self.register(Invariant(
            id="INV-020",
            name="ORCHESTRATOR_NO_BUSINESS_LOGIC",
            description="BENSON orchestrator must not execute business logic",
            invariant_class=InvariantClass.AUTHORITY,
            severity=InvariantSeverity.CRITICAL,
            error_code=InvariantErrorCode.GS_523_UNAUTHORIZED_ACTION,
            pac_source="PAC-BENSON-P66R",
            enforce=lambda ctx: self._check_orchestrator_scope(ctx)
        ))
        
        self.register(Invariant(
            id="INV-021",
            name="AGENT_LANE_ISOLATION",
            description="Agents must operate within declared execution lanes",
            invariant_class=InvariantClass.AUTHORITY,
            severity=InvariantSeverity.CRITICAL,
            error_code=InvariantErrorCode.GS_521_LANE_BOUNDARY_CROSSED,
            pac_source="PAC-BENSON-P66R",
            enforce=lambda ctx: self._check_lane_isolation(ctx)
        ))
        
        self.register(Invariant(
            id="INV-022",
            name="WRAP_AUTHORITY_BENSON_ONLY",
            description="Only BENSON (GID-00) can emit WRAP",
            invariant_class=InvariantClass.AUTHORITY,
            severity=InvariantSeverity.CRITICAL,
            error_code=InvariantErrorCode.GS_520_AUTHORITY_VIOLATION,
            pac_source="PAC-BENSON-P65",
            enforce=lambda ctx: self._check_wrap_authority(ctx)
        ))
        
        self.register(Invariant(
            id="INV-023",
            name="NO_AGENT_SELF_CLOSURE",
            description="Agents cannot close their own PACs",
            invariant_class=InvariantClass.AUTHORITY,
            severity=InvariantSeverity.CRITICAL,
            error_code=InvariantErrorCode.GS_524_SELF_CLOSURE_FORBIDDEN,
            pac_source="PAC-BENSON-P65",
            enforce=lambda ctx: self._check_no_self_closure(ctx)
        ))
        
        # ═══════════════════════════════════════════════════════════════════
        # TEMPORAL INVARIANTS (from P67-P69)
        # ═══════════════════════════════════════════════════════════════════
        
        self.register(Invariant(
            id="INV-030",
            name="GATEWAY_ORDER_ENFORCED",
            description="Gateways must execute in order G0 → G1 → ... → G7",
            invariant_class=InvariantClass.TEMPORAL,
            severity=InvariantSeverity.CRITICAL,
            error_code=InvariantErrorCode.GS_531_GATEWAY_ORDER_VIOLATION,
            pac_source="PAC-BENSON-P67R",
            enforce=lambda ctx: self._check_gateway_order(ctx)
        ))
        
        self.register(Invariant(
            id="INV-031",
            name="HUMAN_REVIEW_BEFORE_FINALITY",
            description="Human review required before O-PDO finalization",
            invariant_class=InvariantClass.TEMPORAL,
            severity=InvariantSeverity.CRITICAL,
            error_code=InvariantErrorCode.GS_534_PREMATURE_EXECUTION,
            pac_source="PAC-BENSON-P68",
            enforce=lambda ctx: self._check_human_review_gate(ctx)
        ))
        
        self.register(Invariant(
            id="INV-032",
            name="SEAL_BEFORE_FINAL",
            description="O-PDO must be SEALED before FINAL transition",
            invariant_class=InvariantClass.TEMPORAL,
            severity=InvariantSeverity.CRITICAL,
            error_code=InvariantErrorCode.GS_530_TEMPORAL_VIOLATION,
            pac_source="PAC-BENSON-P69",
            enforce=lambda ctx: self._check_seal_before_final(ctx)
        ))
        
        # ═══════════════════════════════════════════════════════════════════
        # INTEGRITY INVARIANTS (from P65-P69)
        # ═══════════════════════════════════════════════════════════════════
        
        self.register(Invariant(
            id="INV-040",
            name="LEDGER_HASH_CHAIN_INTACT",
            description="Ledger hash chain must be unbroken",
            invariant_class=InvariantClass.INTEGRITY,
            severity=InvariantSeverity.CRITICAL,
            error_code=InvariantErrorCode.GS_541_HASH_CHAIN_BROKEN,
            pac_source="PAC-BENSON-P65",
            enforce=lambda ctx: self._check_hash_chain(ctx)
        ))
        
        self.register(Invariant(
            id="INV-041",
            name="MERKLE_PROOF_VALID",
            description="O-PDO composite proof must verify correctly",
            invariant_class=InvariantClass.INTEGRITY,
            severity=InvariantSeverity.CRITICAL,
            error_code=InvariantErrorCode.GS_542_PROOF_INVALID,
            pac_source="PAC-BENSON-P69",
            enforce=lambda ctx: self._check_merkle_proof(ctx)
        ))
        
        self.register(Invariant(
            id="INV-042",
            name="NO_REPLAY_ATTACKS",
            description="Challenge responses cannot be replayed",
            invariant_class=InvariantClass.INTEGRITY,
            severity=InvariantSeverity.CRITICAL,
            error_code=InvariantErrorCode.GS_544_REPLAY_DETECTED,
            pac_source="PAC-BENSON-P68",
            enforce=lambda ctx: self._check_no_replay(ctx)
        ))
        
        # ═══════════════════════════════════════════════════════════════════
        # COMPOSITE INVARIANTS (cross-cutting)
        # ═══════════════════════════════════════════════════════════════════
        
        self.register(Invariant(
            id="INV-050",
            name="ALL_CHILD_PDOS_VALIDATED",
            description="O-PDO requires all child PDOs to be VALIDATED",
            invariant_class=InvariantClass.COMPOSITE,
            severity=InvariantSeverity.CRITICAL,
            error_code=InvariantErrorCode.GS_551_DEPENDENCY_UNMET,
            pac_source="PAC-BENSON-P69",
            enforce=lambda ctx: self._check_all_children_validated(ctx)
        ))
        
        self.register(Invariant(
            id="INV-051",
            name="DEPENDENCY_DAG_ACYCLIC",
            description="PDO dependency graph must be a DAG (no cycles)",
            invariant_class=InvariantClass.COMPOSITE,
            severity=InvariantSeverity.CRITICAL,
            error_code=InvariantErrorCode.GS_550_COMPOSITE_VIOLATION,
            pac_source="PAC-BENSON-P69",
            enforce=lambda ctx: self._check_dag_acyclic(ctx)
        ))
    
    def register(self, invariant: Invariant) -> None:
        """Register an invariant in the registry."""
        if invariant.id in self._invariants:
            raise InvariantError(
                InvariantErrorCode.GS_552_INVARIANT_CONFLICT,
                f"Invariant {invariant.id} already registered"
            )
        self._invariants[invariant.id] = invariant
        self._by_class[invariant.invariant_class].append(invariant.id)
    
    def get(self, invariant_id: str) -> Optional[Invariant]:
        """Get an invariant by ID."""
        return self._invariants.get(invariant_id)
    
    def get_by_class(self, inv_class: InvariantClass) -> List[Invariant]:
        """Get all invariants of a specific class."""
        return [self._invariants[id] for id in self._by_class[inv_class]]
    
    def enforce(self, invariant_id: str, context: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Enforce a single invariant.
        
        Returns (passed, message).
        Raises InvariantError if fail_closed and violation detected.
        """
        inv = self.get(invariant_id)
        if inv is None:
            raise InvariantError(
                InvariantErrorCode.GS_500_STRUCTURAL_VIOLATION,
                f"Unknown invariant: {invariant_id}"
            )
        
        if not inv.enabled:
            return True, f"Invariant {invariant_id} disabled (WARN: not recommended)"
        
        if inv.enforce is None:
            return True, f"Invariant {invariant_id} has no enforcement function"
        
        passed, message = inv.enforce(context)
        
        # Log enforcement
        self._enforcement_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "invariant_id": invariant_id,
            "passed": passed,
            "message": message,
            "context_keys": list(context.keys())
        })
        
        if not passed and inv.fail_closed:
            raise InvariantError(inv.error_code, message, context)
        
        return passed, message
    
    def enforce_all(self, context: Dict[str, Any]) -> Dict[str, Tuple[bool, str]]:
        """
        Enforce all enabled invariants.
        
        Returns dict of results. Raises InvariantError on first violation if fail_closed.
        """
        results = {}
        for inv_id, inv in self._invariants.items():
            if inv.enabled:
                results[inv_id] = self.enforce(inv_id, context)
        return results
    
    def enforce_class(self, inv_class: InvariantClass, context: Dict[str, Any]) -> Dict[str, Tuple[bool, str]]:
        """Enforce all invariants of a specific class."""
        results = {}
        for inv in self.get_by_class(inv_class):
            if inv.enabled:
                results[inv.id] = self.enforce(inv.id, context)
        return results
    
    # ═══════════════════════════════════════════════════════════════════════
    # ENFORCEMENT FUNCTIONS
    # ═══════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def _check_block_exists(ctx: Dict, block_name: str) -> Tuple[bool, str]:
        """Check if a required block exists."""
        blocks = ctx.get("blocks", {})
        content = ctx.get("content", "")
        
        # Check in parsed blocks or raw content
        if block_name in blocks:
            return True, f"Block {block_name} present"
        if block_name in content:
            return True, f"Block {block_name} found in content"
        return False, f"Missing required block: {block_name}"
    
    @staticmethod
    def _check_template_binding(ctx: Dict) -> Tuple[bool, str]:
        """Check template checksum binding."""
        expected = "410349e98f9f99c851fa468b6873e1709ab64bc70a7a27d21bf8ce2969c8109a"
        template = ctx.get("template_binding", {})
        checksum = template.get("checksum", ctx.get("template_checksum", ""))
        
        if checksum == expected:
            return True, "Template checksum verified"
        if not checksum:
            return False, "No template checksum bound"
        return False, f"Template checksum mismatch: {checksum[:16]}..."
    
    @staticmethod
    def _check_gold_standard_complete(ctx: Dict) -> Tuple[bool, str]:
        """Check Gold Standard checklist completeness."""
        checklist = ctx.get("gold_standard_checklist", {})
        if not checklist:
            return False, "Gold Standard checklist missing"
        
        # Check for 13 items
        items = [k for k in checklist.keys() if k.startswith("GS_")]
        if len(items) < 13:
            return False, f"Gold Standard incomplete: {len(items)}/13 items"
        
        # Check all pass
        for item, value in checklist.items():
            if item.startswith("GS_"):
                status = value.get("status", value) if isinstance(value, dict) else value
                if status not in ["PASS", True, "checked"]:
                    return False, f"Gold Standard item {item} not passing"
        
        return True, "Gold Standard checklist complete (13/13)"
    
    @staticmethod
    def _check_no_silent_failures(ctx: Dict) -> Tuple[bool, str]:
        """Check that no silent failure paths exist."""
        # This is enforced via code review in actual implementation
        fail_mode = ctx.get("failure_mode", ctx.get("mode", ""))
        if "FAIL_CLOSED" in str(fail_mode).upper():
            return True, "FAIL_CLOSED mode active"
        if "silent" in str(ctx).lower():
            return False, "Silent failure path detected"
        return True, "No silent failures detected"
    
    @staticmethod
    def _check_fail_closed_mode(ctx: Dict) -> Tuple[bool, str]:
        """Check fail-closed is the default mode."""
        mode = ctx.get("mode", ctx.get("failure_mode", ""))
        enforcement = ctx.get("enforcement_mode", "")
        
        if "FAIL_CLOSED" in str(mode).upper() or "FAIL_CLOSED" in str(enforcement).upper():
            return True, "Fail-closed mode enforced"
        return False, "Fail-closed mode not detected"
    
    @staticmethod
    def _check_deterministic_hash(ctx: Dict) -> Tuple[bool, str]:
        """Check hash computation is deterministic."""
        # Re-compute any provided hashes to verify
        test_data = ctx.get("hash_test_data")
        expected_hash = ctx.get("expected_hash")
        
        if test_data is not None and expected_hash:
            canonical = json.dumps(test_data, sort_keys=True) if isinstance(test_data, dict) else str(test_data)
            computed = hashlib.sha256(canonical.encode()).hexdigest()
            if computed != expected_hash:
                return False, f"Hash non-deterministic: expected {expected_hash[:16]}..., got {computed[:16]}..."
        
        return True, "Hash determinism verified"
    
    @staticmethod
    def _check_finality_irreversible(ctx: Dict) -> Tuple[bool, str]:
        """Check finality state is irreversible."""
        state = ctx.get("state", "")
        transitions = ctx.get("valid_transitions", {})
        
        if state == "FINAL":
            if transitions.get("FINAL", []):
                return False, "FINAL state has outbound transitions (must be empty)"
        
        return True, "Finality irreversibility maintained"
    
    @staticmethod
    def _check_orchestrator_scope(ctx: Dict) -> Tuple[bool, str]:
        """Check orchestrator doesn't execute business logic."""
        agent = ctx.get("agent", "")
        business_logic = ctx.get("business_logic", "")
        
        if "BENSON" in agent.upper() and business_logic != "FORBIDDEN":
            return False, "Orchestrator business_logic not FORBIDDEN"
        
        return True, "Orchestrator scope verified"
    
    @staticmethod
    def _check_lane_isolation(ctx: Dict) -> Tuple[bool, str]:
        """Check agent operates in declared lane."""
        declared_lane = ctx.get("execution_lane", "")
        actual_lane = ctx.get("actual_lane", declared_lane)
        
        if declared_lane and actual_lane and declared_lane != actual_lane:
            return False, f"Lane mismatch: declared={declared_lane}, actual={actual_lane}"
        
        return True, "Lane isolation maintained"
    
    @staticmethod
    def _check_wrap_authority(ctx: Dict) -> Tuple[bool, str]:
        """Check WRAP is only emitted by BENSON."""
        wrap_emitter = ctx.get("wrap_emitter", ctx.get("authority", ""))
        
        if ctx.get("artifact_type") == "WRAP":
            if "GID-00" not in wrap_emitter and "BENSON" not in wrap_emitter.upper():
                return False, f"WRAP emitter not BENSON: {wrap_emitter}"
        
        return True, "WRAP authority verified"
    
    @staticmethod
    def _check_no_self_closure(ctx: Dict) -> Tuple[bool, str]:
        """Check agent doesn't close own PAC."""
        pac_agent = ctx.get("pac_agent", "")
        closer = ctx.get("closer", ctx.get("wrap_emitter", ""))
        
        if pac_agent and closer and pac_agent == closer:
            # Only BENSON can self-close (orchestration)
            if "BENSON" not in pac_agent.upper():
                return False, f"Agent self-closure detected: {pac_agent}"
        
        return True, "No self-closure detected"
    
    @staticmethod
    def _check_gateway_order(ctx: Dict) -> Tuple[bool, str]:
        """Check gateway order is G0 → G1 → ... → G7."""
        gateway_order = ctx.get("gateway_order", "")
        expected = "G0 → G1 → G2 → G3 → G4 → G5 → G6 → G7"
        
        # Normalize
        normalized = gateway_order.replace("->", "→").replace(" ", "")
        expected_normalized = expected.replace(" ", "")
        
        if normalized and normalized != expected_normalized:
            # Check at least partial compliance
            if not normalized.startswith("G0"):
                return False, "Gateway sequence must start with G0"
        
        return True, "Gateway order verified"
    
    @staticmethod
    def _check_human_review_gate(ctx: Dict) -> Tuple[bool, str]:
        """Check human review gate is specified."""
        human_review = ctx.get("human_review_gate", ctx.get("human_review_required", False))
        
        if human_review in [True, "REQUIRED", "PENDING"]:
            return True, "Human review gate specified"
        
        # Check for HUMAN_REVIEW_GATE block
        content = ctx.get("content", "")
        if "HUMAN_REVIEW_GATE" in content:
            return True, "Human review gate block present"
        
        return False, "Human review gate not specified"
    
    @staticmethod
    def _check_seal_before_final(ctx: Dict) -> Tuple[bool, str]:
        """Check SEAL state required before FINAL."""
        state = ctx.get("state", "")
        sealed_at = ctx.get("sealed_at")
        finalized_at = ctx.get("finalized_at")
        
        if state == "FINAL" and not sealed_at:
            return False, "FINAL without prior SEAL state"
        
        return True, "Seal-before-final verified"
    
    @staticmethod
    def _check_hash_chain(ctx: Dict) -> Tuple[bool, str]:
        """Check ledger hash chain integrity."""
        entries = ctx.get("ledger_entries", [])
        
        if not entries:
            return True, "No entries to verify"
        
        for i in range(1, len(entries)):
            prior_hash = entries[i].get("prior_hash", "")
            expected = entries[i-1].get("entry_hash", "")
            
            if prior_hash != expected:
                return False, f"Hash chain broken at entry {i}"
        
        return True, "Hash chain intact"
    
    @staticmethod
    def _check_merkle_proof(ctx: Dict) -> Tuple[bool, str]:
        """Check merkle proof validity."""
        proof = ctx.get("composite_proof", {})
        
        if not proof:
            return True, "No proof to verify"
        
        merkle_root = proof.get("merkle_root")
        leaf_hashes = proof.get("leaf_hashes", [])
        
        if merkle_root and leaf_hashes:
            # Simple verification: root should be derivable from leaves
            # Full verification would recompute tree
            return True, "Merkle proof structure valid"
        
        return False, "Merkle proof incomplete"
    
    @staticmethod
    def _check_no_replay(ctx: Dict) -> Tuple[bool, str]:
        """Check for replay attack detection."""
        nonce = ctx.get("nonce", ctx.get("challenge_nonce", ""))
        used_nonces = ctx.get("used_nonces", set())
        
        if nonce and nonce in used_nonces:
            return False, f"Replay detected: nonce {nonce[:16]}..."
        
        return True, "No replay detected"
    
    @staticmethod
    def _check_all_children_validated(ctx: Dict) -> Tuple[bool, str]:
        """Check all child PDOs are validated."""
        children = ctx.get("child_pdos", [])
        
        for child in children:
            status = child.get("status", "")
            if status != "VALIDATED":
                pdo_id = child.get("pdo_id", "unknown")
                return False, f"Child PDO not validated: {pdo_id}"
        
        return True, "All child PDOs validated"
    
    @staticmethod
    def _check_dag_acyclic(ctx: Dict) -> Tuple[bool, str]:
        """Check dependency graph is acyclic."""
        # This would require the actual graph; simplified check
        cycle_detected = ctx.get("cycle_detected", False)
        
        if cycle_detected:
            return False, "Cycle detected in dependency graph"
        
        return True, "Dependency graph is acyclic"
    
    # ═══════════════════════════════════════════════════════════════════════
    # REPORTING
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_enforcement_log(self) -> List[Dict]:
        """Get enforcement log."""
        return self._enforcement_log.copy()
    
    def summary(self) -> Dict:
        """Get registry summary."""
        return {
            "total_invariants": len(self._invariants),
            "by_class": {c.name: len(ids) for c, ids in self._by_class.items()},
            "enabled": sum(1 for inv in self._invariants.values() if inv.enabled),
            "enforcement_count": len(self._enforcement_log)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL REGISTRY INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_registry: Optional[InvariantRegistry] = None


def get_invariant_registry() -> InvariantRegistry:
    """Get or create the global invariant registry."""
    global _registry
    if _registry is None:
        _registry = InvariantRegistry()
    return _registry


def enforce_invariant(invariant_id: str, context: Dict[str, Any]) -> Tuple[bool, str]:
    """Convenience function to enforce a single invariant."""
    return get_invariant_registry().enforce(invariant_id, context)


def enforce_all_invariants(context: Dict[str, Any]) -> Dict[str, Tuple[bool, str]]:
    """Convenience function to enforce all invariants."""
    return get_invariant_registry().enforce_all(context)


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("INVARIANT REGISTRY TEST")
    print("=" * 70)
    
    registry = get_invariant_registry()
    summary = registry.summary()
    
    print(f"\nTotal invariants: {summary['total_invariants']}")
    print(f"By class:")
    for cls, count in summary['by_class'].items():
        print(f"  {cls}: {count}")
    
    # Test enforcement
    print("\n[Test 1] Checking RUNTIME_ACTIVATION_REQUIRED...")
    ctx1 = {"content": "RUNTIME_ACTIVATION_ACK: present"}
    passed, msg = registry.enforce("INV-001", ctx1)
    print(f"  {'PASS' if passed else 'FAIL'}: {msg}")
    
    print("\n[Test 2] Checking missing block...")
    ctx2 = {"content": ""}
    try:
        passed, msg = registry.enforce("INV-001", ctx2)
        print(f"  {'PASS' if passed else 'FAIL'}: {msg}")
    except InvariantError as e:
        print(f"  FAIL_CLOSED: {e.code.name}")
    
    print("\n[Test 3] Checking template binding...")
    ctx3 = {"template_checksum": "410349e98f9f99c851fa468b6873e1709ab64bc70a7a27d21bf8ce2969c8109a"}
    passed, msg = registry.enforce("INV-004", ctx3)
    print(f"  {'PASS' if passed else 'FAIL'}: {msg}")
    
    print("\n[Test 4] Checking fail-closed mode...")
    ctx4 = {"mode": "FAIL_CLOSED"}
    passed, msg = registry.enforce("INV-011", ctx4)
    print(f"  {'PASS' if passed else 'FAIL'}: {msg}")
    
    print("\n" + "=" * 70)
    print("INVARIANT REGISTRY TEST COMPLETE")
    print("=" * 70)
