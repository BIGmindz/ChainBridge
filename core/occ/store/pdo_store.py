"""
PDO Store — Append-Only Immutable Persistence

PAC-CODY-PDO-HARDEN-01: PDO Write-Path Integrity & Immutability

This store enforces:
- APPEND-ONLY: Only INSERT operations permitted
- NO UPDATES: Any update attempt raises PDOImmutabilityError
- NO DELETES: Any delete attempt raises PDOImmutabilityError
- HASH SEALING: Hash computed and frozen at write time
- TAMPER DETECTION: Hash verification on read

CRITICAL GUARANTEES:
1. Once a PDO is written, it CANNOT be modified
2. Once a PDO is written, it CANNOT be deleted
3. Hash is computed ONCE at write time and never recomputed
4. Any tampering attempt fails loudly with explicit errors

Author: CODY (GID-01) - Backend
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

from core.occ.schemas.pdo import PDOCreate, PDOImmutabilityError, PDOOutcome, PDORecord, PDOSourceSystem, PDOTamperDetectedError
from core.occ.telemetry import get_invariant_telemetry

logger = logging.getLogger(__name__)

# Default storage path
DEFAULT_PDO_STORE_PATH = "./data/pdo_records.json"


class PDOStore:
    """
    Append-only, immutable PDO store.

    IMMUTABILITY CONTRACT:
    - create(): INSERT new PDO → allowed
    - get(): READ PDO → allowed (with tamper check)
    - list(): READ multiple PDOs → allowed
    - verify(): CHECK integrity → allowed
    - update(): BLOCKED → raises PDOImmutabilityError
    - delete(): BLOCKED → raises PDOImmutabilityError

    This store provides audit-grade persistence with:
    - Thread-safe operations
    - Atomic JSON persistence
    - Hash verification on read
    - Explicit error handling for violations
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the PDO store.

        Args:
            storage_path: Path to JSON persistence file.
        """
        self._lock = threading.Lock()
        self._records: Dict[UUID, PDORecord] = {}
        self._sequence_counter: int = 0

        # Indexes for efficient queries
        self._by_source_system: Dict[str, List[UUID]] = {}
        self._by_outcome: Dict[str, List[UUID]] = {}
        self._by_correlation: Dict[str, List[UUID]] = {}
        self._by_timestamp: List[UUID] = []  # ordered by recorded_at

        # Resolve storage path
        self._storage_path = Path(storage_path or os.environ.get("CHAINBRIDGE_PDO_STORE_PATH", DEFAULT_PDO_STORE_PATH))

        # Load existing data
        self._load()

    def _load(self) -> None:
        """Load PDOs from JSON file if it exists."""
        if not self._storage_path.exists():
            logger.info(f"PDO store file not found at {self._storage_path}; starting fresh.")
            return

        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._sequence_counter = data.get("sequence_counter", 0)

            for item in data.get("records", []):
                record = PDORecord.model_validate(item)

                # CRITICAL: Verify hash integrity on load
                if not record.verify_hash():
                    logger.error(
                        f"TAMPER DETECTED on load: PDO {record.pdo_id} hash mismatch. "
                        f"Expected: {record.hash}, Computed: {record.compute_hash()}"
                    )
                    raise PDOTamperDetectedError(
                        f"PDO {record.pdo_id} failed integrity check on load",
                        pdo_id=record.pdo_id,
                        expected_hash=record.hash,
                        actual_hash=record.compute_hash(),
                    )

                self._records[record.pdo_id] = record
                self._index_record(record)

            logger.info(f"Loaded {len(self._records)} PDOs from {self._storage_path}")
        except PDOTamperDetectedError:
            raise
        except Exception as e:
            logger.error(f"Failed to load PDO store: {e}")

    def _persist(self) -> None:
        """
        Persist PDOs to JSON file atomically.

        Uses atomic write pattern:
        1. Write to temp file
        2. Rename to target (atomic on POSIX)
        """
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "sequence_counter": self._sequence_counter,
            "schema_version": "1.0",
            "immutability_enforced": True,  # Explicit marker
            "records": [r.model_dump(mode="json") for r in self._records.values()],
        }

        fd, tmp_path = tempfile.mkstemp(
            suffix=".json",
            prefix="pdo_records_",
            dir=self._storage_path.parent,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            os.replace(tmp_path, self._storage_path)
            logger.debug(f"Persisted {len(self._records)} PDOs")
        except Exception as e:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            logger.error(f"Failed to persist PDOs: {e}")
            raise

    def _index_record(self, record: PDORecord) -> None:
        """Add record to indexes (must be called within lock)."""
        # Index by source system
        source_key = record.source_system.value
        if source_key not in self._by_source_system:
            self._by_source_system[source_key] = []
        self._by_source_system[source_key].append(record.pdo_id)

        # Index by outcome
        outcome_key = record.outcome.value
        if outcome_key not in self._by_outcome:
            self._by_outcome[outcome_key] = []
        self._by_outcome[outcome_key].append(record.pdo_id)

        # Index by correlation ID
        if record.correlation_id:
            if record.correlation_id not in self._by_correlation:
                self._by_correlation[record.correlation_id] = []
            self._by_correlation[record.correlation_id].append(record.pdo_id)

        # Index by timestamp (maintain sorted order)
        self._by_timestamp.append(record.pdo_id)
        self._by_timestamp.sort(key=lambda pid: self._records[pid].recorded_at)

    # =========================================================================
    # CREATE (APPEND-ONLY) — THE ONLY WRITE OPERATION PERMITTED
    # =========================================================================

    def create(self, pdo_create: PDOCreate) -> PDORecord:
        """
        Create a new immutable PDO record.

        This is the ONLY way to add data to the store.

        Process:
        1. Generate pdo_id
        2. Set recorded_at to current UTC time
        3. Compute deterministic hash
        4. Create immutable PDORecord
        5. Persist atomically

        Args:
            pdo_create: PDO creation schema

        Returns:
            The created PDORecord (immutable)

        Note:
            The returned PDORecord is frozen and cannot be modified.
        """
        with self._lock:
            self._sequence_counter += 1

            # Generate ID and timestamp at write time
            pdo_id = UUID(int=self._sequence_counter + 0x10000000000000000000000000000000)
            recorded_at = datetime.now(timezone.utc)

            # Create record WITHOUT hash first (to compute it)
            temp_record = PDORecord(
                pdo_id=pdo_id,
                input_refs=list(pdo_create.input_refs),
                decision_ref=pdo_create.decision_ref,
                outcome_ref=pdo_create.outcome_ref,
                outcome=pdo_create.outcome,
                source_system=pdo_create.source_system,
                actor=pdo_create.actor,
                actor_type=pdo_create.actor_type,
                recorded_at=recorded_at,
                previous_pdo_id=pdo_create.previous_pdo_id,
                correlation_id=pdo_create.correlation_id,
                metadata=dict(pdo_create.metadata),
                tags=list(pdo_create.tags),
                hash="",  # Will be computed
                hash_algorithm="sha256",
            )

            # Compute hash seal
            computed_hash = temp_record.compute_hash()

            # Create final immutable record WITH hash
            record = PDORecord(
                pdo_id=pdo_id,
                input_refs=list(pdo_create.input_refs),
                decision_ref=pdo_create.decision_ref,
                outcome_ref=pdo_create.outcome_ref,
                outcome=pdo_create.outcome,
                source_system=pdo_create.source_system,
                actor=pdo_create.actor,
                actor_type=pdo_create.actor_type,
                recorded_at=recorded_at,
                previous_pdo_id=pdo_create.previous_pdo_id,
                correlation_id=pdo_create.correlation_id,
                metadata=dict(pdo_create.metadata),
                tags=list(pdo_create.tags),
                hash=computed_hash,
                hash_algorithm="sha256",
            )

            # Store and index
            self._records[record.pdo_id] = record
            self._index_record(record)
            self._persist()

        logger.info(
            f"Created PDO: id={record.pdo_id}, "
            f"outcome={record.outcome.value}, "
            f"source={record.source_system.value}, "
            f"hash={record.hash[:16]}..."
        )
        return record

    # =========================================================================
    # READ OPERATIONS (ALLOWED)
    # =========================================================================

    def get(self, pdo_id: UUID, verify_integrity: bool = True) -> Optional[PDORecord]:
        """
        Get a PDO by ID.

        Args:
            pdo_id: The PDO identifier
            verify_integrity: If True, verify hash on read (default: True)

        Returns:
            The PDORecord if found, None otherwise

        Raises:
            PDOTamperDetectedError: If verify_integrity=True and hash mismatch
        """
        with self._lock:
            record = self._records.get(pdo_id)

            if record is None:
                return None

            if verify_integrity and not record.verify_hash():
                logger.error(f"TAMPER DETECTED: PDO {pdo_id} hash mismatch")
                # Emit telemetry for tamper detection
                get_invariant_telemetry().log_pdo_tamper_detected(
                    pdo_id=pdo_id,
                    expected_hash=record.hash,
                    actual_hash=record.compute_hash(),
                )
                raise PDOTamperDetectedError(
                    f"PDO {pdo_id} failed integrity check",
                    pdo_id=pdo_id,
                    expected_hash=record.hash,
                    actual_hash=record.compute_hash(),
                )

            return record

    def list(
        self,
        source_system: Optional[PDOSourceSystem] = None,
        outcome: Optional[PDOOutcome] = None,
        correlation_id: Optional[str] = None,
        actor: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        verify_integrity: bool = False,
    ) -> List[PDORecord]:
        """
        List PDOs with optional filtering.

        Returns PDOs sorted by recorded_at descending (newest first).

        Args:
            source_system: Filter by source system
            outcome: Filter by outcome
            correlation_id: Filter by correlation ID
            actor: Filter by actor
            limit: Maximum records to return
            offset: Number of records to skip
            verify_integrity: If True, verify each record's hash

        Returns:
            List of PDORecords matching criteria
        """
        with self._lock:
            # Start with appropriate index if filtered
            if correlation_id:
                pdo_ids = self._by_correlation.get(correlation_id, [])
                results = [self._records[pid] for pid in pdo_ids if pid in self._records]
            elif source_system:
                source_key = source_system.value if isinstance(source_system, PDOSourceSystem) else source_system
                pdo_ids = self._by_source_system.get(source_key, [])
                results = [self._records[pid] for pid in pdo_ids if pid in self._records]
            elif outcome:
                outcome_key = outcome.value if isinstance(outcome, PDOOutcome) else outcome
                pdo_ids = self._by_outcome.get(outcome_key, [])
                results = [self._records[pid] for pid in pdo_ids if pid in self._records]
            else:
                results = list(self._records.values())

        # Apply additional filters
        if source_system and not correlation_id:
            source_value = source_system.value if isinstance(source_system, PDOSourceSystem) else source_system
            results = [r for r in results if r.source_system.value == source_value]

        if outcome and not correlation_id and not source_system:
            outcome_value = outcome.value if isinstance(outcome, PDOOutcome) else outcome
            results = [r for r in results if r.outcome.value == outcome_value]

        if actor:
            results = [r for r in results if r.actor == actor]

        # Verify integrity if requested
        if verify_integrity:
            for record in results:
                if not record.verify_hash():
                    raise PDOTamperDetectedError(
                        f"PDO {record.pdo_id} failed integrity check during list",
                        pdo_id=record.pdo_id,
                        expected_hash=record.hash,
                        actual_hash=record.compute_hash(),
                    )

        # Sort by recorded_at descending
        results.sort(key=lambda r: r.recorded_at, reverse=True)

        # Pagination
        if offset:
            results = results[offset:]
        if limit is not None:
            results = results[:limit]

        return results

    def get_by_correlation(
        self,
        correlation_id: str,
        verify_integrity: bool = True,
    ) -> List[PDORecord]:
        """Get all PDOs with a given correlation ID."""
        return self.list(correlation_id=correlation_id, verify_integrity=verify_integrity)

    def get_chain(
        self,
        pdo_id: UUID,
        verify_integrity: bool = True,
    ) -> List[PDORecord]:
        """
        Get the full chain of PDOs linked by previous_pdo_id.

        Returns PDOs in order from oldest to newest.
        """
        chain: List[PDORecord] = []
        current_id: Optional[UUID] = pdo_id

        # Follow chain backwards
        visited: set[UUID] = set()
        while current_id and current_id not in visited:
            visited.add(current_id)
            record = self.get(current_id, verify_integrity=verify_integrity)
            if record is None:
                break
            chain.append(record)
            current_id = record.previous_pdo_id

        # Reverse to get oldest first
        chain.reverse()
        return chain

    def verify_all(self) -> Dict[UUID, bool]:
        """
        Verify integrity of all PDOs in the store.

        Returns:
            Dict mapping pdo_id to verification result (True=valid, False=tampered)
        """
        results: Dict[UUID, bool] = {}
        with self._lock:
            for pdo_id, record in self._records.items():
                results[pdo_id] = record.verify_hash()
        return results

    def count(self) -> int:
        """Return total number of PDOs in store."""
        with self._lock:
            return len(self._records)

    # =========================================================================
    # BLOCKED OPERATIONS — IMMUTABILITY ENFORCEMENT
    # =========================================================================

    def update(self, pdo_id: UUID, **kwargs) -> None:
        """
        BLOCKED: PDOs cannot be updated.

        Raises:
            PDOImmutabilityError: Always. Updates are not permitted.
        """
        logger.error(f"IMMUTABILITY VIOLATION: Attempted update on PDO {pdo_id}")
        get_invariant_telemetry().log_pdo_update_attempt(pdo_id)
        raise PDOImmutabilityError(
            f"PDO {pdo_id} cannot be updated. PDOs are immutable.",
            pdo_id=pdo_id,
        )

    def delete(self, pdo_id: UUID) -> None:
        """
        BLOCKED: PDOs cannot be deleted.

        Raises:
            PDOImmutabilityError: Always. Deletes are not permitted.
        """
        logger.error(f"IMMUTABILITY VIOLATION: Attempted delete on PDO {pdo_id}")
        get_invariant_telemetry().log_pdo_delete_attempt(pdo_id)
        raise PDOImmutabilityError(
            f"PDO {pdo_id} cannot be deleted. PDOs are immutable.",
            pdo_id=pdo_id,
        )

    def soft_delete(self, pdo_id: UUID) -> None:
        """
        BLOCKED: PDOs cannot be soft-deleted.

        Raises:
            PDOImmutabilityError: Always. Soft-deletes are not permitted.
        """
        logger.error(f"IMMUTABILITY VIOLATION: Attempted soft-delete on PDO {pdo_id}")
        get_invariant_telemetry().log_pdo_delete_attempt(pdo_id)
        raise PDOImmutabilityError(
            f"PDO {pdo_id} cannot be soft-deleted. PDOs are immutable.",
            pdo_id=pdo_id,
        )

    def overwrite(self, pdo_id: UUID, new_record: PDORecord) -> None:
        """
        BLOCKED: PDOs cannot be overwritten.

        Raises:
            PDOImmutabilityError: Always. Overwrites are not permitted.
        """
        logger.error(f"IMMUTABILITY VIOLATION: Attempted overwrite on PDO {pdo_id}")
        get_invariant_telemetry().log_pdo_update_attempt(pdo_id)
        raise PDOImmutabilityError(
            f"PDO {pdo_id} cannot be overwritten. PDOs are immutable.",
            pdo_id=pdo_id,
        )

    def modify_hash(self, pdo_id: UUID, new_hash: str) -> None:
        """
        BLOCKED: PDO hashes cannot be modified.

        Raises:
            PDOImmutabilityError: Always. Hash modification is not permitted.
        """
        logger.error(f"IMMUTABILITY VIOLATION: Attempted hash modification on PDO {pdo_id}")
        get_invariant_telemetry().log_pdo_hash_modification_attempt(pdo_id)
        raise PDOImmutabilityError(
            f"PDO {pdo_id} hash cannot be modified. PDO seals are immutable.",
            pdo_id=pdo_id,
        )


# Module-level singleton for convenience
_default_store: Optional[PDOStore] = None


def get_pdo_store() -> PDOStore:
    """Get the default PDO store singleton."""
    global _default_store
    if _default_store is None:
        _default_store = PDOStore()
    return _default_store


def reset_pdo_store() -> None:
    """Reset the default PDO store (for testing only)."""
    global _default_store
    _default_store = None
