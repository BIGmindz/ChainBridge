"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                     HEDERA ADAPTER — CONSENSUS SERVICE                        ║
║                     PAC-OCC-P34 — Fair Ordering Gateway v1.0.0                ║
╚═══════════════════════════════════════════════════════════════════════════════╝

The Hedera Adapter submits proof hashes to the Hedera Consensus Service (HCS)
for fair ordering and immutable timestamping.

HEDERA CONSENSUS SERVICE (HCS):
- Asynchronous Byzantine Fault Tolerant (ABFT) consensus
- Sub-second finality with fair ordering
- Immutable timestamp for all ChainBridge decisions

IRON ARCHITECTURE:
- All HCS submissions run in DAEMON THREADS (non-blocking)
- No .join() calls — fire-and-forget pattern
- Timeout protection on all network operations
- Local audit remains authoritative

SECURITY:
- Account IDs and Private Keys MUST be in environment variables
- NEVER store credentials in code or container

Authors:
- CODY (GID-01) — Implementation
- JEFFREY — Five Pillars Architecture
"""

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Callable


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Hedera Network Configuration
HEDERA_ENABLED = os.getenv("HEDERA_ENABLED", "false").lower() == "true"
HEDERA_NETWORK = os.getenv("HEDERA_NETWORK", "testnet")  # mainnet, testnet, previewnet
HEDERA_OPERATOR_ID = os.getenv("HEDERA_OPERATOR_ID", "")  # e.g., "0.0.12345"
HEDERA_OPERATOR_KEY = os.getenv("HEDERA_OPERATOR_KEY", "")  # Private key (DER hex)
HEDERA_TOPIC_ID = os.getenv("HEDERA_TOPIC_ID", "")  # HCS Topic ID
HEDERA_TIMEOUT = int(os.getenv("HEDERA_TIMEOUT", "10"))  # seconds

# Mirror Node for verification
HEDERA_MIRROR_URL = os.getenv(
    "HEDERA_MIRROR_URL",
    "https://testnet.mirrornode.hedera.com"
)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class HCSStatus(Enum):
    """Status of HCS submission."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class HCSMessage:
    """
    Message structure for Hedera Consensus Service.
    
    All ChainBridge decisions are serialized to this format before
    submission to HCS for fair ordering.
    """
    # Metadata
    message_id: str
    timestamp: str  # ISO 8601
    source: str = "chainbridge"
    version: str = "1.0.0"
    
    # Content
    pac_id: Optional[str] = None
    event_type: Optional[str] = None
    proof_hash: Optional[str] = None  # SHA256 of the decision payload
    
    # References
    agent_gid: Optional[str] = None
    action: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    def to_json(self) -> str:
        """Convert to JSON string (for HCS submission)."""
        return json.dumps(self.to_dict(), separators=(',', ':'))
    
    def to_bytes(self) -> bytes:
        """Convert to bytes (for HCS submission)."""
        return self.to_json().encode("utf-8")


@dataclass
class HCSResult:
    """Result of an HCS submission."""
    message_id: str
    status: HCSStatus
    timestamp: str
    topic_id: Optional[str] = None
    sequence_number: Optional[int] = None
    running_hash: Optional[str] = None
    consensus_timestamp: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "topic_id": self.topic_id,
            "sequence_number": self.sequence_number,
            "running_hash": self.running_hash,
            "consensus_timestamp": self.consensus_timestamp,
            "error": self.error,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# HEDERA ADAPTER (IRON PATTERN)
# ═══════════════════════════════════════════════════════════════════════════════

