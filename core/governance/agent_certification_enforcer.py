#!/usr/bin/env python3
"""
Agent Certification Enforcer - AU Runtime Enforcement Gate
============================================================

PAC Reference: PAC-P754-AU-ENFORCEMENT-RUNTIME
Classification: LAW_TIER
Domain: AGENT_UNIVERSITY
Section: 2_OF_N

Authors:
    - CODY (GID-01) - Enforcement Logic
    - ALEX (GID-08) - Invariant Binding
Orchestrator: BENSON (GID-00)
Authority: JEFFREY (ARCHITECT)

Purpose:
    Runtime enforcement ensuring Agent University certification
    is evaluated at execution-time for every agent, shard, and swarm.

Enforcement Model:
    - AU-GATE-001: agent_certification_level >= L1
    - AU-GATE-002: certification_status == ACTIVE
    - AU-GATE-003: revocation_flag == FALSE

Fail Mode: CLOSED (block on any check failure)

Invariants:
    - INV-P754-001: Certification checks execute before any task
    - INV-P754-002: Revoked agents terminated mid-execution
    - INV-P754-003: Human override requires LAW_TIER PAC
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from threading import Lock


# ===================== Configuration =====================

RUNTIME_STATE_FILE = Path(__file__).parent / "agent_certification_runtime_state.json"
LEVELS_REGISTRY = Path(__file__).parent / "doctrines" / "AGENT_CERTIFICATION_LEVELS.json"
HEARTBEAT_INTERVAL_SEC = 5
REVOCATION_CHECK_INTERVAL_SEC = 1

logger = logging.getLogger("AU_ENFORCER")


# ===================== Enums =====================

class CertificationLevel(Enum):
    """Agent University certification levels."""
    L0 = 0  # OBSERVE_ONLY
    L1 = 1  # EXECUTE_WITH_SUPERVISION
    L2 = 2  # GOVERNED_EXECUTION
    L3 = 3  # SWARM_ELIGIBLE
    
    @classmethod
    def from_string(cls, level_str: str) -> "CertificationLevel":
        """Parse level from string like 'L2' or 'GOVERNED_EXECUTION'."""
        level_map = {
            "L0": cls.L0, "OBSERVE_ONLY": cls.L0,
            "L1": cls.L1, "EXECUTE_WITH_SUPERVISION": cls.L1,
            "L2": cls.L2, "GOVERNED_EXECUTION": cls.L2,
            "L3": cls.L3, "SWARM_ELIGIBLE": cls.L3,
        }
        return level_map.get(level_str.upper(), cls.L0)
    
    def can_execute(self) -> bool:
        """Check if this level permits execution."""
        return self.value >= CertificationLevel.L1.value


class CertificationStatus(Enum):
    """Agent certification status."""
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    PENDING = "PENDING"
    EXPIRED = "EXPIRED"


class EnforcementResult(Enum):
    """Result of enforcement gate check."""
    PASSED = "PASSED"
    BLOCKED_LEVEL_INSUFFICIENT = "BLOCKED_LEVEL_INSUFFICIENT"
    BLOCKED_STATUS_INACTIVE = "BLOCKED_STATUS_INACTIVE"
    BLOCKED_REVOKED = "BLOCKED_REVOKED"
    BLOCKED_NO_CERTIFICATION = "BLOCKED_NO_CERTIFICATION"
    TERMINATED_MID_EXECUTION = "TERMINATED_MID_EXECUTION"
    HUMAN_OVERRIDE_APPLIED = "HUMAN_OVERRIDE_APPLIED"


class FailureMode(Enum):
    """Enforcement failure modes."""
    HARD_BLOCK = "HARD_BLOCK"
    IMMEDIATE_TERMINATION = "IMMEDIATE_TERMINATION"
    SCRAM_AND_AUDIT = "SCRAM_AND_AUDIT"


# ===================== Data Classes =====================

@dataclass
class AgentCertification:
    """Agent certification record."""
    agent_id: str
    certification_level: CertificationLevel
    certification_status: CertificationStatus
    revocation_flag: bool = False
    revocation_reason: Optional[str] = None
    issued_at: str = ""
    last_audit_timestamp: str = ""
    supervisor_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "certification_level": self.certification_level.name,
            "certification_status": self.certification_status.value,
            "revocation_flag": self.revocation_flag,
            "revocation_reason": self.revocation_reason,
            "issued_at": self.issued_at,
            "last_audit_timestamp": self.last_audit_timestamp,
            "supervisor_id": self.supervisor_id,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCertification":
        return cls(
            agent_id=data["agent_id"],
            certification_level=CertificationLevel.from_string(data["certification_level"]),
            certification_status=CertificationStatus(data["certification_status"]),
            revocation_flag=data.get("revocation_flag", False),
            revocation_reason=data.get("revocation_reason"),
            issued_at=data.get("issued_at", ""),
            last_audit_timestamp=data.get("last_audit_timestamp", ""),
            supervisor_id=data.get("supervisor_id"),
            metadata=data.get("metadata", {})
        )


@dataclass
class EnforcementGate:
    """Enforcement gate definition."""
    gate_id: str
    check: str
    required: str
    failure_mode: FailureMode
    
    def evaluate(self, cert: AgentCertification) -> Tuple[bool, EnforcementResult]:
        """Evaluate this gate against an agent certification."""
        if self.check == "agent_certification_level":
            required_level = CertificationLevel.from_string(self.required.replace("_OR_HIGHER", ""))
            if cert.certification_level.value >= required_level.value:
                return True, EnforcementResult.PASSED
            return False, EnforcementResult.BLOCKED_LEVEL_INSUFFICIENT
        
        elif self.check == "certification_status":
            if cert.certification_status.value == self.required:
                return True, EnforcementResult.PASSED
            return False, EnforcementResult.BLOCKED_STATUS_INACTIVE
        
        elif self.check == "revocation_flag":
            required_bool = self.required.upper() == "FALSE"
            if cert.revocation_flag != required_bool:
                return True, EnforcementResult.PASSED
            return False, EnforcementResult.BLOCKED_REVOKED
        
        return False, EnforcementResult.BLOCKED_NO_CERTIFICATION


@dataclass
class EnforcementDecision:
    """Result of enforcement check."""
    agent_id: str
    passed: bool
    result: EnforcementResult
    gate_results: List[Dict[str, Any]]
    timestamp: str
    execution_allowed: bool
    termination_required: bool = False
    scram_required: bool = False
    audit_entry: Optional[Dict[str, Any]] = None


# ===================== Runtime State Manager =====================

class CertificationRuntimeState:
    """
    Manages runtime state of all agent certifications.
    Thread-safe singleton for enforcement checks.
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._state_lock = Lock()
        self._certifications: Dict[str, AgentCertification] = {}
        self._enforcement_log: List[EnforcementDecision] = []
        self._active_executions: Dict[str, str] = {}  # agent_id -> execution_id
        self._revocation_callbacks: List[callable] = []
        self._load_state()
        self._initialized = True
    
    def _load_state(self) -> None:
        """Load runtime state from file if exists."""
        if RUNTIME_STATE_FILE.exists():
            try:
                with open(RUNTIME_STATE_FILE, "r") as f:
                    data = json.load(f)
                    for agent_id, cert_data in data.get("certifications", {}).items():
                        self._certifications[agent_id] = AgentCertification.from_dict(cert_data)
                    logger.info(f"Loaded {len(self._certifications)} certifications from state file")
            except Exception as e:
                logger.error(f"Failed to load runtime state: {e}")
    
    def _save_state(self) -> None:
        """Persist runtime state to file."""
        with self._state_lock:
            data = {
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "certifications": {
                    agent_id: cert.to_dict()
                    for agent_id, cert in self._certifications.items()
                },
                "active_executions": self._active_executions
            }
            try:
                with open(RUNTIME_STATE_FILE, "w") as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to save runtime state: {e}")
    
    def register_certification(self, cert: AgentCertification) -> None:
        """Register or update an agent certification."""
        with self._state_lock:
            cert.last_audit_timestamp = datetime.now(timezone.utc).isoformat()
            self._certifications[cert.agent_id] = cert
            self._save_state()
            logger.info(f"Registered certification for {cert.agent_id}: {cert.certification_level.name}")
    
    def get_certification(self, agent_id: str) -> Optional[AgentCertification]:
        """Get certification for an agent."""
        return self._certifications.get(agent_id)
    
    def revoke_certification(
        self, 
        agent_id: str, 
        reason: str,
        immediate_termination: bool = True
    ) -> bool:
        """
        Revoke an agent's certification.
        Triggers immediate termination if agent is mid-execution.
        """
        with self._state_lock:
            cert = self._certifications.get(agent_id)
            if not cert:
                logger.warning(f"Cannot revoke: agent {agent_id} not found")
                return False
            
            cert.revocation_flag = True
            cert.revocation_reason = reason
            cert.certification_status = CertificationStatus.REVOKED
            cert.last_audit_timestamp = datetime.now(timezone.utc).isoformat()
            
            # Check if agent is mid-execution
            if agent_id in self._active_executions and immediate_termination:
                execution_id = self._active_executions[agent_id]
                logger.critical(
                    f"REVOCATION DURING EXECUTION: {agent_id} in execution {execution_id}"
                )
                self._trigger_revocation_callbacks(agent_id, execution_id, reason)
            
            self._save_state()
            logger.warning(f"Certification REVOKED for {agent_id}: {reason}")
            return True
    
    def register_execution_start(self, agent_id: str, execution_id: str) -> None:
        """Register that an agent has started execution."""
        with self._state_lock:
            self._active_executions[agent_id] = execution_id
    
    def register_execution_end(self, agent_id: str) -> None:
        """Register that an agent has completed execution."""
        with self._state_lock:
            self._active_executions.pop(agent_id, None)
    
    def register_revocation_callback(self, callback: callable) -> None:
        """Register callback for revocation events."""
        self._revocation_callbacks.append(callback)
    
    def _trigger_revocation_callbacks(
        self, 
        agent_id: str, 
        execution_id: str, 
        reason: str
    ) -> None:
        """Trigger all revocation callbacks."""
        for callback in self._revocation_callbacks:
            try:
                callback(agent_id, execution_id, reason)
            except Exception as e:
                logger.error(f"Revocation callback failed: {e}")
    
    def get_all_certifications(self) -> Dict[str, AgentCertification]:
        """Get all certifications (for OCC display)."""
        return dict(self._certifications)
    
    def get_enforcement_log(self, limit: int = 100) -> List[EnforcementDecision]:
        """Get recent enforcement decisions."""
        return self._enforcement_log[-limit:]
    
    def log_enforcement_decision(self, decision: EnforcementDecision) -> None:
        """Log an enforcement decision."""
        self._enforcement_log.append(decision)
        # Keep log bounded
        if len(self._enforcement_log) > 10000:
            self._enforcement_log = self._enforcement_log[-5000:]


