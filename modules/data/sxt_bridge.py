"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     SPACE AND TIME (SxT) BRIDGE                              ║
║                      PAC-SYN-P930-SXT-BINDING                                ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  The Bridge Between Local State and the Eternal Witness                      ║
║                                                                              ║
║  "The Past is written in Stone. The Future is ours to build."                ║
╚══════════════════════════════════════════════════════════════════════════════╝

This module implements the connection between ChainBridge's local tenant
shards (P920) and the Space and Time (SxT) decentralized data warehouse.

ARCHITECTURE:
    ┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
    │  Local Shard    │────▶│   AsyncAnchor    │────▶│   SxT Network   │
    │  (Hot Wallet)   │     │  (Task Queue)    │     │  (Cold Witness) │
    └─────────────────┘     └──────────────────┘     └─────────────────┘
                                    │
                                    ▼
                            ┌──────────────────┐
                            │  Proof Receipt   │
                            │  (ZK Verified)   │
                            └──────────────────┘

INVARIANTS:
  INV-DATA-005 (Ledger Mirroring): Every finalized tx MUST have SxT record
  INV-DATA-006 (Proof Finality): SxT Record is ultimate arbiter of history

PAC Reference: PAC-SYN-P930-SXT-BINDING
"""

from __future__ import annotations

import os
import json
import time
import queue
import hashlib
import logging
import secrets
import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import (
    Any, Callable, Dict, List, Optional, 
    Tuple, Union, TYPE_CHECKING
)

# Cryptographic signing
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

# Local imports
from .schemas import (
    TransactionSchema,
    AuditLogSchema,
    ProofReceipt,
    PIIHasher,
    SchemaRegistry,
)

if TYPE_CHECKING:
    from .sharding import TenantShard

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

class AnchorState(Enum):
    """States for an anchor request."""
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    ANCHORED = "anchored"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class SxTConfig:
    """Configuration for SxT Bridge."""
    # API Configuration
    api_endpoint: str = "https://api.spaceandtime.io/v1"
    api_key: str = ""
    biscuit_token: str = ""
    
    # Namespace (your SxT schema namespace)
    namespace: str = "chainbridge"
    
    # Performance settings
    batch_size: int = 100
    flush_interval_ms: int = 1000
    max_retry_attempts: int = 3
    retry_backoff_ms: int = 500
    
    # Queue settings
    queue_max_size: int = 10000
    worker_count: int = 2
    
    # Signing key (Ed25519)
    signing_key_path: Optional[str] = None
    
    # PII protection
    pii_pepper: Optional[bytes] = None
    
    # Timeouts
    connect_timeout_ms: int = 5000
    request_timeout_ms: int = 30000
    
    def __post_init__(self):
        # Load from environment if not provided
        if not self.api_key:
            self.api_key = os.environ.get("SXT_API_KEY", "")
        if not self.biscuit_token:
            self.biscuit_token = os.environ.get("SXT_BISCUIT_TOKEN", "")
        if self.pii_pepper is None:
            pepper_hex = os.environ.get("SXT_PII_PEPPER", "")
            if pepper_hex:
                self.pii_pepper = bytes.fromhex(pepper_hex)
            else:
                # Generate deterministic pepper from API key (not ideal but fallback)
                self.pii_pepper = hashlib.sha256(
                    f"chainbridge:pii:{self.api_key}".encode()
                ).digest()


@dataclass 
class AnchorRequest:
    """Request to anchor a transaction to SxT."""
    request_id: str
    tenant_id: str
    tx_data: Dict[str, Any]
    state: AnchorState = AnchorState.PENDING
    created_at: float = field(default_factory=time.time)
    attempts: int = 0
    last_error: Optional[str] = None
    proof_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "tenant_id": self.tenant_id,
            "tx_data": self.tx_data,
            "state": self.state.value,
            "created_at": self.created_at,
            "attempts": self.attempts,
            "last_error": self.last_error,
            "proof_id": self.proof_id,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SxT API CLIENT (MOCK + REAL)
# ═══════════════════════════════════════════════════════════════════════════════

class SxTClientBase(ABC):
    """Abstract base class for SxT API client."""
    
    @abstractmethod
    async def insert_transaction(
        self, 
        schema: TransactionSchema
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Insert a transaction record into SxT.
        
        Args:
            schema: The transaction schema to insert
            
        Returns:
            (success, proof_id, error_message)
        """
        pass
    
    @abstractmethod
    async def batch_insert(
        self, 
        schemas: List[TransactionSchema]
    ) -> List[Tuple[str, bool, Optional[str]]]:
        """
        Batch insert multiple transactions.
        
        Args:
            schemas: List of transaction schemas
            
        Returns:
            List of (tx_id, success, proof_id) tuples
        """
        pass
    
    @abstractmethod
    async def get_proof(
        self, 
        tx_id: str
    ) -> Optional[ProofReceipt]:
        """Get the ZK-Proof for a transaction."""
        pass
    
    @abstractmethod
    async def verify_record(
        self, 
        tx_id: str, 
        expected_hash: str
    ) -> bool:
        """Verify a record exists with the expected hash."""
        pass


