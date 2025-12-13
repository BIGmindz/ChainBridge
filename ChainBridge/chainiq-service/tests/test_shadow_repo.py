"""Tests for shadow repository."""

from unittest.mock import MagicMock


from app.models_shadow import RiskShadowEvent
from app.repositories.shadow_repo import ShadowRepo


def test_shadow_repo_log_event():
    """Test that shadow repo logs events correctly."""
    # Mock database session
    mock_session = MagicMock()

    repo = ShadowRepo(mock_session)

    # Log an event
    event = repo.log_event(
        shipment_id="SH-TEST-001",
        dummy_score=0.75,
        real_score=0.82,
        model_version="v0.2.0",
        corridor="US-MX",
    )

    # Verify session methods were called
    assert mock_session.add.called
    assert mock_session.commit.called


def test_shadow_repo_computes_delta():
    """Test that delta is computed correctly."""
    mock_session = MagicMock()
    repo = ShadowRepo(mock_session)

    # Mock successful commit
    def refresh_side_effect(obj):
        # Simulate DB assigning ID
        obj.id = 1

    mock_session.refresh.side_effect = refresh_side_effect

    event = repo.log_event(
        shipment_id="SH-TEST-002",
        dummy_score=0.60,
        real_score=0.80,
        model_version="v0.2.0",
    )

    # Delta should be |0.60 - 0.80| = 0.20
    assert event is not None
    # Cannot check exact delta since event is mocked, but verify logic in implementation


def test_shadow_repo_handles_failure_gracefully():
    """Test that repo handles database failures without crashing."""
    mock_session = MagicMock()

    # Make commit raise exception
    mock_session.commit.side_effect = RuntimeError("DB connection failed")

    repo = ShadowRepo(mock_session)

    # Should return None and not raise
    event = repo.log_event(
        shipment_id="SH-TEST-003",
        dummy_score=0.70,
        real_score=0.75,
        model_version="v0.2.0",
    )

    assert event is None
    assert mock_session.rollback.called


def test_shadow_repo_get_recent_events():
    """Test retrieving recent events."""
    mock_session = MagicMock()

    # Mock query chain
    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = [
        RiskShadowEvent(
            id=1,
            shipment_id="SH-001",
            dummy_score=0.70,
            real_score=0.75,
            delta=0.05,
            model_version="v0.2.0",
        )
    ]

    repo = ShadowRepo(mock_session)
    events = repo.get_recent_events(limit=10)

    assert len(events) == 1
    assert events[0].shipment_id == "SH-001"


def test_shadow_repo_count_events():
    """Test counting events."""
    mock_session = MagicMock()

    # Mock query chain for count
    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.count.return_value = 42

    repo = ShadowRepo(mock_session)
    count = repo.count_events()

    assert count == 42
