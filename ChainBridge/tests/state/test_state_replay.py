"""
Tests for ChainBridge State Replay Engine

Atlas (GID-05) — System State Engine
Authority: Benson (GID-00)

These tests verify the deterministic replay engine per INV-S08.
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from core.state import (
    ArtifactType,
    EventStateRecord,
    EventType,
    ReplayResult,
    ReplayState,
    ShipmentState,
    StateMetadata,
    StateReplayEngine,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def replay_engine() -> StateReplayEngine:
    """Create a fresh StateReplayEngine instance."""
    return StateReplayEngine()


@pytest.fixture
def shipment_artifact_id() -> str:
    """Create a consistent artifact ID for tests."""
    return f"SHIP-{uuid4().hex[:8]}"


@pytest.fixture
def shipment_event_sequence(shipment_artifact_id: str) -> list[EventStateRecord]:
    """Create a complete shipment event sequence for replay."""
    base_time = datetime.utcnow() - timedelta(days=7)
    
    return [
        EventStateRecord(
            event_id=f"EVT-{uuid4().hex[:8]}",
            event_type=EventType.SHIPMENT_CREATED,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
            timestamp=base_time,
            sequence_number=0,
            payload_hash="hash_create",
            metadata=StateMetadata(),
        ),
        EventStateRecord(
            event_id=f"EVT-{uuid4().hex[:8]}",
            event_type=EventType.SHIPMENT_DEPARTED,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
            timestamp=base_time + timedelta(hours=2),
            sequence_number=1,
            payload_hash="hash_depart",
            metadata=StateMetadata(),
        ),
        EventStateRecord(
            event_id=f"EVT-{uuid4().hex[:8]}",
            event_type=EventType.SHIPMENT_DELIVERED,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
            timestamp=base_time + timedelta(days=2),
            sequence_number=2,
            payload_hash="hash_deliver",
            metadata=StateMetadata(),
        ),
    ]


# =============================================================================
# INV-S08: REPLAY DETERMINISM
# =============================================================================


class TestReplayDeterminism:
    """Tests for INV-S08: Replay determinism."""

    def test_same_events_produce_same_state(
        self,
        replay_engine: StateReplayEngine,
        shipment_event_sequence: list[EventStateRecord],
        shipment_artifact_id: str,
    ) -> None:
        """Same event sequence produces identical state."""
        result1 = replay_engine.replay_events(
            shipment_event_sequence,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
        )
        result2 = replay_engine.replay_events(
            shipment_event_sequence,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
        )
        
        assert result1.final_state is not None
        assert result2.final_state is not None
        assert result1.final_state.current_state == result2.final_state.current_state
        assert result1.state_hash == result2.state_hash

    def test_replay_multiple_times_consistent(
        self,
        replay_engine: StateReplayEngine,
        shipment_event_sequence: list[EventStateRecord],
        shipment_artifact_id: str,
    ) -> None:
        """Multiple replays produce consistent results."""
        results = [
            replay_engine.replay_events(
                shipment_event_sequence,
                artifact_type=ArtifactType.SHIPMENT,
                artifact_id=shipment_artifact_id,
            )
            for _ in range(5)
        ]
        
        # All results should be identical
        first_state = results[0].final_state.current_state
        first_hash = results[0].state_hash
        for i, result in enumerate(results[1:], start=2):
            assert result.final_state.current_state == first_state, f"Replay {i} differs"
            assert result.state_hash == first_hash, f"Replay {i} hash differs"

    def test_different_events_produce_different_state(
        self,
        replay_engine: StateReplayEngine,
        shipment_event_sequence: list[EventStateRecord],
        shipment_artifact_id: str,
    ) -> None:
        """Different event sequences produce different states."""
        # Remove last event
        partial_events = shipment_event_sequence[:-1]
        
        full_result = replay_engine.replay_events(
            shipment_event_sequence,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
        )
        partial_result = replay_engine.replay_events(
            partial_events,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
        )
        
        assert full_result.final_state.current_state != partial_result.final_state.current_state


# =============================================================================
# REPLAY ENGINE FUNCTIONALITY
# =============================================================================


class TestReplayEngine:
    """Tests for StateReplayEngine functionality."""

    def test_replay_empty_events(
        self,
        replay_engine: StateReplayEngine,
        shipment_artifact_id: str,
    ) -> None:
        """Empty event list produces valid result with no state."""
        result = replay_engine.replay_events(
            [],
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
        )
        
        assert result.events_processed == 0
        assert result.final_state is None

    def test_replay_single_event(
        self,
        replay_engine: StateReplayEngine,
        shipment_event_sequence: list[EventStateRecord],
        shipment_artifact_id: str,
    ) -> None:
        """Single event produces initial state."""
        single_event = [shipment_event_sequence[0]]
        result = replay_engine.replay_events(
            single_event,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
        )
        
        assert result.events_processed == 1
        assert result.final_state is not None
        assert result.final_state.current_state == ShipmentState.CREATED.value

    def test_replay_tracks_event_count(
        self,
        replay_engine: StateReplayEngine,
        shipment_event_sequence: list[EventStateRecord],
        shipment_artifact_id: str,
    ) -> None:
        """Replay correctly tracks processed event count."""
        result = replay_engine.replay_events(
            shipment_event_sequence,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
        )
        
        assert result.events_processed == len(shipment_event_sequence)

    def test_replay_computes_final_state(
        self,
        replay_engine: StateReplayEngine,
        shipment_event_sequence: list[EventStateRecord],
        shipment_artifact_id: str,
    ) -> None:
        """Replay computes correct final state."""
        result = replay_engine.replay_events(
            shipment_event_sequence,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
        )
        
        assert result.final_state is not None
        # Last event is SHIPMENT_DELIVERED, which moves to DELIVERED
        assert result.final_state.current_state == ShipmentState.DELIVERED.value


# =============================================================================
# STATE AT TIME COMPUTATION
# =============================================================================


class TestComputeStateAtTime:
    """Tests for compute_state_at_time functionality."""

    def test_state_at_creation(
        self,
        replay_engine: StateReplayEngine,
        shipment_event_sequence: list[EventStateRecord],
        shipment_artifact_id: str,
    ) -> None:
        """State at creation time shows CREATED."""
        creation_time = shipment_event_sequence[0].timestamp + timedelta(minutes=1)
        
        result = replay_engine.compute_state_at_time(
            events=shipment_event_sequence,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
            target_time=creation_time,
        )
        
        assert result.final_state is not None
        assert result.final_state.current_state == ShipmentState.CREATED.value

    def test_state_at_departure(
        self,
        replay_engine: StateReplayEngine,
        shipment_event_sequence: list[EventStateRecord],
        shipment_artifact_id: str,
    ) -> None:
        """State after departure shows IN_TRANSIT."""
        departure_time = shipment_event_sequence[1].timestamp + timedelta(minutes=1)
        
        result = replay_engine.compute_state_at_time(
            events=shipment_event_sequence,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
            target_time=departure_time,
        )
        
        assert result.final_state is not None
        assert result.final_state.current_state == ShipmentState.IN_TRANSIT.value

    def test_state_at_delivery(
        self,
        replay_engine: StateReplayEngine,
        shipment_event_sequence: list[EventStateRecord],
        shipment_artifact_id: str,
    ) -> None:
        """State after delivery shows DELIVERED."""
        delivery_time = shipment_event_sequence[2].timestamp + timedelta(minutes=1)
        
        result = replay_engine.compute_state_at_time(
            events=shipment_event_sequence,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
            target_time=delivery_time,
        )
        
        assert result.final_state is not None
        assert result.final_state.current_state == ShipmentState.DELIVERED.value

    def test_state_before_first_event(
        self,
        replay_engine: StateReplayEngine,
        shipment_event_sequence: list[EventStateRecord],
        shipment_artifact_id: str,
    ) -> None:
        """State before first event returns None."""
        before_time = shipment_event_sequence[0].timestamp - timedelta(hours=1)
        
        result = replay_engine.compute_state_at_time(
            events=shipment_event_sequence,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
            target_time=before_time,
        )
        
        assert result.final_state is None
        assert result.events_processed == 0


# =============================================================================
# STATE CONSISTENCY VERIFICATION
# =============================================================================


class TestVerifyStateConsistency:
    """Tests for verify_state_consistency functionality."""

    def test_consistent_state_passes(
        self,
        replay_engine: StateReplayEngine,
        shipment_event_sequence: list[EventStateRecord],
        shipment_artifact_id: str,
    ) -> None:
        """State consistent with events passes verification."""
        # Replay to get expected state
        replay_result = replay_engine.replay_events(
            shipment_event_sequence,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
        )
        expected_state = replay_result.final_state.current_state
        expected_hash = replay_result.state_hash
        
        # Verify the state matches
        verify_result = replay_engine.verify_state_consistency(
            events=shipment_event_sequence,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
            current_state=expected_state,
            current_hash=expected_hash,
        )
        
        assert verify_result.is_deterministic
        assert verify_result.hashes_match

    def test_inconsistent_state_fails(
        self,
        replay_engine: StateReplayEngine,
        shipment_event_sequence: list[EventStateRecord],
        shipment_artifact_id: str,
    ) -> None:
        """State inconsistent with events fails verification."""
        # Verify with wrong expected state
        verify_result = replay_engine.verify_state_consistency(
            events=shipment_event_sequence,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
            current_state=ShipmentState.CREATED.value,  # Wrong state
            current_hash="wrong_hash",
        )
        
        assert not verify_result.is_deterministic


# =============================================================================
# REPLAY RESULT STRUCTURE
# =============================================================================


class TestReplayResultStructure:
    """Tests for ReplayResult structure."""

    def test_replay_result_contains_timestamps(
        self,
        replay_engine: StateReplayEngine,
        shipment_event_sequence: list[EventStateRecord],
        shipment_artifact_id: str,
    ) -> None:
        """ReplayResult contains timing information."""
        result = replay_engine.replay_events(
            shipment_event_sequence,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
        )
        
        assert result.replayed_at is not None
        assert result.duration_ms >= 0

    def test_replay_result_contains_hash(
        self,
        replay_engine: StateReplayEngine,
        shipment_event_sequence: list[EventStateRecord],
        shipment_artifact_id: str,
    ) -> None:
        """ReplayResult contains state hash for audit."""
        result = replay_engine.replay_events(
            shipment_event_sequence,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
        )
        
        assert result.state_hash is not None
        assert len(result.state_hash) == 64  # SHA256 hex length


# =============================================================================
# REPLAY STATE STRUCTURE
# =============================================================================


class TestReplayStateStructure:
    """Tests for ReplayState structure."""

    def test_replay_state_has_artifact_info(
        self,
        replay_engine: StateReplayEngine,
        shipment_event_sequence: list[EventStateRecord],
        shipment_artifact_id: str,
    ) -> None:
        """ReplayState contains artifact identification."""
        result = replay_engine.replay_events(
            shipment_event_sequence,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
        )
        
        assert result.final_state.artifact_id == shipment_artifact_id
        assert result.final_state.artifact_type == ArtifactType.SHIPMENT

    def test_replay_state_tracks_event_count(
        self,
        replay_engine: StateReplayEngine,
        shipment_event_sequence: list[EventStateRecord],
        shipment_artifact_id: str,
    ) -> None:
        """ReplayState tracks number of events processed."""
        result = replay_engine.replay_events(
            shipment_event_sequence,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
        )
        
        assert result.final_state.event_count == len(shipment_event_sequence)

    def test_replay_state_has_timestamp(
        self,
        replay_engine: StateReplayEngine,
        shipment_event_sequence: list[EventStateRecord],
        shipment_artifact_id: str,
    ) -> None:
        """ReplayState has timestamp of last event."""
        result = replay_engine.replay_events(
            shipment_event_sequence,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=shipment_artifact_id,
        )
        
        assert result.final_state.last_timestamp == shipment_event_sequence[-1].timestamp


# =============================================================================
# EDGE CASES
# =============================================================================


class TestReplayEdgeCases:
    """Tests for edge cases in replay functionality."""

    def test_replay_detects_invalid_transitions(
        self, replay_engine: StateReplayEngine
    ) -> None:
        """Replay detects invalid state transitions."""
        artifact_id = f"SHIP-{uuid4().hex[:8]}"
        base_time = datetime.utcnow()
        
        # Create an invalid sequence (skipping IN_TRANSIT)
        events = [
            EventStateRecord(
                event_id=f"EVT-{uuid4().hex[:8]}",
                event_type=EventType.SHIPMENT_CREATED,
                artifact_type=ArtifactType.SHIPMENT,
                artifact_id=artifact_id,
                timestamp=base_time,
                sequence_number=0,
                payload_hash="hash0",
                metadata=StateMetadata(),
            ),
            # Skip DEPARTED, go straight to DELIVERED (invalid)
            EventStateRecord(
                event_id=f"EVT-{uuid4().hex[:8]}",
                event_type=EventType.SHIPMENT_DELIVERED,
                artifact_type=ArtifactType.SHIPMENT,
                artifact_id=artifact_id,
                timestamp=base_time + timedelta(hours=1),
                sequence_number=1,
                payload_hash="hash1",
                metadata=StateMetadata(),
            ),
        ]
        
        result = replay_engine.replay_events(
            events,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=artifact_id,
        )
        
        # Should detect the invalid transition
        assert not result.is_deterministic
        assert len(result.validation_errors) > 0
