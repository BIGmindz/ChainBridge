#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════════════════════
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
ORCHESTRATOR DISCIPLINE GUARD
PAC-BENSON-P45-ORCHESTRATOR-IDENTITY-GATEWAY-AND-RESPONSE-DISCIPLINE-RESET-01
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
══════════════════════════════════════════════════════════════════════════════

PURPOSE:
    Enforce strict Benson CTO/orchestrator behavior. Eliminate uncontrolled
    execution, agent bleed-through, unsolicited PACs, and non-factual responses.
    
AUTHORITY: BENSON (GID-00)
MODE: FAIL_CLOSED

INVARIANTS:
    - No agent may self-activate
    - No PAC without Benson Gateway approval
    - No execution without explicit request
    - No identity drift or bleed-through
    - Sequential PAC/WRAP enforcement

ERROR CODES:
    GS_116: GATEWAY_BYPASS — PAC issued without Benson Gateway approval
    GS_117: AGENT_SELF_ACTIVATION — Agent attempted self-activation
    GS_118: IDENTITY_DRIFT — Agent identity mismatch detected
    GS_119: UNSOLICITED_EXECUTION — Execution without explicit request

══════════════════════════════════════════════════════════════════════════════
"""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


# ============================================================================
# CONSTANTS
# ============================================================================

# Benson is the sole orchestrator authority
ORCHESTRATOR_GID = "GID-00"
ORCHESTRATOR_NAME = "BENSON"
ORCHESTRATOR_ROLE = "Chief Architect & Orchestrator"
ORCHESTRATOR_LANE = "ORCHESTRATION"
ORCHESTRATOR_COLOR = "TEAL"

# Valid agent GIDs that can be activated by Benson
VALID_AGENT_GIDS = {
    "GID-00": "BENSON",
    "GID-01": "SONNY",
    "GID-02": "MAGGIE",
    "GID-03": "CODY",
    "GID-04": "DAN",
    "GID-05": "ATLAS",
    "GID-06": "SAM",
    "GID-07": "DAN",
    "GID-08": "ALEX",
    "GID-09": "TINA",
    "GID-10": "MAGGIE",
    "GID-11": "ATLAS",
    "GID-12": "RUBY",
}

# Execution lane restrictions
EXECUTION_LANES = {
    "ORCHESTRATION": ["GID-00"],  # Only Benson
    "GOVERNANCE": ["GID-00", "GID-08"],  # Benson, Alex
    "STRATEGY": ["GID-00", "GID-03", "GID-06"],  # Benson, Cody, Sam
    "EXECUTION": ["GID-00", "GID-01", "GID-02", "GID-04", "GID-05", "GID-09", "GID-12"],
    "ADVISORY": ["GID-00", "GID-11"],  # Advisory only
}


# ============================================================================
# ENUMS
# ============================================================================

class GatewayState(Enum):
    """Benson Gateway states."""
    CLOSED = "CLOSED"  # Default - no execution allowed
    OPEN = "OPEN"      # Gateway opened by explicit request
    BLOCKED = "BLOCKED"  # Blocked due to violation


class ActivationState(Enum):
    """Agent activation states."""
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"  # Awaiting AGENT_ACTIVATION_ACK
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class GatewayCheck:
    """Result of Benson Gateway check."""
    passed: bool
    gateway_state: str
    error_code: Optional[str] = None
    message: Optional[str] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class ActivationCheck:
    """Result of agent activation check."""
    valid: bool
    agent_gid: str
    agent_name: str
    activated_by: Optional[str] = None
    error_code: Optional[str] = None
    message: Optional[str] = None


@dataclass
class IdentityCheck:
    """Result of identity consistency check."""
    valid: bool
    declared_gid: str
    declared_name: str
    declared_lane: str
    expected_gid: Optional[str] = None
    expected_name: Optional[str] = None
    error_code: Optional[str] = None
    message: Optional[str] = None


# ============================================================================
# ORCHESTRATOR GUARD CLASS
# ============================================================================

class OrchestratorGuard:
    """
    Orchestrator Discipline Guard.
    
    Enforces:
    - Benson Gateway approval for all PAC issuance
    - Explicit AGENT_ACTIVATION_ACK before agent actions
    - Identity consistency (no drift/bleed-through)
    - Execution only on explicit request
    """
    
    def __init__(self):
        self.gateway_state = GatewayState.CLOSED
        self.active_agents = {}  # gid -> ActivationState
        self.gateway_history = []
    
    # ========================================================================
    # BENSON GATEWAY
    # ========================================================================
    
    def check_gateway(self, pac_content: str, requester_gid: str) -> GatewayCheck:
        """
        Check if PAC issuance is allowed through Benson Gateway.
        
        Rules:
        1. PAC must contain GATEWAY_CHECK or GATEWAY_CHECKS block
        2. Requester must be authorized agent
        3. Gateway must be in OPEN state (explicit request received)
        
        Args:
            pac_content: The PAC artifact content
            requester_gid: GID of the agent issuing the PAC
            
        Returns:
            GatewayCheck result
        """
        # Check for Gateway block
        has_gateway = bool(re.search(
            r'GATEWAY_CHECK[S]?:?\s*\n',
            pac_content,
            re.IGNORECASE
        ))
        
        if not has_gateway:
            return GatewayCheck(
                passed=False,
                gateway_state=self.gateway_state.value,
                error_code="GS_116",
                message="GATEWAY_BYPASS — PAC missing GATEWAY_CHECK block. All PACs require gateway approval."
            )
        
        # Check requester authorization
        if requester_gid not in VALID_AGENT_GIDS:
            return GatewayCheck(
                passed=False,
                gateway_state=self.gateway_state.value,
                error_code="GS_116",
                message=f"GATEWAY_BYPASS — Unknown agent GID: {requester_gid}"
            )
        
        return GatewayCheck(
            passed=True,
            gateway_state=GatewayState.OPEN.value,
            message=f"Gateway check passed for {VALID_AGENT_GIDS.get(requester_gid, 'UNKNOWN')}"
        )
    
    def validate_gateway_block(self, content: str) -> GatewayCheck:
        """
        Validate the GATEWAY_CHECK block content.
        
        Required fields:
        - governance: list of governance modes
        - assumptions: list of assumptions
        """
        # Extract gateway block
        gateway_match = re.search(
            r'GATEWAY_CHECK[S]?:\s*\n(.*?)(?=\n##|\n---|\Z)',
            content,
            re.DOTALL | re.IGNORECASE
        )
        
        if not gateway_match:
            return GatewayCheck(
                passed=False,
                gateway_state=GatewayState.CLOSED.value,
                error_code="GS_116",
                message="GATEWAY_BYPASS — GATEWAY_CHECK block not found or malformed"
            )
        
        gateway_content = gateway_match.group(1)
        
        # Check for required governance field
        has_governance = bool(re.search(r'governance:', gateway_content, re.IGNORECASE))
        if not has_governance:
            return GatewayCheck(
                passed=False,
                gateway_state=GatewayState.CLOSED.value,
                error_code="GS_116",
                message="GATEWAY_BYPASS — GATEWAY_CHECK missing 'governance' field"
            )
        
        return GatewayCheck(
            passed=True,
            gateway_state=GatewayState.OPEN.value,
            message="GATEWAY_CHECK block is valid"
        )
    
    # ========================================================================
    # AGENT ACTIVATION
    # ========================================================================
    
    def check_activation(self, content: str) -> ActivationCheck:
        """
        Check for valid AGENT_ACTIVATION_ACK.
        
        Rules:
        1. AGENT_ACTIVATION_ACK block must be present
        2. Block must contain valid agent_name and gid
        3. Agent must be in VALID_AGENT_GIDS registry
        
        Args:
            content: The artifact content
            
        Returns:
            ActivationCheck result
        """
        # Check for AGENT_ACTIVATION_ACK block
        activation_match = re.search(
            r'AGENT_ACTIVATION_ACK:?\s*\n(.*?)(?=\n##|\n---|\Z)',
            content,
            re.DOTALL | re.IGNORECASE
        )
        
        if not activation_match:
            return ActivationCheck(
                valid=False,
                agent_gid="UNKNOWN",
                agent_name="UNKNOWN",
                error_code="GS_117",
                message="AGENT_SELF_ACTIVATION — Missing AGENT_ACTIVATION_ACK block"
            )
        
        activation_content = activation_match.group(1)
        
        # Extract agent_name
        name_match = re.search(r'agent(?:_name)?:\s*["\']?([A-Z][A-Za-z]+)["\']?', activation_content, re.IGNORECASE)
        agent_name = name_match.group(1).upper() if name_match else "UNKNOWN"
        
        # Extract gid
        gid_match = re.search(r'gid:\s*["\']?(GID-\d+)["\']?', activation_content, re.IGNORECASE)
        agent_gid = gid_match.group(1) if gid_match else "UNKNOWN"
        
        # Validate against registry
        if agent_gid not in VALID_AGENT_GIDS:
            return ActivationCheck(
                valid=False,
                agent_gid=agent_gid,
                agent_name=agent_name,
                error_code="GS_117",
                message=f"AGENT_SELF_ACTIVATION — Invalid GID: {agent_gid} not in registry"
            )
        
        expected_name = VALID_AGENT_GIDS.get(agent_gid, "")
        if agent_name != expected_name:
            return ActivationCheck(
                valid=False,
                agent_gid=agent_gid,
                agent_name=agent_name,
                error_code="GS_118",
                message=f"IDENTITY_DRIFT — Agent name mismatch: declared {agent_name}, expected {expected_name}"
            )
        
        return ActivationCheck(
            valid=True,
            agent_gid=agent_gid,
            agent_name=agent_name,
            activated_by=ORCHESTRATOR_GID,
            message=f"Agent {agent_name} ({agent_gid}) activation valid"
        )
    
    # ========================================================================
    # IDENTITY CONSISTENCY
    # ========================================================================
    
    def check_identity_consistency(self, content: str) -> IdentityCheck:
        """
        Check for identity consistency across the artifact.
        
        Detects:
        - GID/name mismatches
        - Lane/role inconsistencies
        - Identity bleed-through (multiple agent signatures)
        
        Args:
            content: The artifact content
            
        Returns:
            IdentityCheck result
        """
        # Extract all GID references
        gid_refs = re.findall(r'(GID-\d+)', content)
        
        # Extract all agent name references (in YAML context)
        name_refs = re.findall(r'agent(?:_name)?:\s*["\']?([A-Z][A-Za-z]+)["\']?', content, re.IGNORECASE)
        
        # Get primary identity from AGENT_ACTIVATION_ACK
        primary_gid = None
        primary_name = None
        
        activation_match = re.search(
            r'AGENT_ACTIVATION_ACK:?\s*\n(.*?)(?=\n##|\n---|\Z)',
            content,
            re.DOTALL | re.IGNORECASE
        )
        
        if activation_match:
            activation_content = activation_match.group(1)
            gid_match = re.search(r'gid:\s*["\']?(GID-\d+)["\']?', activation_content, re.IGNORECASE)
            name_match = re.search(r'agent(?:_name)?:\s*["\']?([A-Z][A-Za-z]+)["\']?', activation_content, re.IGNORECASE)
            
            primary_gid = gid_match.group(1) if gid_match else None
            primary_name = name_match.group(1).upper() if name_match else None
        
        if not primary_gid or not primary_name:
            return IdentityCheck(
                valid=False,
                declared_gid="UNKNOWN",
                declared_name="UNKNOWN",
                declared_lane="UNKNOWN",
                error_code="GS_118",
                message="IDENTITY_DRIFT — Cannot determine primary identity"
            )
        
        # Check for inconsistent GIDs (excluding references to other agents in context)
        # Allow GID-00 (Benson) to appear in authority fields
        inconsistent_gids = [
            gid for gid in gid_refs 
            if gid != primary_gid and gid != "GID-00"
        ]
        
        # Check execution lane
        lane_match = re.search(r'(?:execution_)?lane:\s*["\']?([A-Z_]+)["\']?', content, re.IGNORECASE)
        declared_lane = lane_match.group(1).upper() if lane_match else "UNKNOWN"
        
        # Validate lane authorization
        if declared_lane != "UNKNOWN":
            authorized_agents = EXECUTION_LANES.get(declared_lane, [])
            if primary_gid not in authorized_agents:
                return IdentityCheck(
                    valid=False,
                    declared_gid=primary_gid,
                    declared_name=primary_name,
                    declared_lane=declared_lane,
                    error_code="GS_118",
                    message=f"IDENTITY_DRIFT — Agent {primary_name} not authorized for lane {declared_lane}"
                )
        
        return IdentityCheck(
            valid=True,
            declared_gid=primary_gid,
            declared_name=primary_name,
            declared_lane=declared_lane,
            expected_gid=primary_gid,
            expected_name=VALID_AGENT_GIDS.get(primary_gid, primary_name),
            message=f"Identity consistent: {primary_name} ({primary_gid}) in {declared_lane}"
        )
    
    # ========================================================================
    # EXECUTION REQUEST VALIDATION
    # ========================================================================
    
    def check_execution_request(self, content: str) -> dict:
        """
        Check if execution was explicitly requested.
        
        Detects:
        - Unsolicited PAC issuance
        - Execution without request
        - Speculative outputs
        
        Args:
            content: The artifact content
            
        Returns:
            dict with 'valid', 'error_code', 'message'
        """
        # Check for artifact_status
        status_match = re.search(
            r'artifact_status:\s*["\']?(\w+)["\']?',
            content,
            re.IGNORECASE
        )
        
        if not status_match:
            return {
                "valid": True,
                "error_code": None,
                "message": "No execution status found — advisory only"
            }
        
        status = status_match.group(1).upper()
        
        # EXECUTED or CLOSED status requires explicit request
        if status in ["EXECUTED", "CLOSED", "POSITIVE_CLOSURE"]:
            # Check for execution mode indicator
            mode_match = re.search(r'mode:\s*["\']?EXECUTABLE["\']?', content, re.IGNORECASE)
            
            if not mode_match:
                return {
                    "valid": False,
                    "error_code": "GS_119",
                    "message": "UNSOLICITED_EXECUTION — Executed status without EXECUTABLE mode declaration"
                }
        
        return {
            "valid": True,
            "error_code": None,
            "message": f"Execution status {status} is valid"
        }
    
    # ========================================================================
    # FULL DISCIPLINE CHECK
    # ========================================================================
    
    def validate_orchestrator_discipline(self, content: str, requester_gid: str = None) -> dict:
        """
        Run full orchestrator discipline validation.
        
        Checks:
        1. Benson Gateway approval
        2. Agent activation validity
        3. Identity consistency
        4. Execution request validity
        
        Args:
            content: The artifact content
            requester_gid: Optional GID of requester
            
        Returns:
            dict with 'valid', 'errors', 'checks'
        """
        errors = []
        checks = {}
        
        # Infer requester GID from content if not provided
        if not requester_gid:
            gid_match = re.search(r'gid:\s*["\']?(GID-\d+)["\']?', content, re.IGNORECASE)
            requester_gid = gid_match.group(1) if gid_match else "UNKNOWN"
        
        # 1. Gateway check
        gateway_result = self.check_gateway(content, requester_gid)
        checks["gateway"] = {
            "passed": gateway_result.passed,
            "state": gateway_result.gateway_state,
            "message": gateway_result.message
        }
        if not gateway_result.passed:
            errors.append({
                "code": gateway_result.error_code,
                "message": gateway_result.message
            })
        
        # 2. Activation check
        activation_result = self.check_activation(content)
        checks["activation"] = {
            "valid": activation_result.valid,
            "agent": f"{activation_result.agent_name} ({activation_result.agent_gid})",
            "message": activation_result.message
        }
        if not activation_result.valid:
            errors.append({
                "code": activation_result.error_code,
                "message": activation_result.message
            })
        
        # 3. Identity check
        identity_result = self.check_identity_consistency(content)
        checks["identity"] = {
            "valid": identity_result.valid,
            "declared": f"{identity_result.declared_name} ({identity_result.declared_gid})",
            "lane": identity_result.declared_lane,
            "message": identity_result.message
        }
        if not identity_result.valid:
            errors.append({
                "code": identity_result.error_code,
                "message": identity_result.message
            })
        
        # 4. Execution check
        execution_result = self.check_execution_request(content)
        checks["execution"] = {
            "valid": execution_result["valid"],
            "message": execution_result["message"]
        }
        if not execution_result["valid"]:
            errors.append({
                "code": execution_result["error_code"],
                "message": execution_result["message"]
            })
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "checks": checks
        }


# ============================================================================
# STANDALONE VALIDATION FUNCTIONS
# ============================================================================

def validate_gateway(content: str) -> list:
    """
    Validate Benson Gateway approval.
    
    Returns list of validation errors (empty if valid).
    """
    guard = OrchestratorGuard()
    
    # Extract requester GID
    gid_match = re.search(r'gid:\s*["\']?(GID-\d+)["\']?', content, re.IGNORECASE)
    requester_gid = gid_match.group(1) if gid_match else "UNKNOWN"
    
    result = guard.check_gateway(content, requester_gid)
    
    if not result.passed:
        return [{"code": result.error_code, "message": result.message}]
    
    return []


def validate_activation(content: str) -> list:
    """
    Validate agent activation.
    
    Returns list of validation errors (empty if valid).
    """
    guard = OrchestratorGuard()
    result = guard.check_activation(content)
    
    if not result.valid:
        return [{"code": result.error_code, "message": result.message}]
    
    return []


def validate_identity(content: str) -> list:
    """
    Validate identity consistency.
    
    Returns list of validation errors (empty if valid).
    """
    guard = OrchestratorGuard()
    result = guard.check_identity_consistency(content)
    
    if not result.valid:
        return [{"code": result.error_code, "message": result.message}]
    
    return []


def validate_execution_request(content: str) -> list:
    """
    Validate execution request.
    
    Returns list of validation errors (empty if valid).
    """
    guard = OrchestratorGuard()
    result = guard.check_execution_request(content)
    
    if not result["valid"]:
        return [{"code": result["error_code"], "message": result["message"]}]
    
    return []


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """CLI for orchestrator discipline validation."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description="Orchestrator Discipline Guard — Identity & Gateway Enforcement"
    )
    parser.add_argument("--file", "-f", required=True, help="File to validate")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
    
    content = file_path.read_text()
    
    guard = OrchestratorGuard()
    result = guard.validate_orchestrator_discipline(content)
    
    if args.verbose:
        print("\n" + "=" * 70)
        print("ORCHESTRATOR DISCIPLINE VALIDATION")
        print("=" * 70)
        print(f"\nFile: {file_path}")
        
        for check_name, check_result in result["checks"].items():
            status = "✅" if check_result.get("valid", check_result.get("passed", False)) else "❌"
            print(f"\n{status} {check_name.upper()}")
            for key, value in check_result.items():
                print(f"    {key}: {value}")
        
        print("\n" + "-" * 70)
    
    if result["valid"]:
        print(f"✅ Orchestrator discipline VALID: {file_path.name}")
        sys.exit(0)
    else:
        print(f"❌ Orchestrator discipline FAILED: {file_path.name}")
        for error in result["errors"]:
            print(f"    [{error['code']}] {error['message']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
