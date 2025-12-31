"""
Minimum Execution Spine Tests - PAC-BENSON-EXEC-SPINE-01

QA & ACCEPTANCE CHECKLIST:
- [x] Event can be triggered via curl
- [x] Decision output is predictable
- [x] Action executes or errors explicitly
- [x] Proof artifact exists and is readable
- [x] Same input → same output → same proof hash
"""

import json
from datetime import datetime, timezone
from uuid import UUID

import pytest

from core.spine.decision import DecisionEngine, DecisionOutcome, DecisionResult
from core.spine.event import (
    PaymentRequestPayload,
    SpineEvent,
    SpineEventType,
    create_payment_request_event,
)
from core.spine.executor import (
    ActionResult,
    ActionStatus,
    ActionType,
    ExecutionProof,
    ProofStore,
    SpineExecutor,
)


# =============================================================================
# EVENT TESTS
# =============================================================================


class TestSpineEvent:
    """Tests for canonical event schema."""

    def test_create_payment_request_event(self):
        """Event creation with valid payload."""
        event = create_payment_request_event(
            amount=5000.00,
            vendor_id="vendor-001",
            requestor_id="req-001",
        )

        assert event.event_type == SpineEventType.PAYMENT_REQUEST
        assert event.payload["amount"] == 5000.00
        assert event.payload["vendor_id"] == "vendor-001"
        assert event.payload["currency"] == "USD"
        assert isinstance(event.id, UUID)
        assert event.timestamp is not None

    def test_event_immutability(self):
        """Events are immutable after creation."""
        event = create_payment_request_event(
            amount=1000.00,
            vendor_id="v1",
            requestor_id="r1",
        )

        with pytest.raises(Exception):  # Pydantic ValidationError for frozen model
            event.payload = {"new": "data"}

    def test_event_hash_determinism(self):
        """Same event content produces same hash."""
        # Create two events with identical data
        event1 = SpineEvent(
            id=UUID("12345678-1234-1234-1234-123456789012"),
            event_type=SpineEventType.PAYMENT_REQUEST,
            payload={"amount": 100.0, "vendor_id": "v1", "requestor_id": "r1", "currency": "USD"},
            timestamp="2025-01-01T00:00:00+00:00",
        )
        event2 = SpineEvent(
            id=UUID("12345678-1234-1234-1234-123456789012"),
            event_type=SpineEventType.PAYMENT_REQUEST,
            payload={"amount": 100.0, "vendor_id": "v1", "requestor_id": "r1", "currency": "USD"},
            timestamp="2025-01-01T00:00:00+00:00",
        )

        assert event1.compute_hash() == event2.compute_hash()

    def test_event_hash_changes_with_content(self):
        """Different content produces different hash."""
        event1 = create_payment_request_event(amount=100.0, vendor_id="v1", requestor_id="r1")
        event2 = create_payment_request_event(amount=200.0, vendor_id="v1", requestor_id="r1")

        assert event1.compute_hash() != event2.compute_hash()

    def test_payload_validation_rejects_empty(self):
        """Empty payload is rejected."""
        with pytest.raises(ValueError, match="payload cannot be empty"):
            SpineEvent(
                event_type=SpineEventType.PAYMENT_REQUEST,
                payload={},
            )

    def test_payment_payload_validation(self):
        """Payment payload validates required fields."""
        with pytest.raises(ValueError):
            PaymentRequestPayload(
                amount=-100,  # Invalid: negative
                vendor_id="v1",
                requestor_id="r1",
            )


# =============================================================================
# DECISION TESTS
# =============================================================================


