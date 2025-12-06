# tests/test_audit_logging.py
"""
Unit tests for the audit event and decision log skeleton.

These tests verify that:
1. AuditEvent rows can be created and persisted
2. DecisionLog rows can be created and persisted
3. Decisions can be linked to events via audit_event_id
4. All required fields are stored correctly

See docs/product/CHAINBRIDGE_AUDIT_PROOFPACK_SPEC.md for semantic details.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

# Import the models to ensure they're registered with Base.metadata
from app.models_audit import AuditEvent, DecisionLog  # noqa: F401
from app.services.audit_service import record_audit_event, record_decision_log


class TestAuditEvent:
    """Tests for AuditEvent creation and persistence."""

    def test_record_audit_event_creates_row(self, db_session: Session):
        """Verify that record_audit_event creates and persists a row."""
        event = record_audit_event(
            db_session,
            event_type="payout_released",
            actor_type="system",
            payment_id="pay_123",
            shipment_id="ship_456",
            customer_id="cust_789",
        )

        assert event.id is not None
        assert event.event_type == "payout_released"
        assert event.actor_type == "system"
        assert event.payment_id == "pay_123"
        assert event.shipment_id == "ship_456"
        assert event.customer_id == "cust_789"
        assert event.created_at is not None

    def test_record_audit_event_with_all_fields(self, db_session: Session):
        """Verify that all optional fields can be set."""
        event = record_audit_event(
            db_session,
            event_type="payment_approved",
            actor_type="agent",
            actor_id="GID-01",
            source_system="ChainIQ",
            shipment_id="ship_001",
            payment_id="pay_001",
            customer_id="cust_001",
            correlation_id="corr_abc123",
            payload_hash="sha256:abc123def456",
            payload_meta={"amount": 5000, "currency": "USD"},
        )

        assert event.id is not None
        assert event.actor_id == "GID-01"
        assert event.source_system == "ChainIQ"
        assert event.correlation_id == "corr_abc123"
        assert event.payload_hash == "sha256:abc123def456"
        assert event.payload_meta["amount"] == 5000
        assert event.payload_meta["currency"] == "USD"

    def test_audit_event_default_payload_meta_is_empty_dict(self, db_session: Session):
        """Verify that payload_meta defaults to empty dict when not provided."""
        event = record_audit_event(
            db_session,
            event_type="test_event",
            actor_type="system",
        )

        assert event.payload_meta == {}


class TestDecisionLog:
    """Tests for DecisionLog creation and persistence."""

    def test_record_decision_log_creates_row(self, db_session: Session):
        """Verify that record_decision_log creates and persists a row."""
        log = record_decision_log(
            db_session,
            decision_type="payout_decision",
            outcome="approve",
            payment_policy_version="chainpay_v1.0",
        )

        assert log.id is not None
        assert log.decision_type == "payout_decision"
        assert log.outcome == "approve"
        assert log.payment_policy_version == "chainpay_v1.0"
        assert log.created_at is not None
        assert log.overridden == 0

    def test_record_decision_log_with_input_snapshot(self, db_session: Session):
        """Verify that input_snapshot JSON is stored correctly."""
        log = record_decision_log(
            db_session,
            decision_type="risk_evaluation",
            outcome="hold",
            input_snapshot={"amount": 1000, "currency": "USD", "risk_score": 0.75},
            rules_fired={"rules": ["HIGH_RISK_AMOUNT", "NEW_CUSTOMER"]},
            explanation={"reason": "Amount exceeds threshold for new customer"},
        )

        assert log.input_snapshot["amount"] == 1000
        assert log.input_snapshot["risk_score"] == 0.75
        assert "HIGH_RISK_AMOUNT" in log.rules_fired["rules"]
        assert "exceeds threshold" in log.explanation["reason"]

    def test_record_decision_log_with_override(self, db_session: Session):
        """Verify that override fields are stored correctly."""
        log = record_decision_log(
            db_session,
            decision_type="payout_decision",
            outcome="approve",
            overridden=True,
            override_actor_id="user_admin_001",
            override_reason="VIP customer - manual approval per policy exception",
        )

        assert log.overridden == 1
        assert log.override_actor_id == "user_admin_001"
        assert "VIP customer" in log.override_reason


class TestDecisionEventLinking:
    """Tests for linking DecisionLog to AuditEvent."""

    def test_decision_log_links_to_audit_event(self, db_session: Session):
        """Verify that decisions can be linked to events via audit_event_id."""
        # First create an event
        event = record_audit_event(
            db_session,
            event_type="payout_evaluated",
            actor_type="system",
            payment_id="pay_abc",
        )

        # Then create a decision linked to that event
        log = record_decision_log(
            db_session,
            decision_type="payout_decision",
            outcome="approve",
            audit_event_id=event.id,
            payment_policy_version="chainpay_v1.0",
            input_snapshot={"amount": 1000, "currency": "USD"},
            rules_fired={"rules": ["MIN_AGE_OK"]},
            explanation={"reason": "All checks passed"},
        )

        assert log.id is not None
        assert log.audit_event_id == event.id
        assert log.outcome == "approve"
        assert log.payment_policy_version == "chainpay_v1.0"
        assert log.input_snapshot["amount"] == 1000

    def test_decision_can_access_linked_event_via_relationship(self, db_session: Session):
        """Verify that the ORM relationship works for navigating from decision to event."""
        event = record_audit_event(
            db_session,
            event_type="payment_processed",
            actor_type="system",
            payment_id="pay_xyz",
            shipment_id="ship_xyz",
        )

        log = record_decision_log(
            db_session,
            decision_type="settlement_decision",
            outcome="settle",
            audit_event_id=event.id,
        )

        # Refresh to ensure relationship is loaded
        db_session.refresh(log)

        assert log.audit_event is not None
        assert log.audit_event.id == event.id
        assert log.audit_event.event_type == "payment_processed"
        assert log.audit_event.payment_id == "pay_xyz"

    def test_event_can_access_linked_decisions_via_relationship(self, db_session: Session):
        """Verify that the ORM relationship works for navigating from event to decisions."""
        event = record_audit_event(
            db_session,
            event_type="multi_decision_event",
            actor_type="system",
        )

        # Create multiple decisions for the same event
        log1 = record_decision_log(
            db_session,
            decision_type="risk_check",
            outcome="pass",
            audit_event_id=event.id,
        )
        log2 = record_decision_log(
            db_session,
            decision_type="compliance_check",
            outcome="pass",
            audit_event_id=event.id,
        )

        # Refresh to ensure relationships are loaded
        db_session.refresh(event)

        assert len(event.decisions) == 2
        decision_ids = {d.id for d in event.decisions}
        assert log1.id in decision_ids
        assert log2.id in decision_ids
