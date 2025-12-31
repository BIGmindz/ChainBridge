"""
Override Module
===============

Human override ("break glass") pathway for Lex enforcement.

Override Principles:
    - Requires explicit human acknowledgment
    - Creates immutable audit trail
    - Cannot override CRITICAL violations (no_override=True)
    - Senior override required for HIGH severity violations
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
import hashlib
import json
import uuid


class OverrideStatus(Enum):
    """Override request status values."""
    
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class OverrideAuthority(Enum):
    """Authority levels for override approval."""
    
    STANDARD = "STANDARD"        # Standard operator
    SENIOR = "SENIOR"            # Senior operator / supervisor
    EXECUTIVE = "EXECUTIVE"      # Executive authority
    EMERGENCY = "EMERGENCY"      # Emergency break-glass


@dataclass
class OverrideRequest:
    """
    Override request for a blocked verdict.
    
    Immutable after creation.
    """
    
    request_id: str
    verdict_id: str
    pdo_hash: str
    rule_ids: list[str]           # Rules being overridden
    requester_id: str             # Who requested the override
    reason: str                   # Business justification
    authority_required: OverrideAuthority
    status: OverrideStatus = OverrideStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    denial_reason: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "request_id": self.request_id,
            "verdict_id": self.verdict_id,
            "pdo_hash": self.pdo_hash,
            "rule_ids": self.rule_ids,
            "requester_id": self.requester_id,
            "reason": self.reason,
            "authority_required": self.authority_required.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "denial_reason": self.denial_reason,
        }
    
    def compute_hash(self) -> str:
        """Compute immutable hash of the request."""
        data = json.dumps({
            "request_id": self.request_id,
            "verdict_id": self.verdict_id,
            "pdo_hash": self.pdo_hash,
            "rule_ids": self.rule_ids,
            "requester_id": self.requester_id,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
        }, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()


@dataclass
class OverrideAuditEntry:
    """
    Immutable audit log entry for override actions.
    """
    
    entry_id: str
    request_id: str
    action: str                   # CREATED, APPROVED, DENIED, EXPIRED, CANCELLED
    actor_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "entry_id": self.entry_id,
            "request_id": self.request_id,
            "action": self.action,
            "actor_id": self.actor_id,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }
    
    def compute_hash(self) -> str:
        """Compute immutable hash of the entry."""
        data = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()


class OverrideManager:
    """
    Manager for override requests and approvals.
    
    Override Flow:
        1. Blocked verdict triggers override request
        2. Request requires appropriate authority level
        3. Approver reviews and approves/denies
        4. Audit trail is created
        5. If approved, new verdict is issued with OVERRIDDEN status
    
    Constraints:
        - CRITICAL violations cannot be overridden
        - HIGH severity requires SENIOR authority
        - All actions create audit entries
        - Requests expire after configured timeout
    """
    
    DEFAULT_EXPIRY_MINUTES = 60
    
    def __init__(self, expiry_minutes: int = DEFAULT_EXPIRY_MINUTES):
        self._requests: dict[str, OverrideRequest] = {}
        self._audit_log: list[OverrideAuditEntry] = []
        self._expiry_minutes = expiry_minutes
    
    def create_request(
        self,
        verdict_id: str,
        pdo_hash: str,
        rule_ids: list[str],
        requester_id: str,
        reason: str,
        requires_senior: bool = False,
    ) -> OverrideRequest:
        """
        Create an override request.
        
        Args:
            verdict_id: ID of the blocked verdict
            pdo_hash: Hash of the PDO
            rule_ids: List of rule IDs to override
            requester_id: ID of the requester
            reason: Business justification
            requires_senior: Whether senior authority is required
            
        Returns:
            OverrideRequest
            
        Raises:
            ValueError: If no overrideable rules
        """
        if not rule_ids:
            raise ValueError("No rule IDs specified for override")
        
        # Determine authority required
        authority = OverrideAuthority.SENIOR if requires_senior else OverrideAuthority.STANDARD
        
        # Calculate expiry
        from datetime import timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self._expiry_minutes)
        
        request = OverrideRequest(
            request_id=f"LEX-OVR-{uuid.uuid4().hex[:12].upper()}",
            verdict_id=verdict_id,
            pdo_hash=pdo_hash,
            rule_ids=rule_ids,
            requester_id=requester_id,
            reason=reason,
            authority_required=authority,
            expires_at=expires_at,
        )
        
        self._requests[request.request_id] = request
        
        # Create audit entry
        self._create_audit_entry(
            request_id=request.request_id,
            action="CREATED",
            actor_id=requester_id,
            details={"rule_ids": rule_ids, "reason": reason},
        )
        
        return request
    
    def approve_request(
        self,
        request_id: str,
        approver_id: str,
        approver_authority: OverrideAuthority,
    ) -> OverrideRequest:
        """
        Approve an override request.
        
        Args:
            request_id: ID of the request to approve
            approver_id: ID of the approver
            approver_authority: Authority level of the approver
            
        Returns:
            Updated OverrideRequest with APPROVED status
            
        Raises:
            ValueError: If request not found, expired, or insufficient authority
        """
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Override request not found: {request_id}")
        
        # Check if expired
        if request.expires_at and datetime.now(timezone.utc) > request.expires_at:
            request.status = OverrideStatus.EXPIRED
            self._create_audit_entry(
                request_id=request_id,
                action="EXPIRED",
                actor_id="SYSTEM",
                details={},
            )
            raise ValueError(f"Override request expired: {request_id}")
        
        # Check if already processed
        if request.status != OverrideStatus.PENDING:
            raise ValueError(f"Override request already processed: {request.status.value}")
        
        # Check authority
        authority_rank = {
            OverrideAuthority.STANDARD: 1,
            OverrideAuthority.SENIOR: 2,
            OverrideAuthority.EXECUTIVE: 3,
            OverrideAuthority.EMERGENCY: 4,
        }
        
        if authority_rank[approver_authority] < authority_rank[request.authority_required]:
            raise ValueError(
                f"Insufficient authority: {approver_authority.value} < {request.authority_required.value}"
            )
        
        # Approve
        request.status = OverrideStatus.APPROVED
        request.approved_by = approver_id
        request.approved_at = datetime.now(timezone.utc)
        
        # Create audit entry
        self._create_audit_entry(
            request_id=request_id,
            action="APPROVED",
            actor_id=approver_id,
            details={"authority": approver_authority.value},
        )
        
        return request
    
    def deny_request(
        self,
        request_id: str,
        denier_id: str,
        reason: str,
    ) -> OverrideRequest:
        """
        Deny an override request.
        
        Args:
            request_id: ID of the request to deny
            denier_id: ID of the person denying
            reason: Reason for denial
            
        Returns:
            Updated OverrideRequest with DENIED status
        """
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Override request not found: {request_id}")
        
        if request.status != OverrideStatus.PENDING:
            raise ValueError(f"Override request already processed: {request.status.value}")
        
        # Deny
        request.status = OverrideStatus.DENIED
        request.denial_reason = reason
        
        # Create audit entry
        self._create_audit_entry(
            request_id=request_id,
            action="DENIED",
            actor_id=denier_id,
            details={"reason": reason},
        )
        
        return request
    
    def cancel_request(
        self,
        request_id: str,
        canceller_id: str,
    ) -> OverrideRequest:
        """Cancel a pending override request."""
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Override request not found: {request_id}")
        
        if request.status != OverrideStatus.PENDING:
            raise ValueError(f"Override request already processed: {request.status.value}")
        
        # Cancel
        request.status = OverrideStatus.CANCELLED
        
        # Create audit entry
        self._create_audit_entry(
            request_id=request_id,
            action="CANCELLED",
            actor_id=canceller_id,
            details={},
        )
        
        return request
    
    def get_request(self, request_id: str) -> Optional[OverrideRequest]:
        """Get an override request by ID."""
        return self._requests.get(request_id)
    
    def get_pending_requests(self) -> list[OverrideRequest]:
        """Get all pending override requests."""
        return [r for r in self._requests.values() if r.status == OverrideStatus.PENDING]
    
    def get_audit_log(self, request_id: Optional[str] = None) -> list[OverrideAuditEntry]:
        """Get audit log entries, optionally filtered by request ID."""
        if request_id:
            return [e for e in self._audit_log if e.request_id == request_id]
        return list(self._audit_log)
    
    def _create_audit_entry(
        self,
        request_id: str,
        action: str,
        actor_id: str,
        details: dict[str, Any],
    ) -> OverrideAuditEntry:
        """Create and store an audit entry."""
        entry = OverrideAuditEntry(
            entry_id=f"LEX-AUD-{uuid.uuid4().hex[:12].upper()}",
            request_id=request_id,
            action=action,
            actor_id=actor_id,
            details=details,
        )
        self._audit_log.append(entry)
        return entry
    
    def render_request_terminal(self, request: OverrideRequest) -> str:
        """Render override request for terminal output."""
        status_icon = {
            OverrideStatus.PENDING: "⏳",
            OverrideStatus.APPROVED: "✅",
            OverrideStatus.DENIED: "🚫",
            OverrideStatus.EXPIRED: "⏰",
            OverrideStatus.CANCELLED: "❌",
        }.get(request.status, "○")
        
        lines = [
            "",
            "─" * 70,
            f"🔓 OVERRIDE REQUEST — {request.request_id}",
            "─" * 70,
            f"Status: {status_icon} {request.status.value}",
            f"Verdict: {request.verdict_id}",
            f"PDO Hash: {request.pdo_hash[:16]}...",
            f"Rules: {', '.join(request.rule_ids)}",
            f"Requester: {request.requester_id}",
            f"Reason: {request.reason}",
            f"Authority Required: {request.authority_required.value}",
            f"Created: {request.created_at.isoformat()}",
            f"Expires: {request.expires_at.isoformat() if request.expires_at else 'N/A'}",
        ]
        
        if request.approved_by:
            lines.append(f"Approved By: {request.approved_by}")
            lines.append(f"Approved At: {request.approved_at.isoformat() if request.approved_at else 'N/A'}")
        
        if request.denial_reason:
            lines.append(f"Denial Reason: {request.denial_reason}")
        
        lines.append("─" * 70)
        
        return "\n".join(lines)
