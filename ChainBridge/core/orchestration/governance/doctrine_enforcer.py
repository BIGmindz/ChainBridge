#!/usr/bin/env python3
"""
OCC Governance Enforcement Module

This module binds the full-swarm governance doctrine into the OCC backend,
enforcing constitutional controls at the operator interface layer.

DOCTRINE REFERENCE: DOCTRINE-FULL-SWARM-EXECUTION-001
CLASSIFICATION: LAW_TIER

INVARIANTS ENFORCED:
- INV-OCC-001: Control > Autonomy
- INV-OCC-002: Proof > Execution
- INV-OCC-003: Human authority final

Authors:
- CODY (GID-01) - Backend OCC Integration
- CINDY (GID-04) - Governance Backend Hardening
- ATLAS (GID-11) - Refactor & Wiring

Created: 2026-01-13
PAC Reference: PAC-JEFFREY-OCC-GOVERNANCE-INTEGRATION-01
"""

import json
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class GovernanceTier(Enum):
    """Governance classification tiers."""
    LAW = "LAW_TIER"
    POLICY = "POLICY_TIER"
    PROCEDURE = "PROCEDURE_TIER"


class EnforcementMode(Enum):
    """Enforcement mode for governance actions."""
    HARD = "HARD"           # Immediate rejection on violation
    SOFT = "SOFT"           # Warning with logging
    AUDIT = "AUDIT_ONLY"    # Log only, no enforcement