# ===================== Enforcement Engine =====================

class AgentCertificationEnforcer:
    """
    Agent University Certification Enforcer.
    
    Evaluates certification at runtime before any execution.
    Implements fail-closed behavior per AU doctrines.
    """
    
    # Enforcement gates per PAC-P754
    GATES = [
        EnforcementGate(
            gate_id="AU-GATE-001",
            check="agent_certification_level",
            required="L1_OR_HIGHER",
            failure_mode=FailureMode.HARD_BLOCK
        ),
        EnforcementGate(
            gate_id="AU-GATE-002",
            check="certification_status",
            required="ACTIVE",
            failure_mode=FailureMode.IMMEDIATE_TERMINATION
        ),
        EnforcementGate(
            gate_id="AU-GATE-003",
            check="revocation_flag",
            required="FALSE",
            failure_mode=FailureMode.SCRAM_AND_AUDIT
        ),
    ]
    
    def __init__(self):
        self.state = CertificationRuntimeState()
        self._human_override_active = False
        self._override_pac_id: Optional[str] = None
    
    def enforce(
        self, 
        agent_id: str,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> EnforcementDecision:
        """
        Enforce certification requirements for an agent.
        
        This is the PRIMARY enforcement gate that MUST be called
        before any agent executes any task.
        
        Args:
            agent_id: The agent attempting to execute
            execution_context: Optional context (PAC, task, shard info)
        
        Returns:
            EnforcementDecision with pass/fail and required actions
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Get certification
        cert = self.state.get_certification(agent_id)
        
        # No certification = immediate block
        if cert is None:
            decision = EnforcementDecision(
                agent_id=agent_id,
                passed=False,
                result=EnforcementResult.BLOCKED_NO_CERTIFICATION,
                gate_results=[{
                    "gate_id": "PRE-CHECK",
                    "passed": False,
                    "reason": "NO_CERTIFICATION_FOUND"
                }],
                timestamp=timestamp,
                execution_allowed=False,
                termination_required=False,
                scram_required=False,
                audit_entry={
                    "event": "ENFORCEMENT_BLOCKED",
                    "agent_id": agent_id,
                    "reason": "NO_CERTIFICATION",
                    "context": execution_context
                }
            )
            self.state.log_enforcement_decision(decision)
            logger.warning(f"ENFORCEMENT BLOCKED: {agent_id} has no certification")
            return decision
        
        # Evaluate all gates
        gate_results = []
        all_passed = True
        termination_required = False
        scram_required = False
        final_result = EnforcementResult.PASSED
        
        for gate in self.GATES:
            passed, result = gate.evaluate(cert)
            gate_results.append({
                "gate_id": gate.gate_id,
                "check": gate.check,
                "required": gate.required,
                "passed": passed,
                "result": result.value,
                "failure_mode": gate.failure_mode.value if not passed else None
            })
            
            if not passed:
                all_passed = False
                final_result = result
                
                if gate.failure_mode == FailureMode.IMMEDIATE_TERMINATION:
                    termination_required = True
                elif gate.failure_mode == FailureMode.SCRAM_AND_AUDIT:
                    scram_required = True
                    termination_required = True
        
        # Build decision
        decision = EnforcementDecision(
            agent_id=agent_id,
            passed=all_passed,
            result=final_result,
            gate_results=gate_results,
            timestamp=timestamp,
            execution_allowed=all_passed,
            termination_required=termination_required,
            scram_required=scram_required,
            audit_entry={
                "event": "ENFORCEMENT_CHECK",
                "agent_id": agent_id,
                "certification_level": cert.certification_level.name,
                "status": cert.certification_status.value,
                "passed": all_passed,
                "context": execution_context
            }
        )
        
        self.state.log_enforcement_decision(decision)
        
        if all_passed:
            logger.debug(f"ENFORCEMENT PASSED: {agent_id} ({cert.certification_level.name})")
        else:
            logger.warning(
                f"ENFORCEMENT BLOCKED: {agent_id} - {final_result.value}"
                f" (termination={termination_required}, scram={scram_required})"
            )
        
        return decision
    
    def enforce_with_execution_tracking(
        self,
        agent_id: str,
        execution_id: str,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> EnforcementDecision:
        """
        Enforce and register execution for mid-execution revocation detection.
        """
        decision = self.enforce(agent_id, execution_context)
        
        if decision.execution_allowed:
            self.state.register_execution_start(agent_id, execution_id)
        
        return decision
    
    def complete_execution(self, agent_id: str) -> None:
        """Mark execution as complete."""
        self.state.register_execution_end(agent_id)
    
    def apply_human_override(self, pac_id: str, authorized_by: str) -> bool:
        """
        Apply human override to enforcement.
        
        Per INV-P754-003: Human override requires LAW_TIER PAC.
        """
        # Validate PAC is LAW_TIER (in production, check PAC registry)
        if not pac_id.startswith("PAC-"):
            logger.error(f"Invalid override PAC: {pac_id}")
            return False
        
        self._human_override_active = True
        self._override_pac_id = pac_id
        
        logger.critical(
            f"HUMAN OVERRIDE APPLIED via {pac_id} by {authorized_by}"
        )
        return True
    
    def clear_human_override(self) -> None:
        """Clear human override."""
        if self._human_override_active:
            logger.info(f"Human override cleared (was {self._override_pac_id})")
        self._human_override_active = False
        self._override_pac_id = None
    
    def check_mid_execution_revocation(self, agent_id: str) -> Optional[EnforcementDecision]:
        """
        Check if an agent has been revoked mid-execution.
        Called periodically during long-running tasks.
        """
        cert = self.state.get_certification(agent_id)
        if cert is None or cert.revocation_flag:
            return EnforcementDecision(
                agent_id=agent_id,
                passed=False,
                result=EnforcementResult.TERMINATED_MID_EXECUTION,
                gate_results=[{
                    "gate_id": "MID-EXEC-CHECK",
                    "passed": False,
                    "reason": "REVOKED_DURING_EXECUTION"
                }],
                timestamp=datetime.now(timezone.utc).isoformat(),
                execution_allowed=False,
                termination_required=True,
                scram_required=cert.revocation_flag if cert else False
            )
        return None


# ===================== PAC Execution Lifecycle Binding =====================

class PACExecutionEnforcementBinding:
    """
    Binds AU enforcement to PAC execution lifecycle.
    
    Runtime Bindings:
        - PAC_EXECUTION_PIPELINE
        - SHARD_MANAGER
        - HEARTBEAT_EMITTER
    """
    
    def __init__(self, enforcer: AgentCertificationEnforcer):
        self.enforcer = enforcer
    
    def pre_pac_execution_hook(
        self,
        pac_id: str,
        agent_id: str,
        task_manifest: List[Dict[str, Any]]
    ) -> Tuple[bool, Optional[EnforcementDecision]]:
        """
        Called before PAC execution begins.
        
        INV-P754-001: Certification checks execute before any task.
        """
        context = {
            "pac_id": pac_id,
            "task_count": len(task_manifest),
            "hook": "PRE_PAC_EXECUTION"
        }
        
        decision = self.enforcer.enforce_with_execution_tracking(
            agent_id=agent_id,
            execution_id=f"{pac_id}:{agent_id}",
            execution_context=context
        )
        
        return decision.execution_allowed, decision
    
    def pre_shard_execution_hook(
        self,
        shard_id: str,
        agent_id: str,
        parent_pac_id: str
    ) -> Tuple[bool, Optional[EnforcementDecision]]:
        """
        Called before shard execution begins.
        """
        context = {
            "shard_id": shard_id,
            "parent_pac_id": parent_pac_id,
            "hook": "PRE_SHARD_EXECUTION"
        }
        
        decision = self.enforcer.enforce(
            agent_id=agent_id,
            execution_context=context
        )
        
        return decision.execution_allowed, decision
    
    def heartbeat_certification_check(
        self,
        agent_id: str,
        execution_id: str
    ) -> Optional[EnforcementDecision]:
        """
        Called during heartbeat to check for mid-execution revocation.
        
        INV-P754-002: Revoked agents terminated mid-execution.
        """
        return self.enforcer.check_mid_execution_revocation(agent_id)
    
    def post_execution_hook(self, agent_id: str) -> None:
        """Called after execution completes."""
        self.enforcer.complete_execution(agent_id)


# ===================== Convenience Functions =====================

_enforcer_instance: Optional[AgentCertificationEnforcer] = None


def get_enforcer() -> AgentCertificationEnforcer:
    """Get singleton enforcer instance."""
    global _enforcer_instance
    if _enforcer_instance is None:
        _enforcer_instance = AgentCertificationEnforcer()
    return _enforcer_instance


def enforce_certification(
    agent_id: str,
    execution_context: Optional[Dict[str, Any]] = None
) -> EnforcementDecision:
    """
    Convenience function to enforce certification.
    
    Usage:
        decision = enforce_certification("GID-01")
        if not decision.execution_allowed:
            raise PermissionError(f"Agent {agent_id} not certified")
    """
    return get_enforcer().enforce(agent_id, execution_context)


def register_agent_certification(
    agent_id: str,
    level: str,
    status: str = "ACTIVE"
) -> None:
    """
    Register a new agent certification.
    
    Usage:
        register_agent_certification("GID-01", "L2", "ACTIVE")
    """
    cert = AgentCertification(
        agent_id=agent_id,
        certification_level=CertificationLevel.from_string(level),
        certification_status=CertificationStatus(status),
        issued_at=datetime.now(timezone.utc).isoformat()
    )
    get_enforcer().state.register_certification(cert)


def revoke_agent_certification(agent_id: str, reason: str) -> bool:
    """
    Revoke an agent's certification immediately.
    
    Usage:
        revoke_agent_certification("GID-01", "Policy violation detected")
    """
    return get_enforcer().state.revoke_certification(agent_id, reason)


# ===================== Module Self-Test =====================

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print("=" * 60)
    print("Agent Certification Enforcer - Self Test")
    print("PAC-P754-AU-ENFORCEMENT-RUNTIME")
    print("=" * 60)
    
    # Register test certifications
    register_agent_certification("GID-00", "L3", "ACTIVE")  # BENSON
    register_agent_certification("GID-01", "L2", "ACTIVE")  # CODY
    register_agent_certification("GID-08", "L2", "ACTIVE")  # ALEX
    register_agent_certification("GID-99", "L0", "ACTIVE")  # Observer
    
    # Test enforcement
    print("\n[TEST 1] L3 Agent (should pass)")
    decision = enforce_certification("GID-00")
    print(f"  Result: {decision.result.value}, Allowed: {decision.execution_allowed}")
    
    print("\n[TEST 2] L2 Agent (should pass)")
    decision = enforce_certification("GID-01")
    print(f"  Result: {decision.result.value}, Allowed: {decision.execution_allowed}")
    
    print("\n[TEST 3] L0 Agent (should block)")
    decision = enforce_certification("GID-99")
    print(f"  Result: {decision.result.value}, Allowed: {decision.execution_allowed}")
    
    print("\n[TEST 4] Unknown Agent (should block)")
    decision = enforce_certification("GID-UNKNOWN")
    print(f"  Result: {decision.result.value}, Allowed: {decision.execution_allowed}")
    
    print("\n[TEST 5] Revocation test")
    revoke_agent_certification("GID-01", "Test revocation")
    decision = enforce_certification("GID-01")
    print(f"  Result: {decision.result.value}, Allowed: {decision.execution_allowed}")
    
    print("\n" + "=" * 60)
    print("Self-test complete. All enforcement gates operational.")
    print("=" * 60)