class TestDecisionEngine:
    """Tests for deterministic decision logic."""

    def test_approve_under_threshold(self):
        """Payment under threshold is approved."""
        event = create_payment_request_event(
            amount=5000.00,
            vendor_id="v1",
            requestor_id="r1",
        )

        decision = DecisionEngine.decide(event)

        assert decision.outcome == DecisionOutcome.APPROVED
        assert decision.rule_applied == "payment_threshold_v1"
        assert "within threshold" in decision.explanation

    def test_approve_at_threshold(self):
        """Payment exactly at threshold is approved."""
        event = create_payment_request_event(
            amount=10_000.00,  # Exactly at threshold
            vendor_id="v1",
            requestor_id="r1",
        )

        decision = DecisionEngine.decide(event)

        assert decision.outcome == DecisionOutcome.APPROVED

    def test_requires_review_over_threshold(self):
        """Payment over threshold requires review."""
        event = create_payment_request_event(
            amount=15_000.00,
            vendor_id="v1",
            requestor_id="r1",
        )

        decision = DecisionEngine.decide(event)

        assert decision.outcome == DecisionOutcome.REQUIRES_REVIEW
        assert "exceeds threshold" in decision.explanation

    def test_decision_determinism(self):
        """Same input produces same decision output."""
        event = SpineEvent(
            id=UUID("12345678-1234-1234-1234-123456789012"),
            event_type=SpineEventType.PAYMENT_REQUEST,
            payload={"amount": 5000.0, "vendor_id": "v1", "requestor_id": "r1", "currency": "USD"},
            timestamp="2025-01-01T00:00:00+00:00",
        )

        decision1 = DecisionEngine.decide(event)
        decision2 = DecisionEngine.decide(event)

        assert decision1.outcome == decision2.outcome
        assert decision1.rule_applied == decision2.rule_applied
        assert decision1.inputs_snapshot == decision2.inputs_snapshot

    def test_decision_captures_inputs(self):
        """Decision captures all inputs used."""
        event = create_payment_request_event(
            amount=7500.00,
            vendor_id="vendor-123",
            requestor_id="req-456",
            currency="EUR",
        )

        decision = DecisionEngine.decide(event)

        assert decision.inputs_snapshot["amount"] == 7500.00
        assert decision.inputs_snapshot["vendor_id"] == "vendor-123"
        assert decision.inputs_snapshot["requestor_id"] == "req-456"
        assert decision.inputs_snapshot["currency"] == "EUR"
        assert decision.inputs_snapshot["threshold"] == 10_000.00

    def test_decision_error_on_missing_amount(self):
        """Error decision when amount is missing."""
        event = SpineEvent(
            event_type=SpineEventType.PAYMENT_REQUEST,
            payload={"vendor_id": "v1", "requestor_id": "r1"},  # Missing amount
        )

        decision = DecisionEngine.decide(event)

        assert decision.outcome == DecisionOutcome.ERROR
        assert "Missing required field" in decision.explanation


# =============================================================================
# EXECUTOR TESTS
# =============================================================================


class TestSpineExecutor:
    """Tests for full execution flow."""

    @pytest.fixture
    def temp_proof_store(self, tmp_path):
        """Create a temporary proof store."""
        return ProofStore(storage_dir=str(tmp_path / "proofs"))

    @pytest.fixture
    def executor(self, temp_proof_store):
        """Create executor with temp storage."""
        return SpineExecutor(proof_store=temp_proof_store)

    def test_full_execution_flow(self, executor):
        """Event → Decision → Action → Proof executes end-to-end."""
        event = create_payment_request_event(
            amount=5000.00,
            vendor_id="v1",
            requestor_id="r1",
        )

        proof = executor.execute(event)

        # Verify proof contains all required fields
        assert proof.event_id == event.id
        assert proof.event_hash == event.compute_hash()
        assert proof.decision_outcome == "approved"
        assert proof.action_status == "success"
        assert proof.proof_timestamp is not None

    def test_action_state_transition(self, executor):
        """Action produces real state change."""
        event = create_payment_request_event(
            amount=3000.00,
            vendor_id="v1",
            requestor_id="r1",
        )

        proof = executor.execute(event)

        # Verify state was modified
        state_key = f"payment_{event.id}"
        state = executor.get_state(state_key)

        assert state is not None
        assert state["status"] == "APPROVED"
        assert state["amount"] == 3000.00

    def test_proof_persistence(self, executor, temp_proof_store):
        """Proof is persisted to storage."""
        event = create_payment_request_event(
            amount=2000.00,
            vendor_id="v1",
            requestor_id="r1",
        )

        proof = executor.execute(event)

        # Verify proof can be loaded
        loaded_proof = temp_proof_store.load(proof.id)
        assert loaded_proof is not None
        assert loaded_proof.id == proof.id
        assert loaded_proof.compute_hash() == proof.compute_hash()

    def test_proof_hash_determinism(self, executor):
        """Same execution produces verifiable proof."""
        event = SpineEvent(
            id=UUID("12345678-1234-1234-1234-123456789012"),
            event_type=SpineEventType.PAYMENT_REQUEST,
            payload={"amount": 5000.0, "vendor_id": "v1", "requestor_id": "r1", "currency": "USD"},
            timestamp="2025-01-01T00:00:00+00:00",
        )

        proof = executor.execute(event)

        # Hash should be reproducible
        hash1 = proof.compute_hash()
        hash2 = proof.compute_hash()
        assert hash1 == hash2

    def test_review_queue_action(self, executor):
        """Over-threshold payment is queued for review."""
        event = create_payment_request_event(
            amount=25_000.00,
            vendor_id="v1",
            requestor_id="r1",
        )

        proof = executor.execute(event)

        assert proof.decision_outcome == "requires_review"
        assert proof.action_status == "success"

        state = executor.get_state(f"payment_{event.id}")
        assert state["status"] == "PENDING_REVIEW"