class ActionStatus(Enum):
    """Status of governance-controlled actions."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    AWAITING_PROOF = "AWAITING_PROOF"
    AWAITING_AUTHORITY = "AWAITING_AUTHORITY"


@dataclass
class GovernanceContext:
    """Context for governance-controlled operations."""
    operator_gid: str
    action_type: str
    target_resource: str
    requested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    proof_hash: Optional[str] = None
    authority_required: bool = False
    authority_gid: Optional[str] = None


@dataclass
class EnforcementResult:
    """Result of governance enforcement check."""
    allowed: bool
    status: ActionStatus
    reason: str
    proof_required: bool = False
    authority_required: bool = False
    audit_entry: Optional[Dict] = None


class DoctrineEnforcer:
    """
    Enforces full-swarm governance doctrine at the OCC layer.
    
    This is the core enforcement engine that validates all operator
    actions against the locked doctrine principles.
    """
    
    DOCTRINE_FILE = "core/governance/DOCTRINE_FULL_SWARM_EXECUTION.json"
    LEDGER_FILE = "core/governance/SOVEREIGNTY_LEDGER.json"
    
    def __init__(self, governance_root: Optional[Path] = None):
        self.governance_root = governance_root or Path(__file__).parent.parent.parent.parent.parent
        self.logger = self._setup_logging()
        self.doctrine = self._load_doctrine()
        self.audit_log: List[Dict] = []
        
    def _setup_logging(self) -> logging.Logger:
        """Configure enforcement logging."""
        logger = logging.getLogger("occ.governance.enforcer")
        logger.setLevel(logging.INFO)
        return logger
    
    def _load_doctrine(self) -> Dict:
        """Load locked doctrine from file."""
        doctrine_path = self.governance_root / self.DOCTRINE_FILE
        
        if not doctrine_path.exists():
            self.logger.error("Doctrine file not found: %s", doctrine_path)
            # FAIL_CLOSED: No doctrine = no operations permitted
            return {"locked": False, "principles": {}}
        
        with open(doctrine_path, encoding="utf-8") as f:
            return json.load(f)
    
    def _log_audit(self, action: str, context: GovernanceContext, result: EnforcementResult) -> Dict:
        """Create immutable audit entry for enforcement action."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "operator_gid": context.operator_gid,
            "action_type": context.action_type,
            "target_resource": context.target_resource,
            "result": result.status.value,
            "reason": result.reason,
            "proof_hash": context.proof_hash,
            "authority_gid": context.authority_gid,
            "entry_hash": self._compute_audit_hash(action, context, result)
        }
        self.audit_log.append(entry)
        self.logger.info(f"AUDIT: {json.dumps(entry)}")
        return entry
    
    def _compute_audit_hash(self, action: str, context: GovernanceContext, result: EnforcementResult) -> str:
        """Compute SHA-256 hash for audit entry integrity."""
        content = f"{action}|{context.operator_gid}|{context.action_type}|{result.status.value}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def check_doctrine_locked(self) -> bool:
        """Verify doctrine is locked before any operation."""
        attestation = self.doctrine.get("attestation", {})
        return "LOCKED" in attestation.get("statement", "")
    
    def validate_gid(self, gid: str) -> bool:
        """
        Validate GID exists and is authorized.
        INV-003: IDENTITY_BINDING enforced.
        """
        valid_gids = [f"GID-{i:02d}" for i in range(13)]  # GID-00 through GID-12
        valid_gids.append("JEFFREY")  # Architect
        return gid in valid_gids or gid.upper() == "JEFFREY"
    
    def check_proof_requirement(self, action_type: str) -> bool:
        """
        Check if action requires proof artifact.
        INV-OCC-002: Proof > Execution
        """
        proof_required_actions = [
            "PAC_EXECUTION",
            "PROMOTION",
            "DOCTRINE_MODIFICATION",
            "SCRAM_TRIGGER",
            "AGENT_OVERRIDE",
            "TIER_ESCALATION"
        ]
        return action_type.upper() in proof_required_actions
    
    def check_authority_requirement(self, action_type: str, tier: GovernanceTier) -> Tuple[bool, str]:
        """
        Check if action requires specific authority level.
        INV-OCC-003: Human authority final
        """
        if tier == GovernanceTier.LAW:
            return True, "JEFFREY"  # Architect only
        
        authority_actions = {
            "DOCTRINE_MODIFICATION": "JEFFREY",
            "SCRAM_TRIGGER": "GID-00",
            "PROMOTION": "JEFFREY",
            "AGENT_OVERRIDE": "GID-00"
        }
        
        if action_type.upper() in authority_actions:
            return True, authority_actions[action_type.upper()]
        
        return False, ""
    
    def enforce(self, context: GovernanceContext, tier: GovernanceTier = GovernanceTier.PROCEDURE) -> EnforcementResult:
        """
        Main enforcement entry point.
        All OCC actions MUST pass through this gate.
        """
        # FAIL_CLOSED: Doctrine must be locked
        if not self.check_doctrine_locked():
            result = EnforcementResult(
                allowed=False,
                status=ActionStatus.REJECTED,
                reason="FAIL_CLOSED: Doctrine not locked"
            )
            self._log_audit("ENFORCE_FAIL_CLOSED", context, result)
            return result
        
        # Validate operator GID
        if not self.validate_gid(context.operator_gid):
            result = EnforcementResult(
                allowed=False,
                status=ActionStatus.REJECTED,
                reason=f"INVALID_GID: {context.operator_gid} not recognized"
            )
            self._log_audit("ENFORCE_INVALID_GID", context, result)
            return result
        
        # Check proof requirement
        proof_required = self.check_proof_requirement(context.action_type)
        if proof_required and not context.proof_hash:
            result = EnforcementResult(
                allowed=False,
                status=ActionStatus.AWAITING_PROOF,
                reason="PROOF_REQUIRED: Action requires proof artifact",
                proof_required=True
            )
            self._log_audit("ENFORCE_AWAITING_PROOF", context, result)
            return result
        
        # Check authority requirement
        authority_required, required_gid = self.check_authority_requirement(context.action_type, tier)
        if authority_required:
            if not context.authority_gid:
                result = EnforcementResult(
                    allowed=False,
                    status=ActionStatus.AWAITING_AUTHORITY,
                    reason=f"AUTHORITY_REQUIRED: Requires authorization from {required_gid}",
                    authority_required=True
                )
                self._log_audit("ENFORCE_AWAITING_AUTHORITY", context, result)
                return result
            
            # Validate authority GID matches requirement
            if context.authority_gid.upper() != required_gid.upper() and context.authority_gid.upper() != "JEFFREY":
                result = EnforcementResult(
                    allowed=False,
                    status=ActionStatus.REJECTED,
                    reason=f"INSUFFICIENT_AUTHORITY: {context.authority_gid} cannot authorize, requires {required_gid}"
                )
                self._log_audit("ENFORCE_INSUFFICIENT_AUTHORITY", context, result)
                return result
        
        # All checks passed
        result = EnforcementResult(
            allowed=True,
            status=ActionStatus.APPROVED,
            reason="All governance gates passed"
        )
        audit_entry = self._log_audit("ENFORCE_APPROVED", context, result)
        result.audit_entry = audit_entry
        
        return result
    
    def get_governance_state(self) -> Dict:
        """
        Get current governance state for OCC display.
        Returns real-time governance status.
        """
        return {
            "doctrine_id": self.doctrine.get("doctrine_id", "UNKNOWN"),
            "doctrine_locked": self.check_doctrine_locked(),
            "principles": list(self.doctrine.get("core_principles", {}).keys()),
            "invariants": list(self.doctrine.get("invariants", {}).keys()),
            "constraints": list(self.doctrine.get("constraints", {}).keys()),
            "enforcement_mode": EnforcementMode.HARD.value,
            "audit_entries": len(self.audit_log),
            "last_check": datetime.now(timezone.utc).isoformat()
        }


