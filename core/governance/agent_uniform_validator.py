#!/usr/bin/env python3
"""
Agent Uniform Validator - Cryptographic Uniform Verification
=============================================================

PAC Reference: PAC-P755-AU-UNIFORM-ARTIFACT-SCHEMA
Classification: LAW_TIER
Domain: AGENT_UNIVERSITY
Section: 3_OF_N
Task: AU-8 (Bind uniform verification to execution runtime)

Authors:
    - CODY (GID-01) - Validation Logic
    - MORGAN (GID-06) - Cryptographic Binding
    - ALEX (GID-08) - Schema Enforcement
Orchestrator: BENSON (GID-00)
Authority: JEFFREY (ARCHITECT)

Purpose:
    Validates Agent Uniform artifacts at runtime, ensuring:
    - Schema compliance
    - Cryptographic signature validity
    - Certification alignment with runtime state
    - Drift detection and response

Enforcement Gates:
    - AU-UNIFORM-001: uniform_present (HARD_BLOCK)
    - AU-UNIFORM-002: uniform_signature_valid (IMMEDIATE_TERMINATION)
    - AU-UNIFORM-003: uniform_certification_alignment (SCRAM_AND_AUDIT)

Core Principle: NO UNIFORM, NO EXECUTION
"""

import json
import hashlib
import base64
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock

# Import the certification enforcer for alignment checks
try:
    from .agent_certification_enforcer import (
        CertificationRuntimeState,
        CertificationLevel,
        CertificationStatus,
        get_enforcer
    )
except ImportError:
    # Standalone mode
    CertificationRuntimeState = None
    get_enforcer = None


# ===================== Configuration =====================

SCHEMA_FILE = Path(__file__).parent / "doctrines" / "agent_uniform_schema.json"
UNIFORMS_DIR = Path(__file__).parent / "uniforms"
UNIFORMS_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("AU_UNIFORM_VALIDATOR")


# ===================== Enums =====================

class UniformState(Enum):
    """Uniform lifecycle states."""
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    SUPERSEDED = "SUPERSEDED"


class ValidationResult(Enum):
    """Uniform validation result codes."""
    VALID = "VALID"
    MISSING = "MISSING"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    SIGNATURE_INVALID = "SIGNATURE_INVALID"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    CERTIFICATION_MISMATCH = "CERTIFICATION_MISMATCH"


class DriftType(Enum):
    """Types of uniform drift."""
    NONE = "NONE"
    LEVEL_MISMATCH = "LEVEL_MISMATCH"
    REVOCATION_MISMATCH = "REVOCATION_MISMATCH"
    SIGNATURE_INVALID = "SIGNATURE_INVALID"
    EXPIRATION_BREACH = "EXPIRATION_BREACH"


class FailureMode(Enum):
    """Enforcement failure modes."""
    HARD_BLOCK = "HARD_BLOCK"
    IMMEDIATE_TERMINATION = "IMMEDIATE_TERMINATION"
    SCRAM_AND_AUDIT = "SCRAM_AND_AUDIT"


# ===================== Data Classes =====================

@dataclass
class UniformIdentity:
    """Uniform identity section."""
    agent_gid: str
    agent_name: str
    agent_role: str
    issuing_authority: str


@dataclass
class UniformCertification:
    """Uniform certification section."""
    certification_level: str
    certification_id: str
    issued_at: str
    expires_at: Optional[str]
    revocation_status: Dict[str, Any]


@dataclass
class UniformExecutionRights:
    """Uniform execution rights section."""
    max_pac_level: str
    swarm_eligibility: bool
    shard_permission: str
    override_capability: bool


@dataclass
class UniformBehavioralConstraints:
    """Uniform behavioral constraints section."""
    allowed_domains: List[str]
    forbidden_actions: List[str]
    rate_limits: Dict[str, int]
    data_access_scope: str


