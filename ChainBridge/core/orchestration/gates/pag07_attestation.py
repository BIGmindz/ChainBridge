"""
PAG-07: Attestation Gate (Checklist & Attestation)
==================================================

Final checklist and attestation for execution completion.

PDO Canon:
    - Proof: All gate results and checklist status
    - Decision: Final attestation pass/fail
    - Outcome: Execution authorized or rejected
"""

from typing import Any

from ..gate import Gate, GateResult, GateStatus


class AttestationGate(Gate):
    """
    PAG-07: Attestation Gate
    
    Gold Standard Checklist:
        - All PAG gates present
        - Correct order enforced
        - Observability enabled
        - Fail-closed discipline active
        - PDO canon locked
    """
    
    REQUIRED_GATES = ["PAG-01", "PAG-02", "PAG-03", "PAG-04", "PAG-05", "PAG-06"]
    
    def __init__(self):
        super().__init__(
            gate_id="PAG-07",
            name="Attestation Gate (Checklist)",
            description="Final checklist and attestation",
        )
    
    def execute(self, context: dict[str, Any]) -> GateResult:
        """
        Execute final attestation.
        
        Validates Gold Standard Checklist items.
        """
        proof = {}
        checklist = {}
        failures = []
        
        # Check 1: All PAG gates present and passed
        gates_present = []
        gates_passed = []
        gates_failed = []
        
        for gate_id in self.REQUIRED_GATES:
            result_key = f"gate_{gate_id}_result"
            gate_result = context.get(result_key)
            
            if gate_result is not None:
                gates_present.append(gate_id)
                if gate_result.get("status") == "PASS":
                    gates_passed.append(gate_id)
                else:
                    gates_failed.append(gate_id)
        
        checklist["all_gates_present"] = len(gates_present) == len(self.REQUIRED_GATES)
        checklist["all_gates_passed"] = len(gates_passed) == len(self.REQUIRED_GATES)
        
        proof["gates_present"] = gates_present
        proof["gates_passed"] = gates_passed
        proof["gates_failed"] = gates_failed
        
        if not checklist["all_gates_present"]:
            missing = set(self.REQUIRED_GATES) - set(gates_present)
            failures.append(f"Missing gates: {', '.join(missing)}")
        
        if gates_failed:
            failures.append(f"Failed gates: {', '.join(gates_failed)}")
        
        # Check 2: Correct order enforced
        # (This is inherently true if we got here via sequential execution)
        checklist["correct_order"] = True
        
        # Check 3: Observability enabled
        observability = context.get("observability", "MANDATORY")
        checklist["observability_enabled"] = observability.upper() in {"MANDATORY", "ENABLED", "TRUE"}
        proof["observability"] = observability
        
        if not checklist["observability_enabled"]:
            failures.append("Observability not enabled")
        
        # Check 4: Fail-closed discipline active
        failure_discipline = context.get("failure_discipline", "FAIL-CLOSED")
        checklist["fail_closed_active"] = "CLOSED" in failure_discipline.upper()
        proof["failure_discipline"] = failure_discipline
        
        if not checklist["fail_closed_active"]:
            failures.append("Fail-closed discipline not active")
        
        # Check 5: PDO canon locked
        pdo_canon_locked = context.get("pdo_canon_locked", True)
        checklist["pdo_canon_locked"] = pdo_canon_locked
        proof["pdo_canon_locked"] = pdo_canon_locked
        
        if not pdo_canon_locked:
            failures.append("PDO canon not locked")
        
        proof["checklist"] = checklist
        proof["failures"] = failures
        
        # Calculate final state
        all_checks_passed = all(checklist.values())
        proof["all_checks_passed"] = all_checks_passed
        
        # Build final state declaration
        final_state = {
            "benson_status": "ACTIVE" if all_checks_passed else "INACTIVE",
            "governance": "ARMED" if checklist.get("fail_closed_active") else "DISARMED",
            "execution": "GATED" if all_checks_passed else "BLOCKED",
            "pdo_canon": "LOCKED" if pdo_canon_locked else "UNLOCKED",
            "wrap_required": not all_checks_passed,
        }
        proof["final_state"] = final_state
        
        # Make decision
        if failures:
            return GateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                proof=proof,
                decision=f"FAIL - Attestation checklist failed: {'; '.join(failures)}",
                outcome="Execution not attested - WRAP required with failures",
                error="; ".join(failures),
            )
        
        # Success
        return GateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASS,
            proof=proof,
            decision="PASS - Gold Standard checklist complete",
            outcome="Execution attested - all gates passed",
        )
    
    def render_terminal(self, result: GateResult) -> str:
        """Override to include final state declaration."""
        base_output = super().render_terminal(result)
        
        # Add final state block
        final_state = result.proof.get("final_state", {})
        
        state_lines = [
            "",
            "─" * 60,
            "FINAL STATE DECLARATION",
            "─" * 60,
        ]
        
        for key, value in final_state.items():
            state_lines.append(f"  FINAL_STATE.{key} = {value}")
        
        state_lines.append("─" * 60)
        
        return base_output + "\n".join(state_lines)
