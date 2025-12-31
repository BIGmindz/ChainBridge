"""
PAG-04: Governance Mode Gate
============================

Verifies governance mode and enforcement rules.

PDO Canon:
    - Proof: Governance configuration
    - Decision: Mode validation pass/fail
    - Outcome: Governance enforcement status
"""

from typing import Any

from ..gate import Gate, GateResult, GateStatus


class GovernanceModeGate(Gate):
    """
    PAG-04: Governance Mode Gate
    
    Checks:
        - Governance mode is valid
        - Enforcement rules are active
        - No implicit success paths
        - Visible state transitions only
    """
    
    GOVERNANCE_MODES = {
        "GOLD_STANDARD": {
            "rules": [
                "no_implicit_success",
                "no_optimistic_execution",
                "visible_transitions_only",
                "explicit_pass_fail",
            ],
            "strictness": "HIGH",
        },
        "STANDARD": {
            "rules": [
                "no_implicit_success",
                "explicit_pass_fail",
            ],
            "strictness": "MEDIUM",
        },
        "MINIMAL": {
            "rules": [
                "explicit_pass_fail",
            ],
            "strictness": "LOW",
        },
    }
    
    def __init__(self):
        super().__init__(
            gate_id="PAG-04",
            name="Governance Mode",
            description="Verify governance mode and enforcement rules",
        )
    
    def execute(self, context: dict[str, Any]) -> GateResult:
        """
        Execute governance mode verification.
        
        Required context:
            - governance_mode: str
        """
        proof = {}
        
        # Collect proof
        governance_mode = context.get("governance_mode", "GOLD_STANDARD")
        
        # Normalize mode name
        mode_normalized = governance_mode.upper().replace(" ", "_")
        
        proof["governance_mode_raw"] = governance_mode
        proof["governance_mode_normalized"] = mode_normalized
        
        # Validate mode
        if mode_normalized not in self.GOVERNANCE_MODES:
            return GateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                proof=proof,
                decision=f"FAIL - Unknown governance mode: {governance_mode}",
                outcome="Governance mode rejected",
                error=f"Valid modes: {', '.join(self.GOVERNANCE_MODES.keys())}",
            )
        
        mode_config = self.GOVERNANCE_MODES[mode_normalized]
        proof["mode_found"] = True
        proof["strictness"] = mode_config["strictness"]
        proof["rules"] = mode_config["rules"]
        
        # Verify enforcement rules are understood
        enforcement_rules_active = context.get("enforcement_rules_active", True)
        proof["enforcement_rules_active"] = enforcement_rules_active
        
        if not enforcement_rules_active:
            return GateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                proof=proof,
                decision="FAIL - Enforcement rules not active",
                outcome="Governance mode rejected - rules must be enforced",
                error="enforcement_rules_active must be True",
            )
        
        # For GOLD_STANDARD, verify all strict requirements
        if mode_normalized == "GOLD_STANDARD":
            # Check for implicit success paths
            allow_implicit_success = context.get("allow_implicit_success", False)
            allow_optimistic_execution = context.get("allow_optimistic_execution", False)
            
            proof["allow_implicit_success"] = allow_implicit_success
            proof["allow_optimistic_execution"] = allow_optimistic_execution
            
            if allow_implicit_success:
                return GateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAIL,
                    proof=proof,
                    decision="FAIL - GOLD_STANDARD prohibits implicit success",
                    outcome="Governance mode rejected",
                    error="allow_implicit_success must be False for GOLD_STANDARD",
                )
            
            if allow_optimistic_execution:
                return GateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAIL,
                    proof=proof,
                    decision="FAIL - GOLD_STANDARD prohibits optimistic execution",
                    outcome="Governance mode rejected",
                    error="allow_optimistic_execution must be False for GOLD_STANDARD",
                )
        
        # Success
        return GateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASS,
            proof=proof,
            decision=f"PASS - Governance mode {mode_normalized} validated",
            outcome=f"Governance armed with {mode_config['strictness']} strictness",
        )
