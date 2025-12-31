"""
PAG-03: Execution Lane Gate
===========================

Verifies execution lane and permitted/forbidden outputs.

PDO Canon:
    - Proof: Lane configuration and boundaries
    - Decision: Lane validation pass/fail
    - Outcome: Lane activation status
"""

from typing import Any

from ..gate import Gate, GateResult, GateStatus


class ExecutionLaneGate(Gate):
    """
    PAG-03: Execution Lane Gate
    
    Checks:
        - Execution lane is specified
        - Permitted outputs are defined
        - Forbidden outputs are defined
        - Requested outputs don't violate boundaries
    """
    
    # Standard lane definitions
    STANDARD_LANES = {
        "orchestration": {
            "name": "Orchestration / Control Plane",
            "permitted": ["pac_issuance", "agent_coordination", "runtime_halts", "structured_events", "ber_issuance"],
            "forbidden": ["code_commits", "ui_decisions", "policy_authorship"],
        },
        "backend": {
            "name": "Backend / Runtime Infrastructure",
            "permitted": ["code", "tests", "runtime_logs", "wrap"],
            "forbidden": ["ui_work", "policy_edits", "research_synthesis"],
        },
        "frontend": {
            "name": "Frontend / UI",
            "permitted": ["ui_code", "styles", "components", "wrap"],
            "forbidden": ["backend_code", "policy_edits", "database_changes"],
        },
        "research": {
            "name": "Research / Analysis",
            "permitted": ["research_synthesis", "documentation", "analysis", "wrap"],
            "forbidden": ["code_commits", "policy_changes", "production_deploys"],
        },
        "governance": {
            "name": "Governance / Policy",
            "permitted": ["policy_documents", "governance_rules", "audit_reports"],
            "forbidden": ["code_commits", "ui_changes", "runtime_modifications"],
        },
    }
    
    def __init__(self):
        super().__init__(
            gate_id="PAG-03",
            name="Execution Lane",
            description="Verify execution lane and output boundaries",
        )
    
    def execute(self, context: dict[str, Any]) -> GateResult:
        """
        Execute lane verification.
        
        Required context:
            - execution_lane: str
            - requested_outputs: list[str] (optional)
        """
        proof = {}
        
        # Collect proof
        execution_lane = context.get("execution_lane", "orchestration")
        requested_outputs = context.get("requested_outputs", [])
        
        # Normalize lane name
        lane_key = execution_lane.lower().replace(" ", "_").replace("/", "_").split("_")[0]
        
        proof["execution_lane_raw"] = execution_lane
        proof["execution_lane_normalized"] = lane_key
        proof["requested_outputs"] = requested_outputs
        
        # Get lane definition
        if lane_key in self.STANDARD_LANES:
            lane_def = self.STANDARD_LANES[lane_key]
            proof["lane_found"] = True
            proof["lane_name"] = lane_def["name"]
            proof["permitted_outputs"] = lane_def["permitted"]
            proof["forbidden_outputs"] = lane_def["forbidden"]
        else:
            # Custom lane - allow if permitted/forbidden are specified
            permitted = context.get("permitted_outputs", [])
            forbidden = context.get("forbidden_outputs", [])
            
            if not permitted:
                return GateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAIL,
                    proof=proof,
                    decision=f"FAIL - Unknown lane '{execution_lane}' with no permitted outputs defined",
                    outcome="Lane activation rejected",
                    error=f"Unknown lane: {execution_lane}",
                )
            
            lane_def = {
                "name": execution_lane,
                "permitted": permitted,
                "forbidden": forbidden,
            }
            proof["lane_found"] = False
            proof["lane_custom"] = True
            proof["lane_name"] = execution_lane
            proof["permitted_outputs"] = permitted
            proof["forbidden_outputs"] = forbidden
        
        # Check requested outputs against boundaries
        violations = []
        for output in requested_outputs:
            output_normalized = output.lower().replace(" ", "_")
            if output_normalized in [f.lower().replace(" ", "_") for f in lane_def["forbidden"]]:
                violations.append(output)
        
        proof["violations"] = violations
        
        if violations:
            return GateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                proof=proof,
                decision=f"FAIL - Requested outputs violate lane boundaries: {', '.join(violations)}",
                outcome="Lane activation rejected due to boundary violations",
                error=f"Forbidden outputs requested: {', '.join(violations)}",
            )
        
        # Success
        return GateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASS,
            proof=proof,
            decision=f"PASS - Lane '{lane_def['name']}' validated",
            outcome=f"Execution lane activated: {lane_def['name']}",
        )
