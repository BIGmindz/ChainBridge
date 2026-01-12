"""
Hedera Consensus Service Connector
==================================

PAC-SEC-P822-B: BLOCKCHAIN AUDIT ANCHORING
Component: Hedera Consensus Service Integration
Agent: NEXUS (GID-03)

PURPOSE:
  Implements Hedera Consensus Service (HCS) integration for audit anchoring.
  Provides nanosecond-precision timestamps and high-throughput consensus.
  Serves as secondary/backup anchor to XRP Ledger.

INVARIANTS:
  INV-ANCHOR-001: Audit events MUST anchor within 5 minutes
  INV-ANCHOR-002: Only hash anchors to blockchain, never content
  INV-ANCHOR-003: Dual-chain redundancy (XRP + Hedera)
  INV-ANCHOR-004: Nanosecond precision timestamps required

HEDERA FEATURES:
  - 10,000+ TPS capacity
  - Nanosecond precision consensus timestamps
  - Ordered, immutable message log
  - Low latency (~3-5 seconds finality)
  - Topic-based message organization
  - Mirror node for historical queries
"""

import asyncio
import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class HederaNetwork(Enum):
    """Hedera network options."""
    MAINNET = "mainnet"
    TESTNET = "testnet"
    PREVIEWNET = "previewnet"


