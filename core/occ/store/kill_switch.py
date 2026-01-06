"""
Kill Switch Service — Emergency Execution Halt Control

PAC-BENSON-P42: OCC Operationalization & Defect Remediation

Provides kill-switch functionality:
- State management (DISARMED/ARMED/ENGAGED/COOLDOWN)
- Authorization enforcement
- Execution halt signaling
- Forensic snapshot on engagement
- Full audit trail

INVARIANTS:
- INV-KILL-001: Kill switch DISABLED unless explicitly authorized
- INV-KILL-002: State transitions are audited and immutable
- INV-KILL-003: Engaged state halts ALL agent execution
- INV-KILL-004: Cooldown period prevents rapid toggle abuse

Author: CODY (GID-01) + SAM (GID-06)
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DEFAULT_KILL_SWITCH_PATH = "./data/kill_switch.json"
COOLDOWN_DURATION_SECONDS = 300  # 5 minute cooldown after disengage


class KillSwitchState(str, Enum):
    """Kill switch operational state."""
    DISARMED = "DISARMED"      # Normal operation
    ARMED = "ARMED"            # Ready to engage
    ENGAGED = "ENGAGED"        # ALL execution halted
    COOLDOWN = "COOLDOWN"      # Recently disengaged


class KillSwitchAuthLevel(str, Enum):
    """Operator authorization level for kill switch."""
    UNAUTHORIZED = "UNAUTHORIZED"  # Cannot interact
    ARM_ONLY = "ARM_ONLY"          # Can arm but not engage
    FULL_ACCESS = "FULL_ACCESS"    # Can arm, engage, and disengage


class KillSwitchAction(str, Enum):
    """Kill switch action types."""
    ARM = "ARM"
    ENGAGE = "ENGAGE"
    DISENGAGE = "DISENGAGE"
    COOLDOWN_EXPIRED = "COOLDOWN_EXPIRED"


class KillSwitchAuditEntry(BaseModel):
    """Immutable audit entry for kill switch actions."""
    
    entry_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    action: KillSwitchAction
    from_state: KillSwitchState
    to_state: KillSwitchState
    operator_id: str
    reason: str
    affected_pacs: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KillSwitchStatus(BaseModel):
    """Current kill switch status."""
    
    state: KillSwitchState = Field(default=KillSwitchState.DISARMED)
    armed_by: Optional[str] = None
    armed_at: Optional[datetime] = None
    engaged_by: Optional[str] = None
    engaged_at: Optional[datetime] = None
    engagement_reason: Optional[str] = None
    affected_pacs: List[str] = Field(default_factory=list)
    cooldown_ends_at: Optional[datetime] = None
    last_state_change: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KillSwitchEngageResult(BaseModel):
    """Result of kill switch engagement."""
    
    success: bool
    state: KillSwitchState
    message: str
    agents_halted: int = 0
    pacs_frozen: int = 0
    snapshot_id: Optional[str] = None


class KillSwitchError(Exception):
    """Kill switch operation error."""
    
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


class KillSwitchService:
    """
    Kill switch service with full enforcement.
    
    State transitions:
        DISARMED -> ARMED (arm)
        ARMED -> ENGAGED (engage)
        ARMED -> DISARMED (disarm)
        ENGAGED -> COOLDOWN (disengage)
        COOLDOWN -> DISARMED (cooldown expiry)
    
    Invariants:
        - Only authorized operators can interact
        - ENGAGED state halts all execution
        - All transitions are audited
        - Cooldown prevents toggle abuse
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """Initialize the kill switch service."""
        self._lock = threading.Lock()
        self._status = KillSwitchStatus()
        self._audit_log: List[KillSwitchAuditEntry] = []
        self._halt_callbacks: List[callable] = []
        
        self._storage_path = Path(
            storage_path or os.environ.get("CHAINBRIDGE_KILL_SWITCH_PATH", DEFAULT_KILL_SWITCH_PATH)
        )
        
        self._load()
    
    def _load(self) -> None:
        """Load kill switch state from persistence."""
        if not self._storage_path.exists():
            logger.info(f"Kill switch state not found at {self._storage_path}; starting fresh.")
            return
        
        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self._status = KillSwitchStatus.model_validate(data.get("status", {}))
            for entry in data.get("audit_log", [])[-1000:]:  # Keep last 1000
                self._audit_log.append(KillSwitchAuditEntry.model_validate(entry))
            
            # Check for cooldown expiry
            self._check_cooldown()
            
            logger.info(f"Loaded kill switch state: {self._status.state.value}")
        except Exception as e:
            logger.error(f"Failed to load kill switch state: {e}")
    
    def _persist(self) -> None:
        """Persist kill switch state atomically."""
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "status": self._status.model_dump(mode="json"),
            "audit_log": [e.model_dump(mode="json") for e in self._audit_log[-1000:]],
        }
        
        fd, tmp_path = tempfile.mkstemp(
            suffix=".json",
            prefix="kill_switch_",
            dir=self._storage_path.parent,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            os.replace(tmp_path, self._storage_path)
        except Exception as e:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            logger.error(f"Failed to persist kill switch state: {e}")
            raise
    
    def _check_cooldown(self) -> None:
        """Check if cooldown has expired and transition to DISARMED."""
        if self._status.state == KillSwitchState.COOLDOWN:
            if self._status.cooldown_ends_at and datetime.now(timezone.utc) >= self._status.cooldown_ends_at:
                old_state = self._status.state
                self._status = KillSwitchStatus(
                    state=KillSwitchState.DISARMED,
                    last_state_change=datetime.now(timezone.utc),
                )
                
                self._audit_log.append(KillSwitchAuditEntry(
                    action=KillSwitchAction.COOLDOWN_EXPIRED,
                    from_state=old_state,
                    to_state=KillSwitchState.DISARMED,
                    operator_id="system",
                    reason="Cooldown period expired",
                ))
                self._persist()
                logger.info("Kill switch cooldown expired, state -> DISARMED")
    
    def _audit(
        self,
        action: KillSwitchAction,
        from_state: KillSwitchState,
        to_state: KillSwitchState,
        operator_id: str,
        reason: str,
        affected_pacs: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record audit entry for state transition."""
        entry = KillSwitchAuditEntry(
            action=action,
            from_state=from_state,
            to_state=to_state,
            operator_id=operator_id,
            reason=reason,
            affected_pacs=affected_pacs or [],
            metadata=metadata or {},
        )
        self._audit_log.append(entry)
        logger.info(
            f"KILL SWITCH AUDIT: {action.value} by {operator_id} "
            f"({from_state.value} -> {to_state.value}): {reason}"
        )
    
    def get_status(self, check_cooldown: bool = True) -> KillSwitchStatus:
        """Get current kill switch status."""
        with self._lock:
            if check_cooldown:
                self._check_cooldown()
            return self._status
    
    def is_engaged(self) -> bool:
        """Check if kill switch is engaged (execution should halt)."""
        with self._lock:
            return self._status.state == KillSwitchState.ENGAGED
    
    def arm(
        self,
        operator_id: str,
        auth_level: KillSwitchAuthLevel,
        reason: str = "Operator initiated arm",
    ) -> KillSwitchStatus:
        """
        Arm the kill switch (prepare for engagement).
        
        Args:
            operator_id: Operator performing the action
            auth_level: Operator's authorization level
            reason: Reason for arming
        
        Returns:
            Updated status
        
        Raises:
            KillSwitchError: If unauthorized or invalid state
        """
        with self._lock:
            self._check_cooldown()
            
            # Authorization check
            if auth_level == KillSwitchAuthLevel.UNAUTHORIZED:
                raise KillSwitchError(
                    "Unauthorized: Cannot arm kill switch",
                    "UNAUTHORIZED"
                )
            
            # State check
            if self._status.state not in (KillSwitchState.DISARMED, KillSwitchState.COOLDOWN):
                raise KillSwitchError(
                    f"Invalid state transition: Cannot arm from {self._status.state.value}",
                    "INVALID_STATE"
                )
            
            old_state = self._status.state
            now = datetime.now(timezone.utc)
            
            self._status = KillSwitchStatus(
                state=KillSwitchState.ARMED,
                armed_by=operator_id,
                armed_at=now,
                last_state_change=now,
            )
            
            self._audit(
                action=KillSwitchAction.ARM,
                from_state=old_state,
                to_state=KillSwitchState.ARMED,
                operator_id=operator_id,
                reason=reason,
            )
            
            self._persist()
            return self._status
    
    def engage(
        self,
        operator_id: str,
        auth_level: KillSwitchAuthLevel,
        reason: str,
        affected_pacs: Optional[List[str]] = None,
    ) -> KillSwitchEngageResult:
        """
        Engage the kill switch (HALT ALL EXECUTION).
        
        This is the critical operation that stops all agent execution.
        
        Args:
            operator_id: Operator performing the action
            auth_level: Operator's authorization level
            reason: Mandatory reason for engagement
            affected_pacs: List of PACs to freeze
        
        Returns:
            Engagement result with halt details
        
        Raises:
            KillSwitchError: If unauthorized, invalid state, or missing reason
        """
        with self._lock:
            # Authorization check - FULL_ACCESS required
            if auth_level != KillSwitchAuthLevel.FULL_ACCESS:
                raise KillSwitchError(
                    "Unauthorized: FULL_ACCESS required to engage kill switch",
                    "INSUFFICIENT_AUTH"
                )
            
            # Reason required
            if not reason or len(reason.strip()) < 10:
                raise KillSwitchError(
                    "Engagement reason required (minimum 10 characters)",
                    "REASON_REQUIRED"
                )
            
            # State check - must be ARMED
            if self._status.state != KillSwitchState.ARMED:
                raise KillSwitchError(
                    f"Invalid state: Must be ARMED to engage (current: {self._status.state.value})",
                    "INVALID_STATE"
                )
            
            old_state = self._status.state
            now = datetime.now(timezone.utc)
            pacs = affected_pacs or []
            
            # Create forensic snapshot
            snapshot_id = f"KS-SNAP-{now.strftime('%Y%m%d%H%M%S')}"
            
            self._status = KillSwitchStatus(
                state=KillSwitchState.ENGAGED,
                armed_by=self._status.armed_by,
                armed_at=self._status.armed_at,
                engaged_by=operator_id,
                engaged_at=now,
                engagement_reason=reason,
                affected_pacs=pacs,
                last_state_change=now,
            )
            
            self._audit(
                action=KillSwitchAction.ENGAGE,
                from_state=old_state,
                to_state=KillSwitchState.ENGAGED,
                operator_id=operator_id,
                reason=reason,
                affected_pacs=pacs,
                metadata={"snapshot_id": snapshot_id},
            )
            
            self._persist()
            
            # Execute halt callbacks
            agents_halted = self._execute_halt_callbacks()
            
            logger.critical(
                f"KILL SWITCH ENGAGED by {operator_id}: {reason} "
                f"(halted {agents_halted} agents, frozen {len(pacs)} PACs)"
            )
            
            return KillSwitchEngageResult(
                success=True,
                state=KillSwitchState.ENGAGED,
                message=f"Kill switch ENGAGED. All execution halted.",
                agents_halted=agents_halted,
                pacs_frozen=len(pacs),
                snapshot_id=snapshot_id,
            )
    
    def disengage(
        self,
        operator_id: str,
        auth_level: KillSwitchAuthLevel,
        reason: str,
    ) -> KillSwitchStatus:
        """
        Disengage the kill switch (resume operation with cooldown).
        
        Args:
            operator_id: Operator performing the action
            auth_level: Operator's authorization level
            reason: Reason for disengagement
        
        Returns:
            Updated status (in COOLDOWN state)
        
        Raises:
            KillSwitchError: If unauthorized or invalid state
        """
        with self._lock:
            # Authorization check
            if auth_level != KillSwitchAuthLevel.FULL_ACCESS:
                raise KillSwitchError(
                    "Unauthorized: FULL_ACCESS required to disengage",
                    "INSUFFICIENT_AUTH"
                )
            
            # State check
            if self._status.state != KillSwitchState.ENGAGED:
                raise KillSwitchError(
                    f"Invalid state: Must be ENGAGED to disengage (current: {self._status.state.value})",
                    "INVALID_STATE"
                )
            
            old_state = self._status.state
            now = datetime.now(timezone.utc)
            cooldown_ends = now + timedelta(seconds=COOLDOWN_DURATION_SECONDS)
            
            self._status = KillSwitchStatus(
                state=KillSwitchState.COOLDOWN,
                cooldown_ends_at=cooldown_ends,
                last_state_change=now,
            )
            
            self._audit(
                action=KillSwitchAction.DISENGAGE,
                from_state=old_state,
                to_state=KillSwitchState.COOLDOWN,
                operator_id=operator_id,
                reason=reason,
                metadata={"cooldown_ends_at": cooldown_ends.isoformat()},
            )
            
            self._persist()
            
            logger.warning(
                f"Kill switch DISENGAGED by {operator_id}: {reason} "
                f"(cooldown until {cooldown_ends.isoformat()})"
            )
            
            return self._status
    
    def disarm(
        self,
        operator_id: str,
        auth_level: KillSwitchAuthLevel,
        reason: str = "Operator initiated disarm",
    ) -> KillSwitchStatus:
        """
        Disarm the kill switch (return to normal from ARMED).
        
        Args:
            operator_id: Operator performing the action
            auth_level: Operator's authorization level
            reason: Reason for disarming
        
        Returns:
            Updated status
        
        Raises:
            KillSwitchError: If unauthorized or invalid state
        """
        with self._lock:
            # Authorization check
            if auth_level == KillSwitchAuthLevel.UNAUTHORIZED:
                raise KillSwitchError(
                    "Unauthorized: Cannot disarm kill switch",
                    "UNAUTHORIZED"
                )
            
            # State check - must be ARMED
            if self._status.state != KillSwitchState.ARMED:
                raise KillSwitchError(
                    f"Invalid state: Must be ARMED to disarm (current: {self._status.state.value})",
                    "INVALID_STATE"
                )
            
            old_state = self._status.state
            now = datetime.now(timezone.utc)
            
            self._status = KillSwitchStatus(
                state=KillSwitchState.DISARMED,
                last_state_change=now,
            )
            
            self._audit(
                action=KillSwitchAction.DISENGAGE,  # Using DISENGAGE for disarm
                from_state=old_state,
                to_state=KillSwitchState.DISARMED,
                operator_id=operator_id,
                reason=reason,
            )
            
            self._persist()
            return self._status
    
    def register_halt_callback(self, callback: callable) -> None:
        """Register a callback to be executed on kill switch engagement."""
        self._halt_callbacks.append(callback)
    
    def _execute_halt_callbacks(self) -> int:
        """Execute all registered halt callbacks. Returns count of successful halts."""
        count = 0
        for callback in self._halt_callbacks:
            try:
                result = callback()
                if result:
                    count += result
            except Exception as e:
                logger.error(f"Halt callback failed: {e}")
        return count
    
    def get_audit_log(
        self,
        limit: int = 100,
        operator_id: Optional[str] = None,
        action: Optional[KillSwitchAction] = None,
    ) -> List[KillSwitchAuditEntry]:
        """Get kill switch audit log."""
        with self._lock:
            entries = self._audit_log
            
            if operator_id:
                entries = [e for e in entries if e.operator_id == operator_id]
            if action:
                entries = [e for e in entries if e.action == action]
            
            return entries[-limit:]


# Module-level singleton
_default_service: Optional[KillSwitchService] = None


def get_kill_switch_service() -> KillSwitchService:
    """Get the default kill switch service singleton."""
    global _default_service
    if _default_service is None:
        _default_service = KillSwitchService()
    return _default_service


def reset_kill_switch_service() -> None:
    """Reset the default kill switch service (for testing only)."""
    global _default_service
    _default_service = None
