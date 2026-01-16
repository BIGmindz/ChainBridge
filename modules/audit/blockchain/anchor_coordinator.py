"""
Blockchain Anchor Coordinator
=============================

PAC-SEC-P822-B: BLOCKCHAIN AUDIT ANCHORING
Component: Dual-Chain Anchor Coordinator
Agent: CODY (GID-01)

PURPOSE:
  Coordinates dual-chain blockchain anchoring strategy with XRP Ledger
  as primary and Hedera Consensus Service as secondary/fallback.
  Manages batch optimization, retry logic, and chain selection.

INVARIANTS:
  INV-ANCHOR-001: Audit events MUST anchor within 5 minutes
  INV-ANCHOR-003: Dual-chain redundancy (XRP + Hedera)
  INV-ANCHOR-006: Fallback MUST activate when primary fails
  INV-ANCHOR-007: Retry logic MUST attempt 3 times before fail-closed

COORDINATION STRATEGY:
  - Primary: XRP Ledger (low cost, public verification)
  - Secondary: Hedera Consensus Service (high throughput, nanosecond precision)
  - Batch: Anchor every 100 events OR 5 minutes, whichever first
  - Fallback: If XRPL fails 3 times, anchor to Hedera
  - Redundancy: Optionally anchor to both chains for critical audits
"""

import asyncio
import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .xrp_connector import XRPLConnector, XRPLConfig, XRPLNetwork, TransactionReceipt
from .hedera_connector import HederaConnector, HederaConfig, HederaNetwork, MessageReceipt
from .proof_generator import ProofGenerator, InclusionProof, AnchorProof
from .pqc_anchor import PQCAnchor, AnchorSignature

logger = logging.getLogger(__name__)


class ChainPriority(Enum):
    """Blockchain chain priority."""
    XRPL_PRIMARY = "xrpl_primary"
    HEDERA_PRIMARY = "hedera_primary"
    DUAL_CHAIN = "dual_chain"


class AnchorStrategy(Enum):
    """Anchoring strategy."""
    SINGLE_CHAIN = "single_chain"
    DUAL_REDUNDANT = "dual_redundant"
    FAILOVER = "failover"


class BatchTrigger(Enum):
    """What triggered a batch anchor."""
    EVENT_COUNT = "event_count"
    TIME_INTERVAL = "time_interval"
    MANUAL = "manual"
    CRITICAL_EVENT = "critical_event"


@dataclass
class CoordinatorConfig:
    """Configuration for anchor coordinator."""
    # Chain priority
    priority: ChainPriority = ChainPriority.XRPL_PRIMARY
    strategy: AnchorStrategy = AnchorStrategy.FAILOVER
    
    # Batch settings
    batch_size: int = 100
    batch_interval_seconds: int = 300  # 5 minutes
    
    # Retry settings
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    retry_backoff_multiplier: float = 2.0
    
    # Timeout settings
    anchor_timeout_seconds: int = 30
    
    # PQC settings
    enable_pqc_signatures: bool = True
    
    # Logging
    log_all_anchors: bool = True


@dataclass
class AnchorResult:
    """Result of an anchoring operation."""
    success: bool
    merkle_root: str
    event_count: int
    trigger: BatchTrigger
    timestamp: str
    xrpl_receipt: Optional[TransactionReceipt] = None
    hedera_receipt: Optional[MessageReceipt] = None
    pqc_signature: Optional[AnchorSignature] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    duration_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "merkle_root": self.merkle_root,
            "event_count": self.event_count,
            "trigger": self.trigger.value,
            "timestamp": self.timestamp,
            "xrpl_receipt": self.xrpl_receipt.to_dict() if self.xrpl_receipt else None,
            "hedera_receipt": self.hedera_receipt.to_dict() if self.hedera_receipt else None,
            "pqc_signature": self.pqc_signature.to_dict() if self.pqc_signature else None,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "duration_ms": self.duration_ms,
        }


@dataclass
class AnchorStatus:
    """Current status of anchor coordinator."""
    is_running: bool
    pending_events: int
    last_anchor_time: Optional[str]
    last_merkle_root: Optional[str]
    total_anchors: int
    successful_anchors: int
    failed_anchors: int
    xrpl_connected: bool
    hedera_connected: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_running": self.is_running,
            "pending_events": self.pending_events,
            "last_anchor_time": self.last_anchor_time,
            "last_merkle_root": self.last_merkle_root,
            "total_anchors": self.total_anchors,
            "successful_anchors": self.successful_anchors,
            "failed_anchors": self.failed_anchors,
            "xrpl_connected": self.xrpl_connected,
            "hedera_connected": self.hedera_connected,
        }