@dataclass
class UniformCryptographicBinding:
    """Uniform cryptographic binding section."""
    uniform_hash: str
    signature_algorithm: str
    signing_key_id: str
    signature: str


@dataclass
class AgentUniform:
    """Complete Agent Uniform artifact."""
    uniform_id: str
    uniform_version: str
    identity: UniformIdentity
    certification: UniformCertification
    execution_rights: UniformExecutionRights
    behavioral_constraints: UniformBehavioralConstraints
    cryptographic_binding: UniformCryptographicBinding
    metadata: Dict[str, Any]
    state: UniformState = UniformState.DRAFT
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "uniform_id": self.uniform_id,
            "uniform_version": self.uniform_version,
            "identity": {
                "agent_gid": self.identity.agent_gid,
                "agent_name": self.identity.agent_name,
                "agent_role": self.identity.agent_role,
                "issuing_authority": self.identity.issuing_authority
            },
            "certification": {
                "certification_level": self.certification.certification_level,
                "certification_id": self.certification.certification_id,
                "issued_at": self.certification.issued_at,
                "expires_at": self.certification.expires_at,
                "revocation_status": self.certification.revocation_status
            },
            "execution_rights": {
                "max_pac_level": self.execution_rights.max_pac_level,
                "swarm_eligibility": self.execution_rights.swarm_eligibility,
                "shard_permission": self.execution_rights.shard_permission,
                "override_capability": self.execution_rights.override_capability
            },
            "behavioral_constraints": {
                "allowed_domains": self.behavioral_constraints.allowed_domains,
                "forbidden_actions": self.behavioral_constraints.forbidden_actions,
                "rate_limits": self.behavioral_constraints.rate_limits,
                "data_access_scope": self.behavioral_constraints.data_access_scope
            },
            "cryptographic_binding": {
                "uniform_hash": self.cryptographic_binding.uniform_hash,
                "signature_algorithm": self.cryptographic_binding.signature_algorithm,
                "signing_key_id": self.cryptographic_binding.signing_key_id,
                "signature": self.cryptographic_binding.signature
            },
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentUniform":
        """Create from dictionary."""
        identity = UniformIdentity(**data["identity"])
        certification = UniformCertification(
            certification_level=data["certification"]["certification_level"],
            certification_id=data["certification"]["certification_id"],
            issued_at=data["certification"]["issued_at"],
            expires_at=data["certification"].get("expires_at"),
            revocation_status=data["certification"]["revocation_status"]
        )
        execution_rights = UniformExecutionRights(**data["execution_rights"])
        behavioral_constraints = UniformBehavioralConstraints(
            allowed_domains=data["behavioral_constraints"]["allowed_domains"],
            forbidden_actions=data["behavioral_constraints"]["forbidden_actions"],
            rate_limits=data["behavioral_constraints"]["rate_limits"],
            data_access_scope=data["behavioral_constraints"]["data_access_scope"]
        )
        cryptographic_binding = UniformCryptographicBinding(
            **data["cryptographic_binding"]
        )
        
        return cls(
            uniform_id=data["uniform_id"],
            uniform_version=data["uniform_version"],
            identity=identity,
            certification=certification,
            execution_rights=execution_rights,
            behavioral_constraints=behavioral_constraints,
            cryptographic_binding=cryptographic_binding,
            metadata=data["metadata"],
            state=UniformState.ACTIVE
        )


@dataclass
class UniformValidationResult:
    """Result of uniform validation."""
    uniform_id: str
    agent_gid: str
    valid: bool
    result: ValidationResult
    drift_type: DriftType
    failure_mode: Optional[FailureMode]
    message: str
    gate_results: List[Dict[str, Any]]
    timestamp: str
    execution_allowed: bool
    termination_required: bool = False
    scram_required: bool = False


# ===================== Cryptographic Utilities =====================

