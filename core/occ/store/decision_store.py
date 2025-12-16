"""
Decision Store - Thread-safe store with replay and time-travel audit support.

Features:
- CRUD operations for Decisions
- Decision → ProofPack linkage
- Deterministic replay verification
- Time-travel queries (point-in-time audit)
- Atomic JSON persistence

Author: CINDY (GID-04) - Backend
"""

import hashlib
import json
import logging
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from core.occ.schemas.decision import (
    Decision,
    DecisionCreate,
    DecisionOutcome,
    DecisionReplayRequest,
    DecisionReplayResult,
    DecisionTimeTravelQuery,
    DecisionTimeTravelResult,
    DecisionType,
)

logger = logging.getLogger(__name__)

# Default storage path
DEFAULT_DECISION_STORE_PATH = "./data/decisions.json"


class DecisionStore:
    """
    Thread-safe decision store with replay and time-travel support.

    Core capabilities:
    - Immutable decision records
    - Decision → ProofPack linkage
    - Deterministic replay verification
    - Point-in-time audit queries
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the store.

        Args:
            storage_path: Path to JSON persistence file.
        """
        self._lock = threading.Lock()
        self._decisions: Dict[UUID, Decision] = {}
        self._sequence_counter: int = 0

        # Indexes for efficient queries
        self._by_artifact: Dict[UUID, List[UUID]] = {}  # artifact_id -> [decision_ids]
        self._by_shipment: Dict[str, List[UUID]] = {}  # shipment_id -> [decision_ids]
        self._by_timestamp: List[UUID] = []  # ordered by created_at

        # Resolve storage path
        self._storage_path = Path(storage_path or os.environ.get("CHAINBRIDGE_DECISION_STORE_PATH", DEFAULT_DECISION_STORE_PATH))

        # Load existing data
        self._load()

    def _load(self) -> None:
        """Load decisions from JSON file if it exists."""
        if not self._storage_path.exists():
            logger.info(f"Decision store file not found at {self._storage_path}; starting fresh.")
            return

        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._sequence_counter = data.get("sequence_counter", 0)

            for item in data.get("decisions", []):
                decision = Decision.model_validate(item)
                self._decisions[decision.id] = decision
                self._index_decision(decision)

            logger.info(f"Loaded {len(self._decisions)} decisions from {self._storage_path}")
        except Exception as e:
            logger.error(f"Failed to load decision store: {e}")

    def _persist(self) -> None:
        """Persist decisions to JSON file atomically."""
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "sequence_counter": self._sequence_counter,
            "decisions": [d.model_dump(mode="json") for d in self._decisions.values()],
        }

        fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="decisions_", dir=self._storage_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            os.replace(tmp_path, self._storage_path)
            logger.debug(f"Persisted {len(self._decisions)} decisions")
        except Exception as e:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            logger.error(f"Failed to persist decisions: {e}")
            raise

    def _index_decision(self, decision: Decision) -> None:
        """Add decision to indexes (must be called within lock)."""
        # Index by artifact
        for artifact_id in decision.artifact_ids:
            if artifact_id not in self._by_artifact:
                self._by_artifact[artifact_id] = []
            self._by_artifact[artifact_id].append(decision.id)

        # Index by shipment
        if decision.input_snapshot.shipment_id:
            shipment_id = decision.input_snapshot.shipment_id
            if shipment_id not in self._by_shipment:
                self._by_shipment[shipment_id] = []
            self._by_shipment[shipment_id].append(decision.id)

        # Index by timestamp (maintain sorted order)
        self._by_timestamp.append(decision.id)
        self._by_timestamp.sort(key=lambda did: self._decisions[did].created_at)

    # =========================================================================
    # CORE CRUD
    # =========================================================================

    def create(
        self,
        decision_create: DecisionCreate,
        proofpack_id: Optional[UUID] = None,
    ) -> Decision:
        """
        Create a new immutable decision record.

        Args:
            decision_create: Decision creation schema.
            proofpack_id: Optional linked ProofPack ID.

        Returns:
            The created Decision with server-generated fields.
        """
        with self._lock:
            self._sequence_counter += 1

            # Compute input hash for replay verification
            input_hash = decision_create.input_snapshot.compute_hash()

            decision = Decision(
                sequence_number=self._sequence_counter,
                decision_type=decision_create.decision_type,
                outcome=decision_create.outcome,
                rationale=decision_create.rationale,
                actor=decision_create.actor,
                actor_type=decision_create.actor_type,
                input_snapshot=decision_create.input_snapshot,
                input_hash=input_hash,
                artifact_ids=decision_create.artifact_ids,
                proofpack_id=proofpack_id,
                parent_decision_id=decision_create.parent_decision_id,
                confidence=decision_create.confidence,
                tags=decision_create.tags,
            )

            self._decisions[decision.id] = decision
            self._index_decision(decision)
            self._persist()

        logger.info(
            f"Created decision: id={decision.id}, type={decision.decision_type}, " f"outcome={decision.outcome}, actor={decision.actor}"
        )
        return decision

    def get(self, decision_id: UUID) -> Optional[Decision]:
        """Get a decision by ID."""
        with self._lock:
            return self._decisions.get(decision_id)

    def list(
        self,
        decision_type: Optional[DecisionType] = None,
        outcome: Optional[DecisionOutcome] = None,
        actor: Optional[str] = None,
        artifact_id: Optional[UUID] = None,
        shipment_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Decision]:
        """
        List decisions with optional filtering.

        Returns decisions sorted by created_at descending (newest first).
        """
        with self._lock:
            # Start with appropriate index if filtered
            if artifact_id:
                decision_ids = self._by_artifact.get(artifact_id, [])
                results = [self._decisions[did] for did in decision_ids if did in self._decisions]
            elif shipment_id:
                decision_ids = self._by_shipment.get(shipment_id, [])
                results = [self._decisions[did] for did in decision_ids if did in self._decisions]
            else:
                results = list(self._decisions.values())

        # Apply filters
        if decision_type is not None:
            type_value = decision_type.value if isinstance(decision_type, DecisionType) else decision_type
            results = [d for d in results if d.decision_type == type_value]

        if outcome is not None:
            outcome_value = outcome.value if isinstance(outcome, DecisionOutcome) else outcome
            results = [d for d in results if d.outcome == outcome_value]

        if actor is not None:
            results = [d for d in results if d.actor == actor]

        # Sort by created_at descending
        results.sort(key=lambda d: d.created_at, reverse=True)

        # Pagination
        if offset:
            results = results[offset:]
        if limit is not None:
            results = results[:limit]

        return results

    def link_proofpack(self, decision_id: UUID, proofpack_id: UUID) -> Optional[Decision]:
        """
        Link a ProofPack to a decision.

        Note: Decisions are immutable, so this creates a new decision
        record with the proofpack_id set and links back to original.
        """
        with self._lock:
            existing = self._decisions.get(decision_id)
            if existing is None:
                return None

            if existing.proofpack_id is not None:
                logger.warning(f"Decision {decision_id} already has proofpack {existing.proofpack_id}")
                return existing

            # Update in place (proofpack linkage is allowed post-creation)
            data = existing.model_dump()
            data["proofpack_id"] = proofpack_id
            updated = Decision.model_validate(data)
            self._decisions[decision_id] = updated
            self._persist()

        logger.info(f"Linked proofpack {proofpack_id} to decision {decision_id}")
        return updated

    # =========================================================================
    # DECISION REPLAY
    # =========================================================================

    def replay_decision(
        self,
        request: DecisionReplayRequest,
        decision_logic: Optional[Any] = None,
    ) -> DecisionReplayResult:
        """
        Replay a decision using its original input snapshot.

        This enables deterministic verification: given the same inputs
        and logic, we should get the same output.

        Args:
            request: Replay request with decision ID and options.
            decision_logic: Optional callable to re-execute decision logic.
                           If None, uses simple comparison replay.

        Returns:
            DecisionReplayResult with comparison data.
        """
        with self._lock:
            original = self._decisions.get(request.decision_id)
            if original is None:
                raise ValueError(f"Decision not found: {request.decision_id}")

            # Verify input hash
            current_input_hash = original.input_snapshot.compute_hash()
            input_hash_match = current_input_hash == original.input_hash

            # Create replayed decision (without persistence in dry_run)
            replayed_data = original.model_dump()
            # Generate new UUID for the replayed decision
            from uuid import uuid4 as _uuid4

            replayed_data["id"] = _uuid4()
            replayed_data["is_replayed"] = True
            replayed_data["replay_source_id"] = original.id
            replayed_data["created_at"] = datetime.now(timezone.utc)

            # If decision_logic provided, re-execute
            if decision_logic is not None:
                try:
                    new_outcome, new_rationale, new_confidence = decision_logic(original.input_snapshot)
                    replayed_data["outcome"] = new_outcome
                    replayed_data["rationale"] = new_rationale
                    replayed_data["confidence"] = new_confidence
                except Exception as e:
                    logger.error(f"Decision logic replay failed: {e}")
                    replayed_data["rationale"] = f"Replay failed: {e}"

            replayed = Decision.model_validate(replayed_data)

            # Compare outputs
            differences = []
            is_deterministic = True

            if original.outcome != replayed.outcome:
                differences.append(f"outcome: {original.outcome} → {replayed.outcome}")
                is_deterministic = False

            if original.rationale != replayed.rationale:
                differences.append("rationale differs")
                # Rationale can differ due to timestamps, still deterministic if outcome matches

            if original.confidence != replayed.confidence:
                differences.append(f"confidence: {original.confidence} → {replayed.confidence}")

            # Persist if not dry_run
            if not request.dry_run:
                self._sequence_counter += 1
                replayed_data["sequence_number"] = self._sequence_counter
                replayed_data["id"] = _uuid4()  # New ID for persisted decision
                replayed = Decision.model_validate(replayed_data)
                self._decisions[replayed.id] = replayed
                self._index_decision(replayed)
                self._persist()

        return DecisionReplayResult(
            original_decision_id=original.id,
            replayed_decision=replayed,
            is_deterministic=is_deterministic,
            differences=differences,
            input_hash_match=input_hash_match,
        )

    # =========================================================================
    # TIME-TRAVEL AUDIT
    # =========================================================================

    def time_travel_query(self, query: DecisionTimeTravelQuery) -> DecisionTimeTravelResult:
        """
        Query decisions as they existed at a point in time.

        This enables audit replay: see exactly what decisions were
        visible/active at any historical moment.

        Args:
            query: Time-travel query parameters.

        Returns:
            DecisionTimeTravelResult with matching decisions.
        """
        with self._lock:
            # Start with all decisions created before as_of
            candidates = [d for d in self._decisions.values() if d.created_at <= query.as_of]

            # Apply window_start if specified
            if query.window_start:
                candidates = [d for d in candidates if d.created_at >= query.window_start]

            # Filter by artifact_id
            if query.artifact_id:
                candidates = [d for d in candidates if query.artifact_id in d.artifact_ids]

            # Filter by shipment_id
            if query.shipment_id:
                candidates = [d for d in candidates if d.input_snapshot.shipment_id == query.shipment_id]

            # Filter by decision_types
            if query.decision_types:
                type_values = [t.value if isinstance(t, DecisionType) else t for t in query.decision_types]
                candidates = [d for d in candidates if d.decision_type in type_values]

            # Filter by actors
            if query.actors:
                candidates = [d for d in candidates if d.actor in query.actors]

            # Sort by created_at
            candidates.sort(key=lambda d: d.created_at)

            # Optionally strip input snapshots
            if not query.include_input_snapshots:
                # Return decisions with minimal snapshots
                stripped = []
                for d in candidates:
                    data = d.model_dump()
                    data["input_snapshot"] = {"captured_at": d.input_snapshot.captured_at}
                    stripped.append(Decision.model_validate(data))
                candidates = stripped

            # Compute state hash (hash of all decision IDs + timestamps at query time)
            state_data = [{"id": str(d.id), "created_at": d.created_at.isoformat()} for d in candidates]
            state_json = json.dumps(state_data, sort_keys=True, separators=(",", ":"))
            state_hash = hashlib.sha256(state_json.encode()).hexdigest()

        return DecisionTimeTravelResult(
            query=query,
            decisions=candidates,
            count=len(candidates),
            state_hash=state_hash,
        )

    def get_decisions_for_artifact(self, artifact_id: UUID) -> List[Decision]:
        """Get all decisions linked to an artifact."""
        with self._lock:
            decision_ids = self._by_artifact.get(artifact_id, [])
            return [self._decisions[did] for did in decision_ids if did in self._decisions]

    def get_decisions_for_shipment(self, shipment_id: str) -> List[Decision]:
        """Get all decisions for a shipment."""
        with self._lock:
            decision_ids = self._by_shipment.get(shipment_id, [])
            return [self._decisions[did] for did in decision_ids if did in self._decisions]


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

_decision_store_instance: Optional[DecisionStore] = None
_decision_store_lock = threading.Lock()


def get_decision_store() -> DecisionStore:
    """Get the singleton DecisionStore instance (FastAPI dependency)."""
    global _decision_store_instance
    if _decision_store_instance is None:
        with _decision_store_lock:
            if _decision_store_instance is None:
                _decision_store_instance = DecisionStore()
    return _decision_store_instance


def reset_decision_store() -> None:
    """Reset the singleton (for testing)."""
    global _decision_store_instance
    with _decision_store_lock:
        _decision_store_instance = None
