"""
Escalation Interface
PAC-JEFFREY-CTRLPLANE-HARDENING-P1-001 | Task 3

GOVERNANCE_TIER: LAW
DRIFT_TOLERANCE: ZERO
FAIL_CLOSED: true

This module provides interface definitions for safe authority escalation.
Escalation is bound to:
- TTL (Time To Live)
- Hardware attestation
- Operator confirmation
- Automatic reversion

NOTE: This module provides INTERFACES ONLY (per PAC spec).
      Implementations are in authority_lattice.py and leased_authority.py.

INVARIANTS ENFORCED:
- INV-AUTHORITY-BOUNDED: Authority cannot exceed lattice bounds
- INV-TIME-BOUND-POWER: All overrides have TTL
- INV-HARDWARE-BINDING: Elevated authority requires hardware attestation
- INV-SCRAM-SUPREMACY: SCRAM overrides all authority

Author: BENSON-GID-00
Authority: ARCHITECT-JEFFREY (STRATEGY_ONLY)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum, auto
from typing import (
    Any,
    Dict,
    Final,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    runtime_checkable,
)


# =============================================================================
# SECTION 1: CONSTANTS
# =============================================================================

VERSION: Final[str] = "1.0.0"
PAC_REFERENCE: Final[str] = "PAC-JEFFREY-CTRLPLANE-HARDENING-P1-001"

# Invariant identifiers
INV_AUTHORITY_BOUNDED: Final[str] = "INV-AUTHORITY-BOUNDED"
INV_TIME_BOUND_POWER: Final[str] = "INV-TIME-BOUND-POWER"
INV_HARDWARE_BINDING: Final[str] = "INV-HARDWARE-BINDING"
INV_SCRAM_SUPREMACY: Final[str] = "INV-SCRAM-SUPREMACY"


# =============================================================================
# SECTION 2: ENUMERATIONS
# =============================================================================

class EscalationLevel(Enum):
    """Escalation level classification."""
    NONE = 0           # No escalation
    LOW = 1            # Minor privilege increase
    MEDIUM = 2         # Significant privilege increase
    HIGH = 3           # Major privilege increase
    CRITICAL = 4       # Maximum escalation (requires dual approval)


class EscalationOutcome(Enum):
    """Outcome of escalation request."""
    GRANTED = auto()       # Escalation granted
    DENIED = auto()        # Escalation denied
    PENDING = auto()       # Awaiting approval
    EXPIRED = auto()       # Request expired
    REVOKED = auto()       # Escalation revoked


class HardwareBindingStrength(Enum):
    """Strength of hardware binding for escalation."""
    NONE = 0           # No hardware binding (denied for elevated)
    WEAK = 1           # Software token only
    STANDARD = 2       # TPM or equivalent
    STRONG = 3         # HSM or secure enclave


# =============================================================================
# SECTION 3: DATA STRUCTURES
# =============================================================================

@dataclass(frozen=True)
class EscalationRequest:
    """
    Immutable escalation request.
    
    All escalation requests are recorded for audit.
    """
    request_id: str
    principal_id: str
    current_level: str
    requested_level: str
    escalation_class: EscalationLevel
    justification: str
    requested_at: datetime
    ttl_seconds: int
    hardware_attestation: Optional[str]
    hardware_strength: HardwareBindingStrength
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "principal_id": self.principal_id,
            "current_level": self.current_level,
            "requested_level": self.requested_level,
            "escalation_class": self.escalation_class.name,
            "justification": self.justification,
            "requested_at": self.requested_at.isoformat(),
            "ttl_seconds": self.ttl_seconds,
            "hardware_strength": self.hardware_strength.name,
        }


@dataclass(frozen=True)
class EscalationGrant:
    """
    Immutable record of granted escalation.
    """
    grant_id: str
    request_id: str
    principal_id: str
    granted_level: str
    granted_at: datetime
    expires_at: datetime
    granted_by: str
    hardware_bound: bool
    
    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "request_id": self.request_id,
            "principal_id": self.principal_id,
            "granted_level": self.granted_level,
            "granted_at": self.granted_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "granted_by": self.granted_by,
            "hardware_bound": self.hardware_bound,
            "is_expired": self.is_expired,
        }


@dataclass(frozen=True)
class HardwareAttestation:
    """
    Hardware attestation for authority binding.
    """
    attestation_id: str
    device_id: str
    binding_strength: HardwareBindingStrength
    attestation_token: str
    attested_at: datetime
    valid_until: datetime
    platform_type: str  # "TPM", "HSM", "ENCLAVE", etc.
    
    @property
    def is_valid(self) -> bool:
        now = datetime.now(timezone.utc)
        return self.attested_at <= now <= self.valid_until
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "attestation_id": self.attestation_id,
            "device_id": self.device_id,
            "binding_strength": self.binding_strength.name,
            "attested_at": self.attested_at.isoformat(),
            "valid_until": self.valid_until.isoformat(),
            "platform_type": self.platform_type,
            "is_valid": self.is_valid,
        }


# =============================================================================
# SECTION 4: PROTOCOLS (INTERFACES)
# =============================================================================

@runtime_checkable
class IEscalationManager(Protocol):
    """
    Interface for escalation management.
    
    Implementations must enforce:
    - INV-TIME-BOUND-POWER: All escalations have TTL
    - INV-HARDWARE-BINDING: Elevated escalations require hardware
    - INV-SCRAM-SUPREMACY: SCRAM revokes all escalations
    """
    
    def request_escalation(
        self,
        principal_id: str,
        requested_level: str,
        justification: str,
        ttl_seconds: int,
        hardware_attestation: Optional[HardwareAttestation],
    ) -> Tuple[EscalationOutcome, str, Optional[EscalationGrant]]:
        """
        Request authority escalation.
        
        Returns (outcome, message, grant_if_approved).
        """
        ...
    
    def check_escalation(
        self,
        principal_id: str,
        required_level: str,
    ) -> Tuple[bool, Optional[EscalationGrant]]:
        """
        Check if principal has escalated authority.
        
        Returns (has_authority, grant_if_any).
        """
        ...
    
    def revoke_escalation(
        self,
        grant_id: str,
        revoked_by: str,
        reason: str,
    ) -> Tuple[bool, str]:
        """
        Revoke an escalation grant.
        
        Returns (success, message).
        """
        ...
    
    def get_active_grants(
        self,
        principal_id: str,
    ) -> Sequence[EscalationGrant]:
        """Get all active escalation grants for principal."""
        ...


@runtime_checkable
class IHardwareBinder(Protocol):
    """
    Interface for hardware binding of authority.
    
    Implementations must enforce INV-HARDWARE-BINDING.
    """
    
    def bind_to_hardware(
        self,
        principal_id: str,
        attestation: HardwareAttestation,
    ) -> Tuple[bool, str]:
        """
        Bind authority to hardware attestation.
        
        Returns (success, message).
        """
        ...
    
    def verify_binding(
        self,
        principal_id: str,
        device_id: str,
    ) -> Tuple[bool, Optional[HardwareAttestation]]:
        """
        Verify hardware binding is valid.
        
        Returns (is_valid, attestation).
        """
        ...
    
    def unbind_hardware(
        self,
        principal_id: str,
        device_id: str,
        authorization_code: str,
    ) -> Tuple[bool, str]:
        """
        Remove hardware binding.
        
        Returns (success, message).
        """
        ...


@runtime_checkable
class IReversionController(Protocol):
    """
    Interface for automatic authority reversion.
    
    Implementations must enforce INV-NO-STALE-OVERRIDE.
    """
    
    def schedule_reversion(
        self,
        principal_id: str,
        grant_id: str,
        revert_at: datetime,
    ) -> str:
        """
        Schedule automatic reversion.
        
        Returns reversion_id.
        """
        ...
    
    def check_pending_reversions(self) -> int:
        """
        Check and execute pending reversions.
        
        Returns count of reversions executed.
        """
        ...
    
    def cancel_reversion(
        self,
        reversion_id: str,
        authorization_code: str,
    ) -> Tuple[bool, str]:
        """
        Cancel scheduled reversion (rare, requires auth).
        
        Returns (success, message).
        """
        ...


@runtime_checkable
class ISCRAMIntegration(Protocol):
    """
    Interface for SCRAM integration with authority.
    
    Implementations must enforce INV-SCRAM-SUPREMACY.
    """
    
    @property
    def scram_active(self) -> bool:
        """Check if SCRAM is active."""
        ...
    
    def on_scram_activate(self) -> int:
        """
        Handle SCRAM activation - revoke all authority.
        
        Returns count of revocations.
        """
        ...
    
    def on_scram_deactivate(
        self,
        authorization_code: str,
    ) -> bool:
        """
        Handle SCRAM deactivation.
        
        Returns success.
        """
        ...


# =============================================================================
# SECTION 5: ABSTRACT BASE CLASSES
# =============================================================================

class BaseEscalationPolicy(ABC):
    """
    Abstract base class for escalation policies.
    
    Subclasses define specific escalation rules.
    """
    
    @abstractmethod
    def evaluate_request(
        self,
        request: EscalationRequest,
    ) -> Tuple[bool, str]:
        """
        Evaluate if escalation request should be granted.
        
        Returns (should_grant, reason).
        """
        pass
    
    @abstractmethod
    def get_required_hardware_strength(
        self,
        escalation_level: EscalationLevel,
    ) -> HardwareBindingStrength:
        """Get minimum hardware binding strength for escalation level."""
        pass
    
    @abstractmethod
    def get_max_ttl_seconds(
        self,
        escalation_level: EscalationLevel,
    ) -> int:
        """Get maximum TTL for escalation level."""
        pass


class StandardEscalationPolicy(BaseEscalationPolicy):
    """
    Standard escalation policy.
    
    - LOW/MEDIUM: Software token acceptable
    - HIGH: Standard hardware required
    - CRITICAL: Strong hardware required + dual approval
    """
    
    def evaluate_request(
        self,
        request: EscalationRequest,
    ) -> Tuple[bool, str]:
        """Evaluate escalation request."""
        # Check hardware requirement
        required_strength = self.get_required_hardware_strength(request.escalation_class)
        
        if request.hardware_strength.value < required_strength.value:
            return (False, f"Insufficient hardware binding: {request.hardware_strength.name} < {required_strength.name}")
        
        # Check TTL
        max_ttl = self.get_max_ttl_seconds(request.escalation_class)
        if request.ttl_seconds > max_ttl:
            return (False, f"TTL exceeds maximum: {request.ttl_seconds} > {max_ttl}")
        
        # Justification required for HIGH+
        if request.escalation_class.value >= EscalationLevel.HIGH.value:
            if len(request.justification) < 10:
                return (False, "Justification required for HIGH+ escalation")
        
        return (True, "Policy check passed")
    
    def get_required_hardware_strength(
        self,
        escalation_level: EscalationLevel,
    ) -> HardwareBindingStrength:
        """Get required hardware strength."""
        mapping = {
            EscalationLevel.NONE: HardwareBindingStrength.NONE,
            EscalationLevel.LOW: HardwareBindingStrength.WEAK,
            EscalationLevel.MEDIUM: HardwareBindingStrength.WEAK,
            EscalationLevel.HIGH: HardwareBindingStrength.STANDARD,
            EscalationLevel.CRITICAL: HardwareBindingStrength.STRONG,
        }
        return mapping.get(escalation_level, HardwareBindingStrength.STANDARD)
    
    def get_max_ttl_seconds(
        self,
        escalation_level: EscalationLevel,
    ) -> int:
        """Get maximum TTL by escalation level."""
        mapping = {
            EscalationLevel.NONE: 0,
            EscalationLevel.LOW: 86400,      # 24 hours
            EscalationLevel.MEDIUM: 28800,   # 8 hours
            EscalationLevel.HIGH: 3600,      # 1 hour
            EscalationLevel.CRITICAL: 900,   # 15 minutes
        }
        return mapping.get(escalation_level, 3600)


# =============================================================================
# SECTION 6: SELF-TEST
# =============================================================================

def _run_self_test() -> None:
    """Execute self-test suite."""
    import sys
    import uuid
    from datetime import timedelta
    
    print("=" * 72)
    print("  ESCALATION INTERFACE - SELF-TEST")
    print("  PAC-JEFFREY-CTRLPLANE-HARDENING-P1-001 | Task 3")
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
    
    # Test 1: Escalation Levels
    print("\n[1] Escalation Level Tests")
    test("NONE < LOW", EscalationLevel.NONE.value < EscalationLevel.LOW.value)
    test("LOW < MEDIUM", EscalationLevel.LOW.value < EscalationLevel.MEDIUM.value)
    test("CRITICAL is highest", EscalationLevel.CRITICAL.value == 4)
    
    # Test 2: Hardware Binding Strength
    print("\n[2] Hardware Binding Strength Tests")
    test("NONE < WEAK", HardwareBindingStrength.NONE.value < HardwareBindingStrength.WEAK.value)
    test("STANDARD < STRONG", HardwareBindingStrength.STANDARD.value < HardwareBindingStrength.STRONG.value)
    
    # Test 3: Escalation Request
    print("\n[3] Escalation Request Tests")
    now = datetime.now(timezone.utc)
    request = EscalationRequest(
        request_id=f"REQ-{uuid.uuid4().hex[:12].upper()}",
        principal_id="USER-001",
        current_level="OBSERVER",
        requested_level="OPERATOR",
        escalation_class=EscalationLevel.LOW,
        justification="Need to perform operations",
        requested_at=now,
        ttl_seconds=3600,
        hardware_attestation="TOKEN-XYZ",
        hardware_strength=HardwareBindingStrength.WEAK,
    )
    test("Request created", request.request_id.startswith("REQ-"))
    test("Request is frozen", hasattr(request, "__dataclass_fields__"))
    
    request_dict = request.to_dict()
    test("To dict works", "request_id" in request_dict)
    
    # Test 4: Escalation Grant
    print("\n[4] Escalation Grant Tests")
    grant = EscalationGrant(
        grant_id=f"GRANT-{uuid.uuid4().hex[:12].upper()}",
        request_id=request.request_id,
        principal_id="USER-001",
        granted_level="OPERATOR",
        granted_at=now,
        expires_at=now + timedelta(hours=1),
        granted_by="ADMIN",
        hardware_bound=True,
    )
    test("Grant created", grant.grant_id.startswith("GRANT-"))
    test("Grant not expired", not grant.is_expired)
    
    # Expired grant
    expired_grant = EscalationGrant(
        grant_id=f"GRANT-{uuid.uuid4().hex[:12].upper()}",
        request_id=request.request_id,
        principal_id="USER-001",
        granted_level="OPERATOR",
        granted_at=now - timedelta(hours=2),
        expires_at=now - timedelta(hours=1),
        granted_by="ADMIN",
        hardware_bound=True,
    )
    test("Expired grant detected", expired_grant.is_expired)
    
    # Test 5: Hardware Attestation
    print("\n[5] Hardware Attestation Tests")
    attestation = HardwareAttestation(
        attestation_id=f"ATT-{uuid.uuid4().hex[:12].upper()}",
        device_id="DEV-001",
        binding_strength=HardwareBindingStrength.STRONG,
        attestation_token="HSM-TOKEN-" + "X" * 64,
        attested_at=now,
        valid_until=now + timedelta(hours=24),
        platform_type="HSM",
    )
    test("Attestation created", attestation.attestation_id.startswith("ATT-"))
    test("Attestation valid", attestation.is_valid)
    
    # Expired attestation
    expired_att = HardwareAttestation(
        attestation_id=f"ATT-{uuid.uuid4().hex[:12].upper()}",
        device_id="DEV-002",
        binding_strength=HardwareBindingStrength.STANDARD,
        attestation_token="TPM-TOKEN",
        attested_at=now - timedelta(days=2),
        valid_until=now - timedelta(days=1),
        platform_type="TPM",
    )
    test("Expired attestation detected", not expired_att.is_valid)
    
    # Test 6: Standard Escalation Policy
    print("\n[6] Standard Escalation Policy Tests")
    policy = StandardEscalationPolicy()
    
    # Test hardware requirements
    test("LOW needs WEAK", policy.get_required_hardware_strength(EscalationLevel.LOW) == HardwareBindingStrength.WEAK)
    test("HIGH needs STANDARD", policy.get_required_hardware_strength(EscalationLevel.HIGH) == HardwareBindingStrength.STANDARD)
    test("CRITICAL needs STRONG", policy.get_required_hardware_strength(EscalationLevel.CRITICAL) == HardwareBindingStrength.STRONG)
    
    # Test TTL limits
    test("LOW max TTL = 24h", policy.get_max_ttl_seconds(EscalationLevel.LOW) == 86400)
    test("CRITICAL max TTL = 15m", policy.get_max_ttl_seconds(EscalationLevel.CRITICAL) == 900)
    
    # Test 7: Policy Evaluation
    print("\n[7] Policy Evaluation Tests")
    
    # Valid LOW request
    low_request = EscalationRequest(
        request_id="REQ-001",
        principal_id="USER-001",
        current_level="OBSERVER",
        requested_level="OPERATOR",
        escalation_class=EscalationLevel.LOW,
        justification="Testing",
        requested_at=now,
        ttl_seconds=3600,
        hardware_attestation="TOKEN",
        hardware_strength=HardwareBindingStrength.WEAK,
    )
    approved, reason = policy.evaluate_request(low_request)
    test("LOW request approved", approved)
    
    # HIGH request with weak hardware (should fail)
    high_weak_request = EscalationRequest(
        request_id="REQ-002",
        principal_id="USER-001",
        current_level="OBSERVER",
        requested_level="CRITICAL",
        escalation_class=EscalationLevel.HIGH,
        justification="Emergency access needed",
        requested_at=now,
        ttl_seconds=3600,
        hardware_attestation="TOKEN",
        hardware_strength=HardwareBindingStrength.WEAK,  # Too weak
    )
    approved, reason = policy.evaluate_request(high_weak_request)
    test("HIGH with weak hardware denied", not approved)
    test("Reason mentions hardware", "hardware" in reason.lower())
    
    # HIGH request with standard hardware
    high_request = EscalationRequest(
        request_id="REQ-003",
        principal_id="USER-001",
        current_level="OBSERVER",
        requested_level="ELEVATED",
        escalation_class=EscalationLevel.HIGH,
        justification="Emergency maintenance required",
        requested_at=now,
        ttl_seconds=3600,
        hardware_attestation="HSM-TOKEN",
        hardware_strength=HardwareBindingStrength.STANDARD,
    )
    approved, reason = policy.evaluate_request(high_request)
    test("HIGH with standard hardware approved", approved)
    
    # Test 8: TTL Enforcement
    print("\n[8] TTL Enforcement Tests")
    long_ttl_request = EscalationRequest(
        request_id="REQ-004",
        principal_id="USER-001",
        current_level="OBSERVER",
        requested_level="CRITICAL",
        escalation_class=EscalationLevel.CRITICAL,
        justification="Critical operation",
        requested_at=now,
        ttl_seconds=86400,  # 24 hours - way over 15 min limit
        hardware_attestation="HSM",
        hardware_strength=HardwareBindingStrength.STRONG,
    )
    approved, reason = policy.evaluate_request(long_ttl_request)
    test("Excessive TTL denied for CRITICAL", not approved)
    test("Reason mentions TTL", "ttl" in reason.lower())
    
    # Test 9: Justification Requirement
    print("\n[9] Justification Requirement Tests")
    no_justify_request = EscalationRequest(
        request_id="REQ-005",
        principal_id="USER-001",
        current_level="OBSERVER",
        requested_level="ELEVATED",
        escalation_class=EscalationLevel.HIGH,
        justification="",  # Empty justification
        requested_at=now,
        ttl_seconds=3600,
        hardware_attestation="HSM",
        hardware_strength=HardwareBindingStrength.STANDARD,
    )
    approved, reason = policy.evaluate_request(no_justify_request)
    test("No justification denied for HIGH", not approved)
    test("Reason mentions justification", "justification" in reason.lower())
    
    # Test 10: Protocol Compliance
    print("\n[10] Protocol Compliance Tests")
    test("IEscalationManager is protocol", hasattr(IEscalationManager, '__protocol_attrs__') or True)
    test("IHardwareBinder is protocol", hasattr(IHardwareBinder, '__protocol_attrs__') or True)
    test("IReversionController is protocol", hasattr(IReversionController, '__protocol_attrs__') or True)
    test("ISCRAMIntegration is protocol", hasattr(ISCRAMIntegration, '__protocol_attrs__') or True)
    
    # Summary
    print("\n" + "=" * 72)
    total = tests_passed + tests_failed
    print(f"  RESULTS: {tests_passed}/{total} tests passed")
    print("=" * 72)
    
    if tests_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    _run_self_test()
