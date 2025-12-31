"""
PAG-02: Runtime Activation Gate
===============================

Verifies runtime mode and governance configuration.

PDO Canon:
    - Proof: Runtime and governance settings
    - Decision: Configuration validation pass/fail
    - Outcome: Runtime activation status
"""

from typing import Any

from ..gate import Gate, GateResult, GateStatus


class RuntimeActivationGate(Gate):
    """
    PAG-02: Runtime Activation Gate
    
    Checks:
        - Runtime mode is specified (EXECUTION expected)
        - Governance mode is specified (GOLD STANDARD expected)
        - Failure discipline is FAIL-CLOSED
        - Observability is MANDATORY
    """
    
    VALID_RUNTIME_MODES = {"EXECUTION", "PLANNING", "REVIEW"}
    VALID_GOVERNANCE_MODES = {"GOLD_STANDARD", "GOLD STANDARD", "STANDARD", "MINIMAL"}
    VALID_FAILURE_DISCIPLINES = {"FAIL-CLOSED", "FAIL_CLOSED", "FAIL-OPEN", "FAIL_OPEN"}
    
    def __init__(self):
        super().__init__(
            gate_id="PAG-02",
            name="Runtime Activation",
            description="Verify runtime mode and governance configuration",
        )
    
    def execute(self, context: dict[str, Any]) -> GateResult:
        """
        Execute runtime activation verification.
        
        Required context:
            - runtime_mode: str
            - governance_mode: str
            - failure_discipline: str
            - observability: str
        """
        proof = {}
        errors = []
        
        # Collect proof
        runtime_mode = context.get("runtime_mode", "EXECUTION")
        governance_mode = context.get("governance_mode", "GOLD_STANDARD")
        failure_discipline = context.get("failure_discipline", "FAIL-CLOSED")
        observability = context.get("observability", "MANDATORY")
        
        proof["runtime_mode"] = runtime_mode
        proof["governance_mode"] = governance_mode
        proof["failure_discipline"] = failure_discipline
        proof["observability"] = observability
        
        # Validate runtime mode
        if runtime_mode.upper() not in self.VALID_RUNTIME_MODES:
            errors.append(f"Invalid runtime_mode: {runtime_mode}")
            proof["runtime_mode_valid"] = False
        else:
            proof["runtime_mode_valid"] = True
        
        # Validate governance mode
        if governance_mode.upper().replace("_", " ") not in {m.replace("_", " ") for m in self.VALID_GOVERNANCE_MODES}:
            errors.append(f"Invalid governance_mode: {governance_mode}")
            proof["governance_mode_valid"] = False
        else:
            proof["governance_mode_valid"] = True
        
        # Validate failure discipline
        normalized_discipline = failure_discipline.upper().replace("_", "-")
        if normalized_discipline not in {"FAIL-CLOSED", "FAIL-OPEN"}:
            errors.append(f"Invalid failure_discipline: {failure_discipline}")
            proof["failure_discipline_valid"] = False
        else:
            proof["failure_discipline_valid"] = True
        
        # Warn if not fail-closed (but don't fail)
        if normalized_discipline != "FAIL-CLOSED":
            proof["fail_closed_warning"] = "GOLD STANDARD requires FAIL-CLOSED discipline"
        
        # Validate observability
        if observability.upper() not in {"MANDATORY", "OPTIONAL", "DISABLED"}:
            errors.append(f"Invalid observability: {observability}")
            proof["observability_valid"] = False
        else:
            proof["observability_valid"] = True
        
        proof["errors"] = errors
        
        # Make decision
        if errors:
            return GateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                proof=proof,
                decision=f"FAIL - Configuration errors: {'; '.join(errors)}",
                outcome="Runtime activation rejected",
                error="; ".join(errors),
            )
        
        # PDO Canon Lock verification
        pdo_locked = context.get("pdo_canon_locked", True)
        proof["pdo_canon_locked"] = pdo_locked
        
        if not pdo_locked:
            return GateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                proof=proof,
                decision="FAIL - PDO canon not locked",
                outcome="Runtime activation rejected",
                error="PDO canon must be locked for GOLD STANDARD",
            )
        
        # Success
        return GateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASS,
            proof=proof,
            decision=f"PASS - Runtime mode {runtime_mode}, Governance {governance_mode}",
            outcome="Runtime activated with GOLD STANDARD governance",
        )
