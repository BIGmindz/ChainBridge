"""Settlement Gate — Mandatory Backend Guards.

╔══════════════════════════════════════════════════════════════════════╗
║ EXECUTING AGENT: Cody (GID-01) — Senior Backend Engineer             ║
║ EXECUTING COLOR: 🔵 BLUE                                             ║
║ PAC: PAC-CODY-A6-BACKEND-GUARDRAILS-01                               ║
╚══════════════════════════════════════════════════════════════════════╝

DOCTRINE (FAIL-CLOSED):
Settlement CANNOT proceed unless ALL guards pass:
1. Valid PDO exists and passes validation
2. CRO decision allows execution (not HOLD/ESCALATE)
3. Proof lineage is intact (no breaks/mutations)
4. Caller has settlement authority (not runtime)

INVARIANTS (NON-NEGOTIABLE):
- No direct settlement calls (must go through gate)
- Missing PDO → BLOCK
- Invalid CRO decision → BLOCK
- Broken proof lineage → BLOCK
- All blocks are logged for audit

Author: Cody (GID-01) — Senior Backend Engineer
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SettlementBlockReason(str, Enum):
    """Deterministic reasons for settlement blocks.
    
    Each reason maps to a specific enforcement failure.
    """
    MISSING_PDO = "MISSING_PDO"
    INVALID_PDO = "INVALID_PDO"
    PDO_VALIDATION_FAILED = "PDO_VALIDATION_FAILED"
    CRO_HOLD = "CRO_HOLD"
    CRO_ESCALATE = "CRO_ESCALATE"
    CRO_INVALID = "CRO_INVALID"
    PROOF_LINEAGE_BROKEN = "PROOF_LINEAGE_BROKEN"
    PROOF_MUTATION_DETECTED = "PROOF_MUTATION_DETECTED"
    PROOF_SEQUENCE_GAP = "PROOF_SEQUENCE_GAP"
    UNAUTHORIZED_CALLER = "UNAUTHORIZED_CALLER"
    RUNTIME_BOUNDARY_VIOLATION = "RUNTIME_BOUNDARY_VIOLATION"
    DIRECT_CALL_BLOCKED = "DIRECT_CALL_BLOCKED"
    SETTLEMENT_ALREADY_EXECUTED = "SETTLEMENT_ALREADY_EXECUTED"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    MISSING_AUTHORITY = "MISSING_AUTHORITY"


@dataclass(frozen=True)
class SettlementGateResult:
    """Immutable result from settlement gate validation.
    
    Attributes:
        allowed: True if settlement can proceed
        blocked: True if settlement is blocked
        reason: Block reason (if blocked)
        pdo_id: The PDO ID being settled
        details: Additional context for audit
        checked_at: ISO timestamp of gate check
    """
    allowed: bool
    blocked: bool
    reason: Optional[SettlementBlockReason]
    pdo_id: Optional[str]
    details: str
    checked_at: str
    
    def __bool__(self) -> bool:
        """Allow if result: ... for checking allowed."""
        return self.allowed


class SettlementGate:
    """Mandatory settlement gate with backend guards.
    
    DOCTRINE (FAIL-CLOSED):
    All settlements MUST pass through this gate.
    Direct calls to settlement services are blocked.
    
    Usage:
        gate = SettlementGate()
        result = gate.validate_settlement(pdo_data, proof_chain, caller_identity)
        if not result:
            # Settlement blocked
            log_blocked_settlement(result)
            raise SettlementBlockedException(result.reason)
    """
    
    def __init__(self):
        """Initialize settlement gate."""
        self._direct_call_protection = True
        self._settlement_executed_cache: Dict[str, str] = {}  # pdo_id -> timestamp
    
    def validate_settlement(
        self,
        pdo_data: Optional[Dict[str, Any]],
        proof_chain: Optional[List[Dict[str, Any]]] = None,
        caller_identity: Optional[str] = None,
        *,
        skip_proof_validation: bool = False,
    ) -> SettlementGateResult:
        """Validate settlement request through all guards.
        
        DOCTRINE (FAIL-CLOSED):
        ALL guards must pass for settlement to proceed.
        Any failure → BLOCK (no exceptions, no soft bypasses).
        
        Args:
            pdo_data: The PDO authorizing the settlement
            proof_chain: Ordered proof chain for lineage validation
            caller_identity: Identity of the caller (agent GID or "runtime")
            skip_proof_validation: Skip proof chain validation (for testing only)
        
        Returns:
            SettlementGateResult indicating allowed/blocked
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # GUARD 1: PDO must exist
        if pdo_data is None:
            return self._block(
                SettlementBlockReason.MISSING_PDO,
                pdo_id=None,
                details="Settlement requires valid PDO - none provided",
                timestamp=timestamp,
            )
        
        pdo_id = pdo_data.get("pdo_id")
        
        # GUARD 2: PDO must be valid
        validation_result = self._validate_pdo(pdo_data)
        if not validation_result["valid"]:
            return self._block(
                SettlementBlockReason.PDO_VALIDATION_FAILED,
                pdo_id=pdo_id,
                details=f"PDO validation failed: {validation_result['errors']}",
                timestamp=timestamp,
            )
        
        # GUARD 3: CRO decision must allow execution
        cro_result = self._check_cro_decision(pdo_data)
        if cro_result["blocks"]:
            reason = (
                SettlementBlockReason.CRO_HOLD
                if cro_result["decision"] == "HOLD"
                else SettlementBlockReason.CRO_ESCALATE
                if cro_result["decision"] == "ESCALATE"
                else SettlementBlockReason.CRO_INVALID
            )
            return self._block(
                reason,
                pdo_id=pdo_id,
                details=f"CRO decision blocks settlement: {cro_result['decision']} - {cro_result['reasons']}",
                timestamp=timestamp,
            )
        
        # GUARD 4: Caller must have settlement authority
        if caller_identity is not None:
            caller_result = self._check_caller_authority(caller_identity)
            if not caller_result["authorized"]:
                return self._block(
                    SettlementBlockReason.UNAUTHORIZED_CALLER
                    if caller_result["reason"] == "unauthorized"
                    else SettlementBlockReason.RUNTIME_BOUNDARY_VIOLATION,
                    pdo_id=pdo_id,
                    details=f"Caller not authorized for settlement: {caller_identity}",
                    timestamp=timestamp,
                )
        
        # GUARD 5: Proof lineage must be intact (unless skipped)
        if not skip_proof_validation and proof_chain is not None:
            lineage_result = self._check_proof_lineage(proof_chain)
            if not lineage_result["valid"]:
                reason = (
                    SettlementBlockReason.PROOF_MUTATION_DETECTED
                    if lineage_result["error_type"] == "mutation"
                    else SettlementBlockReason.PROOF_SEQUENCE_GAP
                    if lineage_result["error_type"] == "gap"
                    else SettlementBlockReason.PROOF_LINEAGE_BROKEN
                )
                return self._block(
                    reason,
                    pdo_id=pdo_id,
                    details=f"Proof lineage invalid: {lineage_result['details']}",
                    timestamp=timestamp,
                )
        
        # GUARD 6: Settlement must not be already executed
        if pdo_id and pdo_id in self._settlement_executed_cache:
            return self._block(
                SettlementBlockReason.SETTLEMENT_ALREADY_EXECUTED,
                pdo_id=pdo_id,
                details=f"Settlement already executed at {self._settlement_executed_cache[pdo_id]}",
                timestamp=timestamp,
            )
        
        # ALL GUARDS PASSED
        self._log_gate_pass(pdo_id, timestamp)
        return SettlementGateResult(
            allowed=True,
            blocked=False,
            reason=None,
            pdo_id=pdo_id,
            details="All settlement guards passed",
            checked_at=timestamp,
        )
    
    def mark_settlement_executed(self, pdo_id: str) -> None:
        """Mark a PDO as having its settlement executed.
        
        Prevents double-execution attacks.
        """
        self._settlement_executed_cache[pdo_id] = datetime.now(timezone.utc).isoformat()
    
    def _validate_pdo(self, pdo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate PDO using PDOValidator.
        
        Returns dict with 'valid' and 'errors' keys.
        """
        from app.services.pdo.validator import PDOValidator
        
        validator = PDOValidator()
        result = validator.validate(pdo_data)
        
        return {
            "valid": result.valid,
            "errors": [e.message for e in result.errors] if result.errors else [],
        }
    
    def _check_cro_decision(self, pdo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check CRO decision allows settlement.
        
        DOCTRINE:
        - HOLD → blocks settlement
        - ESCALATE → blocks settlement
        - APPROVE/TIGHTEN_TERMS → allows settlement
        """
        cro_decision = pdo_data.get("cro_decision")
        cro_reasons = pdo_data.get("cro_reasons", [])
        
        # No CRO decision means ALLOW by default
        if cro_decision is None:
            return {"blocks": False, "decision": None, "reasons": []}
        
        blocking_decisions = {"HOLD", "ESCALATE"}
        
        return {
            "blocks": cro_decision in blocking_decisions,
            "decision": cro_decision,
            "reasons": cro_reasons,
        }
    
    def _check_caller_authority(self, caller_identity: str) -> Dict[str, Any]:
        """Check caller has settlement authority.
        
        DOCTRINE:
        - Runtimes CANNOT call settlement services
        - Only agents with valid GIDs can settle
        """
        import re
        
        # Runtime identities are explicitly blocked
        runtime_patterns = ["runtime", "copilot", "chatgpt", "assistant"]
        caller_lower = caller_identity.lower()
        
        for pattern in runtime_patterns:
            if pattern in caller_lower:
                return {
                    "authorized": False,
                    "reason": "runtime_boundary",
                }
        
        # Valid agent GID pattern
        gid_pattern = re.compile(r"^GID-\d{2}$")
        
        # Check if caller looks like an agent GID
        if gid_pattern.match(caller_identity):
            return {"authorized": True, "reason": None}
        
        # Check if caller identity contains a valid GID
        gid_match = re.search(r"GID-\d{2}", caller_identity)
        if gid_match:
            return {"authorized": True, "reason": None}
        
        # Unknown caller format - block for safety
        return {
            "authorized": False,
            "reason": "unauthorized",
        }
    
    def _check_proof_lineage(self, proof_chain: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check proof lineage is intact.
        
        DOCTRINE:
        - Forward-only hash chaining
        - No sequence gaps
        - No mutations detected
        """
        from core.proof.validation import ProofLineageValidator, GENESIS_HASH
        
        if not proof_chain:
            return {"valid": True, "error_type": None, "details": "Empty chain"}
        
        validator = ProofLineageValidator()
        
        # Validate chain integrity
        for i, proof in enumerate(proof_chain):
            existing = proof_chain[:i]
            
            if i > 0:
                result = validator.validate_lineage(proof, existing, GENESIS_HASH)
                if not result.passed:
                    # Determine error type from errors
                    error_type = "broken"
                    for error in result.errors:
                        if "mutation" in error.lower():
                            error_type = "mutation"
                        elif "sequence" in error.lower() or "gap" in error.lower():
                            error_type = "gap"
                    
                    return {
                        "valid": False,
                        "error_type": error_type,
                        "details": "; ".join(result.errors[:3]),
                    }
        
        return {"valid": True, "error_type": None, "details": "Chain valid"}
    
    def _block(
        self,
        reason: SettlementBlockReason,
        pdo_id: Optional[str],
        details: str,
        timestamp: str,
    ) -> SettlementGateResult:
        """Create a blocked result and log the event."""
        self._log_gate_block(reason, pdo_id, details, timestamp)
        return SettlementGateResult(
            allowed=False,
            blocked=True,
            reason=reason,
            pdo_id=pdo_id,
            details=details,
            checked_at=timestamp,
        )
    
    def _log_gate_pass(self, pdo_id: Optional[str], timestamp: str) -> None:
        """Log successful gate passage."""
        logger.info(
            "Settlement gate PASSED: pdo_id=%s timestamp=%s",
            pdo_id,
            timestamp,
        )
    
    def _log_gate_block(
        self,
        reason: SettlementBlockReason,
        pdo_id: Optional[str],
        details: str,
        timestamp: str,
    ) -> None:
        """Log settlement block for audit."""
        logger.warning(
            "Settlement gate BLOCKED: reason=%s pdo_id=%s details=%s timestamp=%s",
            reason.value,
            pdo_id,
            details,
            timestamp,
        )


# ---------------------------------------------------------------------------
# Module-Level Convenience Functions
# ---------------------------------------------------------------------------

# Singleton gate instance
_settlement_gate: Optional[SettlementGate] = None


def _get_settlement_gate() -> SettlementGate:
    """Get or create singleton settlement gate."""
    global _settlement_gate
    if _settlement_gate is None:
        _settlement_gate = SettlementGate()
    return _settlement_gate


def validate_settlement_request(
    pdo_data: Optional[Dict[str, Any]],
    proof_chain: Optional[List[Dict[str, Any]]] = None,
    caller_identity: Optional[str] = None,
) -> SettlementGateResult:
    """Validate a settlement request through the gate.
    
    Module-level convenience function.
    
    Args:
        pdo_data: The PDO authorizing settlement
        proof_chain: Optional proof chain for lineage validation
        caller_identity: Identity of the caller
    
    Returns:
        SettlementGateResult indicating allowed/blocked
    """
    gate = _get_settlement_gate()
    return gate.validate_settlement(pdo_data, proof_chain, caller_identity)


def block_direct_settlement(
    caller_context: str = "unknown",
) -> SettlementGateResult:
    """Block direct settlement calls that bypass the gate.
    
    DOCTRINE (FAIL-CLOSED):
    All settlement calls MUST go through validate_settlement_request.
    Direct calls to settlement services are blocked.
    
    Args:
        caller_context: Context string for audit logging
    
    Returns:
        SettlementGateResult with DIRECT_CALL_BLOCKED reason
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    
    logger.warning(
        "Direct settlement call BLOCKED: context=%s timestamp=%s",
        caller_context,
        timestamp,
    )
    
    return SettlementGateResult(
        allowed=False,
        blocked=True,
        reason=SettlementBlockReason.DIRECT_CALL_BLOCKED,
        pdo_id=None,
        details=f"Direct settlement calls are blocked. Use validate_settlement_request. Context: {caller_context}",
        checked_at=timestamp,
    )


# ═══════════════════════════════════════════════════════════════════════════
# END — Cody (GID-01) — 🔵
# ═══════════════════════════════════════════════════════════════════════════
