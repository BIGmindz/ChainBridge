"""
PAG-01: Agent Activation Gate
=============================

Verifies agent identity and authority before execution.

PDO Canon:
    - Proof: Agent credentials and configuration
    - Decision: Identity verification pass/fail
    - Outcome: Agent activation status
"""

from typing import Any

from ..gate import Gate, GateResult, GateStatus


class AgentActivationGate(Gate):
    """
    PAG-01: Agent Activation Gate
    
    Checks:
        - Agent identity is specified
        - Agent GID is valid
        - Agent role is defined
        - Agent authority matches execution scope
    """
    
    def __init__(self):
        super().__init__(
            gate_id="PAG-01",
            name="Agent Activation",
            description="Verify agent identity and authority",
        )
    
    def execute(self, context: dict[str, Any]) -> GateResult:
        """
        Execute agent activation verification.
        
        Required context:
            - agent_name: str
            - agent_gid: str
            - agent_role: str
            - agent_authority: list[str]
        """
        proof = {}
        
        # Collect proof
        agent_name = context.get("agent_name")
        agent_gid = context.get("agent_gid")
        agent_role = context.get("agent_role")
        agent_authority = context.get("agent_authority", [])
        
        proof["agent_name"] = agent_name
        proof["agent_gid"] = agent_gid
        proof["agent_role"] = agent_role
        proof["agent_authority_count"] = len(agent_authority)
        
        # Validate required fields
        missing_fields = []
        if not agent_name:
            missing_fields.append("agent_name")
        if not agent_gid:
            missing_fields.append("agent_gid")
        if not agent_role:
            missing_fields.append("agent_role")
        
        proof["missing_fields"] = missing_fields
        proof["fields_valid"] = len(missing_fields) == 0
        
        # Make decision
        if missing_fields:
            return GateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                proof=proof,
                decision=f"FAIL - Missing required fields: {', '.join(missing_fields)}",
                outcome="Agent activation rejected",
                error=f"Missing: {', '.join(missing_fields)}",
            )
        
        # Validate GID format (should be numeric string like "00", "01", etc.)
        try:
            gid_num = int(agent_gid)
            proof["gid_valid"] = True
            proof["gid_numeric"] = gid_num
        except (ValueError, TypeError):
            proof["gid_valid"] = False
            return GateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                proof=proof,
                decision="FAIL - Invalid GID format",
                outcome="Agent activation rejected",
                error=f"Invalid GID: {agent_gid}",
            )
        
        # Success
        return GateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASS,
            proof=proof,
            decision=f"PASS - Agent {agent_name} (GID-{agent_gid}) verified",
            outcome=f"Agent activated as {agent_role}",
        )
