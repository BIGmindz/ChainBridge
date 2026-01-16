"""
Leased Authority Primitive (LAP)
PAC-JEFFREY-CTRLPLANE-HARDENING-P1-001 | Task 2

GOVERNANCE_TIER: LAW
DRIFT_TOLERANCE: ZERO
FAIL_CLOSED: true

Authority is NEVER permanent. All elevated authority is LEASED:
- Leases have TTL (Time To Live)
- Leases expire automatically
- Expired leases revert to NOMINAL
- No manual intervention required for reversion

CORE PRINCIPLE: Power is temporary, contextual, and provable.

INVARIANTS ENFORCED:
- INV-TIME-BOUND-POWER: All overrides have TTL
- INV-NO-STALE-OVERRIDE: Expired overrides auto-revert
- INV-SCRAM-SUPREMACY: SCRAM revokes all leases

Author: BENSON-GID-00
Authority: ARCHITECT-JEFFREY (STRATEGY_ONLY)
"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum, auto
from typing import (
    Any,
    Callable,
    Dict,
    Final,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
)


# =============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# =============================================================================

VERSION: Final[str] = "1.0.0"
PAC_REFERENCE: Final[str] = "PAC-JEFFREY-CTRLPLANE-HARDENING-P1-001"

# Lease timing constants
DEFAULT_LEASE_TTL_SECONDS: Final[int] = 3600          # 1 hour default
MAX_LEASE_TTL_SECONDS: Final[int] = 86400             # 24 hours max
MIN_LEASE_TTL_SECONDS: Final[int] = 60                # 1 minute min
LEASE_RENEWAL_WINDOW_SECONDS: Final[int] = 300        # 5 minutes before expiry
LEASE_CLEANUP_INTERVAL_SECONDS: Final[int] = 60       # Cleanup every minute

# Override decay
OVERRIDE_DECAY_RATE: Final[float] = 0.1               # 10% per hour
OVERRIDE_REVERSION_THRESHOLD: Final[float] = 0.2      # Revert below 20%

# Invariant identifiers
INV_TIME_BOUND_POWER: Final[str] = "INV-TIME-BOUND-POWER"
INV_NO_STALE_OVERRIDE: Final[str] = "INV-NO-STALE-OVERRIDE"
INV_SCRAM_SUPREMACY: Final[str] = "INV-SCRAM-SUPREMACY"


# =============================================================================
# SECTION 2: ENUMERATIONS
# =============================================================================

class LeaseState(Enum):
    """State of an authority lease."""
    PENDING = auto()       # Lease requested, not yet active
    ACTIVE = auto()        # Lease active and valid
    EXPIRING = auto()      # Within renewal window
    EXPIRED = auto()       # Lease expired
    REVOKED = auto()       # Lease revoked (SCRAM or admin)
    RENEWED = auto()       # Lease renewed (new TTL)


class LeaseType(Enum):
    """Type of authority lease."""
    STANDARD = auto()      # Standard operational lease
    ELEVATED = auto()      # Elevated privilege lease
    EMERGENCY = auto()     # Emergency override lease
    MAINTENANCE = auto()   # Maintenance window lease


class ReversionReason(Enum):
    """Reason for authority reversion."""
    TTL_EXPIRED = auto()   # Time to live expired
    SCRAM_TRIGGERED = auto() # SCRAM revoked lease
    ADMIN_REVOKED = auto()  # Administrator revoked
    DECAY_THRESHOLD = auto() # Override decayed below threshold
    CONTEXT_LOST = auto()   # Context no longer valid


# =============================================================================
# SECTION 3: CORE DATA STRUCTURES
# =============================================================================

@dataclass(frozen=True)
class LeaseRequest:
    """
    Immutable lease request.
    """
    request_id: str
    principal_id: str
    lease_type: LeaseType
    requested_level: str       # Authority level requested
    ttl_seconds: int           # Requested TTL
    justification: str         # Why is this lease needed?
    hardware_bound: bool       # Requires hardware attestation?
    requested_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "principal_id": self.principal_id,
            "lease_type": self.lease_type.name,
            "requested_level": self.requested_level,
            "ttl_seconds": self.ttl_seconds,
            "justification": self.justification,
            "hardware_bound": self.hardware_bound,
            "requested_at": self.requested_at.isoformat(),
        }


@dataclass
class AuthorityLease:
    """
    Authority lease with TTL and automatic reversion.
    
    A lease grants temporary authority that expires automatically.
    """
    lease_id: str
    principal_id: str
    lease_type: LeaseType
    granted_level: str
    state: LeaseState
    issued_at: datetime
    expires_at: datetime
    ttl_seconds: int
    hardware_attestation: Optional[str]
    justification: str
    issued_by: str
    renewal_count: int = 0
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None
    reversion_reason: Optional[ReversionReason] = None
    
    @property
    def is_active(self) -> bool:
        """Check if lease is currently active."""
        if self.state not in (LeaseState.ACTIVE, LeaseState.EXPIRING):
            return False
        return datetime.now(timezone.utc) < self.expires_at
    
    @property
    def remaining_seconds(self) -> float:
        """Get remaining lease time in seconds."""
        now = datetime.now(timezone.utc)
        if now >= self.expires_at:
            return 0.0
        return (self.expires_at - now).total_seconds()
    
    @property
    def is_in_renewal_window(self) -> bool:
        """Check if lease is within renewal window."""
        return self.remaining_seconds <= LEASE_RENEWAL_WINDOW_SECONDS
    
    def check_expiration(self) -> bool:
        """
        Check if lease has expired and update state.
        
        Returns True if lease is still valid.
        """
        now = datetime.now(timezone.utc)
        
        if self.state in (LeaseState.EXPIRED, LeaseState.REVOKED):
            return False
        
        if now >= self.expires_at:
            self.state = LeaseState.EXPIRED
            self.reversion_reason = ReversionReason.TTL_EXPIRED
            return False
        
        if self.is_in_renewal_window and self.state == LeaseState.ACTIVE:
            self.state = LeaseState.EXPIRING
        
        return True
    
    def renew(self, additional_seconds: int, renewed_by: str) -> bool:
        """
        Renew the lease with additional TTL.
        
        Returns True if renewal successful.
        """
        if not self.is_active:
            return False
        
        if additional_seconds > MAX_LEASE_TTL_SECONDS:
            additional_seconds = MAX_LEASE_TTL_SECONDS
        
        if additional_seconds < MIN_LEASE_TTL_SECONDS:
            return False
        
        self.expires_at = datetime.now(timezone.utc) + timedelta(seconds=additional_seconds)
        self.ttl_seconds = additional_seconds
        self.state = LeaseState.RENEWED
        self.renewal_count += 1
        
        return True
    
    def revoke(self, revoked_by: str, reason: ReversionReason) -> None:
        """Revoke the lease."""
        self.state = LeaseState.REVOKED
        self.revoked_at = datetime.now(timezone.utc)
        self.revoked_by = revoked_by
        self.reversion_reason = reason
    
    def compute_hash(self) -> str:
        """Compute hash for audit."""
        data = {
            "lease_id": self.lease_id,
            "principal_id": self.principal_id,
            "granted_level": self.granted_level,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }
        return hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()[:32]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "lease_id": self.lease_id,
            "principal_id": self.principal_id,
            "lease_type": self.lease_type.name,
            "granted_level": self.granted_level,
            "state": self.state.name,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "ttl_seconds": self.ttl_seconds,
            "remaining_seconds": self.remaining_seconds,
            "is_active": self.is_active,
            "renewal_count": self.renewal_count,
            "reversion_reason": self.reversion_reason.name if self.reversion_reason else None,
            "lease_hash": self.compute_hash(),
        }


@dataclass(frozen=True)
class ReversionEvent:
    """Immutable record of authority reversion."""
    event_id: str
    lease_id: str
    principal_id: str
    previous_level: str
    reverted_to: str
    reason: ReversionReason
    occurred_at: datetime
    automatic: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "lease_id": self.lease_id,
            "principal_id": self.principal_id,
            "previous_level": self.previous_level,
            "reverted_to": self.reverted_to,
            "reason": self.reason.name,
            "occurred_at": self.occurred_at.isoformat(),
            "automatic": self.automatic,
        }


# =============================================================================
# SECTION 4: OVERRIDE TRACKER
# =============================================================================

@dataclass
class OverrideState:
    """
    Tracks override strength with automatic decay.
    
    Overrides decay over time and auto-revert when below threshold.
    """
    override_id: str
    principal_id: str
    initial_strength: float    # 1.0 = full strength
    current_strength: float
    started_at: datetime
    last_decay_at: datetime
    decay_rate: float          # Per hour
    reverted: bool = False
    
    def apply_decay(self) -> float:
        """
        Apply time-based decay to override strength.
        
        Returns new strength after decay.
        """
        if self.reverted:
            return 0.0
        
        now = datetime.now(timezone.utc)
        hours_elapsed = (now - self.last_decay_at).total_seconds() / 3600
        
        # Apply exponential decay
        decay_factor = (1 - self.decay_rate) ** hours_elapsed
        self.current_strength = self.current_strength * decay_factor
        self.last_decay_at = now
        
        # Check reversion threshold
        if self.current_strength < OVERRIDE_REVERSION_THRESHOLD:
            self.current_strength = 0.0
            self.reverted = True
        
        return self.current_strength
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "override_id": self.override_id,
            "principal_id": self.principal_id,
            "initial_strength": self.initial_strength,
            "current_strength": self.current_strength,
            "started_at": self.started_at.isoformat(),
            "decay_rate": self.decay_rate,
            "reverted": self.reverted,
        }


# =============================================================================
# SECTION 5: LEASED AUTHORITY MANAGER
# =============================================================================

class LeasedAuthority:
    """
    Leased Authority Primitive (LAP) implementation.
    
    Manages time-bound authority leases with automatic reversion.
    
    INVARIANTS:
    - INV-TIME-BOUND-POWER: All authority has TTL
    - INV-NO-STALE-OVERRIDE: Expired leases auto-revert
    - INV-SCRAM-SUPREMACY: SCRAM revokes all leases
    """
    
    def __init__(
        self,
        default_ttl_seconds: int = DEFAULT_LEASE_TTL_SECONDS,
        on_reversion: Optional[Callable[[ReversionEvent], None]] = None,
    ) -> None:
        """
        Initialize leased authority manager.
        
        Args:
            default_ttl_seconds: Default TTL for new leases
            on_reversion: Callback when authority reverts
        """
        self._default_ttl = min(default_ttl_seconds, MAX_LEASE_TTL_SECONDS)
        self._on_reversion = on_reversion
        self._leases: Dict[str, AuthorityLease] = {}
        self._principal_leases: Dict[str, List[str]] = {}  # principal_id -> lease_ids
        self._overrides: Dict[str, OverrideState] = {}
        self._reversion_log: List[ReversionEvent] = []
        self._scram_active = False
        self._lock = threading.Lock()
    
    @property
    def scram_active(self) -> bool:
        return self._scram_active
    
    def request_lease(
        self,
        principal_id: str,
        lease_type: LeaseType,
        requested_level: str,
        ttl_seconds: Optional[int] = None,
        justification: str = "",
        hardware_attestation: Optional[str] = None,
        issued_by: str = "SYSTEM",
    ) -> Tuple[bool, str, Optional[AuthorityLease]]:
        """
        Request an authority lease.
        
        Returns (success, message, lease).
        """
        with self._lock:
            # Check SCRAM
            if self._scram_active:
                return (False, "SCRAM active - no leases can be issued", None)
            
            # Validate TTL (INV-TIME-BOUND-POWER)
            if ttl_seconds is None:
                ttl_seconds = self._default_ttl
            
            ttl_seconds = max(MIN_LEASE_TTL_SECONDS, min(ttl_seconds, MAX_LEASE_TTL_SECONDS))
            
            # Create lease
            now = datetime.now(timezone.utc)
            lease_id = f"LEASE-{uuid.uuid4().hex[:12].upper()}"
            
            lease = AuthorityLease(
                lease_id=lease_id,
                principal_id=principal_id,
                lease_type=lease_type,
                granted_level=requested_level,
                state=LeaseState.ACTIVE,
                issued_at=now,
                expires_at=now + timedelta(seconds=ttl_seconds),
                ttl_seconds=ttl_seconds,
                hardware_attestation=hardware_attestation,
                justification=justification,
                issued_by=issued_by,
            )
            
            self._leases[lease_id] = lease
            
            # Track by principal
            if principal_id not in self._principal_leases:
                self._principal_leases[principal_id] = []
            self._principal_leases[principal_id].append(lease_id)
            
            return (True, f"Lease issued: {lease_id}", lease)
    
    def get_lease(self, lease_id: str) -> Optional[AuthorityLease]:
        """Get lease by ID."""
        return self._leases.get(lease_id)
    
    def get_active_leases(self, principal_id: str) -> List[AuthorityLease]:
        """Get all active leases for a principal."""
        lease_ids = self._principal_leases.get(principal_id, [])
        leases = []
        
        for lid in lease_ids:
            lease = self._leases.get(lid)
            if lease and lease.state in (LeaseState.ACTIVE, LeaseState.EXPIRING, LeaseState.RENEWED):
                leases.append(lease)
        
        return leases
    
    def check_authority(
        self,
        principal_id: str,
        required_level: str,
    ) -> Tuple[bool, Optional[AuthorityLease]]:
        """
        Check if principal has required authority via active lease.
        
        Returns (has_authority, lease_if_any).
        """
        with self._lock:
            if self._scram_active:
                return (False, None)
            
            leases = self.get_active_leases(principal_id)
            
            for lease in leases:
                # Check expiration
                if not lease.check_expiration():
                    self._trigger_reversion(lease, automatic=True)
                    continue
                
                # Simple string comparison for level
                # In production, would use proper level ordering
                if lease.granted_level == required_level or lease.granted_level == "CONSTITUTIONAL":
                    return (True, lease)
            
            return (False, None)
    
    def renew_lease(
        self,
        lease_id: str,
        additional_seconds: int,
        renewed_by: str,
    ) -> Tuple[bool, str]:
        """
        Renew a lease.
        
        Returns (success, message).
        """
        with self._lock:
            if self._scram_active:
                return (False, "SCRAM active - cannot renew leases")
            
            lease = self._leases.get(lease_id)
            if not lease:
                return (False, f"Lease not found: {lease_id}")
            
            if lease.renew(additional_seconds, renewed_by):
                return (True, f"Lease renewed until {lease.expires_at.isoformat()}")
            else:
                return (False, "Lease renewal failed - may be expired or invalid TTL")
    
    def revoke_lease(
        self,
        lease_id: str,
        revoked_by: str,
        reason: ReversionReason = ReversionReason.ADMIN_REVOKED,
    ) -> Tuple[bool, str]:
        """
        Revoke a lease.
        
        Returns (success, message).
        """
        with self._lock:
            lease = self._leases.get(lease_id)
            if not lease:
                return (False, f"Lease not found: {lease_id}")
            
            if not lease.is_active:
                return (False, "Lease is not active")
            
            lease.revoke(revoked_by, reason)
            self._trigger_reversion(lease, automatic=False)
            
            return (True, f"Lease revoked: {lease_id}")
    
    def activate_scram(self) -> int:
        """
        Activate SCRAM - revoke ALL leases.
        
        Returns count of revoked leases.
        """
        with self._lock:
            self._scram_active = True
            revoked_count = 0
            
            for lease in self._leases.values():
                if lease.is_active:
                    lease.revoke("SCRAM", ReversionReason.SCRAM_TRIGGERED)
                    self._trigger_reversion(lease, automatic=True)
                    revoked_count += 1
            
            return revoked_count
    
    def deactivate_scram(self, authorization_code: str) -> bool:
        """Deactivate SCRAM."""
        if len(authorization_code) < 16:
            return False
        
        with self._lock:
            self._scram_active = False
            return True
    
    def _trigger_reversion(
        self,
        lease: AuthorityLease,
        automatic: bool,
    ) -> None:
        """Trigger reversion event."""
        event = ReversionEvent(
            event_id=f"REV-{uuid.uuid4().hex[:12].upper()}",
            lease_id=lease.lease_id,
            principal_id=lease.principal_id,
            previous_level=lease.granted_level,
            reverted_to="NOMINAL",
            reason=lease.reversion_reason or ReversionReason.TTL_EXPIRED,
            occurred_at=datetime.now(timezone.utc),
            automatic=automatic,
        )
        self._reversion_log.append(event)
        
        # Invoke callback
        if self._on_reversion:
            try:
                self._on_reversion(event)
            except Exception:
                pass  # Callback should not disrupt reversion
    
    def cleanup_expired(self) -> int:
        """
        Cleanup expired leases.
        
        Returns count of cleaned up leases.
        """
        with self._lock:
            cleaned = 0
            
            for lease in list(self._leases.values()):
                if lease.state in (LeaseState.ACTIVE, LeaseState.EXPIRING):
                    if not lease.check_expiration():
                        self._trigger_reversion(lease, automatic=True)
                        cleaned += 1
            
            return cleaned
    
    # Override tracking
    def track_override(
        self,
        principal_id: str,
        initial_strength: float = 1.0,
        decay_rate: float = OVERRIDE_DECAY_RATE,
    ) -> OverrideState:
        """
        Track an override with automatic decay.
        
        Returns override state.
        """
        with self._lock:
            override_id = f"OVR-{uuid.uuid4().hex[:12].upper()}"
            now = datetime.now(timezone.utc)
            
            override = OverrideState(
                override_id=override_id,
                principal_id=principal_id,
                initial_strength=initial_strength,
                current_strength=initial_strength,
                started_at=now,
                last_decay_at=now,
                decay_rate=decay_rate,
            )
            
            self._overrides[override_id] = override
            return override
    
    def get_override_strength(self, override_id: str) -> float:
        """Get current override strength after decay."""
        override = self._overrides.get(override_id)
        if not override:
            return 0.0
        
        return override.apply_decay()
    
    def get_reversion_log(self) -> Sequence[ReversionEvent]:
        """Get reversion log."""
        return tuple(self._reversion_log)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get LAP statistics."""
        active_count = sum(1 for l in self._leases.values() if l.is_active)
        expired_count = sum(1 for l in self._leases.values() if l.state == LeaseState.EXPIRED)
        revoked_count = sum(1 for l in self._leases.values() if l.state == LeaseState.REVOKED)
        
        return {
            "total_leases": len(self._leases),
            "active_leases": active_count,
            "expired_leases": expired_count,
            "revoked_leases": revoked_count,
            "reversion_events": len(self._reversion_log),
            "tracked_overrides": len(self._overrides),
            "scram_active": self._scram_active,
            "default_ttl_seconds": self._default_ttl,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "statistics": self.get_statistics(),
            "active_leases": [l.to_dict() for l in self._leases.values() if l.is_active],
        }


