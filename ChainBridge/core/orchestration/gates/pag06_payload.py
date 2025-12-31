"""
PAG-06: Payload Gate
====================

Authorizes and validates the execution payload.

PDO Canon:
    - Proof: Payload specification and requirements
    - Decision: Payload authorization pass/fail
    - Outcome: Payload ready for execution
"""

from typing import Any

from ..gate import Gate, GateResult, GateStatus


class PayloadGate(Gate):
    """
    PAG-06: Payload Gate
    
    Checks:
        - Payload type is specified
        - Payload purpose is defined
        - Execution requirements are met
        - All prior gates (PAG-01 through PAG-05) passed
    """
    
    VALID_PAYLOAD_TYPES = {
        "orchestration",
        "backend_implementation",
        "frontend_implementation",
        "research",
        "governance",
        "testing",
        "deployment",
        "audit",
    }
    
    def __init__(self):
        super().__init__(
            gate_id="PAG-06",
            name="Payload Gate",
            description="Authorize and validate execution payload",
        )
    
    def execute(self, context: dict[str, Any]) -> GateResult:
        """
        Execute payload authorization.
        
        Required context:
            - payload_type: str
            - payload_purpose: str
            - execution_requirements: list[str] (optional)
        """
        proof = {}
        errors = []
        
        # Collect proof
        payload_type = context.get("payload_type", "orchestration")
        payload_purpose = context.get("payload_purpose", "")
        execution_requirements = context.get("execution_requirements", [])
        
        proof["payload_type"] = payload_type
        proof["payload_purpose"] = payload_purpose
        proof["execution_requirements"] = execution_requirements
        
        # Validate payload type
        payload_type_normalized = payload_type.lower().replace(" ", "_")
        if payload_type_normalized not in self.VALID_PAYLOAD_TYPES:
            # Allow custom types if purpose is specified
            if not payload_purpose:
                errors.append(f"Unknown payload type '{payload_type}' requires payload_purpose")
            proof["payload_type_standard"] = False
        else:
            proof["payload_type_standard"] = True
        
        # Validate payload purpose
        if not payload_purpose:
            errors.append("payload_purpose is required")
            proof["purpose_specified"] = False
        else:
            proof["purpose_specified"] = True
        
        # Verify prior gates passed (PAG-01 through PAG-05)
        prior_gates = ["PAG-01", "PAG-02", "PAG-03", "PAG-04", "PAG-05"]
        prior_gate_status = {}
        
        for gate_id in prior_gates:
            result_key = f"gate_{gate_id}_result"
            gate_result = context.get(result_key, {})
            status = gate_result.get("status", "UNKNOWN")
            prior_gate_status[gate_id] = status
            
            if status != "PASS":
                errors.append(f"Prior gate {gate_id} did not pass (status: {status})")
        
        proof["prior_gate_status"] = prior_gate_status
        
        # Validate execution requirements
        if execution_requirements:
            unmet_requirements = []
            for req in execution_requirements:
                # Check if requirement is satisfied in context
                req_key = req.lower().replace(" ", "_").replace("-", "_")
                if not context.get(req_key, True):  # Default to True if not specified
                    unmet_requirements.append(req)
            
            proof["unmet_requirements"] = unmet_requirements
            
            if unmet_requirements:
                errors.append(f"Unmet requirements: {', '.join(unmet_requirements)}")
        
        proof["errors"] = errors
        
        # Make decision
        if errors:
            return GateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                proof=proof,
                decision=f"FAIL - Payload authorization failed: {'; '.join(errors)}",
                outcome="Payload rejected",
                error="; ".join(errors),
            )
        
        # Success
        return GateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASS,
            proof=proof,
            decision=f"PASS - Payload type '{payload_type}' authorized",
            outcome=f"Payload ready: {payload_purpose}",
        )