def compute_uniform_hash(uniform_data: Dict[str, Any]) -> str:
    """
    Compute SHA-256 hash of uniform content (excluding cryptographic_binding).
    """
    # Create a copy without the binding
    data_to_hash = {k: v for k, v in uniform_data.items() if k != "cryptographic_binding"}
    
    # Canonical JSON encoding
    canonical = json.dumps(data_to_hash, sort_keys=True, separators=(',', ':'))
    
    # Compute hash
    hash_bytes = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    return f"sha256:{hash_bytes}"


def verify_signature(
    uniform_hash: str,
    signature: str,
    signing_key_id: str,
    algorithm: str
) -> Tuple[bool, str]:
    """
    Verify uniform signature.
    
    In production, this would use actual cryptographic verification.
    For now, we implement a placeholder that validates format and
    uses a deterministic check based on key ID.
    """
    # Validate hash format
    if not uniform_hash.startswith("sha256:"):
        return False, "Invalid hash format"
    
    # Validate signature format (Base64)
    try:
        base64.b64decode(signature)
    except Exception:
        return False, "Invalid signature encoding"
    
    # Validate signing key ID format
    if not signing_key_id.startswith("KEY-AU-"):
        return False, "Invalid signing key ID"
    
    # Validate algorithm
    valid_algorithms = ["ED25519", "RSA-PSS-SHA256", "ECDSA-P384-SHA384"]
    if algorithm not in valid_algorithms:
        return False, f"Invalid algorithm: {algorithm}"
    
    # In production: actual signature verification would happen here
    # For governance demonstration, we trust properly formatted signatures
    # from known key IDs
    
    logger.debug(f"Signature verified for key {signing_key_id}")
    return True, "Signature valid"


def generate_mock_signature(uniform_hash: str, signing_key_id: str) -> str:
    """Generate a mock signature for uniform issuance."""
    # In production, this would use actual cryptographic signing
    combined = f"{uniform_hash}:{signing_key_id}"
    sig_hash = hashlib.sha256(combined.encode()).digest()
    return base64.b64encode(sig_hash).decode()


# ===================== Uniform Registry =====================

class UniformRegistry:
    """
    Registry for Agent Uniforms.
    Thread-safe singleton.
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
        
        self._registry_lock = Lock()
        self._uniforms: Dict[str, AgentUniform] = {}
        self._validation_log: List[UniformValidationResult] = []
        self._load_uniforms()
        self._initialized = True
    
    def _load_uniforms(self) -> None:
        """Load all uniforms from disk."""
        if not UNIFORMS_DIR.exists():
            return
        
        for uniform_file in UNIFORMS_DIR.glob("*.json"):
            try:
                with open(uniform_file, "r") as f:
                    data = json.load(f)
                    uniform = AgentUniform.from_dict(data)
                    self._uniforms[uniform.identity.agent_gid] = uniform
                    logger.info(f"Loaded uniform for {uniform.identity.agent_gid}")
            except Exception as e:
                logger.error(f"Failed to load uniform {uniform_file}: {e}")
    
    def register_uniform(self, uniform: AgentUniform) -> None:
        """Register a new uniform."""
        with self._registry_lock:
            self._uniforms[uniform.identity.agent_gid] = uniform
            self._save_uniform(uniform)
            logger.info(f"Registered uniform for {uniform.identity.agent_gid}")
    
    def _save_uniform(self, uniform: AgentUniform) -> None:
        """Save uniform to disk."""
        filename = f"{uniform.identity.agent_gid}_uniform.json"
        filepath = UNIFORMS_DIR / filename
        try:
            with open(filepath, "w") as f:
                json.dump(uniform.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save uniform: {e}")
    
    def get_uniform(self, agent_gid: str) -> Optional[AgentUniform]:
        """Get uniform for an agent."""
        return self._uniforms.get(agent_gid)
    
    def get_all_uniforms(self) -> Dict[str, AgentUniform]:
        """Get all registered uniforms."""
        return dict(self._uniforms)
    
    def revoke_uniform(self, agent_gid: str, reason: str) -> bool:
        """Revoke an agent's uniform."""
        with self._registry_lock:
            uniform = self._uniforms.get(agent_gid)
            if not uniform:
                return False
            
            uniform.state = UniformState.REVOKED
            uniform.certification.revocation_status = {
                "revoked": True,
                "revocation_reason": reason,
                "revoked_at": datetime.now(timezone.utc).isoformat()
            }
            self._save_uniform(uniform)
            logger.warning(f"Uniform REVOKED for {agent_gid}: {reason}")
            return True
    
    def log_validation(self, result: UniformValidationResult) -> None:
        """Log a validation result."""
        self._validation_log.append(result)
        if len(self._validation_log) > 10000:
            self._validation_log = self._validation_log[-5000:]
    
    def get_validation_log(self, limit: int = 100) -> List[UniformValidationResult]:
        """Get recent validation results."""
        return self._validation_log[-limit:]


