"""
OCC Governance Approval Gate Middleware

Implements operator approval gates for governance-controlled actions.
Wires into the OCC request pipeline to enforce governance constraints.

DOCTRINE REFERENCE: DOCTRINE-FULL-SWARM-EXECUTION-001
PAC REFERENCE: PAC-JEFFREY-OCC-GOVERNANCE-INTEGRATION-01

INVARIANTS:
- INV-OCC-001: Control > Autonomy
- INV-OCC-002: Proof > Execution
- INV-OCC-003: Human authority final

Authors:
- PAX (GID-05) - Operator Workflow Design
- SAM (GID-06) - OCC Threat Modeling
- DAN (GID-07) - OCC CI / Runtime Hooks
- ALEX (GID-08) - Governance Guardrails
"""

import json
import logging
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class GateType(Enum):
    """Types of governance gates."""
    PROOF_REQUIRED = "PROOF_REQUIRED"
    AUTHORITY_REQUIRED = "AUTHORITY_REQUIRED"
    DUAL_APPROVAL = "DUAL_APPROVAL"
    SCRAM_ENABLED = "SCRAM_ENABLED"


class GateStatus(Enum):
    """Gate enforcement status."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PENDING = "PENDING"
    OVERRIDDEN = "OVERRIDDEN"


@dataclass
class GateContext:
    """Context for gate evaluation."""
    operator_gid: str
    action: str
    resource: str
    proof_hash: Optional[str] = None
    authority_gid: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GateResult:
    """Result of gate evaluation."""
    passed: bool
    gate_type: GateType
    status: GateStatus
    reason: str
    required_action: Optional[str] = None
    timeout_seconds: Optional[int] = None


class ApprovalGate:
    """
    Individual approval gate implementation.
    Each gate enforces a specific governance constraint.
    """
    
    def __init__(self, gate_id: str, gate_type: GateType, config: Dict[str, Any]):
        self.gate_id = gate_id
        self.gate_type = gate_type
        self.config = config
        self.logger = logging.getLogger(f"occ.gate.{gate_id}")
        self.evaluation_log: List[Dict] = []
    
    def evaluate(self, context: GateContext) -> GateResult:
        """Evaluate if context passes this gate."""
        raise NotImplementedError("Subclasses must implement evaluate()")
    
    def _log_evaluation(self, context: GateContext, result: GateResult):
        """Log gate evaluation for audit."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "gate_id": self.gate_id,
            "operator_gid": context.operator_gid,
            "action": context.action,
            "passed": result.passed,
            "reason": result.reason
        }
        self.evaluation_log.append(entry)
        self.logger.info(f"GATE_EVAL: {json.dumps(entry)}")


class ProofRequirementGate(ApprovalGate):
    """
    Gate enforcing proof artifact requirement.
    INV-OCC-002: Proof > Execution
    """
    
    def __init__(self, gate_id: str, config: Dict[str, Any]):
        super().__init__(gate_id, GateType.PROOF_REQUIRED, config)
        self.proof_required_actions = config.get("proof_required_actions", [])
    
    def evaluate(self, context: GateContext) -> GateResult:
        """Check if proof is provided for actions requiring it."""
        action_requires_proof = context.action.upper() in [a.upper() for a in self.proof_required_actions]
        
        if not action_requires_proof:
            result = GateResult(
                passed=True,
                gate_type=self.gate_type,
                status=GateStatus.OPEN,
                reason="Action does not require proof"
            )
        elif context.proof_hash:
            # Verify proof hash format (basic validation)
            if len(context.proof_hash) >= 32:
                result = GateResult(
                    passed=True,
                    gate_type=self.gate_type,
                    status=GateStatus.OPEN,
                    reason="Valid proof hash provided"
                )
            else:
                result = GateResult(
                    passed=False,
                    gate_type=self.gate_type,
                    status=GateStatus.CLOSED,
                    reason="Invalid proof hash format",
                    required_action="Provide valid SHA-256 proof hash"
                )
        else:
            result = GateResult(
                passed=False,
                gate_type=self.gate_type,
                status=GateStatus.PENDING,
                reason="Proof artifact required for this action",
                required_action="Submit proof hash via proof_hash parameter"
            )
        
        self._log_evaluation(context, result)
        return result