class OCCGovernanceGate:
    """
    Operator approval gate for OCC actions.
    Implements the operator-facing governance interface.
    """
    
    def __init__(self, enforcer: DoctrineEnforcer):
        self.enforcer = enforcer
        self.pending_approvals: Dict[str, GovernanceContext] = {}
        self.logger = logging.getLogger("occ.governance.gate")
    
    def request_action(self, context: GovernanceContext, tier: GovernanceTier = GovernanceTier.PROCEDURE) -> EnforcementResult:
        """
        Request an action through the governance gate.
        This is the primary operator entry point.
        """
        result = self.enforcer.enforce(context, tier)
        
        if result.status == ActionStatus.AWAITING_AUTHORITY:
            # Queue for approval
            request_id = hashlib.sha256(
                f"{context.operator_gid}:{context.action_type}:{datetime.now().isoformat()}".encode()
            ).hexdigest()[:12]
            
            self.pending_approvals[request_id] = context
            self.logger.info(f"Action queued for approval: {request_id}")
            result.audit_entry = {"request_id": request_id}
        
        return result
    
    def approve_action(self, request_id: str, authority_gid: str) -> EnforcementResult:
        """
        Approve a pending action.
        Only authorized GIDs can approve.
        """
        if request_id not in self.pending_approvals:
            return EnforcementResult(
                allowed=False,
                status=ActionStatus.REJECTED,
                reason=f"Request {request_id} not found"
            )
        
        context = self.pending_approvals[request_id]
        context.authority_gid = authority_gid
        
        result = self.enforcer.enforce(context)
        
        if result.allowed:
            del self.pending_approvals[request_id]
        
        return result
    
    def reject_action(self, request_id: str, authority_gid: str, reason: str) -> EnforcementResult:
        """Reject a pending action."""
        if request_id not in self.pending_approvals:
            return EnforcementResult(
                allowed=False,
                status=ActionStatus.REJECTED,
                reason=f"Request {request_id} not found"
            )
        
        del self.pending_approvals[request_id]
        
        return EnforcementResult(
            allowed=False,
            status=ActionStatus.REJECTED,
            reason=f"Rejected by {authority_gid}: {reason}"
        )
    
    def get_pending_approvals(self) -> List[Dict]:
        """Get list of pending approval requests."""
        return [
            {
                "request_id": rid,
                "operator_gid": ctx.operator_gid,
                "action_type": ctx.action_type,
                "target_resource": ctx.target_resource,
                "requested_at": ctx.requested_at
            }
            for rid, ctx in self.pending_approvals.items()
        ]


# Module-level singleton
_enforcer: Optional[DoctrineEnforcer] = None
_gate: Optional[OCCGovernanceGate] = None


def get_enforcer() -> DoctrineEnforcer:
    """Get or create the doctrine enforcer singleton."""
    global _enforcer
    if _enforcer is None:
        _enforcer = DoctrineEnforcer()
    return _enforcer


def get_gate() -> OCCGovernanceGate:
    """Get or create the governance gate singleton."""
    global _gate
    if _gate is None:
        _gate = OCCGovernanceGate(get_enforcer())
    return _gate


if __name__ == "__main__":
    # Self-test
    print("OCC Governance Enforcer - Self Test")
    print("=" * 50)
    
    enforcer = get_enforcer()
    state = enforcer.get_governance_state()
    
    print(f"Doctrine ID: {state['doctrine_id']}")
    print(f"Doctrine Locked: {state['doctrine_locked']}")
    print(f"Enforcement Mode: {state['enforcement_mode']}")
    print("✓ OCC Governance Enforcement Module Loaded")