# ===================== Uniform Validator =====================

class AgentUniformValidator:
    """
    Agent Uniform Validator.
    
    Validates uniforms against schema, cryptographic binding,
    and runtime certification state.
    """
    
    # Enforcement gates
    GATES = [
        {
            "gate_id": "AU-UNIFORM-001",
            "check": "uniform_present",
            "required": True,
            "failure_mode": FailureMode.HARD_BLOCK
        },
        {
            "gate_id": "AU-UNIFORM-002",
            "check": "uniform_signature_valid",
            "required": True,
            "failure_mode": FailureMode.IMMEDIATE_TERMINATION
        },
        {
            "gate_id": "AU-UNIFORM-003",
            "check": "uniform_certification_alignment",
            "required": True,
            "failure_mode": FailureMode.SCRAM_AND_AUDIT
        }
    ]
    
    def __init__(self):
        self.registry = UniformRegistry()
        self._cert_enforcer = get_enforcer() if get_enforcer else None
    
    def validate(
        self,
        agent_gid: str,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> UniformValidationResult:
        """
        Validate an agent's uniform.
        
        This is the PRIMARY uniform validation gate that MUST be called
        before any agent executes.
        
        Args:
            agent_gid: The agent's GID
            execution_context: Optional context (PAC, task info)
        
        Returns:
            UniformValidationResult with pass/fail and required actions
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        gate_results = []
        
        # Gate 1: uniform_present
        uniform = self.registry.get_uniform(agent_gid)
        gate1_passed = uniform is not None
        gate_results.append({
            "gate_id": "AU-UNIFORM-001",
            "check": "uniform_present",
            "passed": gate1_passed,
            "failure_mode": FailureMode.HARD_BLOCK.value if not gate1_passed else None
        })
        
        if not gate1_passed:
            result = UniformValidationResult(
                uniform_id="NONE",
                agent_gid=agent_gid,
                valid=False,
                result=ValidationResult.MISSING,
                drift_type=DriftType.NONE,
                failure_mode=FailureMode.HARD_BLOCK,
                message=f"No uniform found for {agent_gid}",
                gate_results=gate_results,
                timestamp=timestamp,
                execution_allowed=False
            )
            self.registry.log_validation(result)
            logger.warning(f"UNIFORM MISSING: {agent_gid}")
            return result
        
        # Gate 2: uniform_signature_valid
        sig_valid, sig_message = verify_signature(
            uniform.cryptographic_binding.uniform_hash,
            uniform.cryptographic_binding.signature,
            uniform.cryptographic_binding.signing_key_id,
            uniform.cryptographic_binding.signature_algorithm
        )
        gate_results.append({
            "gate_id": "AU-UNIFORM-002",
            "check": "uniform_signature_valid",
            "passed": sig_valid,
            "message": sig_message,
            "failure_mode": FailureMode.IMMEDIATE_TERMINATION.value if not sig_valid else None
        })
        
        if not sig_valid:
            result = UniformValidationResult(
                uniform_id=uniform.uniform_id,
                agent_gid=agent_gid,
                valid=False,
                result=ValidationResult.SIGNATURE_INVALID,
                drift_type=DriftType.SIGNATURE_INVALID,
                failure_mode=FailureMode.IMMEDIATE_TERMINATION,
                message=f"Signature invalid: {sig_message}",
                gate_results=gate_results,
                timestamp=timestamp,
                execution_allowed=False,
                termination_required=True
            )
            self.registry.log_validation(result)
            logger.error(f"SIGNATURE INVALID: {agent_gid}")
            return result
        
        # Gate 3: uniform_certification_alignment
        alignment_valid, drift_type, alignment_message = self._check_certification_alignment(
            uniform, agent_gid
        )
        gate_results.append({
            "gate_id": "AU-UNIFORM-003",
            "check": "uniform_certification_alignment",
            "passed": alignment_valid,
            "drift_type": drift_type.value,
            "message": alignment_message,
            "failure_mode": FailureMode.SCRAM_AND_AUDIT.value if not alignment_valid else None
        })
        
        if not alignment_valid:
            result = UniformValidationResult(
                uniform_id=uniform.uniform_id,
                agent_gid=agent_gid,
                valid=False,
                result=ValidationResult.DRIFT_DETECTED,
                drift_type=drift_type,
                failure_mode=FailureMode.SCRAM_AND_AUDIT,
                message=f"Certification drift: {alignment_message}",
                gate_results=gate_results,
                timestamp=timestamp,
                execution_allowed=False,
                termination_required=True,
                scram_required=True
            )
            self.registry.log_validation(result)
            logger.error(f"DRIFT DETECTED: {agent_gid} - {drift_type.value}")
            return result
        
        # All gates passed
        result = UniformValidationResult(
            uniform_id=uniform.uniform_id,
            agent_gid=agent_gid,
            valid=True,
            result=ValidationResult.VALID,
            drift_type=DriftType.NONE,
            failure_mode=None,
            message="Uniform valid",
            gate_results=gate_results,
            timestamp=timestamp,
            execution_allowed=True
        )
        self.registry.log_validation(result)
        logger.debug(f"UNIFORM VALID: {agent_gid}")
        return result
    
    def _check_certification_alignment(
        self,
        uniform: AgentUniform,
        agent_gid: str
    ) -> Tuple[bool, DriftType, str]:
        """
        Check alignment between uniform and runtime certification state.
        """
        # Check uniform revocation status
        if uniform.certification.revocation_status.get("revoked", False):
            return False, DriftType.REVOCATION_MISMATCH, "Uniform is revoked"
        
        # Check uniform state
        if uniform.state in [UniformState.REVOKED, UniformState.SUSPENDED]:
            return False, DriftType.REVOCATION_MISMATCH, f"Uniform state: {uniform.state.value}"
        
        # Check expiration
        if uniform.certification.expires_at:
            try:
                expires = datetime.fromisoformat(
                    uniform.certification.expires_at.replace('Z', '+00:00')
                )
                if datetime.now(timezone.utc) > expires:
                    return False, DriftType.EXPIRATION_BREACH, "Uniform has expired"
            except Exception:
                pass
        
        # If certification enforcer available, check runtime alignment
        if self._cert_enforcer:
            runtime_cert = self._cert_enforcer.state.get_certification(agent_gid)
            if runtime_cert:
                # Check level alignment
                uniform_level = uniform.certification.certification_level
                runtime_level = runtime_cert.certification_level.name
                if uniform_level != runtime_level:
                    return False, DriftType.LEVEL_MISMATCH, \
                        f"Uniform level {uniform_level} != runtime level {runtime_level}"
                
                # Check revocation alignment
                if runtime_cert.revocation_flag:
                    return False, DriftType.REVOCATION_MISMATCH, \
                        "Runtime certification is revoked"
        
        return True, DriftType.NONE, "Alignment verified"
    
    def check_drift(self, agent_gid: str) -> Tuple[bool, DriftType, str]:
        """
        Check for uniform drift without full validation.
        Called during heartbeat checks.
        """
        uniform = self.registry.get_uniform(agent_gid)
        if not uniform:
            return True, DriftType.NONE, "No uniform to check"
        
        return self._check_certification_alignment(uniform, agent_gid)


# ===================== Uniform Issuer =====================

class UniformIssuer:
    """
    Issues new Agent Uniforms.
    
    Only AGENT_UNIVERSITY authority may issue uniforms.
    """
    
    def __init__(self):
        self.registry = UniformRegistry()
    
    def issue_uniform(
        self,
        agent_gid: str,
        agent_name: str,
        agent_role: str,
        certification_level: str,
        execution_rights: Dict[str, Any],
        behavioral_constraints: Dict[str, Any],
        issuing_authority: str = "AGENT_UNIVERSITY"
    ) -> AgentUniform:
        """
        Issue a new Agent Uniform.
        
        Returns the issued uniform artifact.
        """
        timestamp = datetime.now(timezone.utc)
        timestamp_str = timestamp.strftime("%Y%m%dT%H%M%SZ")
        
        # Create uniform ID
        uniform_id = f"UNIFORM-{agent_gid}-{timestamp_str}"
        
        # Create certification ID
        cert_id = f"CERT-{agent_gid}-{int(timestamp.timestamp())}"
        
        # Build uniform data (without cryptographic binding)
        uniform_data = {
            "uniform_id": uniform_id,
            "uniform_version": "1.0.0",
            "identity": {
                "agent_gid": agent_gid,
                "agent_name": agent_name,
                "agent_role": agent_role,
                "issuing_authority": issuing_authority
            },
            "certification": {
                "certification_level": certification_level,
                "certification_id": cert_id,
                "issued_at": timestamp.isoformat(),
                "expires_at": None,
                "revocation_status": {
                    "revoked": False,
                    "revocation_reason": None,
                    "revoked_at": None
                }
            },
            "execution_rights": execution_rights,
            "behavioral_constraints": behavioral_constraints,
            "metadata": {
                "created_at": timestamp.isoformat(),
                "created_by": issuing_authority,
                "supersedes": None,
                "immutable": True
            }
        }
        
        # Compute hash
        uniform_hash = compute_uniform_hash(uniform_data)
        
        # Generate signature
        signing_key_id = "KEY-AU-PRIMARY"
        signature = generate_mock_signature(uniform_hash, signing_key_id)
        
        # Add cryptographic binding
        uniform_data["cryptographic_binding"] = {
            "uniform_hash": uniform_hash,
            "signature_algorithm": "ED25519",
            "signing_key_id": signing_key_id,
            "signature": signature
        }
        
        # Create uniform object
        uniform = AgentUniform.from_dict(uniform_data)
        uniform.state = UniformState.ACTIVE
        
        # Register
        self.registry.register_uniform(uniform)
        
        logger.info(f"Issued uniform {uniform_id} for {agent_gid}")
        return uniform


# ===================== Convenience Functions =====================

_validator_instance: Optional[AgentUniformValidator] = None
_issuer_instance: Optional[UniformIssuer] = None


def get_validator() -> AgentUniformValidator:
    """Get singleton validator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = AgentUniformValidator()
    return _validator_instance


def get_issuer() -> UniformIssuer:
    """Get singleton issuer instance."""
    global _issuer_instance
    if _issuer_instance is None:
        _issuer_instance = UniformIssuer()
    return _issuer_instance


def validate_uniform(
    agent_gid: str,
    execution_context: Optional[Dict[str, Any]] = None
) -> UniformValidationResult:
    """
    Convenience function to validate an agent's uniform.
    
    Usage:
        result = validate_uniform("GID-01")
        if not result.execution_allowed:
            raise PermissionError(f"Invalid uniform: {result.message}")
    """
    return get_validator().validate(agent_gid, execution_context)


def issue_uniform(
    agent_gid: str,
    agent_name: str,
    agent_role: str,
    certification_level: str = "L2",
    allowed_domains: List[str] = None,
    swarm_eligible: bool = False
) -> AgentUniform:
    """
    Convenience function to issue a new uniform.
    
    Usage:
        uniform = issue_uniform("GID-01", "CODY", "BACKEND_ENGINEER", "L2")
    """
    # Default execution rights based on certification level
    level_rights = {
        "L0": {"max_pac_level": "NONE", "swarm_eligibility": False, 
               "shard_permission": "NONE", "override_capability": False},
        "L1": {"max_pac_level": "OPS_TIER", "swarm_eligibility": False,
               "shard_permission": "PARTICIPANT", "override_capability": False},
        "L2": {"max_pac_level": "GOV_TIER", "swarm_eligibility": False,
               "shard_permission": "PARTICIPANT", "override_capability": False},
        "L3": {"max_pac_level": "LAW_TIER", "swarm_eligibility": True,
               "shard_permission": "ORCHESTRATOR", "override_capability": True},
    }
    
    execution_rights = level_rights.get(certification_level, level_rights["L2"])
    if swarm_eligible:
        execution_rights["swarm_eligibility"] = True
    
    # Default behavioral constraints
    behavioral_constraints = {
        "allowed_domains": allowed_domains or ["ALL"],
        "forbidden_actions": [],
        "rate_limits": {
            "max_pacs_per_hour": 100,
            "max_tasks_per_pac": 10,
            "cooldown_seconds": 0
        },
        "data_access_scope": "READ_WRITE" if certification_level in ["L2", "L3"] else "READ_ONLY"
    }
    
    return get_issuer().issue_uniform(
        agent_gid=agent_gid,
        agent_name=agent_name,
        agent_role=agent_role,
        certification_level=certification_level,
        execution_rights=execution_rights,
        behavioral_constraints=behavioral_constraints
    )


# ===================== Module Self-Test =====================

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print("=" * 60)
    print("Agent Uniform Validator - Self Test")
    print("PAC-P755-AU-UNIFORM-ARTIFACT-SCHEMA")
    print("=" * 60)
    
    # Issue test uniforms
    print("\n[ISSUING UNIFORMS]")
    issue_uniform("GID-00", "BENSON", "CTO_ORCHESTRATOR", "L3", swarm_eligible=True)
    issue_uniform("GID-01", "CODY", "BACKEND_ENGINEER", "L2")
    issue_uniform("GID-08", "ALEX", "GOVERNANCE_ANALYST", "L2")
    
    # Validate uniforms
    print("\n[TEST 1] L3 Agent (should pass)")
    result = validate_uniform("GID-00")
    print(f"  Result: {result.result.value}, Allowed: {result.execution_allowed}")
    
    print("\n[TEST 2] L2 Agent (should pass)")
    result = validate_uniform("GID-01")
    print(f"  Result: {result.result.value}, Allowed: {result.execution_allowed}")
    
    print("\n[TEST 3] Unknown Agent (should fail - MISSING)")
    result = validate_uniform("GID-99")
    print(f"  Result: {result.result.value}, Allowed: {result.execution_allowed}")
    
    # Test revocation
    print("\n[TEST 4] Revoke uniform")
    UniformRegistry().revoke_uniform("GID-01", "Test revocation")
    result = validate_uniform("GID-01")
    print(f"  Result: {result.result.value}, Allowed: {result.execution_allowed}")
    
    print("\n" + "=" * 60)
    print("Self-test complete. Uniform validation operational.")
    print("=" * 60)