class AuthorityRequirementGate(ApprovalGate):
    """
    Gate enforcing authority-level approval.
    INV-OCC-003: Human authority final
    CONS-OCC-002: No override without Architect authority
    """
    
    def __init__(self, gate_id: str, config: Dict[str, Any]):
        super().__init__(gate_id, GateType.AUTHORITY_REQUIRED, config)
        self.authority_map = config.get("authority_map", {})
        self.architect_gid = config.get("architect_gid", "JEFFREY")
    
    def evaluate(self, context: GateContext) -> GateResult:
        """Check if appropriate authority has approved action."""
        action_upper = context.action.upper()
        required_authority = self.authority_map.get(action_upper)
        
        if not required_authority:
            result = GateResult(
                passed=True,
                gate_type=self.gate_type,
                status=GateStatus.OPEN,
                reason="Action does not require specific authority"
            )
        elif context.authority_gid:
            # Check if authority matches or is architect (supreme authority)
            authority_valid = (
                context.authority_gid.upper() == required_authority.upper() or
                context.authority_gid.upper() == self.architect_gid.upper()
            )
            
            if authority_valid:
                result = GateResult(
                    passed=True,
                    gate_type=self.gate_type,
                    status=GateStatus.OPEN,
                    reason=f"Authorized by {context.authority_gid}"
                )
            else:
                result = GateResult(
                    passed=False,
                    gate_type=self.gate_type,
                    status=GateStatus.CLOSED,
                    reason=f"Insufficient authority: {context.authority_gid} cannot authorize, requires {required_authority}",
                    required_action=f"Obtain approval from {required_authority}"
                )
        else:
            result = GateResult(
                passed=False,
                gate_type=self.gate_type,
                status=GateStatus.PENDING,
                reason=f"Action requires authorization from {required_authority}",
                required_action=f"Request approval from {required_authority}",
                timeout_seconds=3600  # 1 hour timeout for pending approvals
            )
        
        self._log_evaluation(context, result)
        return result


class DualApprovalGate(ApprovalGate):
    """
    Gate requiring dual approval for critical actions.
    Implements separation of duties for LAW_TIER operations.
    """
    
    def __init__(self, gate_id: str, config: Dict[str, Any]):
        super().__init__(gate_id, GateType.DUAL_APPROVAL, config)
        self.dual_approval_actions = config.get("dual_approval_actions", [])
    
    def evaluate(self, context: GateContext) -> GateResult:
        """Check if dual approval is present."""
        action_requires_dual = context.action.upper() in [a.upper() for a in self.dual_approval_actions]
        
        if not action_requires_dual:
            return GateResult(
                passed=True,
                gate_type=self.gate_type,
                status=GateStatus.OPEN,
                reason="Action does not require dual approval"
            )
        
        # Check for dual approval in metadata
        approvals = context.metadata.get("approvals", [])
        unique_approvers = set(a.get("gid") for a in approvals if a.get("gid"))
        
        if len(unique_approvers) >= 2:
            return GateResult(
                passed=True,
                gate_type=self.gate_type,
                status=GateStatus.OPEN,
                reason=f"Dual approval present: {', '.join(unique_approvers)}"
            )
        
        return GateResult(
            passed=False,
            gate_type=self.gate_type,
            status=GateStatus.PENDING,
            reason="Dual approval required for this action",
            required_action="Obtain approval from second authorized party"
        )


class ApprovalGatePipeline:
    """
    Pipeline of approval gates.
    Actions must pass ALL gates to proceed.
    """
    
    def __init__(self, pipeline_id: str):
        self.pipeline_id = pipeline_id
        self.gates: List[ApprovalGate] = []
        self.logger = logging.getLogger(f"occ.gate.pipeline.{pipeline_id}")
    
    def add_gate(self, gate: ApprovalGate):
        """Add gate to pipeline."""
        self.gates.append(gate)
        self.logger.info(f"Added gate {gate.gate_id} to pipeline")
    
    def evaluate(self, context: GateContext) -> Tuple[bool, List[GateResult]]:
        """
        Evaluate all gates in pipeline.
        Returns (all_passed, list_of_results).
        """
        results = []
        all_passed = True
        
        for gate in self.gates:
            result = gate.evaluate(context)
            results.append(result)
            
            if not result.passed:
                all_passed = False
                # Continue evaluating to collect all failures
        
        self.logger.info(
            f"Pipeline {self.pipeline_id} evaluation: "
            f"{'PASSED' if all_passed else 'FAILED'} "
            f"({len([r for r in results if r.passed])}/{len(results)} gates)"
        )
        
        return all_passed, results


