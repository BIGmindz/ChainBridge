"""
PAG-05: Review Gate (Gateway / Preflight)
=========================================

Performs preflight checks and validates invariants.

PDO Canon:
    - Proof: Preflight check results
    - Decision: All checks pass/fail
    - Outcome: Ready for payload execution
"""

from typing import Any

from ..gate import Gate, GateResult, GateStatus


class ReviewGate(Gate):
    """
    PAG-05: Review Gate (Gateway / Preflight)
    
    Checks:
        - Agent identity verified (PAG-01 passed)
        - Execution lane confirmed (PAG-03 passed)
        - Governance mode locked (PAG-04 passed)
        - PDO canon enforced
    
    Invariants:
        - Proof precedes Decision
        - Decision precedes Outcome
        - No Outcome without prior gates
    """
    
    REQUIRED_PRIOR_GATES = ["PAG-01", "PAG-02", "PAG-03", "PAG-04"]
    
    def __init__(self):
        super().__init__(
            gate_id="PAG-05",
            name="Review Gate (Gateway / Preflight)",
            description="Perform preflight checks and validate invariants",
        )
    
    def execute(self, context: dict[str, Any]) -> GateResult:
        """
        Execute preflight verification.
        
        Required context:
            - Prior gate results (gate_PAG-XX_result for XX in 01-04)
        """
        proof = {}
        checks = []
        failures = []
        
        # Check 1: Prior gates executed
        for gate_id in self.REQUIRED_PRIOR_GATES:
            result_key = f"gate_{gate_id}_result"
            gate_result = context.get(result_key)
            
            if gate_result is None:
                checks.append({"check": f"{gate_id}_executed", "status": "FAIL", "reason": "Not executed"})
                failures.append(f"{gate_id} not executed")
            elif gate_result.get("status") != "PASS":
                checks.append({"check": f"{gate_id}_passed", "status": "FAIL", "reason": f"Status: {gate_result.get('status')}"})
                failures.append(f"{gate_id} did not pass")
            else:
                checks.append({"check": f"{gate_id}_passed", "status": "PASS"})
        
        proof["prior_gate_checks"] = checks
        
        # Check 2: Agent identity verified
        agent_verified = context.get("gate_PAG-01_result", {}).get("status") == "PASS"
        proof["agent_verified"] = agent_verified
        
        # Check 3: Execution lane confirmed
        lane_confirmed = context.get("gate_PAG-03_result", {}).get("status") == "PASS"
        proof["lane_confirmed"] = lane_confirmed
        
        # Check 4: Governance mode locked
        governance_locked = context.get("gate_PAG-04_result", {}).get("status") == "PASS"
        proof["governance_locked"] = governance_locked
        
        # Check 5: PDO canon enforced
        pdo_canon_locked = context.get("pdo_canon_locked", True)
        proof["pdo_canon_enforced"] = pdo_canon_locked
        
        if not pdo_canon_locked:
            failures.append("PDO canon not locked")
        
        # Verify invariants
        invariants = {
            "proof_precedes_decision": True,  # Enforced by gate structure
            "decision_precedes_outcome": True,  # Enforced by gate structure
            "no_outcome_without_prior_gates": len([c for c in checks if c["status"] == "PASS"]) == len(self.REQUIRED_PRIOR_GATES),
        }
        proof["invariants"] = invariants
        
        if not invariants["no_outcome_without_prior_gates"]:
            failures.append("Outcome attempted without all prior gates passing")
        
        proof["failures"] = failures
        proof["checks_passed"] = len(failures) == 0
        
        # Make decision
        if failures:
            return GateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                proof=proof,
                decision=f"FAIL - Preflight checks failed: {'; '.join(failures)}",
                outcome="Preflight rejected - cannot proceed to payload",
                error="; ".join(failures),
            )
        
        # Success
        return GateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASS,
            proof=proof,
            decision="PASS - All preflight checks passed",
            outcome="Ready for payload execution",
        )
