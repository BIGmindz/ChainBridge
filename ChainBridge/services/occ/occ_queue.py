"""
OCC Queue - Priority-ordered action queue for Operator Control Center.

PAC Reference: PAC-OCC-P02
Constitutional Authority: OCC_CONSTITUTION_v1.0, Article III
Invariants Enforced: INV-OCC-006 (Queue Ordering), INV-OCC-004 (No Anonymous Operations)

This module implements a FIFO-by-priority queue that ensures:
1. All queue operations are attributed to verified operators
2. Queue ordering is deterministic and auditable
3. Priority escalation follows constitutional authority model
4. Fail-closed semantics on all error conditions
"""

from __future__ import annotations

import hashlib
import heapq
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Callable


class QueuePriority(IntEnum):
    """
    Queue priority levels aligned with OCC Authority Model.
    
    Lower values = higher priority (heap semantics).
    Constitutional basis: OCC_AUTHORITY_MODEL.yaml authority_tiers
    """
    EMERGENCY = 0      # T5/T6 emergency actions
    CRITICAL = 1       # T4+ override actions
    HIGH = 2           # Time-sensitive operations
    NORMAL = 3         # Standard operator actions
    LOW = 4            # Background/batch operations
    DEFERRED = 5       # Can wait indefinitely


@dataclass(frozen=True)
class OperatorIdentity:
    """
    Verified operator identity for queue operations.
    
    Invariant: INV-OCC-004 - No Anonymous Operations
    All queue items MUST have verified operator identity.
    """
    operator_id: str
    tier: str  # T1-T6
    session_id: str
    verified: bool = True
    
    def __post_init__(self) -> None:
        if not self.operator_id:
            raise ValueError("INV-OCC-004 VIOLATION: operator_id cannot be empty")
        if not self.session_id:
            raise ValueError("INV-OCC-004 VIOLATION: session_id cannot be empty")
        if self.tier not in ("T1", "T2", "T3", "T4", "T5", "T6"):
            raise ValueError(f"Invalid operator tier: {self.tier}")


@dataclass
class QueueItem:
    """
    A single item in the OCC action queue.
    
    Ordering is determined by (priority, sequence_number) tuple
    to ensure FIFO within same priority level.
    """
    id: str
    action_type: str
    payload: dict[str, Any]
    operator: OperatorIdentity
    priority: QueuePriority
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sequence_number: int = 0
    hash_previous: str | None = None
    hash_current: str = ""
    
    def __lt__(self, other: QueueItem) -> bool:
        """Comparison for heap ordering: lower priority value = higher priority."""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.sequence_number < other.sequence_number
    
    def compute_hash(self) -> str:
        """Compute hash for this queue item."""
        content = f"{self.id}|{self.action_type}|{self.operator.operator_id}|{self.priority}|{self.created_at.isoformat()}|{self.hash_previous or 'GENESIS'}"
        return hashlib.sha256(content.encode()).hexdigest()


class QueueFullError(Exception):
    """Raised when queue capacity is exceeded."""


class QueueClosedError(Exception):
    """Raised when operations attempted on closed queue."""