class MockSxTClient(SxTClientBase):
    """
    Mock SxT client for testing and offline operation.
    
    Stores records in memory and generates mock proofs.
    """
    
    def __init__(self, config: SxTConfig):
        self.config = config
        self.records: Dict[str, TransactionSchema] = {}
        self.proofs: Dict[str, ProofReceipt] = {}
        self.insert_latency_ms = 5  # Simulated latency
        self._lock = threading.Lock()
    
    async def insert_transaction(
        self, 
        schema: TransactionSchema
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Mock insert with simulated latency."""
        import asyncio
        
        # Simulate network latency
        await asyncio.sleep(self.insert_latency_ms / 1000.0)
        
        with self._lock:
            # Store the record
            self.records[schema.tx_id] = schema
            
            # Generate mock proof
            proof_id = f"proof_{secrets.token_hex(16)}"
            proof = ProofReceipt(
                proof_id=proof_id,
                source_table="chainbridge_transactions",
                source_id=schema.tx_id,
                proof_type="ZK_SQL_PROOF",
                prover_version="mock_1.0.0",
                proof_data=hashlib.sha256(
                    json.dumps(schema.to_dict()).encode()
                ).hexdigest(),
                verified_at=int(time.time() * 1000),
                verification_status="VERIFIED",
                sxt_commitment=secrets.token_hex(32),
                sxt_block_hash=secrets.token_hex(32),
            )
            self.proofs[schema.tx_id] = proof
            
            logger.debug(f"[MockSxT] Inserted tx={schema.tx_id}, proof={proof_id}")
            return (True, proof_id, None)
    
    async def batch_insert(
        self, 
        schemas: List[TransactionSchema]
    ) -> List[Tuple[str, bool, Optional[str]]]:
        """Mock batch insert."""
        results = []
        for schema in schemas:
            success, proof_id, error = await self.insert_transaction(schema)
            results.append((schema.tx_id, success, proof_id))
        return results
    
    async def get_proof(self, tx_id: str) -> Optional[ProofReceipt]:
        """Get mock proof."""
        return self.proofs.get(tx_id)
    
    async def verify_record(self, tx_id: str, expected_hash: str) -> bool:
        """Verify mock record."""
        with self._lock:
            if tx_id not in self.records:
                return False
            actual_hash = self.records[tx_id].compute_content_hash()
            return actual_hash == expected_hash


class LiveSxTClient(SxTClientBase):
    """
    Production SxT client using the Space and Time API.
    
    Requires valid API credentials and network access.
    """
    
    def __init__(self, config: SxTConfig):
        self.config = config
        self._session = None
        
    async def _get_session(self):
        """Get or create aiohttp session."""
        if self._session is None:
            try:
                import aiohttp
                timeout = aiohttp.ClientTimeout(
                    connect=self.config.connect_timeout_ms / 1000.0,
                    total=self.config.request_timeout_ms / 1000.0,
                )
                self._session = aiohttp.ClientSession(
                    timeout=timeout,
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "X-Biscuit-Token": self.config.biscuit_token,
                        "Content-Type": "application/json",
                    }
                )
            except ImportError:
                raise RuntimeError("aiohttp required for LiveSxTClient")
        return self._session
    
    async def insert_transaction(
        self, 
        schema: TransactionSchema
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Insert transaction via SxT API."""
        session = await self._get_session()
        
        url = f"{self.config.api_endpoint}/sql/dml"
        
        # Build INSERT statement
        data = schema.to_dict()
        columns = ", ".join(data.keys())
        placeholders = ", ".join([f":{k}" for k in data.keys()])
        
        sql = f"""
            INSERT INTO {self.config.namespace}.chainbridge_transactions 
            ({columns}) VALUES ({placeholders})
        """
        
        payload = {
            "resourceId": f"{self.config.namespace}.chainbridge_transactions",
            "sqlText": sql,
            "parameters": data,
        }
        
        try:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    proof_id = result.get("proofId")
                    return (True, proof_id, None)
                else:
                    error = await resp.text()
                    logger.error(f"SxT insert failed: {resp.status} - {error}")
                    return (False, None, error)
        except Exception as e:
            logger.exception("SxT insert exception")
            return (False, None, str(e))
    
    async def batch_insert(
        self, 
        schemas: List[TransactionSchema]
    ) -> List[Tuple[str, bool, Optional[str]]]:
        """Batch insert via SxT API."""
        # SxT supports batch operations via SQL
        results = []
        for schema in schemas:
            success, proof_id, error = await self.insert_transaction(schema)
            results.append((schema.tx_id, success, proof_id))
        return results
    
    async def get_proof(self, tx_id: str) -> Optional[ProofReceipt]:
        """Get proof from SxT."""
        session = await self._get_session()
        
        url = f"{self.config.api_endpoint}/proofs/{tx_id}"
        
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return ProofReceipt(
                        proof_id=data["proofId"],
                        source_table="chainbridge_transactions",
                        source_id=tx_id,
                        proof_type=data.get("proofType", "ZK_SQL_PROOF"),
                        proof_data=data.get("proofData", ""),
                        verification_status=data.get("status", "PENDING"),
                        sxt_commitment=data.get("commitment"),
                        sxt_block_hash=data.get("blockHash"),
                    )
                return None
        except Exception as e:
            logger.exception("Failed to get proof")
            return None
    
    async def verify_record(self, tx_id: str, expected_hash: str) -> bool:
        """Verify record via SxT API."""
        session = await self._get_session()
        
        url = f"{self.config.api_endpoint}/sql/query"
        sql = f"""
            SELECT tx_hash FROM {self.config.namespace}.chainbridge_transactions
            WHERE tx_id = :tx_id
        """
        
        try:
            async with session.post(url, json={"sqlText": sql, "parameters": {"tx_id": tx_id}}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("rows"):
                        return data["rows"][0]["tx_hash"] == expected_hash
                return False
        except Exception:
            return False
    
    async def close(self):
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None


# ═══════════════════════════════════════════════════════════════════════════════
# ASYNC ANCHOR WORKER (PRODUCER/CONSUMER)
# ═══════════════════════════════════════════════════════════════════════════════

class AsyncAnchor:
    """
    Asynchronous anchoring worker using producer/consumer pattern.
    
    Transactions are queued for anchoring without blocking the main
    settlement thread. Workers process the queue in batches.
    
    GOAL: <50ms overhead on main thread.
    """
    
    def __init__(
        self, 
        config: SxTConfig,
        client: Optional[SxTClientBase] = None,
        on_anchor_complete: Optional[Callable[[AnchorRequest], None]] = None,
    ):
        self.config = config
        self.client = client or MockSxTClient(config)
        self.on_anchor_complete = on_anchor_complete
        
        # Task queue
        self._queue: queue.Queue[AnchorRequest] = queue.Queue(
            maxsize=config.queue_max_size
        )
        
        # Tracking
        self._pending: Dict[str, AnchorRequest] = {}
        self._completed: Dict[str, AnchorRequest] = {}
        self._failed: Dict[str, AnchorRequest] = {}
        
        # Worker threads
        self._workers: List[threading.Thread] = []
        self._running = False
        self._lock = threading.Lock()
        
        # Metrics
        self.metrics = {
            "queued": 0,
            "anchored": 0,
            "failed": 0,
            "total_latency_ms": 0.0,
        }
        
        # PII Hasher
        if config.pii_pepper:
            self._pii_hasher = PIIHasher(config.pii_pepper)
        else:
            self._pii_hasher = None
    
    def start(self):
        """Start the worker threads."""
        if self._running:
            return
        
        self._running = True
        
        for i in range(self.config.worker_count):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"SxTAnchor-{i}",
                daemon=True,
            )
            worker.start()
            self._workers.append(worker)
        
        logger.info(f"AsyncAnchor started with {self.config.worker_count} workers")
    
    def stop(self, timeout: float = 5.0):
        """Stop all worker threads."""
        self._running = False
        
        # Signal workers to stop
        for _ in self._workers:
            try:
                self._queue.put_nowait(None)  # Poison pill
            except queue.Full:
                pass
        
        # Wait for workers
        for worker in self._workers:
            worker.join(timeout=timeout)
        
        self._workers.clear()
        logger.info("AsyncAnchor stopped")
    
    def enqueue(
        self, 
        tenant_id: str, 
        tx_data: Dict[str, Any],
    ) -> str:
        """
        Enqueue a transaction for anchoring.
        
        This is the main entry point, designed to be <50ms.
        
        Args:
            tenant_id: The tenant identifier
            tx_data: Raw transaction data
            
        Returns:
            request_id for tracking
        """
        start = time.perf_counter()
        
        request_id = f"anchor_{uuid.uuid4().hex}"
        
        request = AnchorRequest(
            request_id=request_id,
            tenant_id=tenant_id,
            tx_data=tx_data,
            state=AnchorState.PENDING,
        )
        
        try:
            self._queue.put_nowait(request)
            request.state = AnchorState.QUEUED
            
            with self._lock:
                self._pending[request_id] = request
                self.metrics["queued"] += 1
            
        except queue.Full:
            logger.error("Anchor queue full! Transaction may not be anchored.")
            request.state = AnchorState.FAILED
            request.last_error = "Queue full"
            with self._lock:
                self._failed[request_id] = request
                self.metrics["failed"] += 1
        
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.debug(f"Enqueue completed in {elapsed_ms:.2f}ms")
        
        return request_id
    
    def get_status(self, request_id: str) -> Optional[AnchorRequest]:
        """Get the status of an anchor request."""
        with self._lock:
            if request_id in self._pending:
                return self._pending[request_id]
            if request_id in self._completed:
                return self._completed[request_id]
            if request_id in self._failed:
                return self._failed[request_id]
        return None
    
    def _worker_loop(self):
        """Main worker loop (runs in thread)."""
        import asyncio
        
        # Each worker gets its own event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            while self._running:
                try:
                    # Get from queue with timeout
                    request = self._queue.get(timeout=0.1)
                    
                    if request is None:  # Poison pill
                        break
                    
                    # Process the request
                    loop.run_until_complete(self._process_request(request))
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.exception(f"Worker error: {e}")
        finally:
            loop.close()
    
    async def _process_request(self, request: AnchorRequest):
        """Process a single anchor request."""
        start = time.perf_counter()
        request.state = AnchorState.SENDING
        request.attempts += 1
        
        try:
            # Build the schema
            schema = self._build_schema(request)
            
            # Send to SxT
            success, proof_id, error = await self.client.insert_transaction(schema)
            
            if success:
                request.state = AnchorState.ANCHORED
                request.proof_id = proof_id
                
                with self._lock:
                    self._pending.pop(request.request_id, None)
                    self._completed[request.request_id] = request
                    self.metrics["anchored"] += 1
                
                logger.info(f"Anchored tx={schema.tx_id}, proof={proof_id}")
                
            else:
                # Retry logic
                if request.attempts < self.config.max_retry_attempts:
                    request.state = AnchorState.RETRYING
                    request.last_error = error
                    
                    # Back off and re-queue
                    await asyncio.sleep(
                        self.config.retry_backoff_ms / 1000.0 * request.attempts
                    )
                    self._queue.put_nowait(request)
                    
                else:
                    # Max retries exceeded
                    request.state = AnchorState.FAILED
                    request.last_error = error
                    
                    with self._lock:
                        self._pending.pop(request.request_id, None)
                        self._failed[request.request_id] = request
                        self.metrics["failed"] += 1
                    
                    logger.error(f"Anchor failed after {request.attempts} attempts: {error}")
            
        except Exception as e:
            logger.exception(f"Anchor processing error: {e}")
            request.state = AnchorState.FAILED
            request.last_error = str(e)
            
            with self._lock:
                self._pending.pop(request.request_id, None)
                self._failed[request.request_id] = request
                self.metrics["failed"] += 1
        
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            with self._lock:
                self.metrics["total_latency_ms"] += elapsed_ms
            
            # Callback if provided
            if self.on_anchor_complete:
                try:
                    self.on_anchor_complete(request)
                except Exception:
                    logger.exception("Anchor callback error")
    
    def _build_schema(self, request: AnchorRequest) -> TransactionSchema:
        """Build TransactionSchema from raw tx_data with PII hashing."""
        tx = request.tx_data
        tenant_id = request.tenant_id
        
        # Hash PII fields
        if self._pii_hasher:
            tenant_hash = self._pii_hasher.hash_tenant(tenant_id)
            sender_hash = self._pii_hasher.hash_pii(
                tx.get("sender", ""), tenant_id
            )
            receiver_hash = self._pii_hasher.hash_pii(
                tx.get("receiver", ""), tenant_id
            )
        else:
            # Fallback to simple hashing
            tenant_hash = hashlib.sha256(tenant_id.encode()).hexdigest()
            sender_hash = hashlib.sha256(
                tx.get("sender", "").encode()
            ).hexdigest()
            receiver_hash = hashlib.sha256(
                tx.get("receiver", "").encode()
            ).hexdigest()
        
        # Current time
        now_ms = int(time.time() * 1000)
        
        return TransactionSchema(
            tx_id=tx.get("tx_id", uuid.uuid4().hex),
            tenant_hash=tenant_hash,
            tx_type=tx.get("tx_type", "TRANSFER"),
            amount_cents=tx.get("amount_cents", 0),
            currency=tx.get("currency", "USD"),
            sender_hash=sender_hash,
            receiver_hash=receiver_hash,
            created_at=tx.get("created_at", now_ms),
            finalized_at=tx.get("finalized_at", now_ms),
            anchor_time=now_ms,
            tx_hash=tx.get("tx_hash", hashlib.sha256(
                json.dumps(tx, sort_keys=True).encode()
            ).hexdigest()),
            merkle_root=tx.get("merkle_root"),
            state_root_before=tx.get("state_root_before"),
            state_root_after=tx.get("state_root_after", ""),
            node_id=tx.get("node_id", "local"),
            node_signature=tx.get("node_signature", "unsigned"),
            raft_term=tx.get("raft_term"),
            raft_index=tx.get("raft_index"),
            block_height=tx.get("block_height"),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SxT BRIDGE (MAIN INTERFACE)
# ═══════════════════════════════════════════════════════════════════════════════

class SxTBridge:
    """
    The Bridge between Local State and Space and Time.
    
    Primary interface for anchoring transactions to the decentralized
    data warehouse. Uses async worker for non-blocking operation.
    
    Usage:
        bridge = SxTBridge(config)
        bridge.start()
        
        # Anchor a transaction (non-blocking, <50ms)
        proof_id = bridge.anchor_transaction(tenant_id, tx_data)
        
        # Check status later
        status = bridge.get_anchor_status(proof_id)
    """
    
    def __init__(
        self, 
        config: Optional[SxTConfig] = None,
        use_mock: bool = True,
        signing_key: Optional[ed25519.Ed25519PrivateKey] = None,
    ):
        """
        Initialize the SxT Bridge.
        
        Args:
            config: SxT configuration (uses defaults if None)
            use_mock: Use mock client for testing
            signing_key: Ed25519 key for signing payloads
        """
        self.config = config or SxTConfig()
        self._signing_key = signing_key
        
        # Create client
        if use_mock:
            self._client = MockSxTClient(self.config)
        else:
            self._client = LiveSxTClient(self.config)
        
        # Create async anchor
        self._anchor = AsyncAnchor(
            config=self.config,
            client=self._client,
            on_anchor_complete=self._on_anchor_complete,
        )
        
        # Completion callbacks
        self._callbacks: Dict[str, Callable[[AnchorRequest], None]] = {}
        self._lock = threading.Lock()
        
        # State
        self._started = False
        
        logger.info(f"SxTBridge initialized (mock={use_mock})")
    
    def start(self):
        """Start the bridge (begins processing queue)."""
        if self._started:
            return
        self._anchor.start()
        self._started = True
        logger.info("SxTBridge started")
    
    def stop(self, timeout: float = 5.0):
        """Stop the bridge gracefully."""
        if not self._started:
            return
        self._anchor.stop(timeout)
        self._started = False
        logger.info("SxTBridge stopped")
    
    def anchor_transaction(
        self,
        tenant_id: str,
        tx_data: Dict[str, Any],
        callback: Optional[Callable[[AnchorRequest], None]] = None,
    ) -> str:
        """
        Anchor a transaction to SxT.
        
        This is a non-blocking call that queues the transaction for
        asynchronous anchoring. Target: <50ms overhead.
        
        Args:
            tenant_id: The tenant identifier
            tx_data: Transaction data dict containing:
                - tx_id: Unique transaction ID
                - tx_type: Transaction type (TRANSFER, PAYMENT, etc.)
                - amount_cents: Amount in cents
                - currency: Currency code
                - sender: Sender identifier (will be hashed)
                - receiver: Receiver identifier (will be hashed)
                - state_root_after: Post-transaction state root
                - ...other fields
            callback: Optional callback when anchoring completes
            
        Returns:
            request_id for tracking
        """
        if not self._started:
            raise RuntimeError("SxTBridge not started. Call start() first.")
        
        # Sign the transaction if we have a key
        if self._signing_key and "node_signature" not in tx_data:
            tx_data = self._sign_transaction(tx_data)
        
        # Enqueue for anchoring
        request_id = self._anchor.enqueue(tenant_id, tx_data)
        
        # Register callback if provided
        if callback:
            with self._lock:
                self._callbacks[request_id] = callback
        
        return request_id
    
    def get_anchor_status(self, request_id: str) -> Optional[AnchorRequest]:
        """Get the status of an anchor request."""
        return self._anchor.get_status(request_id)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get anchoring metrics."""
        return {
            **self._anchor.metrics,
            "avg_latency_ms": (
                self._anchor.metrics["total_latency_ms"] / 
                max(1, self._anchor.metrics["anchored"])
            ),
        }
    
    async def verify_integrity(
        self, 
        tx_id: str, 
        local_hash: str
    ) -> bool:
        """
        Verify local state matches SxT record.
        
        This is the FREEZE check - if this returns False, the system
        should halt until manual intervention.
        
        Args:
            tx_id: Transaction ID to verify
            local_hash: Hash of local record
            
        Returns:
            True if hashes match, False otherwise (FREEZE!)
        """
        return await self._client.verify_record(tx_id, local_hash)
    
    async def get_proof(self, tx_id: str) -> Optional[ProofReceipt]:
        """Get the ZK-Proof for a transaction."""
        return await self._client.get_proof(tx_id)
    
    def _sign_transaction(self, tx_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sign transaction data with Ed25519 key."""
        if not CRYPTO_AVAILABLE or not self._signing_key:
            return tx_data
        
        # Create canonical representation
        canonical = json.dumps(tx_data, sort_keys=True, separators=(',', ':'))
        
        # Sign
        signature = self._signing_key.sign(canonical.encode())
        
        # Add signature
        tx_data = tx_data.copy()
        tx_data["node_signature"] = signature.hex()
        tx_data["node_id"] = hashlib.sha256(
            self._signing_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
        ).hexdigest()[:16]
        
        return tx_data
    
    def _on_anchor_complete(self, request: AnchorRequest):
        """Internal callback when anchor completes."""
        with self._lock:
            callback = self._callbacks.pop(request.request_id, None)
        
        if callback:
            try:
                callback(request)
            except Exception:
                logger.exception("Anchor completion callback error")


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

def create_sxt_bridge(
    use_mock: bool = True,
    **config_kwargs
) -> SxTBridge:
    """
    Factory function to create a configured SxTBridge.
    
    Args:
        use_mock: Use mock client (True for testing)
        **config_kwargs: Passed to SxTConfig
        
    Returns:
        Configured SxTBridge instance (not started)
    """
    config = SxTConfig(**config_kwargs)
    return SxTBridge(config=config, use_mock=use_mock)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Main classes
    "SxTBridge",
    "SxTConfig",
    "AsyncAnchor",
    "AnchorRequest",
    "AnchorState",
    # Clients
    "SxTClientBase",
    "MockSxTClient",
    "LiveSxTClient",
    # Factory
    "create_sxt_bridge",
]