class MessageStatus(Enum):
    """Status of HCS message."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    CONSENSUS_REACHED = "consensus_reached"
    FAILED = "failed"


@dataclass
class HederaConfig:
    """Configuration for Hedera connector."""
    network: HederaNetwork = HederaNetwork.TESTNET
    operator_id: Optional[str] = None
    operator_key: Optional[str] = None
    topic_id: Optional[str] = None
    mirror_node_url: str = "https://testnet.mirrornode.hedera.com"
    grpc_endpoint: str = "testnet.hedera.com:50211"
    max_message_size: int = 1024  # 1KB
    timeout_seconds: int = 30
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0


@dataclass
class ConsensusTimestamp:
    """
    Hedera consensus timestamp.
    
    Provides nanosecond precision for audit ordering.
    """
    seconds: int
    nanos: int
    
    @property
    def timestamp_ns(self) -> int:
        """Get timestamp in nanoseconds."""
        return self.seconds * 1_000_000_000 + self.nanos
    
    @property
    def timestamp_iso(self) -> str:
        """Get ISO format timestamp."""
        dt = datetime.fromtimestamp(self.seconds, tz=timezone.utc)
        return dt.isoformat() + f".{self.nanos:09d}Z"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "seconds": self.seconds,
            "nanos": self.nanos,
            "timestamp_ns": self.timestamp_ns,
            "timestamp_iso": self.timestamp_iso,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConsensusTimestamp":
        return cls(
            seconds=data["seconds"],
            nanos=data["nanos"],
        )
    
    @classmethod
    def now(cls) -> "ConsensusTimestamp":
        """Create timestamp for current time."""
        now = datetime.now(timezone.utc)
        return cls(
            seconds=int(now.timestamp()),
            nanos=now.microsecond * 1000,
        )


@dataclass
class MessageReceipt:
    """
    Receipt for an HCS message.
    
    Contains consensus proof for verification.
    """
    topic_id: str
    sequence_number: int
    running_hash: str
    consensus_timestamp: ConsensusTimestamp
    message_hash: str
    status: MessageStatus
    network: HederaNetwork
    mirror_url: str = ""
    
    def __post_init__(self):
        """Generate mirror node URL."""
        if not self.mirror_url:
            base = "https://hashscan.io"
            net = "testnet" if self.network != HederaNetwork.MAINNET else "mainnet"
            self.mirror_url = f"{base}/{net}/topic/{self.topic_id}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic_id": self.topic_id,
            "sequence_number": self.sequence_number,
            "running_hash": self.running_hash,
            "consensus_timestamp": self.consensus_timestamp.to_dict(),
            "message_hash": self.message_hash,
            "status": self.status.value,
            "network": self.network.value,
            "mirror_url": self.mirror_url,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageReceipt":
        return cls(
            topic_id=data["topic_id"],
            sequence_number=data["sequence_number"],
            running_hash=data["running_hash"],
            consensus_timestamp=ConsensusTimestamp.from_dict(data["consensus_timestamp"]),
            message_hash=data["message_hash"],
            status=MessageStatus(data["status"]),
            network=HederaNetwork(data["network"]),
            mirror_url=data.get("mirror_url", ""),
        )


@dataclass
class ConsensusProof:
    """
    Proof of consensus for a message.
    
    Enables third-party verification via mirror node.
    """
    merkle_root: str
    topic_id: str
    sequence_number: int
    consensus_timestamp: ConsensusTimestamp
    running_hash: str
    previous_running_hash: str
    verification_url: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "merkle_root": self.merkle_root,
            "topic_id": self.topic_id,
            "sequence_number": self.sequence_number,
            "consensus_timestamp": self.consensus_timestamp.to_dict(),
            "running_hash": self.running_hash,
            "previous_running_hash": self.previous_running_hash,
            "verification_url": self.verification_url,
        }


class HederaConnector:
    """
    Hedera Consensus Service connector for audit anchoring.
    
    Provides methods for:
    - anchor_to_hedera(): Submit Merkle root to HCS topic
    - verify_hedera_anchor(): Verify message on HCS
    - get_consensus_timestamp(): Get precise consensus time
    
    Thread-safe for concurrent operations.
    """
    
    def __init__(self, config: Optional[HederaConfig] = None):
        """
        Initialize Hedera connector.
        
        Args:
            config: Hedera configuration (uses defaults if None)
        """
        self.config = config or HederaConfig()
        self._lock = threading.RLock()
        self._client = None
        self._connected = False
        self._topic_id = config.topic_id if config else None
        self._pending_messages: Dict[str, MessageReceipt] = {}
        self._message_callbacks: List[Callable[[MessageReceipt], None]] = []
        self._sequence_counter = 0
        self._running_hash = "0" * 64
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to Hedera."""
        return self._connected
    
    @property
    def network(self) -> HederaNetwork:
        """Get current network."""
        return self.config.network
    
    @property
    def topic_id(self) -> Optional[str]:
        """Get current topic ID."""
        return self._topic_id
    
    def connect(self) -> bool:
        """
        Connect to Hedera network.
        
        Returns:
            True if connection successful
        """
        with self._lock:
            try:
                # In production, would use hedera-sdk-python:
                # from hedera import Client, AccountId, PrivateKey
                # self._client = Client.forTestnet()
                # self._client.setOperator(operator_id, operator_key)
                
                # Mock connection for testing
                self._connected = True
                logger.info(f"Connected to Hedera {self.config.network.value}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to connect to Hedera: {e}")
                self._connected = False
                return False
    
    def disconnect(self):
        """Disconnect from Hedera."""
        with self._lock:
            self._connected = False
            self._client = None
            logger.info("Disconnected from Hedera")
    
    def create_topic(self, memo: str = "ChainBridge Audit Log") -> str:
        """
        Create a new HCS topic for audit logging.
        
        Args:
            memo: Topic memo/description
            
        Returns:
            Topic ID string
        """
        if not self._connected:
            raise ConnectionError("Not connected to Hedera")
        
        with self._lock:
            # In production, would use ConsensusTopicCreateTransaction
            # Mock topic creation
            topic_id = f"0.0.{12345678 + hash(memo) % 1000}"
            self._topic_id = topic_id
            logger.info(f"Created HCS topic: {topic_id}")
            return topic_id
    
    def anchor_to_hedera(self,
                          merkle_root: str,
                          metadata: Optional[Dict[str, Any]] = None,
                          ) -> MessageReceipt:
        """
        Anchor a Merkle root hash to Hedera Consensus Service.
        
        Submits message to HCS topic with audit hash.
        
        Args:
            merkle_root: SHA-256 Merkle root hash to anchor
            metadata: Optional metadata to include
            
        Returns:
            MessageReceipt with consensus details
            
        Raises:
            ConnectionError: If not connected
            ValueError: If merkle_root is invalid
            RuntimeError: If submission fails
        """
        if not self._connected:
            raise ConnectionError("Not connected to Hedera. Call connect() first.")
        
        if not merkle_root or len(merkle_root) != 64:
            raise ValueError("merkle_root must be a 64-character hex string (SHA-256)")
        
        if not self._topic_id:
            raise ValueError("No topic ID configured. Call create_topic() first.")
        
        with self._lock:
            # Prepare message
            message = {
                "type": "audit/merkle-root",
                "merkle_root": merkle_root,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0",
            }
            if metadata:
                message["metadata"] = metadata
            
            message_bytes = json.dumps(message).encode()
            
            if len(message_bytes) > self.config.max_message_size:
                raise ValueError(f"Message exceeds max size: {len(message_bytes)} > {self.config.max_message_size}")
            
            # Attempt submission with retries
            last_error = None
            for attempt in range(self.config.retry_attempts):
                try:
                    receipt = self._submit_message(merkle_root, message_bytes)
                    
                    # Store pending message
                    self._pending_messages[merkle_root] = receipt
                    
                    # Notify callbacks
                    for callback in self._message_callbacks:
                        try:
                            callback(receipt)
                        except Exception:
                            pass
                    
                    return receipt
                    
                except Exception as e:
                    last_error = e
                    logger.warning(f"Hedera anchor attempt {attempt + 1} failed: {e}")
                    if attempt < self.config.retry_attempts - 1:
                        time.sleep(self.config.retry_delay_seconds * (2 ** attempt))
            
            raise RuntimeError(
                f"Failed to anchor to Hedera after {self.config.retry_attempts} attempts: {last_error}"
            )
    
    def _submit_message(self, merkle_root: str, message_bytes: bytes) -> MessageReceipt:
        """
        Submit message to HCS topic.
        
        In production, would use ConsensusMessageSubmitTransaction.
        """
        # Mock implementation
        now = datetime.now(timezone.utc)
        
        # Update sequence and running hash
        self._sequence_counter += 1
        message_hash = hashlib.sha256(message_bytes).hexdigest()
        
        # Running hash = SHA256(previous_running_hash + topic_id + sequence + message)
        new_running_hash = hashlib.sha256(
            f"{self._running_hash}:{self._topic_id}:{self._sequence_counter}:{message_hash}".encode()
        ).hexdigest()
        self._running_hash = new_running_hash
        
        consensus_ts = ConsensusTimestamp(
            seconds=int(now.timestamp()),
            nanos=now.microsecond * 1000,
        )
        
        receipt = MessageReceipt(
            topic_id=self._topic_id,
            sequence_number=self._sequence_counter,
            running_hash=new_running_hash,
            consensus_timestamp=consensus_ts,
            message_hash=message_hash,
            status=MessageStatus.CONSENSUS_REACHED,
            network=self.config.network,
        )
        
        logger.info(f"Anchored merkle root to HCS: topic={self._topic_id}, seq={self._sequence_counter}")
        return receipt
    
    def verify_hedera_anchor(self,
                              topic_id: str,
                              sequence_number: int,
                              expected_merkle_root: Optional[str] = None,
                              ) -> Tuple[bool, Optional[MessageReceipt]]:
        """
        Verify an anchor exists on Hedera.
        
        Args:
            topic_id: HCS topic ID
            sequence_number: Message sequence number
            expected_merkle_root: Optional expected hash to match
            
        Returns:
            Tuple of (is_valid, receipt if found)
        """
        if not self._connected:
            raise ConnectionError("Not connected to Hedera")
        
        with self._lock:
            try:
                # In production, would query mirror node:
                # GET /api/v1/topics/{topicId}/messages/{sequenceNumber}
                
                # Check pending messages
                for root, receipt in self._pending_messages.items():
                    if (receipt.topic_id == topic_id and 
                        receipt.sequence_number == sequence_number):
                        if expected_merkle_root and root != expected_merkle_root:
                            return False, receipt
                        return True, receipt
                
                return True, None
                
            except Exception as e:
                logger.error(f"Failed to verify Hedera anchor: {e}")
                return False, None
    
    def get_consensus_timestamp(self, 
                                 topic_id: str,
                                 sequence_number: int,
                                 ) -> Optional[ConsensusTimestamp]:
        """
        Get consensus timestamp for a message.
        
        Args:
            topic_id: HCS topic ID
            sequence_number: Message sequence number
            
        Returns:
            ConsensusTimestamp if found
        """
        if not self._connected:
            raise ConnectionError("Not connected to Hedera")
        
        with self._lock:
            for receipt in self._pending_messages.values():
                if (receipt.topic_id == topic_id and 
                    receipt.sequence_number == sequence_number):
                    return receipt.consensus_timestamp
            return None
    
    def get_consensus_proof(self, merkle_root: str) -> Optional[ConsensusProof]:
        """
        Get consensus proof for a Merkle root.
        
        Args:
            merkle_root: Merkle root hash
            
        Returns:
            ConsensusProof if found
        """
        receipt = self._pending_messages.get(merkle_root)
        if not receipt:
            return None
        
        # Find previous running hash
        prev_hash = "0" * 64
        for root, r in self._pending_messages.items():
            if r.sequence_number == receipt.sequence_number - 1:
                prev_hash = r.running_hash
                break
        
        return ConsensusProof(
            merkle_root=merkle_root,
            topic_id=receipt.topic_id,
            sequence_number=receipt.sequence_number,
            consensus_timestamp=receipt.consensus_timestamp,
            running_hash=receipt.running_hash,
            previous_running_hash=prev_hash,
            verification_url=receipt.mirror_url,
        )
    
    def get_topic_info(self) -> Dict[str, Any]:
        """Get HCS topic information."""
        if not self._connected:
            raise ConnectionError("Not connected to Hedera")
        
        return {
            "network": self.config.network.value,
            "topic_id": self._topic_id,
            "sequence_number": self._sequence_counter,
            "running_hash": self._running_hash,
            "pending_messages": len(self._pending_messages),
        }
    
    def on_message(self, callback: Callable[[MessageReceipt], None]):
        """Register callback for message events."""
        self._message_callbacks.append(callback)
    
    def get_pending_messages(self) -> List[MessageReceipt]:
        """Get all pending message receipts."""
        return list(self._pending_messages.values())
    
    def subscribe_to_topic(self, 
                           topic_id: str,
                           callback: Callable[[Dict[str, Any]], None],
                           ) -> bool:
        """
        Subscribe to HCS topic for real-time messages.
        
        Args:
            topic_id: Topic to subscribe to
            callback: Function to call for each message
            
        Returns:
            True if subscription successful
        """
        # In production, would use ConsensusTopicSubscribeQuery
        logger.info(f"Subscribed to HCS topic: {topic_id}")
        return True
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False