def create_default_pipeline() -> ApprovalGatePipeline:
    """
    Create the default OCC governance gate pipeline.
    Implements all doctrine constraints.
    """
    pipeline = ApprovalGatePipeline("occ-governance-default")
    
    # Gate 1: Proof Requirement (INV-OCC-002)
    proof_gate = ProofRequirementGate(
        "GATE-PROOF-001",
        {
            "proof_required_actions": [
                "PAC_EXECUTION",
                "PROMOTION",
                "DOCTRINE_MODIFICATION",
                "SCRAM_TRIGGER",
                "AGENT_OVERRIDE",
                "TIER_ESCALATION"
            ]
        }
    )
    pipeline.add_gate(proof_gate)
    
    # Gate 2: Authority Requirement (INV-OCC-003, CONS-OCC-002)
    authority_gate = AuthorityRequirementGate(
        "GATE-AUTH-001",
        {
            "authority_map": {
                "DOCTRINE_MODIFICATION": "JEFFREY",
                "SCRAM_TRIGGER": "GID-00",
                "PROMOTION": "JEFFREY",
                "AGENT_OVERRIDE": "GID-00"
            },
            "architect_gid": "JEFFREY"
        }
    )
    pipeline.add_gate(authority_gate)
    
    # Gate 3: Dual Approval for critical operations
    dual_gate = DualApprovalGate(
        "GATE-DUAL-001",
        {
            "dual_approval_actions": [
                "DOCTRINE_MODIFICATION",
                "EMERGENCY_PROMOTION"
            ]
        }
    )
    pipeline.add_gate(dual_gate)
    
    return pipeline


# ══════════════════════════════════════════════════════════════════════════════
# DECORATOR FOR ROUTE PROTECTION
# ══════════════════════════════════════════════════════════════════════════════

def require_governance_approval(
    action: str,
    resource: str,
    pipeline: Optional[ApprovalGatePipeline] = None
):
    """
    Decorator to enforce governance gates on API routes.
    
    Usage:
        @require_governance_approval("PAC_EXECUTION", "active_pacs")
        async def execute_pac(request: PACRequest):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract operator GID from request (implementation depends on auth system)
            operator_gid = kwargs.get("operator_gid", "UNKNOWN")
            proof_hash = kwargs.get("proof_hash")
            authority_gid = kwargs.get("authority_gid")
            
            context = GateContext(
                operator_gid=operator_gid,
                action=action,
                resource=resource,
                proof_hash=proof_hash,
                authority_gid=authority_gid
            )
            
            gate_pipeline = pipeline or create_default_pipeline()
            passed, results = gate_pipeline.evaluate(context)
            
            if not passed:
                # Collect failure reasons
                failures = [r for r in results if not r.passed]
                failure_reasons = [f.reason for f in failures]
                
                # Return gate failure response
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "GOVERNANCE_GATE_FAILED",
                        "failures": failure_reasons,
                        "required_actions": [f.required_action for f in failures if f.required_action]
                    }
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Module-level default pipeline
_default_pipeline: Optional[ApprovalGatePipeline] = None


def get_default_pipeline() -> ApprovalGatePipeline:
    """Get or create the default gate pipeline."""
    global _default_pipeline
    if _default_pipeline is None:
        _default_pipeline = create_default_pipeline()
    return _default_pipeline


if __name__ == "__main__":
    # Self-test
    print("OCC Approval Gate Middleware - Self Test")
    print("=" * 50)
    
    pipeline = create_default_pipeline()
    
    # Test 1: Action without requirements
    ctx1 = GateContext(
        operator_gid="GID-01",
        action="READ_STATUS",
        resource="dashboard"
    )
    passed, results = pipeline.evaluate(ctx1)
    print(f"Test 1 (no requirements): {'PASS' if passed else 'FAIL'}")
    
    # Test 2: Action requiring proof without proof
    ctx2 = GateContext(
        operator_gid="GID-01",
        action="PAC_EXECUTION",
        resource="PAC-001"
    )
    passed, results = pipeline.evaluate(ctx2)
    print(f"Test 2 (needs proof, none provided): {'PASS' if not passed else 'FAIL'}")
    
    # Test 3: Action requiring authority without authority
    ctx3 = GateContext(
        operator_gid="GID-01",
        action="DOCTRINE_MODIFICATION",
        resource="doctrine",
        proof_hash="a" * 64
    )
    passed, results = pipeline.evaluate(ctx3)
    print(f"Test 3 (needs authority, none provided): {'PASS' if not passed else 'FAIL'}")
    
    # Test 4: Fully authorized action
    ctx4 = GateContext(
        operator_gid="GID-01",
        action="DOCTRINE_MODIFICATION",
        resource="doctrine",
        proof_hash="a" * 64,
        authority_gid="JEFFREY",
        metadata={"approvals": [{"gid": "JEFFREY"}, {"gid": "GID-00"}]}
    )
    passed, results = pipeline.evaluate(ctx4)
    print(f"Test 4 (fully authorized): {'PASS' if passed else 'FAIL'}")
    
    print("\n✓ OCC Approval Gate Middleware Loaded")
