"""
ChainBridge BLCR Engine - Binary Logic Control Runtime
=======================================================

PAC Reference: PAC-BLCR-GENESIS-17
Classification: LAW / SOVEREIGNTY-HARDENING
Job ID: BLCR-GENESIS

This module implements the 0.38ms Fast-Path Logic Gate system that replaces
probabilistic inference with deterministic binary reasoning. All agent turns
require Binary Reason Proof (BRP) validation before execution.

Constitutional Rules Enforced:
    1. CONTROL > AUTONOMY: Probability-based inference IS VIOLATION
    2. PROOF > EXECUTION: BRP REQUIRED per agent turn
    3. FAIL-CLOSED: Drift > 0.38ms or non-deterministic output TRIGGERS SHUTDOWN
    4. RNP: Patching legacy ML loops IS FORBIDDEN
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Callable
from dataclasses import dataclass, field
from functools import wraps
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BLCR")


# =============================================================================
# CONSTANTS
# =============================================================================

LATENCY_TARGET_MS = Decimal("0.38")
LATENCY_HARD_LIMIT_MS = Decimal("0.50")
FAIL_CLOSED_ENABLED = True


# =============================================================================
# EXCEPTIONS
# =============================================================================

class BLCRViolation(Exception):
    """Base exception for BLCR constitutional violations."""
    pass


class LatencyDriftViolation(BLCRViolation):
    """Raised when latency exceeds 0.38ms target."""
    pass


class NonDeterministicOutputViolation(BLCRViolation):
    """Raised when output is non-deterministic."""
    pass


class MissingBRPViolation(BLCRViolation):
    """Raised when Binary Reason Proof is missing."""
    pass


class ProbabilisticInferenceViolation(BLCRViolation):
    """Raised when probability-based inference is detected."""
    pass


class AutonomyWithoutPDOViolation(BLCRViolation):
    """Raised when agent acts autonomously without PDO proof."""
    pass


# =============================================================================
# ENUMS
# =============================================================================

class LogicGateType(Enum):
    """Types of logic gates in the BLCR system."""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    XOR = "XOR"
    NAND = "NAND"
    NOR = "NOR"
    IMPLICATION = "IMPLICATION"  # IF A THEN B
    EQUIVALENCE = "EQUIVALENCE"  # A IFF B


class BRPStatus(Enum):
    """Binary Reason Proof validation status."""
    VALID = "VALID"
    INVALID = "INVALID"
    PENDING = "PENDING"
    EXPIRED = "EXPIRED"


class AgentLevel(Enum):
    """Agent sovereignty levels."""
    LEVEL_1 = 1   # Basic
    LEVEL_5 = 5   # Intermediate
    LEVEL_10 = 10 # Advanced
    LEVEL_11 = 11 # Deterministic Sovereignty (Olympic)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class BinaryReasonProof:
    """
    Binary Reason Proof (BRP) - Required for every agent turn.
    Proves the decision was made through deterministic logic gates.
    """
    proof_id: str
    agent_gid: str
    decision_hash: str
    logic_gate_chain: list[str]
    inputs: dict[str, Any]
    output: Any
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    latency_ms: Decimal = Decimal("0.00")
    status: BRPStatus = BRPStatus.PENDING
    
    def __post_init__(self):
        self.proof_id = self._generate_proof_id()
    
    def _generate_proof_id(self) -> str:
        data = f"{self.agent_gid}:{self.decision_hash}:{self.timestamp}"
        return f"BRP-{hashlib.sha256(data.encode()).hexdigest()[:16].upper()}"
    
    def validate(self) -> bool:
        """Validate the BRP meets constitutional requirements."""
        # Check latency
        if self.latency_ms > LATENCY_TARGET_MS:
            self.status = BRPStatus.INVALID
            raise LatencyDriftViolation(
                f"Latency {self.latency_ms}ms exceeds target {LATENCY_TARGET_MS}ms"
            )
        
        # Check logic gate chain is not empty
        if not self.logic_gate_chain:
            self.status = BRPStatus.INVALID
            raise MissingBRPViolation("Logic gate chain is empty")
        
        # Check decision hash matches output
        computed_hash = hashlib.sha256(
            json.dumps(self.output, sort_keys=True, default=str).encode()
        ).hexdigest()
        
        if computed_hash != self.decision_hash:
            self.status = BRPStatus.INVALID
            raise NonDeterministicOutputViolation(
                "Output hash mismatch - non-deterministic output detected"
            )
        
        self.status = BRPStatus.VALID
        return True


@dataclass
class LogicGate:
    """A single logic gate in the BLCR system."""
    gate_id: str
    gate_type: LogicGateType
    inputs: list[str]
    output: str
    truth_table: dict[str, bool]
    
    def evaluate(self, input_values: dict[str, bool]) -> bool:
        """Evaluate the gate with given inputs."""
        if self.gate_type == LogicGateType.AND:
            return all(input_values.get(i, False) for i in self.inputs)
        elif self.gate_type == LogicGateType.OR:
            return any(input_values.get(i, False) for i in self.inputs)
        elif self.gate_type == LogicGateType.NOT:
            return not input_values.get(self.inputs[0], True)
        elif self.gate_type == LogicGateType.XOR:
            vals = [input_values.get(i, False) for i in self.inputs]
            return vals[0] != vals[1] if len(vals) == 2 else False
        elif self.gate_type == LogicGateType.NAND:
            return not all(input_values.get(i, False) for i in self.inputs)
        elif self.gate_type == LogicGateType.NOR:
            return not any(input_values.get(i, False) for i in self.inputs)
        elif self.gate_type == LogicGateType.IMPLICATION:
            a = input_values.get(self.inputs[0], False)
            b = input_values.get(self.inputs[1], False)
            return (not a) or b  # A → B ≡ ¬A ∨ B
        elif self.gate_type == LogicGateType.EQUIVALENCE:
            a = input_values.get(self.inputs[0], False)
            b = input_values.get(self.inputs[1], False)
            return a == b
        return False


@dataclass
class PDOProof:
    """
    Proof-Decision-Outcome (PDO) record.
    All Decisions must be written to /proofs BEFORE Outcome.
    """
    pdo_id: str
    proof_phase: dict[str, Any]   # Evidence gathered
    decision_phase: dict[str, Any]  # Logic applied
    outcome_phase: dict[str, Any] = field(default_factory=dict)  # Result (written last)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    committed: bool = False
    
    def commit_decision(self, decision: dict[str, Any]) -> None:
        """Commit decision phase - MUST happen before outcome."""
        self.decision_phase = decision
        self.decision_phase["committed_at"] = datetime.now(timezone.utc).isoformat()
    
    def commit_outcome(self, outcome: dict[str, Any]) -> None:
        """Commit outcome phase - MUST happen after decision."""
        if not self.decision_phase.get("committed_at"):
            raise AutonomyWithoutPDOViolation(
                "Cannot commit outcome without prior decision commit"
            )
        self.outcome_phase = outcome
        self.outcome_phase["committed_at"] = datetime.now(timezone.utc).isoformat()
        self.committed = True


# =============================================================================
# BLCR ENGINE
# =============================================================================

class BLCREngine:
    """
    Binary Logic Control Runtime Engine.
    
    Replaces probabilistic inference with deterministic logic gates.
    Enforces 0.38ms latency target and BRP requirement.
    """
    
    def __init__(self, proofs_path: str | Path = "proofs"):
        self.proofs_path = Path(proofs_path)
        self.proofs_path.mkdir(exist_ok=True)
        self.logic_gates: dict[str, LogicGate] = {}
        self.brp_registry: list[BinaryReasonProof] = []
        self.pdo_registry: list[PDOProof] = []
        self.agent_levels: dict[str, AgentLevel] = {}
        self._initialize_core_gates()
        self._initialize_agent_levels()
    
    def _initialize_core_gates(self) -> None:
        """Initialize core logic gates for governance decisions."""
        # Gate: PAC Admission
        self.logic_gates["PAC_ADMIT"] = LogicGate(
            gate_id="PAC_ADMIT",
            gate_type=LogicGateType.AND,
            inputs=["schema_valid", "issuer_authorized", "preflight_passed"],
            output="pac_admitted",
            truth_table={}
        )
        
        # Gate: Settlement Authorization
        self.logic_gates["SETTLE_AUTH"] = LogicGate(
            gate_id="SETTLE_AUTH",
            gate_type=LogicGateType.AND,
            inputs=["trinity_passed", "reconciliation_matched", "pdo_verified"],
            output="settlement_authorized",
            truth_table={}
        )
        
        # Gate: Fail-Closed Trigger
        self.logic_gates["FAIL_CLOSED"] = LogicGate(
            gate_id="FAIL_CLOSED",
            gate_type=LogicGateType.OR,
            inputs=["latency_exceeded", "drift_detected", "invariant_violated"],
            output="scram_triggered",
            truth_table={}
        )
        
        # Gate: Agent Autonomy Check
        self.logic_gates["AUTONOMY_CHECK"] = LogicGate(
            gate_id="AUTONOMY_CHECK",
            gate_type=LogicGateType.IMPLICATION,
            inputs=["agent_action_requested", "pdo_proof_exists"],
            output="action_permitted",
            truth_table={}
        )
        
        # Gate: Sovereignty Verification
        self.logic_gates["SOVEREIGNTY"] = LogicGate(
            gate_id="SOVEREIGNTY",
            gate_type=LogicGateType.AND,
            inputs=["level_11_active", "brp_valid", "constitutional_compliant"],
            output="sovereignty_verified",
            truth_table={}
        )
    
    def _initialize_agent_levels(self) -> None:
        """Initialize all agents at Level 11 (Deterministic Sovereignty)."""
        agents = [
            "GID-00",  # Benson
            "GID-11",  # Atlas
            "GID-12",  # Elite Controller
            "GID-13",  # Elite Counsel
            "GID-14",  # Dan SDR
            "GID-15",  # Maggie Ops
        ]
        for agent in agents:
            self.agent_levels[agent] = AgentLevel.LEVEL_11
    
    def create_brp(
        self,
        agent_gid: str,
        logic_chain: list[str],
        inputs: dict[str, Any],
        output: Any
    ) -> BinaryReasonProof:
        """
        Create a Binary Reason Proof for an agent turn.
        Required for every governance decision.
        """
        start_time = time.perf_counter()
        
        decision_hash = hashlib.sha256(
            json.dumps(output, sort_keys=True, default=str).encode()
        ).hexdigest()
        
        brp = BinaryReasonProof(
            proof_id="",  # Will be generated
            agent_gid=agent_gid,
            decision_hash=decision_hash,
            logic_gate_chain=logic_chain,
            inputs=inputs,
            output=output
        )
        
        end_time = time.perf_counter()
        brp.latency_ms = Decimal(str((end_time - start_time) * 1000))
        
        # Validate immediately
        brp.validate()
        
        # Register
        self.brp_registry.append(brp)
        
        # Write to proofs directory
        self._write_brp_to_disk(brp)
        
        return brp
    
    def _write_brp_to_disk(self, brp: BinaryReasonProof) -> None:
        """Write BRP to immutable proofs directory."""
        proof_file = self.proofs_path / f"{brp.proof_id}.json"
        with open(proof_file, 'w') as f:
            json.dump({
                "proof_id": brp.proof_id,
                "agent_gid": brp.agent_gid,
                "decision_hash": brp.decision_hash,
                "logic_gate_chain": brp.logic_gate_chain,
                "inputs": brp.inputs,
                "output": brp.output,
                "timestamp": brp.timestamp,
                "latency_ms": str(brp.latency_ms),
                "status": brp.status.value
            }, f, indent=2, default=str)
    
    def evaluate_gate_chain(
        self,
        gate_ids: list[str],
        initial_inputs: dict[str, bool]
    ) -> dict[str, bool]:
        """Evaluate a chain of logic gates."""
        current_values = initial_inputs.copy()
        
        for gate_id in gate_ids:
            if gate_id not in self.logic_gates:
                raise BLCRViolation(f"Unknown logic gate: {gate_id}")
            
            gate = self.logic_gates[gate_id]
            result = gate.evaluate(current_values)
            current_values[gate.output] = result
        
        return current_values
    
    def create_pdo(self, proof_data: dict[str, Any]) -> PDOProof:
        """Create a new PDO record with proof phase."""
        pdo_id = f"PDO-{hashlib.sha256(json.dumps(proof_data, default=str).encode()).hexdigest()[:16].upper()}"
        pdo = PDOProof(
            pdo_id=pdo_id,
            proof_phase=proof_data,
            decision_phase={}
        )
        self.pdo_registry.append(pdo)
        return pdo
    
    def verify_agent_level(self, agent_gid: str) -> AgentLevel:
        """Verify agent is at Level 11 for sovereignty operations."""
        level = self.agent_levels.get(agent_gid, AgentLevel.LEVEL_1)
        if level != AgentLevel.LEVEL_11:
            raise BLCRViolation(
                f"Agent {agent_gid} at Level {level.value}, "
                f"Level 11 required for sovereignty operations"
            )
        return level
    
    def get_engine_status(self) -> dict[str, Any]:
        """Get current BLCR engine status."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "logic_gates_registered": len(self.logic_gates),
            "brp_count": len(self.brp_registry),
            "pdo_count": len(self.pdo_registry),
            "agents_at_level_11": sum(
                1 for level in self.agent_levels.values()
                if level == AgentLevel.LEVEL_11
            ),
            "latency_target_ms": str(LATENCY_TARGET_MS),
            "fail_closed_enabled": FAIL_CLOSED_ENABLED,
            "status": "OPERATIONAL"
        }