class AnchorCoordinator:
    """
    Coordinates dual-chain blockchain anchoring.
    
    Provides methods for:
    - anchor(): Anchor batch of events to blockchain(s)
    - get_anchor_status(): Get current coordinator status
    - fallback_logic(): Handle chain failures with fallback
    
    Thread-safe for concurrent operations.
    """
    
    def __init__(self,
                 config: Optional[CoordinatorConfig] = None,
                 xrpl_connector: Optional[XRPLConnector] = None,
                 hedera_connector: Optional[HederaConnector] = None,
                 proof_generator: Optional[ProofGenerator] = None,
                 pqc_anchor: Optional[PQCAnchor] = None):
        """
        Initialize anchor coordinator.
        
        Args:
            config: Coordinator configuration
            xrpl_connector: XRP Ledger connector
            hedera_connector: Hedera connector
            proof_generator: Proof generator
            pqc_anchor: PQC anchor for signatures
        """
        self.config = config or CoordinatorConfig()
        self._xrpl = xrpl_connector or XRPLConnector()
        self._hedera = hedera_connector or HederaConnector()
        self._proof_gen = proof_generator or ProofGenerator()
        self._pqc = pqc_anchor or PQCAnchor()
        
        self._lock = threading.RLock()
        self._running = False
        self._pending_hashes: List[str] = []
        self._last_anchor_time: Optional[datetime] = None
        self._anchor_results: List[AnchorResult] = []
        self._callbacks: List[Callable[[AnchorResult], None]] = []
        
        # Statistics
        self._total_anchors = 0
        self._successful_anchors = 0
        self._failed_anchors = 0
    
    def start(self) -> bool:
        """
        Start anchor coordinator.
        
        Connects to blockchain networks.
        
        Returns:
            True if started successfully
        """
        with self._lock:
            if self._running:
                return True
            
            try:
                # Connect to XRPL
                if not self._xrpl.connect():
                    logger.warning("Failed to connect to XRPL")
                
                # Connect to Hedera
                if not self._hedera.connect():
                    logger.warning("Failed to connect to Hedera")
                
                # Create Hedera topic if needed
                if self._hedera.is_connected and not self._hedera.topic_id:
                    self._hedera.create_topic("ChainBridge Audit Log")
                
                # Generate PQC key pair
                if self.config.enable_pqc_signatures:
                    self._pqc.generate_key_pair()
                
                self._running = True
                logger.info("Anchor coordinator started")
                return True
                
            except Exception as e:
                logger.error(f"Failed to start coordinator: {e}")
                return False
    
    def stop(self):
        """Stop anchor coordinator."""
        with self._lock:
            if self._running:
                # Anchor any pending events
                if self._pending_hashes:
                    try:
                        self._anchor_batch(BatchTrigger.MANUAL)
                    except Exception:
                        pass
                
                self._xrpl.disconnect()
                self._hedera.disconnect()
                self._running = False
                logger.info("Anchor coordinator stopped")
    
    def add_event(self, event_hash: str) -> Optional[AnchorResult]:
        """
        Add event hash for anchoring.
        
        Automatically triggers batch anchor if threshold reached.
        
        Args:
            event_hash: SHA-256 hash of event
            
        Returns:
            AnchorResult if batch was triggered, None otherwise
        """
        with self._lock:
            self._pending_hashes.append(event_hash)
            
            # Check if batch threshold reached
            if len(self._pending_hashes) >= self.config.batch_size:
                return self._anchor_batch(BatchTrigger.EVENT_COUNT)
            
            return None
    
    def check_time_trigger(self) -> Optional[AnchorResult]:
        """
        Check if time-based anchor should trigger.
        
        Returns:
            AnchorResult if triggered, None otherwise
        """
        with self._lock:
            if not self._pending_hashes:
                return None
            
            now = datetime.now(timezone.utc)
            
            if self._last_anchor_time:
                elapsed = (now - self._last_anchor_time).total_seconds()
                if elapsed >= self.config.batch_interval_seconds:
                    return self._anchor_batch(BatchTrigger.TIME_INTERVAL)
            else:
                # First anchor after startup
                self._last_anchor_time = now
            
            return None
    
    def anchor(self,
                merkle_root: str,
                event_count: int,
                trigger: BatchTrigger = BatchTrigger.MANUAL,
                ) -> AnchorResult:
        """
        Anchor a Merkle root to blockchain(s).
        
        Args:
            merkle_root: Merkle root hash to anchor
            event_count: Number of events in batch
            trigger: What triggered this anchor
            
        Returns:
            AnchorResult with details
        """
        start_time = time.time()
        
        xrpl_receipt = None
        hedera_receipt = None
        pqc_signature = None
        error_message = None
        retry_count = 0
        success = False
        
        try:
            # Try primary chain with retries
            if self.config.priority in (ChainPriority.XRPL_PRIMARY, ChainPriority.DUAL_CHAIN):
                xrpl_receipt, retry_count = self._anchor_to_xrpl_with_retry(merkle_root)
                if xrpl_receipt:
                    success = True
            
            # If primary failed or dual-chain, try secondary
            if not success or self.config.priority == ChainPriority.DUAL_CHAIN:
                if self.config.priority == ChainPriority.HEDERA_PRIMARY or not success:
                    hedera_receipt = self._anchor_to_hedera_with_retry(merkle_root)
                    if hedera_receipt:
                        success = True
            
            # Generate PQC signature
            if success and self.config.enable_pqc_signatures:
                tx_ref = xrpl_receipt.tx_hash if xrpl_receipt else f"{hedera_receipt.topic_id}/{hedera_receipt.sequence_number}"
                blockchain = "xrpl" if xrpl_receipt else "hedera"
                pqc_signature = self._pqc.hybrid_anchor(merkle_root, blockchain, tx_ref)
            
            if not success:
                error_message = "All blockchain anchoring attempts failed"
                
        except Exception as e:
            error_message = str(e)
            logger.error(f"Anchor failed: {e}")
        
        duration_ms = (time.time() - start_time) * 1000
        
        result = AnchorResult(
            success=success,
            merkle_root=merkle_root,
            event_count=event_count,
            trigger=trigger,
            timestamp=datetime.now(timezone.utc).isoformat(),
            xrpl_receipt=xrpl_receipt,
            hedera_receipt=hedera_receipt,
            pqc_signature=pqc_signature,
            error_message=error_message,
            retry_count=retry_count,
            duration_ms=duration_ms,
        )
        
        # Update statistics
        self._total_anchors += 1
        if success:
            self._successful_anchors += 1
        else:
            self._failed_anchors += 1
        
        # Store result
        self._anchor_results.append(result)
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(result)
            except Exception:
                pass
        
        if self.config.log_all_anchors:
            logger.info(f"Anchor {'succeeded' if success else 'failed'}: {merkle_root[:16]}... ({event_count} events, {duration_ms:.1f}ms)")
        
        return result
    
    def _anchor_batch(self, trigger: BatchTrigger) -> AnchorResult:
        """Anchor current batch of pending events."""
        if not self._pending_hashes:
            raise ValueError("No pending events to anchor")
        
        # Compute Merkle root
        merkle_root = self._compute_merkle_root(self._pending_hashes)
        event_count = len(self._pending_hashes)
        
        # Clear pending
        self._pending_hashes = []
        self._last_anchor_time = datetime.now(timezone.utc)
        
        return self.anchor(merkle_root, event_count, trigger)
    
    def _compute_merkle_root(self, hashes: List[str]) -> str:
        """Compute Merkle root from event hashes."""
        if not hashes:
            return "0" * 64
        
        current_level = list(hashes)
        
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = hashlib.sha256(f"{left}{right}".encode()).hexdigest()
                next_level.append(combined)
            current_level = next_level
        
        return current_level[0]
    
    def _anchor_to_xrpl_with_retry(self, 
                                    merkle_root: str,
                                    ) -> Tuple[Optional[TransactionReceipt], int]:
        """Anchor to XRPL with retry logic."""
        if not self._xrpl.is_connected:
            return None, 0
        
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                receipt = self._xrpl.anchor_to_xrpl(merkle_root)
                return receipt, attempt
            except Exception as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay_seconds * (self.config.retry_backoff_multiplier ** attempt)
                    time.sleep(delay)
        
        logger.warning(f"XRPL anchoring failed after {self.config.max_retries} attempts: {last_error}")
        return None, self.config.max_retries
    
    def _anchor_to_hedera_with_retry(self, 
                                      merkle_root: str,
                                      ) -> Optional[MessageReceipt]:
        """Anchor to Hedera with retry logic."""
        if not self._hedera.is_connected:
            return None
        
        for attempt in range(self.config.max_retries):
            try:
                return self._hedera.anchor_to_hedera(merkle_root)
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay_seconds * (self.config.retry_backoff_multiplier ** attempt)
                    time.sleep(delay)
        
        logger.warning(f"Hedera anchoring failed after {self.config.max_retries} attempts")
        return None
    
    def fallback_logic(self, primary_chain: str) -> str:
        """
        Determine fallback chain when primary fails.
        
        Args:
            primary_chain: Name of failed primary chain
            
        Returns:
            Name of fallback chain
        """
        if primary_chain == "xrpl":
            return "hedera"
        elif primary_chain == "hedera":
            return "xrpl"
        else:
            return "hedera"  # Default fallback
    
    def get_anchor_status(self) -> AnchorStatus:
        """Get current coordinator status."""
        with self._lock:
            last_result = self._anchor_results[-1] if self._anchor_results else None
            
            return AnchorStatus(
                is_running=self._running,
                pending_events=len(self._pending_hashes),
                last_anchor_time=last_result.timestamp if last_result else None,
                last_merkle_root=last_result.merkle_root if last_result else None,
                total_anchors=self._total_anchors,
                successful_anchors=self._successful_anchors,
                failed_anchors=self._failed_anchors,
                xrpl_connected=self._xrpl.is_connected,
                hedera_connected=self._hedera.is_connected,
            )
    
    def get_anchor_history(self, limit: int = 100) -> List[AnchorResult]:
        """Get recent anchor history."""
        with self._lock:
            return self._anchor_results[-limit:]
    
    def verify_anchor(self, 
                       merkle_root: str,
                       ) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify an anchor exists on blockchain.
        
        Args:
            merkle_root: Merkle root to verify
            
        Returns:
            Tuple of (is_verified, verification_details)
        """
        details = {
            "merkle_root": merkle_root,
            "xrpl_verified": False,
            "hedera_verified": False,
        }
        
        # Check XRPL
        xrpl_receipt = self._xrpl.get_anchor_by_merkle_root(merkle_root)
        if xrpl_receipt:
            is_valid, _ = self._xrpl.verify_xrpl_anchor(xrpl_receipt.tx_hash, merkle_root)
            details["xrpl_verified"] = is_valid
            details["xrpl_tx_hash"] = xrpl_receipt.tx_hash
            details["xrpl_explorer"] = xrpl_receipt.explorer_url
        
        # Check Hedera
        hedera_proof = self._hedera.get_consensus_proof(merkle_root)
        if hedera_proof:
            is_valid, _ = self._hedera.verify_hedera_anchor(
                hedera_proof.topic_id,
                hedera_proof.sequence_number,
                merkle_root
            )
            details["hedera_verified"] = is_valid
            details["hedera_topic"] = hedera_proof.topic_id
            details["hedera_sequence"] = hedera_proof.sequence_number
        
        is_verified = details["xrpl_verified"] or details["hedera_verified"]
        return is_verified, details
    
    def on_anchor(self, callback: Callable[[AnchorResult], None]):
        """Register callback for anchor events."""
        self._callbacks.append(callback)
    
    def force_anchor(self) -> Optional[AnchorResult]:
        """Force immediate anchor of pending events."""
        with self._lock:
            if self._pending_hashes:
                return self._anchor_batch(BatchTrigger.MANUAL)
            return None
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False


def create_anchor_coordinator(
    priority: ChainPriority = ChainPriority.XRPL_PRIMARY,
    strategy: AnchorStrategy = AnchorStrategy.FAILOVER,
    batch_size: int = 100,
    batch_interval_seconds: int = 300,
) -> AnchorCoordinator:
    """
    Factory function for creating anchor coordinator.
    
    Args:
        priority: Chain priority setting
        strategy: Anchoring strategy
        batch_size: Events per batch
        batch_interval_seconds: Max time between anchors
        
    Returns:
        Configured AnchorCoordinator
    """
    config = CoordinatorConfig(
        priority=priority,
        strategy=strategy,
        batch_size=batch_size,
        batch_interval_seconds=batch_interval_seconds,
    )
    return AnchorCoordinator(config=config)
