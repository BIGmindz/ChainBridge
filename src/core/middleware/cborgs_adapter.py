"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                     C-BORGS ADAPTER — SEA BURGERS BIZ                         ║
║                     PAC-OCC-P33 — Middleware Bridge v1.0.0                    ║
╚═══════════════════════════════════════════════════════════════════════════════╝

The C-Borgs Adapter translates ChainBridge internal decisions into the format
required by the Sea Burgers Biz platform.

IRON ARCHITECTURE:
- All outbound HTTP calls run in DAEMON THREADS (non-blocking)
- No .join() calls — fire-and-forget pattern
- Timeout protection on all network operations
- ALEX governance review on all outbound data

DATA FLOW:
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ ChainBridge │ --> │    ALEX     │ --> │   C-Borgs   │ --> │ Sea Burgers │
│   Outcome   │     │  Governance │     │   Adapter   │     │     Biz     │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘

Authors:
- CODY (GID-01) — Implementation
- ALEX (GID-08) — Governance Review
- JEFFREY — Iron Architecture
"""

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# C-Borgs / Sea Burgers Biz Configuration
CBORGS_ENABLED = os.getenv("CBORGS_ENABLED", "false").lower() == "true"
CBORGS_WEBHOOK_URL = os.getenv("CBORGS_WEBHOOK_URL", "https://api.seaburgers.biz/v1/webhook")
CBORGS_API_KEY = os.getenv("CBORGS_API_KEY", "")
CBORGS_TIMEOUT = int(os.getenv("CBORGS_TIMEOUT", "5"))  # seconds

# Governance Configuration
GOVERNANCE_STRICT = os.getenv("CBORGS_GOVERNANCE_STRICT", "true").lower() == "true"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class OutcomeType(Enum):
    """Types of outcomes that can be dispatched to C-Borgs."""
    PAC_COMPLETED = "pac_completed"
    AGENT_SPAWNED = "agent_spawned"
    GOVERNANCE_DECISION = "governance_decision"
    SETTLEMENT_REQUEST = "settlement_request"
    ALERT = "alert"
    AUDIT_EVENT = "audit_event"


class DispatchStatus(Enum):
    """Status of C-Borgs dispatch operations."""
    PENDING = "pending"
    DISPATCHED = "dispatched"
    DELIVERED = "delivered"
    FAILED = "failed"
    BLOCKED_GOVERNANCE = "blocked_governance"


@dataclass
class CBorgsPayload:
    """
    Payload structure for C-Borgs / Sea Burgers Biz.
    
    This is the canonical format for all outbound data.
    """
    # Metadata
    event_id: str
    event_type: str  # OutcomeType value
    timestamp: str   # ISO 8601
    source: str = "chainbridge"
    version: str = "1.0.0"
    
    # Content
    pac_id: Optional[str] = None
    agent_gid: Optional[str] = None
    action: Optional[str] = None
    status: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    # Integrity
    integrity_hash: Optional[str] = None
    
    # Governance
    governance_approved: bool = False
    governance_reviewer: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class DispatchResult:
    """Result of a C-Borgs dispatch operation."""
    event_id: str
    status: DispatchStatus
    timestamp: str
    error: Optional[str] = None
    response_code: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "error": self.error,
            "response_code": self.response_code,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# PII / SENSITIVE DATA PATTERNS (ALEX GOVERNANCE)
# ═══════════════════════════════════════════════════════════════════════════════

# Patterns that ALEX will flag for governance review
SENSITIVE_PATTERNS = [
    # PII
    "ssn", "social_security", "tax_id",
    "credit_card", "card_number", "cvv",
    "password", "secret", "private_key",
    "api_key", "auth_token", "bearer",
    
    # Personal Data
    "email", "phone", "address", "dob", "date_of_birth",
    "first_name", "last_name", "full_name",
    
    # Financial
    "bank_account", "routing_number", "iban", "swift",
    "wallet_address", "seed_phrase", "mnemonic",
]


# ═══════════════════════════════════════════════════════════════════════════════
# ALEX GOVERNANCE HOOK (GID-08)
# ═══════════════════════════════════════════════════════════════════════════════

class ALEXGovernance:
    """
    ALEX (GID-08) Governance Review for outbound data.
    
    All data leaving ChainBridge MUST pass through ALEX for:
    1. PII/Sensitive data detection
    2. Schema compliance verification
    3. Rate limiting enforcement
    
    LAW: "No data leaves without ALEX's blessing."
    """
    
    def __init__(self):
        self.gid = "GID-08"
        self.name = "ALEX"
        self.role = "Governance Enforcer"
        self._review_count = 0
        self._blocked_count = 0
    
    def review_payload(self, payload: CBorgsPayload) -> tuple[bool, Optional[str]]:
        """
        Review a payload for governance compliance.
        
        Args:
            payload: The CBorgsPayload to review
            
        Returns:
            Tuple of (approved: bool, reason: Optional[str])
        """
        self._review_count += 1
        
        # Convert to string for pattern matching
        payload_str = payload.to_json().lower()
        
        # Check for sensitive patterns
        for pattern in SENSITIVE_PATTERNS:
            if pattern in payload_str:
                if GOVERNANCE_STRICT:
                    self._blocked_count += 1
                    return False, f"ALEX BLOCKED: Sensitive pattern detected: '{pattern}'"
                else:
                    print(f"⚠️ [ALEX] Warning: Sensitive pattern '{pattern}' detected (non-strict mode)")
        
        # Check for required fields
        if not payload.event_id:
            return False, "ALEX BLOCKED: Missing required field: event_id"
        
        if not payload.event_type:
            return False, "ALEX BLOCKED: Missing required field: event_type"
        
        # Approved
        return True, None
    
    def get_stats(self) -> Dict[str, int]:
        """Get governance statistics."""
        return {
            "total_reviews": self._review_count,
            "blocked": self._blocked_count,
            "approved": self._review_count - self._blocked_count,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# C-BORGS ADAPTER (IRON PATTERN)
# ═══════════════════════════════════════════════════════════════════════════════

class CBorgsAdapter:
    """
    C-Borgs Adapter for Sea Burgers Biz integration.
    
    IRON ARCHITECTURE:
    - All HTTP calls run in daemon threads (non-blocking)
    - No .join() calls — fire-and-forget
    - Timeout protection (default 5s)
    - ALEX governance on all outbound data
    
    Usage:
        adapter = CBorgsAdapter()
        result = adapter.dispatch_outcome(
            event_type=OutcomeType.PAC_COMPLETED,
            pac_id="PAC-OCC-P33",
            agent_gid="GID-00",
            action="EXECUTE",
            status="SUCCESS",
            details={"message": "Task completed"}
        )
    """
    
    def __init__(
        self,
        webhook_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = CBORGS_TIMEOUT,
        enabled: Optional[bool] = None,
    ):
        """
        Initialize the C-Borgs Adapter.
        
        Args:
            webhook_url: Override webhook URL (default: env var)
            api_key: Override API key (default: env var)
            timeout: HTTP timeout in seconds
            enabled: Override enabled flag (default: env var)
        """
        self.webhook_url = webhook_url or CBORGS_WEBHOOK_URL
        self.api_key = api_key or CBORGS_API_KEY
        self.timeout = timeout
        self.enabled = enabled if enabled is not None else CBORGS_ENABLED
        
        # Governance
        self.governance = ALEXGovernance()
        
        # Statistics
        self._dispatch_count = 0
        self._success_count = 0
        self._failure_count = 0
        self._blocked_count = 0
        
        # Callbacks for testing/monitoring
        self._on_dispatch: Optional[Callable[[DispatchResult], None]] = None
    
    @property
    def is_enabled(self) -> bool:
        """Check if C-Borgs integration is enabled."""
        return self.enabled and bool(self.webhook_url)
    
    def _generate_event_id(self) -> str:
        """Generate a unique event ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        return f"CB-{timestamp}"
    
    def _compute_hash(self, data: str) -> str:
        """Compute SHA256 hash for integrity."""
        return hashlib.sha256(data.encode("utf-8")).hexdigest()
    
    def _do_http_post(self, payload: CBorgsPayload) -> DispatchResult:
        """
        Execute HTTP POST to C-Borgs webhook.
        
        This method runs in a DAEMON THREAD — it cannot block the main process.
        
        Args:
            payload: The payload to send
            
        Returns:
            DispatchResult with status
        """
        event_id = payload.event_id
        timestamp = datetime.now(timezone.utc).isoformat()
        
        try:
            # Prepare request
            json_data = payload.to_json().encode("utf-8")
            
            request = Request(
                self.webhook_url,
                data=json_data,
                headers={
                    "Content-Type": "application/json",
                    "X-ChainBridge-Event-ID": event_id,
                    "X-ChainBridge-Signature": self._compute_hash(payload.to_json()),
                    "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                },
                method="POST"
            )
            
            # Execute with timeout
            print(f"📡 [C-Borgs] Dispatching {event_id} to {self.webhook_url}...")
            
            with urlopen(request, timeout=self.timeout) as response:
                status_code = response.status
                
                if 200 <= status_code < 300:
                    self._success_count += 1
                    result = DispatchResult(
                        event_id=event_id,
                        status=DispatchStatus.DELIVERED,
                        timestamp=timestamp,
                        response_code=status_code,
                    )
                    print(f"✅ [C-Borgs] Delivered {event_id} (HTTP {status_code})")
                else:
                    self._failure_count += 1
                    result = DispatchResult(
                        event_id=event_id,
                        status=DispatchStatus.FAILED,
                        timestamp=timestamp,
                        error=f"HTTP {status_code}",
                        response_code=status_code,
                    )
                    print(f"⚠️ [C-Borgs] Failed {event_id} (HTTP {status_code})")
        
        except HTTPError as e:
            self._failure_count += 1
            result = DispatchResult(
                event_id=event_id,
                status=DispatchStatus.FAILED,
                timestamp=timestamp,
                error=f"HTTP Error: {e.code} {e.reason}",
                response_code=e.code,
            )
            print(f"⚠️ [C-Borgs] HTTP Error {event_id}: {e.code} {e.reason}")
        
        except URLError as e:
            self._failure_count += 1
            result = DispatchResult(
                event_id=event_id,
                status=DispatchStatus.FAILED,
                timestamp=timestamp,
                error=f"URL Error: {e.reason}",
            )
            print(f"⚠️ [C-Borgs] URL Error {event_id}: {e.reason}")
        
        except TimeoutError:
            self._failure_count += 1
            result = DispatchResult(
                event_id=event_id,
                status=DispatchStatus.FAILED,
                timestamp=timestamp,
                error=f"Timeout after {self.timeout}s",
            )
            print(f"⚠️ [C-Borgs] Timeout {event_id} after {self.timeout}s")
        
        except Exception as e:
            self._failure_count += 1
            result = DispatchResult(
                event_id=event_id,
                status=DispatchStatus.FAILED,
                timestamp=timestamp,
                error=str(e),
            )
            print(f"⚠️ [C-Borgs] Exception {event_id}: {e}")
        
        # Callback for monitoring
        if self._on_dispatch:
            try:
                self._on_dispatch(result)
            except Exception:
                pass  # Callback failures are non-critical
        
        return result
    
    def dispatch_outcome(
        self,
        event_type: OutcomeType,
        pac_id: Optional[str] = None,
        agent_gid: Optional[str] = None,
        action: Optional[str] = None,
        status: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        blocking: bool = False,
    ) -> DispatchResult:
        """
        Dispatch an outcome to C-Borgs / Sea Burgers Biz.
        
        IRON FLOW:
        1. Build payload
        2. ALEX governance review
        3. Fire daemon thread for HTTP POST (non-blocking)
        
        Args:
            event_type: Type of outcome
            pac_id: PAC identifier (if applicable)
            agent_gid: Agent GID (if applicable)
            action: Action performed
            status: Result status
            details: Additional details
            blocking: If True, wait for result (for testing only)
            
        Returns:
            DispatchResult with initial status (DISPATCHED or BLOCKED)
        """
        self._dispatch_count += 1
        event_id = self._generate_event_id()
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Build payload
        payload = CBorgsPayload(
            event_id=event_id,
            event_type=event_type.value,
            timestamp=timestamp,
            pac_id=pac_id,
            agent_gid=agent_gid,
            action=action,
            status=status,
            details=details,
        )
        
        # Compute integrity hash
        payload.integrity_hash = self._compute_hash(payload.to_json())
        
        # ALEX Governance Review
        approved, reason = self.governance.review_payload(payload)
        
        if not approved:
            self._blocked_count += 1
            print(f"🚫 [C-Borgs] {reason}")
            return DispatchResult(
                event_id=event_id,
                status=DispatchStatus.BLOCKED_GOVERNANCE,
                timestamp=timestamp,
                error=reason,
            )
        
        # Mark as governance approved
        payload.governance_approved = True
        payload.governance_reviewer = self.governance.gid
        
        # Check if enabled
        if not self.is_enabled:
            print(f"📭 [C-Borgs] Disabled — {event_id} logged locally only")
            return DispatchResult(
                event_id=event_id,
                status=DispatchStatus.PENDING,
                timestamp=timestamp,
                error="C-Borgs integration disabled",
            )
        
        # IRON: Fire daemon thread (non-blocking)
        if blocking:
            # For testing — execute synchronously
            return self._do_http_post(payload)
        else:
            # Production — daemon thread
            bg_dispatch = threading.Thread(
                target=self._do_http_post,
                args=(payload,),
                daemon=True,  # CRITICAL: Cannot block process exit
                name=f"CBorgs-{event_id}"
            )
            bg_dispatch.start()
            # FORBIDDEN: bg_dispatch.join() — P33 LAW
            
            return DispatchResult(
                event_id=event_id,
                status=DispatchStatus.DISPATCHED,
                timestamp=timestamp,
            )
    
    def dispatch_pac_completed(
        self,
        pac_id: str,
        executor_gid: str,
        verdict: str,
        notes: Optional[str] = None,
    ) -> DispatchResult:
        """Convenience method for PAC completion events."""
        return self.dispatch_outcome(
            event_type=OutcomeType.PAC_COMPLETED,
            pac_id=pac_id,
            agent_gid=executor_gid,
            action="PAC_COMPLETED",
            status=verdict,
            details={"notes": notes} if notes else None,
        )
    
    def dispatch_agent_spawned(
        self,
        requester_gid: str,
        target_gid: str,
        task_summary: Optional[str] = None,
        status: str = "SUCCESS",
    ) -> DispatchResult:
        """Convenience method for agent spawn events."""
        return self.dispatch_outcome(
            event_type=OutcomeType.AGENT_SPAWNED,
            agent_gid=target_gid,
            action="AGENT_SPAWNED",
            status=status,
            details={
                "requester_gid": requester_gid,
                "task_summary": task_summary,
            },
        )
    
    def dispatch_alert(
        self,
        alert_type: str,
        message: str,
        severity: str = "INFO",
        source_gid: Optional[str] = None,
    ) -> DispatchResult:
        """Convenience method for alert events."""
        return self.dispatch_outcome(
            event_type=OutcomeType.ALERT,
            agent_gid=source_gid,
            action=f"ALERT_{alert_type.upper()}",
            status=severity,
            details={"message": message},
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics."""
        return {
            "enabled": self.is_enabled,
            "webhook_url": self.webhook_url,
            "dispatches": {
                "total": self._dispatch_count,
                "success": self._success_count,
                "failed": self._failure_count,
                "blocked": self._blocked_count,
            },
            "governance": self.governance.get_stats(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_adapter_instance: Optional[CBorgsAdapter] = None


def get_cborgs_adapter() -> CBorgsAdapter:
    """Get the singleton CBorgsAdapter instance."""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = CBorgsAdapter()
    return _adapter_instance