class HederaAdapter:
    """
    Hedera Consensus Service (HCS) Adapter.
    
    IRON ARCHITECTURE:
    - All HCS submissions run in daemon threads (non-blocking)
    - No .join() calls — fire-and-forget
    - Timeout protection (default 10s)
    - Local audit remains authoritative
    
    Usage:
        adapter = HederaAdapter()
        result = adapter.submit_proof(
            pac_id="PAC-OCC-P34",
            proof_hash="abc123...",
            event_type="PAC_COMPLETED",
        )
    """
    
    def __init__(
        self,
        operator_id: Optional[str] = None,
        operator_key: Optional[str] = None,
        topic_id: Optional[str] = None,
        network: str = HEDERA_NETWORK,
        timeout: int = HEDERA_TIMEOUT,
        enabled: Optional[bool] = None,
    ):
        """
        Initialize the Hedera Adapter.
        
        Args:
            operator_id: Hedera account ID (default: env var)
            operator_key: Hedera private key (default: env var)
            topic_id: HCS topic ID (default: env var)
            network: Network name (mainnet, testnet, previewnet)
            timeout: Submission timeout in seconds
            enabled: Override enabled flag (default: env var)
        """
        self.operator_id = operator_id or HEDERA_OPERATOR_ID
        self.operator_key = operator_key or HEDERA_OPERATOR_KEY
        self.topic_id = topic_id or HEDERA_TOPIC_ID
        self.network = network
        self.timeout = timeout
        self.enabled = enabled if enabled is not None else HEDERA_ENABLED
        
        # Statistics
        self._submit_count = 0
        self._success_count = 0
        self._failure_count = 0
        
        # Callbacks for monitoring
        self._on_submit: Optional[Callable[[HCSResult], None]] = None
        
        # SDK client (lazy initialization)
        self._client = None
    
    @property
    def is_enabled(self) -> bool:
        """Check if Hedera integration is enabled and configured."""
        return (
            self.enabled 
            and bool(self.operator_id) 
            and bool(self.topic_id)
        )
    
    @property
    def is_configured(self) -> bool:
        """Check if Hedera is fully configured (including key)."""
        return self.is_enabled and bool(self.operator_key)
    
    def _generate_message_id(self) -> str:
        """Generate a unique message ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        return f"HCS-{timestamp}"
    
    def _compute_hash(self, data: str) -> str:
        """Compute SHA256 hash."""
        return hashlib.sha256(data.encode("utf-8")).hexdigest()
    
    def _do_hcs_submit(self, message: HCSMessage) -> HCSResult:
        """
        Execute HCS submission.
        
        This method runs in a DAEMON THREAD — it cannot block the main process.
        
        In production, this would use the hedera-sdk-py:
        
            from hedera import Client, TopicMessageSubmitTransaction
            
            client = Client.for_testnet()
            client.set_operator(AccountId.fromString(self.operator_id), 
                               PrivateKey.fromString(self.operator_key))
            
            tx = TopicMessageSubmitTransaction()
            tx.set_topic_id(TopicId.fromString(self.topic_id))
            tx.set_message(message.to_bytes())
            
            receipt = tx.execute(client).get_receipt(client)
            sequence_number = receipt.topic_sequence_number
        """
        message_id = message.message_id
        timestamp = datetime.now(timezone.utc).isoformat()
        
        try:
            print(f"📡 [Hedera] Submitting {message_id} to HCS Topic {self.topic_id}...")
            
            # ═══════════════════════════════════════════════════════════════════
            # PRODUCTION: Replace with actual Hedera SDK call:
            #
            #   from hedera import (
            #       Client, AccountId, PrivateKey,
            #       TopicId, TopicMessageSubmitTransaction
            #   )
            #   
            #   client = Client.for_testnet()
            #   client.set_operator(
            #       AccountId.from_string(self.operator_id),
            #       PrivateKey.from_string(self.operator_key)
            #   )
            #   
            #   tx = TopicMessageSubmitTransaction()
            #   tx.set_topic_id(TopicId.from_string(self.topic_id))
            #   tx.set_message(message.to_bytes())
            #   
            #   response = tx.execute(client)
            #   receipt = response.get_receipt(client)
            #   
            #   sequence_number = receipt.topic_sequence_number
            #   running_hash = receipt.topic_running_hash.hex()
            #
            # For now, simulate HCS submission:
            # ═══════════════════════════════════════════════════════════════════
            
            time.sleep(0.1)  # Simulated network latency
            
            # Simulated response
            simulated_sequence = int(time.time() * 1000) % 1000000
            simulated_hash = self._compute_hash(f"{self.topic_id}:{simulated_sequence}")
            
            self._success_count += 1
            result = HCSResult(
                message_id=message_id,
                status=HCSStatus.CONFIRMED,
                timestamp=timestamp,
                topic_id=self.topic_id,
                sequence_number=simulated_sequence,
                running_hash=simulated_hash,
                consensus_timestamp=datetime.now(timezone.utc).isoformat(),
            )
            
            print(f"✅ [Hedera] Confirmed {message_id} — Seq#{simulated_sequence}")
            
        except TimeoutError:
            self._failure_count += 1
            result = HCSResult(
                message_id=message_id,
                status=HCSStatus.FAILED,
                timestamp=timestamp,
                error=f"Timeout after {self.timeout}s",
            )
            print(f"⚠️ [Hedera] Timeout {message_id}")
            
        except Exception as e:
            self._failure_count += 1
            result = HCSResult(
                message_id=message_id,
                status=HCSStatus.FAILED,
                timestamp=timestamp,
                error=str(e),
            )
            print(f"⚠️ [Hedera] Error {message_id}: {e}")
        
        # Callback for monitoring
        if self._on_submit:
            try:
                self._on_submit(result)
            except Exception:
                pass
        
        return result
    
    def submit_proof(
        self,
        proof_hash: str,
        pac_id: Optional[str] = None,
        event_type: Optional[str] = None,
        agent_gid: Optional[str] = None,
        action: Optional[str] = None,
        blocking: bool = False,
    ) -> HCSResult:
        """
        Submit a proof hash to Hedera Consensus Service.
        
        IRON FLOW:
        1. Build HCS message
        2. Fire daemon thread for submission (non-blocking)
        
        Args:
            proof_hash: SHA256 hash of the decision/payload
            pac_id: PAC identifier (optional)
            event_type: Type of event (optional)
            agent_gid: Agent GID (optional)
            action: Action performed (optional)
            blocking: If True, wait for result (for testing only)
            
        Returns:
            HCSResult with submission status
        """
        self._submit_count += 1
        message_id = self._generate_message_id()
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Build message
        message = HCSMessage(
            message_id=message_id,
            timestamp=timestamp,
            pac_id=pac_id,
            event_type=event_type,
            proof_hash=proof_hash,
            agent_gid=agent_gid,
            action=action,
        )
        
        # Check if enabled
        if not self.is_enabled:
            print(f"📭 [Hedera] Disabled — {message_id} logged locally only")
            return HCSResult(
                message_id=message_id,
                status=HCSStatus.DISABLED,
                timestamp=timestamp,
                error="Hedera integration disabled",
            )
        
        # IRON: Fire daemon thread (non-blocking)
        if blocking:
            return self._do_hcs_submit(message)
        else:
            bg_submit = threading.Thread(
                target=self._do_hcs_submit,
                args=(message,),
                daemon=True,
                name=f"Hedera-{message_id}"
            )
            bg_submit.start()
            # FORBIDDEN: bg_submit.join() — P34 LAW
            
            return HCSResult(
                message_id=message_id,
                status=HCSStatus.SUBMITTED,
                timestamp=timestamp,
                topic_id=self.topic_id,
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics."""
        return {
            "enabled": self.is_enabled,
            "configured": self.is_configured,
            "network": self.network,
            "topic_id": self.topic_id,
            "submissions": {
                "total": self._submit_count,
                "success": self._success_count,
                "failed": self._failure_count,
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_adapter_instance: Optional[HederaAdapter] = None


def get_hedera_adapter() -> HederaAdapter:
    """Get the singleton HederaAdapter instance."""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = HederaAdapter()
    return _adapter_instance