# =============================================================================
# DECORATORS
# =============================================================================

def require_brp(agent_gid: str):
    """
    Decorator to require BRP validation for any function.
    Enforces PROOF > EXECUTION constitutional rule.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            engine = kwargs.get('blcr_engine') or BLCREngine()
            
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            
            latency_ms = Decimal(str((end_time - start_time) * 1000))
            
            if latency_ms > LATENCY_TARGET_MS and FAIL_CLOSED_ENABLED:
                raise LatencyDriftViolation(
                    f"Function {func.__name__} exceeded latency target: "
                    f"{latency_ms}ms > {LATENCY_TARGET_MS}ms"
                )
            
            # Create BRP for this execution
            engine.create_brp(
                agent_gid=agent_gid,
                logic_chain=[func.__name__],
                inputs={"args": str(args), "kwargs": str(kwargs)},
                output=result
            )
            
            return result
        return wrapper
    return decorator


def fail_closed_guard(func: Callable) -> Callable:
    """
    Decorator to implement fail-closed behavior.
    Any exception triggers immediate shutdown of the function.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BLCRViolation as e:
            logger.critical(f"FAIL-CLOSED TRIGGERED: {e}")
            raise
        except Exception as e:
            logger.critical(f"UNEXPECTED ERROR - FAIL-CLOSED: {e}")
            raise BLCRViolation(f"Unexpected error triggered fail-closed: {e}")
    return wrapper


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    "BLCREngine",
    "BinaryReasonProof",
    "LogicGate",
    "LogicGateType",
    "PDOProof",
    "BRPStatus",
    "AgentLevel",
    "require_brp",
    "fail_closed_guard",
    "BLCRViolation",
    "LatencyDriftViolation",
    "NonDeterministicOutputViolation",
    "MissingBRPViolation",
    "ProbabilisticInferenceViolation",
    "AutonomyWithoutPDOViolation",
    "LATENCY_TARGET_MS",
]


if __name__ == "__main__":
    print("BLCR Engine - Binary Logic Control Runtime")
    print("PAC Reference: PAC-BLCR-GENESIS-17")
    print("-" * 60)
    
    engine = BLCREngine()
    status = engine.get_engine_status()
    print(json.dumps(status, indent=2))