# =============================================================================
# SECTION 6: SELF-TEST
# =============================================================================

def _run_self_test() -> None:
    """Execute self-test suite."""
    import sys
    import time
    
    print("=" * 72)
    print("  LEASED AUTHORITY PRIMITIVE - SELF-TEST")
    print("  PAC-JEFFREY-CTRLPLANE-HARDENING-P1-001 | Task 2")
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
    
    # Test 1: Lease Request
    print("\n[1] Lease Request Tests")
    lap = LeasedAuthority(default_ttl_seconds=300)
    
    success, msg, lease = lap.request_lease(
        principal_id="USER-001",
        lease_type=LeaseType.STANDARD,
        requested_level="OPERATOR",
        justification="Standard operations",
    )
    test("Lease issued", success and lease is not None)
    test("Lease is active", lease.is_active)
    test("Lease has TTL", lease.ttl_seconds == 300)
    test("Lease ID format", lease.lease_id.startswith("LEASE-"))
    
    # Test 2: Lease State
    print("\n[2] Lease State Tests")
    test("State is ACTIVE", lease.state == LeaseState.ACTIVE)
    test("Remaining time > 0", lease.remaining_seconds > 0)
    test("Not in renewal window", not lease.is_in_renewal_window)
    
    # Test 3: Authority Check
    print("\n[3] Authority Check Tests")
    has_auth, found_lease = lap.check_authority("USER-001", "OPERATOR")
    test("Has OPERATOR authority", has_auth)
    test("Found lease matches", found_lease and found_lease.lease_id == lease.lease_id)
    
    has_auth, _ = lap.check_authority("USER-001", "CRITICAL")
    test("Does not have CRITICAL", not has_auth)
    
    has_auth, _ = lap.check_authority("UNKNOWN-USER", "OPERATOR")
    test("Unknown user has no authority", not has_auth)
    
    # Test 4: Lease Renewal
    print("\n[4] Lease Renewal Tests")
    original_expiry = lease.expires_at
    success, msg = lap.renew_lease(lease.lease_id, 600, "ADMIN")
    test("Renewal succeeded", success)
    test("Expiry extended", lease.expires_at > original_expiry)
    test("Renewal count incremented", lease.renewal_count == 1)
    test("State is RENEWED", lease.state == LeaseState.RENEWED)
    
    # Test 5: TTL Enforcement (INV-TIME-BOUND-POWER)
    print("\n[5] TTL Enforcement Tests")
    # Try to request very long TTL
    success, msg, long_lease = lap.request_lease(
        principal_id="USER-002",
        lease_type=LeaseType.ELEVATED,
        requested_level="ELEVATED",
        ttl_seconds=999999,  # Way over max
    )
    test("Long TTL lease issued", success)
    test("TTL bounded to max", long_lease.ttl_seconds == MAX_LEASE_TTL_SECONDS)
    
    # Very short TTL
    success, msg, short_lease = lap.request_lease(
        principal_id="USER-003",
        lease_type=LeaseType.STANDARD,
        requested_level="OBSERVER",
        ttl_seconds=10,  # Below min
    )
    test("Short TTL lease issued", success)
    test("TTL bounded to min", short_lease.ttl_seconds == MIN_LEASE_TTL_SECONDS)
    
    # Test 6: Lease Expiration (INV-NO-STALE-OVERRIDE)
    print("\n[6] Expiration Tests (short-lived lease)")
    reversion_events: List[ReversionEvent] = []
    
    def on_revert(event: ReversionEvent) -> None:
        reversion_events.append(event)
    
    lap2 = LeasedAuthority(on_reversion=on_revert)
    success, msg, expiring_lease = lap2.request_lease(
        principal_id="EXPIRING-USER",
        lease_type=LeaseType.STANDARD,
        requested_level="OPERATOR",
        ttl_seconds=MIN_LEASE_TTL_SECONDS,  # Minimum TTL
    )
    test("Expiring lease created", success)
    
    # Manually expire the lease for testing
    expiring_lease.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    
    # Check should trigger reversion
    has_auth, _ = lap2.check_authority("EXPIRING-USER", "OPERATOR")
    test("Expired lease has no authority", not has_auth)
    test("Reversion event triggered", len(reversion_events) == 1)
    test("Reversion was automatic", reversion_events[0].automatic)
    test("Reason is TTL_EXPIRED", reversion_events[0].reason == ReversionReason.TTL_EXPIRED)
    
    # Test 7: Manual Revocation
    print("\n[7] Manual Revocation Tests")
    success, msg, revoke_lease = lap.request_lease(
        principal_id="REVOKE-USER",
        lease_type=LeaseType.ELEVATED,
        requested_level="ELEVATED",
    )
    test("Lease to revoke created", success)
    
    success, msg = lap.revoke_lease(revoke_lease.lease_id, "ADMIN", ReversionReason.ADMIN_REVOKED)
    test("Revocation succeeded", success)
    test("Lease state is REVOKED", revoke_lease.state == LeaseState.REVOKED)
    test("No longer active", not revoke_lease.is_active)
    test("Revoked by recorded", revoke_lease.revoked_by == "ADMIN")
    
    # Test 8: SCRAM Supremacy (INV-SCRAM-SUPREMACY)
    print("\n[8] SCRAM Supremacy Tests")
    lap3 = LeasedAuthority()
    
    # Issue multiple leases
    lap3.request_lease("SCRAM-USER-1", LeaseType.STANDARD, "OPERATOR")
    lap3.request_lease("SCRAM-USER-2", LeaseType.ELEVATED, "ELEVATED")
    lap3.request_lease("SCRAM-USER-3", LeaseType.STANDARD, "OPERATOR")
    
    # Verify all active
    test("User 1 has authority before SCRAM", lap3.check_authority("SCRAM-USER-1", "OPERATOR")[0])
    test("User 2 has authority before SCRAM", lap3.check_authority("SCRAM-USER-2", "ELEVATED")[0])
    
    # Activate SCRAM
    revoked_count = lap3.activate_scram()
    test("SCRAM revoked leases", revoked_count == 3)
    test("SCRAM is active", lap3.scram_active)
    
    # Verify all authority lost
    test("User 1 no authority after SCRAM", not lap3.check_authority("SCRAM-USER-1", "OPERATOR")[0])
    test("User 2 no authority after SCRAM", not lap3.check_authority("SCRAM-USER-2", "ELEVATED")[0])
    
    # Cannot issue new leases during SCRAM
    success, msg, _ = lap3.request_lease("NEW-USER", LeaseType.STANDARD, "OPERATOR")
    test("Cannot issue lease during SCRAM", not success)
    
    # Deactivate SCRAM
    deactivated = lap3.deactivate_scram("0123456789abcdef")
    test("SCRAM deactivated", deactivated and not lap3.scram_active)
    
    # Can issue new leases now
    success, msg, _ = lap3.request_lease("NEW-USER", LeaseType.STANDARD, "OPERATOR")
    test("Can issue lease after SCRAM clear", success)
    
    # Test 9: Override Decay
    print("\n[9] Override Decay Tests")
    override = lap.track_override("OVERRIDE-USER", initial_strength=1.0, decay_rate=0.5)
    test("Override created", override.override_id.startswith("OVR-"))
    test("Initial strength is 1.0", override.current_strength == 1.0)
    
    # Apply decay
    strength = lap.get_override_strength(override.override_id)
    test("Strength retrieved", strength > 0)
    
    # Simulate time passage
    override.last_decay_at = datetime.now(timezone.utc) - timedelta(hours=2)
    strength = lap.get_override_strength(override.override_id)
    test("Strength decayed", strength < 1.0)
    
    # Force reversion
    override.last_decay_at = datetime.now(timezone.utc) - timedelta(hours=10)
    strength = lap.get_override_strength(override.override_id)
    test("Override reverted (below threshold)", override.reverted)
    test("Reverted strength is 0", strength == 0.0)
    
    # Test 10: Multiple Leases Per Principal
    print("\n[10] Multiple Leases Tests")
    lap4 = LeasedAuthority()
    lap4.request_lease("MULTI-USER", LeaseType.STANDARD, "OBSERVER")
    lap4.request_lease("MULTI-USER", LeaseType.ELEVATED, "OPERATOR")
    lap4.request_lease("MULTI-USER", LeaseType.EMERGENCY, "CRITICAL")
    
    active = lap4.get_active_leases("MULTI-USER")
    test("Multiple active leases", len(active) == 3)
    
    # Check highest authority available
    has_auth, lease = lap4.check_authority("MULTI-USER", "CRITICAL")
    test("Has CRITICAL via multiple leases", has_auth)
    
    # Test 11: Lease Hash
    print("\n[11] Lease Hash Tests")
    test("Lease has hash", len(lease.compute_hash()) == 32)
    
    # Same lease should have same hash
    hash1 = lease.compute_hash()
    hash2 = lease.compute_hash()
    test("Hash is deterministic", hash1 == hash2)
    
    # Test 12: Statistics
    print("\n[12] Statistics Tests")
    stats = lap.get_statistics()
    test("Stats has total_leases", "total_leases" in stats)
    test("Stats has active_leases", "active_leases" in stats)
    test("Stats has reversion_events", "reversion_events" in stats)
    
    # Test 13: Reversion Log
    print("\n[13] Reversion Log Tests")
    log = lap3.get_reversion_log()
    test("Reversion log populated", len(log) >= 3)  # At least SCRAM revocations
    test("Log entries have IDs", all(e.event_id.startswith("REV-") for e in log))
    
    # Test 14: Cleanup
    print("\n[14] Cleanup Tests")
    # Create expired lease
    lap5 = LeasedAuthority()
    success, _, cleanup_lease = lap5.request_lease("CLEANUP-USER", LeaseType.STANDARD, "OPERATOR")
    cleanup_lease.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    
    cleaned = lap5.cleanup_expired()
    test("Cleanup found expired", cleaned == 1)
    test("Lease state is EXPIRED", cleanup_lease.state == LeaseState.EXPIRED)
    
    # Summary
    print("\n" + "=" * 72)
    total = tests_passed + tests_failed
    print(f"  RESULTS: {tests_passed}/{total} tests passed")
    print("=" * 72)
    
    if tests_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    _run_self_test()