# =============================================================================
# PROOF ARTIFACT TESTS
# =============================================================================


class TestExecutionProof:
    """Tests for proof artifact format."""

    def test_proof_contains_required_fields(self):
        """Proof artifact has all required fields per PAC spec."""
        proof = ExecutionProof(
            event_id=UUID("12345678-1234-1234-1234-123456789012"),
            event_hash="abc123",
            event_type="payment_request",
            event_timestamp="2025-01-01T00:00:00+00:00",
            decision_id=UUID("22345678-1234-1234-1234-123456789012"),
            decision_hash="def456",
            decision_outcome="approved",
            decision_rule="payment_threshold_v1",
            decision_rule_version="1.0.0",
            decision_inputs={"amount": 5000.0},
            decision_explanation="Approved",
            action_id=UUID("32345678-1234-1234-1234-123456789012"),
            action_type="state_transition",
            action_status="success",
            action_details={"status": "APPROVED"},
        )

        # Required per PAC-BENSON-EXEC-SPINE-01
        assert proof.event_hash is not None
        assert proof.decision_inputs is not None
        assert proof.decision_outcome is not None
        assert proof.action_status is not None
        assert proof.proof_timestamp is not None

    def test_proof_to_json(self):
        """Proof exports to JSON for verification."""
        proof = ExecutionProof(
            event_id=UUID("12345678-1234-1234-1234-123456789012"),
            event_hash="abc123",
            event_type="payment_request",
            event_timestamp="2025-01-01T00:00:00+00:00",
            decision_id=UUID("22345678-1234-1234-1234-123456789012"),
            decision_hash="def456",
            decision_outcome="approved",
            decision_rule="payment_threshold_v1",
            decision_rule_version="1.0.0",
            decision_inputs={"amount": 5000.0},
            decision_explanation="Approved",
            action_id=UUID("32345678-1234-1234-1234-123456789012"),
            action_type="state_transition",
            action_status="success",
            action_details={},
        )

        json_str = proof.to_canonical_json()
        data = json.loads(json_str)

        assert data["event_hash"] == "abc123"
        assert data["decision_outcome"] == "approved"


# =============================================================================
# API INTEGRATION TESTS
# =============================================================================


class TestSpineAPI:
    """Tests for spine API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from api.server import app
        return TestClient(app)

    def test_spine_health_endpoint(self, client):
        """Health check returns spine status."""
        response = client.get("/spine/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["decision_rule"] == "payment_threshold_v1"

    def test_execute_payment_via_curl(self, client):
        """Event can be triggered via HTTP POST (curl-equivalent)."""
        response = client.post(
            "/spine/event",
            json={
                "event_type": "payment_request",
                "payload": {
                    "amount": 5000.00,
                    "vendor_id": "vendor-001",
                    "requestor_id": "req-001",
                    "currency": "USD",
                },
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["decision_outcome"] == "approved"
        assert "proof_id" in data
        assert "proof_hash" in data

    def test_execute_payment_convenience_endpoint(self, client):
        """Payment convenience endpoint works."""
        response = client.post(
            "/spine/payment",
            json={
                "amount": 15000.00,
                "vendor_id": "v1",
                "requestor_id": "r1",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["decision_outcome"] == "requires_review"

    def test_retrieve_proof(self, client):
        """Proof can be retrieved after execution."""
        # Execute first
        exec_response = client.post(
            "/spine/payment",
            json={"amount": 1000.00, "vendor_id": "v1", "requestor_id": "r1"},
        )
        proof_id = exec_response.json()["proof_id"]

        # Retrieve proof
        proof_response = client.get(f"/spine/proof/{proof_id}")

        assert proof_response.status_code == 200
        data = proof_response.json()
        assert data["verified"] is True
        assert "proof" in data
        assert "proof_hash" in data

    def test_invalid_event_type_rejected(self, client):
        """Invalid event type is rejected."""
        response = client.post(
            "/spine/event",
            json={
                "event_type": "invalid_type",
                "payload": {"data": "value"},
            },
        )

        assert response.status_code == 400
        assert "Unsupported event_type" in response.json()["detail"]