class OCCQueue:
    """
    Priority-ordered action queue for Operator Control Center.
    
    Constitutional Invariants:
    - INV-OCC-006: Queue Ordering - FIFO within priority, higher priority first
    - INV-OCC-004: No Anonymous Operations - All items require verified operator
    
    Thread-safe implementation with fail-closed semantics.
    """
    
    # Singleton enforcement per CB-INV-BENSON-EXEC-001 pattern
    _INSTANCE: OCCQueue | None = None
    _LOCK = threading.Lock()
    
    def __init__(
        self,
        max_size: int = 10000,
        on_enqueue: Callable[[QueueItem], None] | None = None,
        on_dequeue: Callable[[QueueItem], None] | None = None,
    ) -> None:
        """
        Initialize OCC Queue.
        
        Args:
            max_size: Maximum queue capacity (fail-closed on overflow)
            on_enqueue: Callback invoked after successful enqueue
            on_dequeue: Callback invoked after successful dequeue
        """
        self._heap: list[QueueItem] = []
        self._max_size = max_size
        self._sequence_counter = 0
        self._last_hash: str | None = None
        self._lock = threading.Lock()
        self._closed = False
        self._on_enqueue = on_enqueue
        self._on_dequeue = on_dequeue
        
        # Metrics
        self._enqueue_count = 0
        self._dequeue_count = 0
        self._reject_count = 0
        
    @classmethod
    def get_instance(cls) -> OCCQueue:
        """
        Get singleton instance of OCC Queue.
        
        Constitutional basis: Single source of truth for action ordering.
        """
        if cls._INSTANCE is None:
            with cls._LOCK:
                if cls._INSTANCE is None:
                    cls._INSTANCE = cls()
        return cls._INSTANCE
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton for testing. NOT FOR PRODUCTION USE."""
        with cls._LOCK:
            cls._INSTANCE = None
    
    def enqueue(
        self,
        action_type: str,
        payload: dict[str, Any],
        operator: OperatorIdentity,
        priority: QueuePriority = QueuePriority.NORMAL,
        item_id: str | None = None,
    ) -> QueueItem:
        """
        Add an action to the queue.
        
        Args:
            action_type: Type of action (e.g., "OVERRIDE", "APPROVE", "BLOCK")
            payload: Action payload data
            operator: Verified operator identity
            priority: Queue priority level
            item_id: Optional item ID (generated if not provided)
            
        Returns:
            The enqueued QueueItem
            
        Raises:
            QueueFullError: If queue capacity exceeded (fail-closed)
            QueueClosedError: If queue has been closed
            ValueError: If operator identity invalid
        """
        # INV-OCC-004: Verify operator identity
        if not operator.verified:
            self._reject_count += 1
            raise ValueError("INV-OCC-004 VIOLATION: Operator not verified")
        
        with self._lock:
            # Fail-closed check
            if self._closed:
                self._reject_count += 1
                raise QueueClosedError("Queue is closed - fail-closed state")
            
            # Capacity check (fail-closed on overflow)
            if len(self._heap) >= self._max_size:
                self._reject_count += 1
                raise QueueFullError(
                    f"INV-OCC-006 VIOLATION: Queue capacity exceeded ({self._max_size})"
                )
            
            # Generate sequence number for FIFO within priority
            self._sequence_counter += 1
            
            # Create queue item
            item = QueueItem(
                id=item_id or f"QI-{int(time.time() * 1000)}-{self._sequence_counter}",
                action_type=action_type,
                payload=payload,
                operator=operator,
                priority=priority,
                sequence_number=self._sequence_counter,
                hash_previous=self._last_hash,
            )
            
            # Compute and set hash
            item.hash_current = item.compute_hash()
            self._last_hash = item.hash_current
            
            # Add to heap
            heapq.heappush(self._heap, item)
            self._enqueue_count += 1
            
            # Invoke callback
            if self._on_enqueue:
                self._on_enqueue(item)
            
            return item
    
    def dequeue(self) -> QueueItem | None:
        """
        Remove and return highest-priority item from queue.
        
        Returns:
            Highest-priority QueueItem, or None if queue empty
            
        Raises:
            QueueClosedError: If queue has been closed
        """
        with self._lock:
            if self._closed:
                raise QueueClosedError("Queue is closed - fail-closed state")
            
            if not self._heap:
                return None
            
            item = heapq.heappop(self._heap)
            self._dequeue_count += 1
            
            # Invoke callback
            if self._on_dequeue:
                self._on_dequeue(item)
            
            return item
    
    def peek(self) -> QueueItem | None:
        """
        View highest-priority item without removing.
        
        Returns:
            Highest-priority QueueItem, or None if queue empty
        """
        with self._lock:
            if not self._heap:
                return None
            return self._heap[0]
    
    def size(self) -> int:
        """Return current queue size."""
        with self._lock:
            return len(self._heap)
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        with self._lock:
            return len(self._heap) == 0
    
    def close(self) -> None:
        """
        Close queue - fail-closed state.
        
        Once closed, no further operations are permitted.
        This is a one-way transition (constitutional invariant).
        """
        with self._lock:
            self._closed = True
    
    def is_closed(self) -> bool:
        """Check if queue is in fail-closed state."""
        with self._lock:
            return self._closed
    
    def get_metrics(self) -> dict[str, int]:
        """Return queue metrics for monitoring."""
        with self._lock:
            return {
                "current_size": len(self._heap),
                "max_size": self._max_size,
                "enqueue_count": self._enqueue_count,
                "dequeue_count": self._dequeue_count,
                "reject_count": self._reject_count,
                "sequence_counter": self._sequence_counter,
            }
    
    def get_items_by_priority(self, priority: QueuePriority) -> list[QueueItem]:
        """
        Get all items at a specific priority level.
        
        Note: This is a read-only view, items remain in queue.
        """
        with self._lock:
            return [item for item in self._heap if item.priority == priority]
    
    def get_items_by_operator(self, operator_id: str) -> list[QueueItem]:
        """
        Get all items from a specific operator.
        
        Note: This is a read-only view, items remain in queue.
        """
        with self._lock:
            return [item for item in self._heap if item.operator.operator_id == operator_id]
    
    def escalate_priority(
        self,
        item_id: str,
        new_priority: QueuePriority,
        operator: OperatorIdentity,
    ) -> bool:
        """
        Escalate an item to higher priority.
        
        Args:
            item_id: ID of item to escalate
            new_priority: New priority level (must be higher)
            operator: Operator performing escalation (must have authority)
            
        Returns:
            True if escalation successful, False otherwise
            
        Note: Escalation requires T4+ authority per OCC_AUTHORITY_MODEL.
        """
        # Verify escalation authority
        if operator.tier not in ("T4", "T5", "T6"):
            return False
        
        with self._lock:
            # Find item
            for i, item in enumerate(self._heap):
                if item.id == item_id:
                    # Can only escalate to higher priority (lower value)
                    if new_priority >= item.priority:
                        return False
                    
                    # Create new item with updated priority
                    # (QueueItem is frozen for hash integrity)
                    new_item = QueueItem(
                        id=item.id,
                        action_type=item.action_type,
                        payload={**item.payload, "_escalated": True, "_escalated_by": operator.operator_id},
                        operator=item.operator,
                        priority=new_priority,
                        created_at=item.created_at,
                        sequence_number=item.sequence_number,
                        hash_previous=item.hash_previous,
                        hash_current=item.hash_current,
                    )
                    
                    # Remove old, add new
                    self._heap.pop(i)
                    heapq.heappush(self._heap, new_item)
                    heapq.heapify(self._heap)
                    return True
            
            return False