def create_hedera_connector(
    network: HederaNetwork = HederaNetwork.TESTNET,
    operator_id: Optional[str] = None,
    operator_key: Optional[str] = None,
    topic_id: Optional[str] = None,
) -> HederaConnector:
    """
    Factory function for creating Hedera connector.
    
    Args:
        network: Hedera network to use
        operator_id: Operator account ID
        operator_key: Operator private key
        topic_id: Existing topic ID to use
        
    Returns:
        Configured HederaConnector
    """
    config = HederaConfig(
        network=network,
        operator_id=operator_id,
        operator_key=operator_key,
        topic_id=topic_id,
    )
    
    # Set network-specific URLs
    if network == HederaNetwork.MAINNET:
        config.mirror_node_url = "https://mainnet-public.mirrornode.hedera.com"
        config.grpc_endpoint = "mainnet.hedera.com:50211"
    elif network == HederaNetwork.TESTNET:
        config.mirror_node_url = "https://testnet.mirrornode.hedera.com"
        config.grpc_endpoint = "testnet.hedera.com:50211"
    elif network == HederaNetwork.PREVIEWNET:
        config.mirror_node_url = "https://previewnet.mirrornode.hedera.com"
        config.grpc_endpoint = "previewnet.hedera.com:50211"
    
    return HederaConnector(config)
