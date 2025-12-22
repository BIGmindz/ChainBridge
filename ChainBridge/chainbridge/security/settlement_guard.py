"""Settlement Guard Module.

Defends against settlement attack scenarios:
- Double-settlement attempts
- Race-condition execution
- CRO override misuse

DOCTRINE: Settlement is final, atomic, and authorized.

Author: Sam (GID-06) — Security & Threat Engineer
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Security Exceptions
# ---------------------------------------------------------------------------


class DoubleSettlementError(Exception):
    """Raised when double-settlement attack detected."""

    def __init__(self, pdo_id: str, first_settlement_id: str, attempt_id: str):
        self.pdo_id = pdo_id
        self.first_settlement_id = first_settlement_id
        self.attempt_id = attempt_id
        self.detected_at = datetime.now(timezone.utc).isoformat()
        super().__init__(
            f"Double-settlement blocked: PDO {pdo_id} already settled "
            f"({first_settlement_id}), rejecting {attempt_id}"
        )


class SettlementRaceConditionError(Exception):
    """Raised when race condition detected in settlement."""

    def __init__(self, pdo_id: str, competing_settlement_ids: list[str]):
        self.pdo_id = pdo_id
        self.competing_settlement_ids = competing_settlement_ids
        self.detected_at = datetime.now(timezone.utc).isoformat()
        super().__init__(
            f"Race condition detected: PDO {pdo_id} has {len(competing_settlement_ids)} "
            f"concurrent settlement attempts"
        )


class UnauthorizedCROOverrideError(Exception):
    """Raised when unauthorized CRO override attempted."""

    def __init__(
        self,
        pdo_id: str,
        requesting_agent: str,
        reason: str,
    ):
        self.pdo_id = pdo_id
        self.requesting_agent = requesting_agent
        self.reason = reason
        self.detected_at = datetime.now(timezone.utc).isoformat()
        super().__init__(
            f"Unauthorized CRO override blocked: {requesting_agent} "
            f"cannot override PDO {pdo_id}: {reason}"
        )


class SettlementLockError(Exception):
    """Raised when settlement lock cannot be acquired."""

    def __init__(self, pdo_id: str, holder: str):
        self.pdo_id = pdo_id
        self.holder = holder
        self.detected_at = datetime.now(timezone.utc).isoformat()
        super().__init__(
            f"Settlement lock held by {holder} for PDO {pdo_id}"
        )


# ---------------------------------------------------------------------------
# Settlement Attack Types
# ---------------------------------------------------------------------------


class SettlementAttackType(str, Enum):
    """Types of settlement attacks."""

    DOUBLE_SETTLEMENT = "DOUBLE_SETTLEMENT"
    RACE_CONDITION = "RACE_CONDITION"
    UNAUTHORIZED_CRO_OVERRIDE = "UNAUTHORIZED_CRO_OVERRIDE"
    SETTLEMENT_REPLAY = "SETTLEMENT_REPLAY"
    PREMATURE_SETTLEMENT = "PREMATURE_SETTLEMENT"
    SETTLEMENT_REVERSAL = "SETTLEMENT_REVERSAL"
    AMOUNT_MANIPULATION = "AMOUNT_MANIPULATION"
    DESTINATION_TAMPERING = "DESTINATION_TAMPERING"


@dataclass(frozen=True)
class SettlementGuardResult:
    """Result from settlement guard check."""

    allowed: bool
    attack_type: Optional[SettlementAttackType]
    pdo_id: str
    settlement_id: Optional[str]
    reason: str
    evidence: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_audit_log(self) -> dict:
        """Convert to audit log format."""
        return {
            "event": "settlement_guard_check",
            "allowed": self.allowed,
            "attack_type": self.attack_type.value if self.attack_type else None,
            "pdo_id": self.pdo_id,
            "settlement_id": self.settlement_id,
            "reason": self.reason,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# CRO Override Validation
# ---------------------------------------------------------------------------


@dataclass
class CROOverrideRequest:
    """Represents a CRO override request."""

    pdo_id: str
    requesting_agent: str
    reason: str
    override_type: str  # HALT, MODIFY, CANCEL
    authorization_signature: Optional[str] = None
    cro_approval_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# Settlement Guard
# ---------------------------------------------------------------------------


class SettlementGuard:
    """Guards settlement operations against adversarial attacks.

    SECURITY INVARIANTS:
    - Each PDO settles exactly once
    - No race conditions in settlement
    - CRO overrides require explicit authorization
    - All blocked attempts are observable

    Usage:
        guard = SettlementGuard()
        guard.pre_settle_check(pdo, settlement_request)
        guard.acquire_settlement_lock(pdo_id)
        try:
            # perform settlement
            guard.record_settlement(pdo_id, settlement_id)
        finally:
            guard.release_settlement_lock(pdo_id)
    """

    # Authorized CRO override roles
    AUTHORIZED_CRO_ROLES: frozenset[str] = frozenset([
        "CRO",
        "COMPLIANCE_OFFICER",
        "SYSTEM_ADMIN",
    ])

    # Valid override types
    VALID_OVERRIDE_TYPES: frozenset[str] = frozenset([
        "HALT",
        "MODIFY",
        "CANCEL",
        "EMERGENCY_STOP",
    ])

    def __init__(self):
        """Initialize settlement guard."""
        # PDO ID -> settlement ID mapping
        self._settled_pdos: dict[str, str] = {}
        # PDO ID -> settlement timestamp
        self._settlement_times: dict[str, str] = {}
        # Active settlement locks: PDO ID -> (holder, acquire_time)
        self._locks: dict[str, tuple[str, float]] = {}
        # Lock timeout in seconds
        self._lock_timeout: float = 30.0
        # Thread safety
        self._lock_mutex = threading.Lock()
        # Concurrent settlement attempt tracking
        self._pending_settlements: dict[str, Set[str]] = {}

    def pre_settle_check(
        self,
        pdo_data: dict[str, Any],
        settlement_request: dict[str, Any],
    ) -> SettlementGuardResult:
        """Perform pre-settlement security checks.

        Validates:
        1. PDO not already settled
        2. No concurrent settlement race
        3. Settlement amounts match PDO
        4. Destination not tampered

        Args:
            pdo_data: The PDO to settle
            settlement_request: Settlement request details

        Returns:
            SettlementGuardResult

        Raises:
            DoubleSettlementError: If already settled
            SettlementRaceConditionError: If race detected
        """
        pdo_id = pdo_data.get("pdo_id", "UNKNOWN")
        settlement_id = settlement_request.get("settlement_id")

        # Check 1: Already settled?
        if pdo_id in self._settled_pdos:
            result = SettlementGuardResult(
                allowed=False,
                attack_type=SettlementAttackType.DOUBLE_SETTLEMENT,
                pdo_id=pdo_id,
                settlement_id=settlement_id,
                reason="PDO already settled",
                evidence={
                    "first_settlement": self._settled_pdos[pdo_id],
                    "attempt": settlement_id,
                },
            )
            self._log_attack(result)
            raise DoubleSettlementError(
                pdo_id,
                self._settled_pdos[pdo_id],
                settlement_id,
            )

        # Check 2: Race condition?
        result = self._check_race_condition(pdo_id, settlement_id)
        if not result.allowed:
            self._log_attack(result)
            raise SettlementRaceConditionError(
                pdo_id,
                list(self._pending_settlements.get(pdo_id, set())),
            )

        # Check 3: Amount manipulation?
        result = self._verify_amount(pdo_data, settlement_request)
        if not result.allowed:
            self._log_attack(result)
            return result

        # Check 4: Destination tampering?
        result = self._verify_destination(pdo_data, settlement_request)
        if not result.allowed:
            self._log_attack(result)
            return result

        return SettlementGuardResult(
            allowed=True,
            attack_type=None,
            pdo_id=pdo_id,
            settlement_id=settlement_id,
            reason="Pre-settlement checks passed",
        )

    def acquire_settlement_lock(self, pdo_id: str, requester: str) -> bool:
        """Acquire exclusive lock for settlement.

        Args:
            pdo_id: PDO to lock
            requester: ID of requesting process

        Returns:
            True if lock acquired

        Raises:
            SettlementLockError: If lock held by another
        """
        with self._lock_mutex:
            now = time.time()

            # Clean expired locks
            self._cleanup_expired_locks(now)

            if pdo_id in self._locks:
                holder, _ = self._locks[pdo_id]
                if holder != requester:
                    raise SettlementLockError(pdo_id, holder)

            self._locks[pdo_id] = (requester, now)

            # Track pending settlement
            if pdo_id not in self._pending_settlements:
                self._pending_settlements[pdo_id] = set()
            self._pending_settlements[pdo_id].add(requester)

            return True

    def release_settlement_lock(self, pdo_id: str, requester: str) -> None:
        """Release settlement lock.

        Args:
            pdo_id: PDO to unlock
            requester: ID of releasing process
        """
        with self._lock_mutex:
            if pdo_id in self._locks:
                holder, _ = self._locks[pdo_id]
                if holder == requester:
                    del self._locks[pdo_id]

            # Remove from pending
            if pdo_id in self._pending_settlements:
                self._pending_settlements[pdo_id].discard(requester)
                if not self._pending_settlements[pdo_id]:
                    del self._pending_settlements[pdo_id]

    def record_settlement(self, pdo_id: str, settlement_id: str) -> None:
        """Record completed settlement.

        Args:
            pdo_id: Settled PDO
            settlement_id: Settlement transaction ID
        """
        self._settled_pdos[pdo_id] = settlement_id
        self._settlement_times[pdo_id] = datetime.now(timezone.utc).isoformat()

        logger.info(
            "Settlement recorded: pdo_id=%s settlement_id=%s",
            pdo_id,
            settlement_id,
        )

    def validate_cro_override(
        self,
        override_request: CROOverrideRequest,
        agent_roles: list[str],
    ) -> SettlementGuardResult:
        """Validate CRO override request.

        Args:
            override_request: The override request
            agent_roles: Roles of requesting agent

        Returns:
            SettlementGuardResult

        Raises:
            UnauthorizedCROOverrideError: If not authorized
        """
        pdo_id = override_request.pdo_id
        requesting_agent = override_request.requesting_agent

        # Check 1: Agent has authorized role?
        has_role = any(
            role in self.AUTHORIZED_CRO_ROLES
            for role in agent_roles
        )

        if not has_role:
            result = SettlementGuardResult(
                allowed=False,
                attack_type=SettlementAttackType.UNAUTHORIZED_CRO_OVERRIDE,
                pdo_id=pdo_id,
                settlement_id=None,
                reason="Agent lacks CRO authority",
                evidence={
                    "agent": requesting_agent,
                    "roles": agent_roles,
                    "required_roles": list(self.AUTHORIZED_CRO_ROLES),
                },
            )
            self._log_attack(result)
            raise UnauthorizedCROOverrideError(
                pdo_id,
                requesting_agent,
                "Agent lacks CRO authority",
            )

        # Check 2: Valid override type?
        if override_request.override_type not in self.VALID_OVERRIDE_TYPES:
            result = SettlementGuardResult(
                allowed=False,
                attack_type=SettlementAttackType.UNAUTHORIZED_CRO_OVERRIDE,
                pdo_id=pdo_id,
                settlement_id=None,
                reason="Invalid override type",
                evidence={
                    "override_type": override_request.override_type,
                    "valid_types": list(self.VALID_OVERRIDE_TYPES),
                },
            )
            self._log_attack(result)
            raise UnauthorizedCROOverrideError(
                pdo_id,
                requesting_agent,
                f"Invalid override type: {override_request.override_type}",
            )

        # Check 3: Authorization signature present?
        if not override_request.authorization_signature:
            result = SettlementGuardResult(
                allowed=False,
                attack_type=SettlementAttackType.UNAUTHORIZED_CRO_OVERRIDE,
                pdo_id=pdo_id,
                settlement_id=None,
                reason="Missing authorization signature",
                evidence={"agent": requesting_agent},
            )
            self._log_attack(result)
            raise UnauthorizedCROOverrideError(
                pdo_id,
                requesting_agent,
                "Missing authorization signature",
            )

        # Check 4: Reason provided?
        if not override_request.reason or len(override_request.reason) < 10:
            result = SettlementGuardResult(
                allowed=False,
                attack_type=SettlementAttackType.UNAUTHORIZED_CRO_OVERRIDE,
                pdo_id=pdo_id,
                settlement_id=None,
                reason="Insufficient override reason",
                evidence={
                    "reason_length": len(override_request.reason or ""),
                    "minimum_length": 10,
                },
            )
            self._log_attack(result)
            raise UnauthorizedCROOverrideError(
                pdo_id,
                requesting_agent,
                "Override reason too brief",
            )

        logger.warning(
            "CRO override approved: pdo_id=%s agent=%s type=%s reason=%s",
            pdo_id,
            requesting_agent,
            override_request.override_type,
            override_request.reason[:50],
        )

        return SettlementGuardResult(
            allowed=True,
            attack_type=None,
            pdo_id=pdo_id,
            settlement_id=None,
            reason="CRO override authorized",
            evidence={
                "override_type": override_request.override_type,
                "agent": requesting_agent,
            },
        )

    def detect_settlement_replay(
        self,
        settlement_request: dict[str, Any],
    ) -> SettlementGuardResult:
        """Detect replay of previous settlement.

        Args:
            settlement_request: Settlement request to check

        Returns:
            SettlementGuardResult
        """
        settlement_id = settlement_request.get("settlement_id")
        pdo_id = settlement_request.get("pdo_id", "UNKNOWN")

        # Check if this settlement ID was already used
        for recorded_pdo, recorded_settlement in self._settled_pdos.items():
            if recorded_settlement == settlement_id:
                return SettlementGuardResult(
                    allowed=False,
                    attack_type=SettlementAttackType.SETTLEMENT_REPLAY,
                    pdo_id=pdo_id,
                    settlement_id=settlement_id,
                    reason="Settlement ID already used",
                    evidence={
                        "original_pdo": recorded_pdo,
                        "replay_pdo": pdo_id,
                    },
                )

        return SettlementGuardResult(
            allowed=True,
            attack_type=None,
            pdo_id=pdo_id,
            settlement_id=settlement_id,
            reason="Not a replay",
        )

    # ---------------------------------------------------------------------------
    # Internal Methods
    # ---------------------------------------------------------------------------

    def _check_race_condition(
        self, pdo_id: str, settlement_id: str
    ) -> SettlementGuardResult:
        """Check for race condition in settlement."""
        with self._lock_mutex:
            pending = self._pending_settlements.get(pdo_id, set())

            if len(pending) > 1:
                return SettlementGuardResult(
                    allowed=False,
                    attack_type=SettlementAttackType.RACE_CONDITION,
                    pdo_id=pdo_id,
                    settlement_id=settlement_id,
                    reason=f"Race detected: {len(pending)} concurrent attempts",
                    evidence={
                        "concurrent_count": len(pending),
                        "pending_ids": list(pending),
                    },
                )

        return SettlementGuardResult(
            allowed=True,
            attack_type=None,
            pdo_id=pdo_id,
            settlement_id=settlement_id,
            reason="No race condition",
        )

    def _verify_amount(
        self,
        pdo_data: dict[str, Any],
        settlement_request: dict[str, Any],
    ) -> SettlementGuardResult:
        """Verify settlement amount matches PDO."""
        pdo_id = pdo_data.get("pdo_id", "UNKNOWN")
        pdo_amount = pdo_data.get("settlement_amount")
        request_amount = settlement_request.get("amount")

        if pdo_amount is not None and request_amount is not None:
            if pdo_amount != request_amount:
                return SettlementGuardResult(
                    allowed=False,
                    attack_type=SettlementAttackType.AMOUNT_MANIPULATION,
                    pdo_id=pdo_id,
                    settlement_id=settlement_request.get("settlement_id"),
                    reason="Settlement amount mismatch",
                    evidence={
                        "pdo_amount": pdo_amount,
                        "request_amount": request_amount,
                    },
                )

        return SettlementGuardResult(
            allowed=True,
            attack_type=None,
            pdo_id=pdo_id,
            settlement_id=settlement_request.get("settlement_id"),
            reason="Amount verified",
        )

    def _verify_destination(
        self,
        pdo_data: dict[str, Any],
        settlement_request: dict[str, Any],
    ) -> SettlementGuardResult:
        """Verify settlement destination matches PDO."""
        pdo_id = pdo_data.get("pdo_id", "UNKNOWN")
        pdo_dest = pdo_data.get("settlement_destination")
        request_dest = settlement_request.get("destination")

        if pdo_dest and request_dest:
            if pdo_dest != request_dest:
                return SettlementGuardResult(
                    allowed=False,
                    attack_type=SettlementAttackType.DESTINATION_TAMPERING,
                    pdo_id=pdo_id,
                    settlement_id=settlement_request.get("settlement_id"),
                    reason="Settlement destination mismatch",
                    evidence={
                        "pdo_destination": pdo_dest[:20] + "..." if len(pdo_dest) > 20 else pdo_dest,
                        "request_destination": request_dest[:20] + "..." if len(request_dest) > 20 else request_dest,
                    },
                )

        return SettlementGuardResult(
            allowed=True,
            attack_type=None,
            pdo_id=pdo_id,
            settlement_id=settlement_request.get("settlement_id"),
            reason="Destination verified",
        )

    def _cleanup_expired_locks(self, now: float) -> None:
        """Clean up expired locks (called with lock held)."""
        expired = [
            pdo_id
            for pdo_id, (_, acquire_time) in self._locks.items()
            if now - acquire_time > self._lock_timeout
        ]
        for pdo_id in expired:
            del self._locks[pdo_id]
            logger.warning("Expired settlement lock: pdo_id=%s", pdo_id)

    def _log_attack(self, result: SettlementGuardResult) -> None:
        """Log settlement attack for audit."""
        logger.error(
            "SETTLEMENT_ATTACK: %s pdo_id=%s reason=%s",
            result.attack_type.value if result.attack_type else "UNKNOWN",
            result.pdo_id,
            result.reason,
        )
        logger.error("Attack evidence: %s", json.dumps(result.to_audit_log()))

    def clear_state(self) -> None:
        """Clear all state (for testing only)."""
        with self._lock_mutex:
            self._settled_pdos.clear()
            self._settlement_times.clear()
            self._locks.clear()
            self._pending_settlements.clear()

    def is_settled(self, pdo_id: str) -> bool:
        """Check if PDO is already settled."""
        return pdo_id in self._settled_pdos

    def get_settlement_info(self, pdo_id: str) -> Optional[dict]:
        """Get settlement info for PDO."""
        if pdo_id not in self._settled_pdos:
            return None
        return {
            "pdo_id": pdo_id,
            "settlement_id": self._settled_pdos[pdo_id],
            "settled_at": self._settlement_times.get(pdo_id),
        }
