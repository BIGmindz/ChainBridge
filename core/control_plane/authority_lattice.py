"""
Authority Lattice (AL) Primitive
PAC-JEFFREY-CTRLPLANE-HARDENING-P1-001 | Task 1

GOVERNANCE_TIER: LAW
DRIFT_TOLERANCE: ZERO
FAIL_CLOSED: true

Authority is not a scalar boolean. It is a multi-dimensional coordinate:
  Authority = Identity × Context × Hardware × Time

Any missing coordinate collapses authority to ZERO.
No permanent elevation possible — all authority is contextual.

INVARIANTS ENFORCED:
- INV-AUTHORITY-BOUNDED: Authority cannot exceed lattice bounds
- INV-SCRAM-SUPREMACY: SCRAM overrides all authority
- INV-NO-PERMANENT-ELEVATION: All authority is context-dependent

Author: BENSON-GID-00
Authority: ARCHITECT-JEFFREY (STRATEGY_ONLY)
"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum, auto
from typing import (
    Any,
    Callable,
    Dict,
    Final,
    FrozenSet,
    Generic,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
    runtime_checkable,
)


# =============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# =============================================================================

VERSION: Final[str] = "1.0.0"
PAC_REFERENCE: Final[str] = "PAC-JEFFREY-CTRLPLANE-HARDENING-P1-001"

# Authority evaluation constants
LATTICE_DIMENSION_COUNT: Final[int] = 4  # Identity, Context, Hardware, Time
AUTHORITY_EVALUATION_TIMEOUT_MS: Final[int] = 100
HARDWARE_ATTESTATION_STALENESS_MS: Final[int] = 60000  # 1 minute

# Invariant identifiers
INV_AUTHORITY_BOUNDED: Final[str] = "INV-AUTHORITY-BOUNDED"
INV_SCRAM_SUPREMACY: Final[str] = "INV-SCRAM-SUPREMACY"
INV_NO_PERMANENT_ELEVATION: Final[str] = "INV-NO-PERMANENT-ELEVATION"


# =============================================================================
# SECTION 2: ENUMERATIONS
# =============================================================================

class AuthorityLevel(Enum):
    """
    Authority levels in ascending order.
    
    Authority is NOT a binary concept — it's a graduated scale.
    Each level has specific capabilities and restrictions.
    """
    ZERO = 0           # No authority — blocked
    OBSERVER = 1       # Read-only access
    OPERATOR = 2       # Standard operational authority
    ELEVATED = 3       # Elevated access (time-bound)
    CRITICAL = 4       # Critical operations (requires confirmation)
    CONSTITUTIONAL = 5 # System-level (SCRAM, governance)
    
    def __ge__(self, other: "AuthorityLevel") -> bool:
        return self.value >= other.value
    
    def __gt__(self, other: "AuthorityLevel") -> bool:
        return self.value > other.value
    
    def __le__(self, other: "AuthorityLevel") -> bool:
        return self.value <= other.value
    
    def __lt__(self, other: "AuthorityLevel") -> bool:
        return self.value < other.value


class ContextType(Enum):
    """Context in which authority is exercised."""
    UNKNOWN = auto()       # Context not established
    DEVELOPMENT = auto()   # Development environment
    STAGING = auto()       # Staging environment
    PRODUCTION = auto()    # Production environment
    EMERGENCY = auto()     # Emergency context (SCRAM active)
    AUDIT = auto()         # Audit/review context


class HardwareBindingType(Enum):
    """Type of hardware binding for authority."""
    NONE = auto()          # No hardware binding (authority reduced)
    SOFTWARE_TOKEN = auto() # Software-based token
    TPM = auto()           # Trusted Platform Module
    HSM = auto()           # Hardware Security Module
    SECURE_ENCLAVE = auto() # Secure enclave (TEE)


class EvaluationResult(Enum):
    """Result of authority evaluation."""
    GRANTED = auto()       # Authority granted
    DENIED = auto()        # Authority denied
    INSUFFICIENT = auto()  # Insufficient coordinates
    EXPIRED = auto()       # Time coordinate expired
    SCRAM_BLOCKED = auto() # Blocked by SCRAM


# =============================================================================
# SECTION 3: CORE DATA STRUCTURES
# =============================================================================

@dataclass(frozen=True)
class IdentityCoordinate:
    """
    Identity dimension of authority.
    
    WHO is requesting authority?
    """
    principal_id: str           # Unique identifier
    principal_type: str         # "HUMAN", "AGENT", "SYSTEM"
    gid: Optional[str]          # Governance ID (for agents)
    session_id: str             # Current session
    authenticated_at: datetime  # Authentication timestamp
    authentication_method: str  # "PASSWORD", "MFA", "CERTIFICATE", etc.
    
    def is_valid(self) -> bool:
        """Check if identity coordinate is valid."""
        if not self.principal_id or not self.session_id:
            return False
        if not self.authenticated_at:
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "principal_id": self.principal_id,
            "principal_type": self.principal_type,
            "gid": self.gid,
            "session_id": self.session_id,
            "authenticated_at": self.authenticated_at.isoformat(),
            "authentication_method": self.authentication_method,
        }


@dataclass(frozen=True)
class ContextCoordinate:
    """
    Context dimension of authority.
    
    WHERE is authority being exercised?
    """
    context_type: ContextType
    environment: str            # Environment identifier
    operation_type: str         # What operation is requested
    resource_id: Optional[str]  # Target resource
    scram_active: bool          # Is SCRAM active?
    
    def is_valid(self) -> bool:
        """Check if context coordinate is valid."""
        if self.context_type == ContextType.UNKNOWN:
            return False
        if self.scram_active:
            # SCRAM blocks all non-constitutional authority
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_type": self.context_type.name,
            "environment": self.environment,
            "operation_type": self.operation_type,
            "resource_id": self.resource_id,
            "scram_active": self.scram_active,
        }


@dataclass(frozen=True)
class HardwareCoordinate:
    """
    Hardware dimension of authority.
    
    WHAT device is being used?
    """
    binding_type: HardwareBindingType
    device_id: str              # Unique device identifier
    attestation_token: str      # Hardware attestation
    attested_at: datetime       # When attestation was performed
    trusted: bool               # Is device trusted?
    
    def is_valid(self, staleness_threshold_ms: int = HARDWARE_ATTESTATION_STALENESS_MS) -> bool:
        """Check if hardware coordinate is valid."""
        if self.binding_type == HardwareBindingType.NONE:
            return False
        if not self.trusted:
            return False
        
        # Check attestation freshness
        now = datetime.now(timezone.utc)
        age_ms = (now - self.attested_at).total_seconds() * 1000
        if age_ms > staleness_threshold_ms:
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "binding_type": self.binding_type.name,
            "device_id": self.device_id,
            "attestation_token": self.attestation_token[:16] + "...",
            "attested_at": self.attested_at.isoformat(),
            "trusted": self.trusted,
        }


@dataclass(frozen=True)
class TimeCoordinate:
    """
    Time dimension of authority.
    
    WHEN is authority valid?
    """
    valid_from: datetime        # Authority valid from
    valid_until: datetime       # Authority valid until
    timezone_id: str            # Timezone context
    
    def is_valid(self) -> bool:
        """Check if time coordinate is currently valid."""
        now = datetime.now(timezone.utc)
        return self.valid_from <= now <= self.valid_until
    
    def remaining_seconds(self) -> float:
        """Get remaining validity in seconds."""
        now = datetime.now(timezone.utc)
        if now > self.valid_until:
            return 0.0
        return (self.valid_until - now).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid_from": self.valid_from.isoformat(),
            "valid_until": self.valid_until.isoformat(),
            "timezone_id": self.timezone_id,
            "remaining_seconds": self.remaining_seconds(),
        }


@dataclass(frozen=True)
class AuthorityCoordinate:
    """
    Complete authority coordinate in the lattice.
    
    Authority = Identity × Context × Hardware × Time
    
    ALL coordinates must be valid for authority to be non-zero.
    """
    identity: IdentityCoordinate
    context: ContextCoordinate
    hardware: HardwareCoordinate
    time: TimeCoordinate
    requested_level: AuthorityLevel
    
    def evaluate(self) -> Tuple[AuthorityLevel, EvaluationResult, str]:
        """
        Evaluate authority coordinate.
        
        Returns (granted_level, result, reason).
        
        INVARIANT: Missing coordinate ⇒ authority = ZERO
        """
        # Check SCRAM first (INV-SCRAM-SUPREMACY)
        if self.context.scram_active:
            if self.requested_level != AuthorityLevel.CONSTITUTIONAL:
                return (AuthorityLevel.ZERO, EvaluationResult.SCRAM_BLOCKED, 
                        "SCRAM active - only CONSTITUTIONAL authority permitted")
        
        # Validate each coordinate
        if not self.identity.is_valid():
            return (AuthorityLevel.ZERO, EvaluationResult.INSUFFICIENT,
                    "Invalid identity coordinate")
        
        if not self.context.is_valid():
            return (AuthorityLevel.ZERO, EvaluationResult.INSUFFICIENT,
                    "Invalid context coordinate")
        
        if not self.hardware.is_valid():
            # Hardware not required for OBSERVER level
            if self.requested_level > AuthorityLevel.OBSERVER:
                return (AuthorityLevel.ZERO, EvaluationResult.INSUFFICIENT,
                        "Invalid hardware coordinate")
        
        if not self.time.is_valid():
            return (AuthorityLevel.ZERO, EvaluationResult.EXPIRED,
                    "Time coordinate expired")
        
        # All coordinates valid — grant requested level
        return (self.requested_level, EvaluationResult.GRANTED,
                "Authority granted")
    
    def compute_hash(self) -> str:
        """Compute hash of coordinate for audit."""
        data = {
            "identity": self.identity.to_dict(),
            "context": self.context.to_dict(),
            "hardware": self.hardware.to_dict(),
            "time": self.time.to_dict(),
            "requested_level": self.requested_level.name,
        }
        return hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()[:32]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "context": self.context.to_dict(),
            "hardware": self.hardware.to_dict(),
            "time": self.time.to_dict(),
            "requested_level": self.requested_level.name,
            "coordinate_hash": self.compute_hash(),
        }


# =============================================================================
# SECTION 4: LATTICE NODE
# =============================================================================

@dataclass
class LatticeNode:
    """
    Node in the authority lattice.
    
    Represents a principal's position in the authority space.
    """
    node_id: str
    principal_id: str
    base_level: AuthorityLevel
    effective_level: AuthorityLevel
    coordinates: Optional[AuthorityCoordinate]
    created_at: datetime
    last_evaluated_at: Optional[datetime]
    evaluation_count: int = 0
    grant_count: int = 0
    deny_count: int = 0
    
    def update_evaluation(
        self,
        result: EvaluationResult,
        granted_level: AuthorityLevel,
    ) -> None:
        """Update node with evaluation result."""
        self.last_evaluated_at = datetime.now(timezone.utc)
        self.evaluation_count += 1
        self.effective_level = granted_level
        
        if result == EvaluationResult.GRANTED:
            self.grant_count += 1
        else:
            self.deny_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "principal_id": self.principal_id,
            "base_level": self.base_level.name,
            "effective_level": self.effective_level.name,
            "created_at": self.created_at.isoformat(),
            "last_evaluated_at": self.last_evaluated_at.isoformat() if self.last_evaluated_at else None,
            "evaluation_count": self.evaluation_count,
            "grant_count": self.grant_count,
            "deny_count": self.deny_count,
        }


# =============================================================================
# SECTION 5: AUTHORITY LATTICE
# =============================================================================

@dataclass(frozen=True)
class EvaluationRecord:
    """Immutable record of authority evaluation."""
    record_id: str
    coordinate_hash: str
    principal_id: str
    requested_level: AuthorityLevel
    granted_level: AuthorityLevel
    result: EvaluationResult
    reason: str
    evaluated_at: datetime
    context_type: ContextType
    scram_active: bool


class AuthorityLattice:
    """
    Authority Lattice (AL) implementation.
    
    The lattice is a multi-dimensional space where authority is evaluated
    based on coordinates: Identity × Context × Hardware × Time.
    
    INVARIANTS:
    - INV-AUTHORITY-BOUNDED: Authority cannot exceed lattice bounds
    - INV-SCRAM-SUPREMACY: SCRAM overrides all non-constitutional authority
    - INV-NO-PERMANENT-ELEVATION: All authority is context-dependent
    """
    
    def __init__(
        self,
        max_level: AuthorityLevel = AuthorityLevel.CRITICAL,
    ) -> None:
        """
        Initialize authority lattice.
        
        Args:
            max_level: Maximum authority level this lattice can grant.
                       CONSTITUTIONAL requires special lattice.
        """
        self._max_level = max_level
        self._nodes: Dict[str, LatticeNode] = {}
        self._evaluation_log: List[EvaluationRecord] = []
        self._scram_active = False
        self._lock = threading.Lock()
    
    @property
    def max_level(self) -> AuthorityLevel:
        return self._max_level
    
    @property
    def scram_active(self) -> bool:
        return self._scram_active
    
    def activate_scram(self) -> None:
        """Activate SCRAM — collapse all authority."""
        with self._lock:
            self._scram_active = True
            # Collapse all nodes to ZERO
            for node in self._nodes.values():
                node.effective_level = AuthorityLevel.ZERO
    
    def deactivate_scram(self, authorization_code: str) -> bool:
        """Deactivate SCRAM — requires authorization."""
        if len(authorization_code) < 16:
            return False
        
        with self._lock:
            self._scram_active = False
            return True
    
    def register_principal(
        self,
        principal_id: str,
        base_level: AuthorityLevel = AuthorityLevel.OBSERVER,
    ) -> LatticeNode:
        """Register a principal in the lattice."""
        with self._lock:
            node_id = f"NODE-{uuid.uuid4().hex[:12].upper()}"
            node = LatticeNode(
                node_id=node_id,
                principal_id=principal_id,
                base_level=base_level,
                effective_level=AuthorityLevel.ZERO,  # Starts at ZERO
                coordinates=None,
                created_at=datetime.now(timezone.utc),
                last_evaluated_at=None,
            )
            self._nodes[principal_id] = node
            return node
    
    def evaluate_authority(
        self,
        coordinate: AuthorityCoordinate,
    ) -> Tuple[AuthorityLevel, EvaluationResult, str]:
        """
        Evaluate authority for a coordinate.
        
        Returns (granted_level, result, reason).
        """
        with self._lock:
            # Override coordinate SCRAM status with lattice status
            if self._scram_active:
                context_with_scram = ContextCoordinate(
                    context_type=coordinate.context.context_type,
                    environment=coordinate.context.environment,
                    operation_type=coordinate.context.operation_type,
                    resource_id=coordinate.context.resource_id,
                    scram_active=True,
                )
                coordinate = AuthorityCoordinate(
                    identity=coordinate.identity,
                    context=context_with_scram,
                    hardware=coordinate.hardware,
                    time=coordinate.time,
                    requested_level=coordinate.requested_level,
                )
            
            # Evaluate coordinate
            granted_level, result, reason = coordinate.evaluate()
            
            # Apply lattice bounds (INV-AUTHORITY-BOUNDED)
            if granted_level > self._max_level:
                granted_level = self._max_level
                reason = f"Bounded to lattice max: {self._max_level.name}"
            
            # Update node if registered
            principal_id = coordinate.identity.principal_id
            if principal_id in self._nodes:
                node = self._nodes[principal_id]
                node.coordinates = coordinate
                node.update_evaluation(result, granted_level)
            
            # Log evaluation
            record = EvaluationRecord(
                record_id=f"EVAL-{uuid.uuid4().hex[:12].upper()}",
                coordinate_hash=coordinate.compute_hash(),
                principal_id=principal_id,
                requested_level=coordinate.requested_level,
                granted_level=granted_level,
                result=result,
                reason=reason,
                evaluated_at=datetime.now(timezone.utc),
                context_type=coordinate.context.context_type,
                scram_active=self._scram_active,
            )
            self._evaluation_log.append(record)
            
            return (granted_level, result, reason)
    
    def get_effective_authority(
        self,
        principal_id: str,
    ) -> AuthorityLevel:
        """Get current effective authority for a principal."""
        with self._lock:
            if principal_id not in self._nodes:
                return AuthorityLevel.ZERO
            
            node = self._nodes[principal_id]
            
            # Check SCRAM
            if self._scram_active:
                return AuthorityLevel.ZERO
            
            # Re-evaluate time coordinate if exists
            if node.coordinates and not node.coordinates.time.is_valid():
                node.effective_level = AuthorityLevel.ZERO
            
            return node.effective_level
    
    def require_authority(
        self,
        principal_id: str,
        required_level: AuthorityLevel,
    ) -> Tuple[bool, str]:
        """
        Check if principal has required authority.
        
        Returns (has_authority, reason).
        """
        effective = self.get_effective_authority(principal_id)
        
        if effective >= required_level:
            return (True, f"Authority sufficient: {effective.name} >= {required_level.name}")
        else:
            return (False, f"Insufficient authority: {effective.name} < {required_level.name}")
    
    def get_node(self, principal_id: str) -> Optional[LatticeNode]:
        """Get lattice node for principal."""
        return self._nodes.get(principal_id)
    
    def get_evaluation_log(self) -> Sequence[EvaluationRecord]:
        """Get evaluation log."""
        return tuple(self._evaluation_log)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get lattice statistics."""
        total_evals = len(self._evaluation_log)
        grants = sum(1 for r in self._evaluation_log if r.result == EvaluationResult.GRANTED)
        denies = total_evals - grants
        
        return {
            "node_count": len(self._nodes),
            "evaluation_count": total_evals,
            "grant_count": grants,
            "deny_count": denies,
            "grant_rate": grants / total_evals if total_evals > 0 else 0.0,
            "scram_active": self._scram_active,
            "max_level": self._max_level.name,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_level": self._max_level.name,
            "scram_active": self._scram_active,
            "statistics": self.get_statistics(),
        }


# =============================================================================
# SECTION 6: AUTHORITY BUILDER
# =============================================================================

class AuthorityCoordinateBuilder:
    """Builder for constructing authority coordinates."""
    
    def __init__(self) -> None:
        self._identity: Optional[IdentityCoordinate] = None
        self._context: Optional[ContextCoordinate] = None
        self._hardware: Optional[HardwareCoordinate] = None
        self._time: Optional[TimeCoordinate] = None
        self._requested_level: AuthorityLevel = AuthorityLevel.OBSERVER
    
    def with_identity(
        self,
        principal_id: str,
        principal_type: str,
        session_id: str,
        authentication_method: str = "MFA",
        gid: Optional[str] = None,
    ) -> "AuthorityCoordinateBuilder":
        """Set identity coordinate."""
        self._identity = IdentityCoordinate(
            principal_id=principal_id,
            principal_type=principal_type,
            gid=gid,
            session_id=session_id,
            authenticated_at=datetime.now(timezone.utc),
            authentication_method=authentication_method,
        )
        return self
    
    def with_context(
        self,
        context_type: ContextType,
        environment: str,
        operation_type: str,
        resource_id: Optional[str] = None,
        scram_active: bool = False,
    ) -> "AuthorityCoordinateBuilder":
        """Set context coordinate."""
        self._context = ContextCoordinate(
            context_type=context_type,
            environment=environment,
            operation_type=operation_type,
            resource_id=resource_id,
            scram_active=scram_active,
        )
        return self
    
    def with_hardware(
        self,
        binding_type: HardwareBindingType,
        device_id: str,
        attestation_token: str,
        trusted: bool = True,
    ) -> "AuthorityCoordinateBuilder":
        """Set hardware coordinate."""
        self._hardware = HardwareCoordinate(
            binding_type=binding_type,
            device_id=device_id,
            attestation_token=attestation_token,
            attested_at=datetime.now(timezone.utc),
            trusted=trusted,
        )
        return self
    
    def with_time_window(
        self,
        duration_seconds: float,
        timezone_id: str = "UTC",
    ) -> "AuthorityCoordinateBuilder":
        """Set time coordinate with duration from now."""
        now = datetime.now(timezone.utc)
        self._time = TimeCoordinate(
            valid_from=now,
            valid_until=now + timedelta(seconds=duration_seconds),
            timezone_id=timezone_id,
        )
        return self
    
    def with_level(
        self,
        level: AuthorityLevel,
    ) -> "AuthorityCoordinateBuilder":
        """Set requested authority level."""
        self._requested_level = level
        return self
    
    def build(self) -> AuthorityCoordinate:
        """Build the authority coordinate."""
        if not self._identity:
            raise ValueError("Identity coordinate required")
        if not self._context:
            raise ValueError("Context coordinate required")
        if not self._hardware:
            # Default to no hardware binding
            self._hardware = HardwareCoordinate(
                binding_type=HardwareBindingType.NONE,
                device_id="UNKNOWN",
                attestation_token="NONE",
                attested_at=datetime.now(timezone.utc),
                trusted=False,
            )
        if not self._time:
            # Default to 1 hour
            now = datetime.now(timezone.utc)
            self._time = TimeCoordinate(
                valid_from=now,
                valid_until=now + timedelta(hours=1),
                timezone_id="UTC",
            )
        
        return AuthorityCoordinate(
            identity=self._identity,
            context=self._context,
            hardware=self._hardware,
            time=self._time,
            requested_level=self._requested_level,
        )


# =============================================================================
# SECTION 7: SELF-TEST
# =============================================================================

def _run_self_test() -> None:
    """Execute self-test suite."""
    import sys
    import time
    
    print("=" * 72)
    print("  AUTHORITY LATTICE - SELF-TEST")
    print("  PAC-JEFFREY-CTRLPLANE-HARDENING-P1-001 | Task 1")
    print("=" * 72)
    
    tests_passed = 0
    tests_failed = 0
    
    def test(name: str, condition: bool, msg: str = "") -> None:
        nonlocal tests_passed, tests_failed
        if condition:
            print(f"  ✓ {name}")
            tests_passed += 1
        else:
            print(f"  ✗ {name}: {msg}")
            tests_failed += 1
    
    # Test 1: Authority Levels
    print("\n[1] Authority Level Tests")
    test("ZERO < OBSERVER", AuthorityLevel.ZERO < AuthorityLevel.OBSERVER)
    test("OPERATOR > OBSERVER", AuthorityLevel.OPERATOR > AuthorityLevel.OBSERVER)
    test("CONSTITUTIONAL is highest", AuthorityLevel.CONSTITUTIONAL.value == 5)
    test("Level comparison", AuthorityLevel.CRITICAL >= AuthorityLevel.ELEVATED)
    
    # Test 2: Identity Coordinate
    print("\n[2] Identity Coordinate Tests")
    identity = IdentityCoordinate(
        principal_id="USER-001",
        principal_type="HUMAN",
        gid=None,
        session_id="SESSION-123",
        authenticated_at=datetime.now(timezone.utc),
        authentication_method="MFA",
    )
    test("Identity created", identity.principal_id == "USER-001")
    test("Identity valid", identity.is_valid())
    
    # Invalid identity
    invalid_identity = IdentityCoordinate(
        principal_id="",
        principal_type="HUMAN",
        gid=None,
        session_id="",
        authenticated_at=datetime.now(timezone.utc),
        authentication_method="MFA",
    )
    test("Empty identity invalid", not invalid_identity.is_valid())
    
    # Test 3: Context Coordinate
    print("\n[3] Context Coordinate Tests")
    context = ContextCoordinate(
        context_type=ContextType.PRODUCTION,
        environment="PROD-US-EAST",
        operation_type="READ",
        resource_id="RES-001",
        scram_active=False,
    )
    test("Context created", context.context_type == ContextType.PRODUCTION)
    test("Context valid", context.is_valid())
    
    # SCRAM context
    scram_context = ContextCoordinate(
        context_type=ContextType.EMERGENCY,
        environment="PROD",
        operation_type="HALT",
        resource_id=None,
        scram_active=True,
    )
    test("SCRAM context invalid (blocks authority)", not scram_context.is_valid())
    
    # Test 4: Hardware Coordinate
    print("\n[4] Hardware Coordinate Tests")
    hardware = HardwareCoordinate(
        binding_type=HardwareBindingType.TPM,
        device_id="DEV-001",
        attestation_token="ATTEST-" + "X" * 64,
        attested_at=datetime.now(timezone.utc),
        trusted=True,
    )
    test("Hardware created", hardware.binding_type == HardwareBindingType.TPM)
    test("Hardware valid", hardware.is_valid())
    
    # Stale attestation
    stale_hardware = HardwareCoordinate(
        binding_type=HardwareBindingType.TPM,
        device_id="DEV-002",
        attestation_token="STALE",
        attested_at=datetime.now(timezone.utc) - timedelta(hours=1),
        trusted=True,
    )
    test("Stale attestation invalid", not stale_hardware.is_valid())
    
    # Test 5: Time Coordinate
    print("\n[5] Time Coordinate Tests")
    now = datetime.now(timezone.utc)
    time_coord = TimeCoordinate(
        valid_from=now - timedelta(minutes=5),
        valid_until=now + timedelta(hours=1),
        timezone_id="UTC",
    )
    test("Time created", time_coord.timezone_id == "UTC")
    test("Time valid", time_coord.is_valid())
    test("Remaining > 0", time_coord.remaining_seconds() > 0)
    
    # Expired time
    expired_time = TimeCoordinate(
        valid_from=now - timedelta(hours=2),
        valid_until=now - timedelta(hours=1),
        timezone_id="UTC",
    )
    test("Expired time invalid", not expired_time.is_valid())
    test("Expired remaining = 0", expired_time.remaining_seconds() == 0)
    
    # Test 6: Authority Coordinate
    print("\n[6] Authority Coordinate Tests")
    coord = AuthorityCoordinate(
        identity=identity,
        context=context,
        hardware=hardware,
        time=time_coord,
        requested_level=AuthorityLevel.OPERATOR,
    )
    test("Coordinate created", coord.requested_level == AuthorityLevel.OPERATOR)
    test("Coordinate has hash", len(coord.compute_hash()) == 32)
    
    # Evaluate
    level, result, reason = coord.evaluate()
    test("Evaluation grants OPERATOR", level == AuthorityLevel.OPERATOR)
    test("Evaluation result GRANTED", result == EvaluationResult.GRANTED)
    
    # Test 7: Authority Lattice
    print("\n[7] Authority Lattice Tests")
    lattice = AuthorityLattice(max_level=AuthorityLevel.CRITICAL)
    test("Lattice created", lattice.max_level == AuthorityLevel.CRITICAL)
    test("SCRAM not active", not lattice.scram_active)
    
    # Register principal
    node = lattice.register_principal("USER-001", AuthorityLevel.OPERATOR)
    test("Node registered", node.principal_id == "USER-001")
    test("Node starts at ZERO", node.effective_level == AuthorityLevel.ZERO)
    
    # Evaluate authority
    level, result, reason = lattice.evaluate_authority(coord)
    test("Lattice grants authority", level == AuthorityLevel.OPERATOR)
    test("Node updated", lattice.get_node("USER-001").effective_level == AuthorityLevel.OPERATOR)
    
    # Test 8: Lattice Bounds
    print("\n[8] Lattice Bounds Tests (INV-AUTHORITY-BOUNDED)")
    high_coord = AuthorityCoordinate(
        identity=identity,
        context=context,
        hardware=hardware,
        time=time_coord,
        requested_level=AuthorityLevel.CONSTITUTIONAL,  # Above max
    )
    level, result, reason = lattice.evaluate_authority(high_coord)
    test("CONSTITUTIONAL bounded to CRITICAL", level == AuthorityLevel.CRITICAL)
    
    # Test 9: SCRAM Supremacy
    print("\n[9] SCRAM Supremacy Tests (INV-SCRAM-SUPREMACY)")
    lattice.activate_scram()
    test("SCRAM activated", lattice.scram_active)
    
    # Re-evaluate
    level, result, reason = lattice.evaluate_authority(coord)
    test("SCRAM blocks authority", level == AuthorityLevel.ZERO)
    test("Result is SCRAM_BLOCKED", result == EvaluationResult.SCRAM_BLOCKED)
    
    # Effective authority during SCRAM
    eff = lattice.get_effective_authority("USER-001")
    test("Effective is ZERO during SCRAM", eff == AuthorityLevel.ZERO)
    
    # Deactivate SCRAM
    deactivated = lattice.deactivate_scram("0123456789abcdef")
    test("SCRAM deactivated", deactivated and not lattice.scram_active)
    
    # Test 10: Authority Builder
    print("\n[10] Authority Builder Tests")
    builder = AuthorityCoordinateBuilder()
    built_coord = (
        builder
        .with_identity("AGENT-BENSON", "AGENT", "SESS-001", gid="GID-00")
        .with_context(ContextType.PRODUCTION, "PROD", "EXECUTE")
        .with_hardware(HardwareBindingType.HSM, "HSM-001", "TOKEN-XYZ")
        .with_time_window(3600)  # 1 hour
        .with_level(AuthorityLevel.ELEVATED)
        .build()
    )
    test("Built coordinate", built_coord.requested_level == AuthorityLevel.ELEVATED)
    test("Identity is agent", built_coord.identity.principal_type == "AGENT")
    test("Has GID", built_coord.identity.gid == "GID-00")
    
    # Test 11: Require Authority
    print("\n[11] Require Authority Tests")
    lattice2 = AuthorityLattice()
    lattice2.register_principal("TEST-USER")
    
    # Build and evaluate
    test_coord = (
        AuthorityCoordinateBuilder()
        .with_identity("TEST-USER", "HUMAN", "SESS-TEST")
        .with_context(ContextType.DEVELOPMENT, "DEV", "TEST")
        .with_hardware(HardwareBindingType.SOFTWARE_TOKEN, "DEV-001", "TOKEN")
        .with_time_window(3600)
        .with_level(AuthorityLevel.OPERATOR)
        .build()
    )
    lattice2.evaluate_authority(test_coord)
    
    has_auth, msg = lattice2.require_authority("TEST-USER", AuthorityLevel.OBSERVER)
    test("Has OBSERVER", has_auth)
    
    has_auth, msg = lattice2.require_authority("TEST-USER", AuthorityLevel.CRITICAL)
    test("Does not have CRITICAL", not has_auth)
    
    # Test 12: Evaluation Log
    print("\n[12] Evaluation Log Tests")
    log = lattice.get_evaluation_log()
    test("Evaluation log populated", len(log) > 0)
    test("Log has records", all(r.record_id.startswith("EVAL-") for r in log))
    
    # Test 13: Statistics
    print("\n[13] Statistics Tests")
    stats = lattice.get_statistics()
    test("Statistics has node_count", "node_count" in stats)
    test("Statistics has evaluation_count", "evaluation_count" in stats)
    test("Grant rate computed", 0 <= stats["grant_rate"] <= 1)
    
    # Test 14: Time Expiration
    print("\n[14] Time Expiration Tests (INV-NO-PERMANENT-ELEVATION)")
    short_time = TimeCoordinate(
        valid_from=datetime.now(timezone.utc),
        valid_until=datetime.now(timezone.utc) + timedelta(milliseconds=100),
        timezone_id="UTC",
    )
    short_coord = AuthorityCoordinate(
        identity=identity,
        context=context,
        hardware=hardware,
        time=short_time,
        requested_level=AuthorityLevel.ELEVATED,
    )
    
    level, result, _ = short_coord.evaluate()
    test("Short-lived authority granted", result == EvaluationResult.GRANTED)
    
    # Wait for expiration
    time.sleep(0.15)
    level, result, _ = short_coord.evaluate()
    test("Authority expired", result == EvaluationResult.EXPIRED)
    test("Expired level is ZERO", level == AuthorityLevel.ZERO)
    
    # Summary
    print("\n" + "=" * 72)
    total = tests_passed + tests_failed
    print(f"  RESULTS: {tests_passed}/{total} tests passed")
    print("=" * 72)
    
    if tests_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    _run_self_test()
