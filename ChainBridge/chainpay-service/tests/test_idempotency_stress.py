"""
Idempotency and stress tests for Smart Settlements.

Tests that ensure:
- Same event sent twice creates only ONE MilestoneSettlement (unique constraint)
- No exceptions or weird database state on duplicate events
- Clean rollback behavior
- Concurrent-like scenarios are safe
"""

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import PaymentIntent, MilestoneSettlement, PaymentStatus, RiskTier


class TestIdempotencyUniqueConstraint:
    """Test idempotency via unique constraint on (payment_intent_id, event_type)."""

    def test_duplicate_event_type_creates_single_settlement(self, db_session: Session) -> None:
        """Sending same event twice should create only one settlement."""
        # Create payment intent
        intent = PaymentIntent(
            freight_token_id=501,
            amount=1000.0,
            currency="USD",
            risk_tier=RiskTier.LOW,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(intent)
        db_session.commit()

        # Create first milestone settlement
        milestone1 = MilestoneSettlement(
            payment_intent_id=intent.id,
            event_type="POD_CONFIRMED",
            amount=700.0,
            currency="USD",
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(milestone1)
        db_session.commit()

        # Try to create duplicate (same event_type)
        milestone2 = MilestoneSettlement(
            payment_intent_id=intent.id,
            event_type="POD_CONFIRMED",
            amount=700.0,
            currency="USD",
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(milestone2)

        # Should raise IntegrityError due to unique constraint
        try:
            db_session.commit()
            assert False, "Expected IntegrityError but none was raised"
        except IntegrityError:
            db_session.rollback()
            pass

        # Verify only one settlement exists
        settlements = (
            db_session.query(MilestoneSettlement)
            .filter(
                MilestoneSettlement.payment_intent_id == intent.id,
                MilestoneSettlement.event_type == "POD_CONFIRMED",
            )
            .all()
        )
        assert len(settlements) == 1

    def test_different_event_types_allow_multiple_settlements(
        self, db_session: Session
    ):
        """Different event types should allow multiple settlements for same intent."""
        intent = PaymentIntent(
            freight_token_id=502,
            amount=1000.0,
            currency="USD",
            risk_tier=RiskTier.LOW,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(intent)
        db_session.commit()

        # Create milestones for different events
        events = ["PICKUP_CONFIRMED", "POD_CONFIRMED", "CLAIM_WINDOW_CLOSED"]
        for i, event in enumerate(events):
            milestone = MilestoneSettlement(
                payment_intent_id=intent.id,
                event_type=event,
                amount=1000.0 * (0.2 if i == 0 else 0.7 if i == 1 else 0.1),
                currency="USD",
                status=PaymentStatus.PENDING,
                created_at=datetime.utcnow(),
            )
            db_session.add(milestone)
        db_session.commit()

        # Verify all three settlements exist
        settlements = (
            db_session.query(MilestoneSettlement)
            .filter(MilestoneSettlement.payment_intent_id == intent.id)
            .all()
        )
        assert len(settlements) == 3

    def test_duplicate_event_different_intent_allowed(self, db_session: Session) -> None:
        """Same event type can exist in different payment intents."""
        # Create two intents
        intent1 = PaymentIntent(
            freight_token_id=503,
            amount=1000.0,
            currency="USD",
            risk_tier=RiskTier.LOW,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        intent2 = PaymentIntent(
            freight_token_id=504,
            amount=2000.0,
            currency="USD",
            risk_tier=RiskTier.MEDIUM,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add_all([intent1, intent2])
        db_session.commit()

        # Create same event for both intents
        milestone1 = MilestoneSettlement(
            payment_intent_id=intent1.id,
            event_type="POD_CONFIRMED",
            amount=700.0,
            currency="USD",
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        milestone2 = MilestoneSettlement(
            payment_intent_id=intent2.id,
            event_type="POD_CONFIRMED",
            amount=1600.0,
            currency="USD",
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add_all([milestone1, milestone2])
        db_session.commit()

        # Both should exist
        settlements = (
            db_session.query(MilestoneSettlement)
            .filter(MilestoneSettlement.event_type == "POD_CONFIRMED")
            .all()
        )
        assert len(settlements) == 2


class TestIdempotencyStatusUpdates:
    """Test that status updates are handled safely with duplicates."""

    def test_duplicate_event_with_different_status_fails(self, db_session: Session) -> None:
        """Cannot create duplicate event with different status (unique constraint)."""
        intent = PaymentIntent(
            freight_token_id=505,
            amount=1000.0,
            currency="USD",
            risk_tier=RiskTier.LOW,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(intent)
        db_session.commit()

        # Create first settlement with PENDING status
        milestone1 = MilestoneSettlement(
            payment_intent_id=intent.id,
            event_type="POD_CONFIRMED",
            amount=700.0,
            currency="USD",
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(milestone1)
        db_session.commit()

        # Try to create duplicate with different status
        milestone2 = MilestoneSettlement(
            payment_intent_id=intent.id,
            event_type="POD_CONFIRMED",
            amount=700.0,
            currency="USD",
            status=PaymentStatus.APPROVED,
            created_at=datetime.utcnow(),
        )
        db_session.add(milestone2)

        try:
            db_session.commit()
            assert False, "Expected IntegrityError"
        except IntegrityError:
            db_session.rollback()
            pass

        # Original should still have PENDING status
        settlement = (
            db_session.query(MilestoneSettlement)
            .filter(
                MilestoneSettlement.payment_intent_id == intent.id,
                MilestoneSettlement.event_type == "POD_CONFIRMED",
            )
            .first()
        )
        assert settlement.status == PaymentStatus.PENDING


class TestStressMultipleMilestones:
    """Stress tests with many milestones."""

    def test_create_many_milestones_for_single_intent(self, db_session: Session) -> None:
        """Should handle creating many different milestones for single intent."""
        intent = PaymentIntent(
            freight_token_id=506,
            amount=10000.0,
            currency="USD",
            risk_tier=RiskTier.LOW,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(intent)
        db_session.commit()

        # Create 100 different event type settlements
        for i in range(100):
            milestone = MilestoneSettlement(
                payment_intent_id=intent.id,
                event_type=f"EVENT_{i:03d}",
                amount=100.0,
                currency="USD",
                status=PaymentStatus.PENDING,
                created_at=datetime.utcnow(),
            )
            db_session.add(milestone)
        db_session.commit()

        # Verify all 100 exist
        settlements = (
            db_session.query(MilestoneSettlement)
            .filter(MilestoneSettlement.payment_intent_id == intent.id)
            .all()
        )
        assert len(settlements) == 100

    def test_create_many_intents_with_same_event_type(self, db_session: Session) -> None:
        """Should handle many intents each with same event type."""
        # Create 50 payment intents
        intents = []
        for i in range(50):
            intent = PaymentIntent(
                freight_token_id=600 + i,
                amount=1000.0,
                currency="USD",
                risk_tier=RiskTier.LOW,
                status=PaymentStatus.PENDING,
                created_at=datetime.utcnow(),
            )
            intents.append(intent)
        db_session.add_all(intents)
        db_session.commit()

        # Create POD_CONFIRMED milestone for each
        for intent in intents:
            milestone = MilestoneSettlement(
                payment_intent_id=intent.id,
                event_type="POD_CONFIRMED",
                amount=700.0,
                currency="USD",
                status=PaymentStatus.PENDING,
                created_at=datetime.utcnow(),
            )
            db_session.add(milestone)
        db_session.commit()

        # Verify all 50 POD_CONFIRMED settlements exist
        settlements = (
            db_session.query(MilestoneSettlement)
            .filter(MilestoneSettlement.event_type == "POD_CONFIRMED")
            .all()
        )
        assert len(settlements) == 50


class TestIdempotencyDataIntegrity:
    """Test data integrity under idempotency constraints."""

    def test_payment_intent_amount_unchanged_after_duplicate_attempt(
        self, db_session: Session
    ):
        """Payment intent amount should not be modified by duplicate settlement attempt."""
        original_amount = 1000.0
        intent = PaymentIntent(
            freight_token_id=507,
            amount=original_amount,
            currency="USD",
            risk_tier=RiskTier.LOW,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(intent)
        db_session.commit()

        # Create settlement
        milestone1 = MilestoneSettlement(
            payment_intent_id=intent.id,
            event_type="POD_CONFIRMED",
            amount=700.0,
            currency="USD",
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(milestone1)
        db_session.commit()

        # Try to create duplicate
        milestone2 = MilestoneSettlement(
            payment_intent_id=intent.id,
            event_type="POD_CONFIRMED",
            amount=700.0,
            currency="USD",
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(milestone2)

        try:
            db_session.commit()
        except IntegrityError:
            db_session.rollback()

        # Refresh and verify amount unchanged
        db_session.refresh(intent)
        assert intent.amount == original_amount

    def test_multiple_settlements_amounts_sum_correctly(self, db_session: Session) -> None:
        """Multiple settlements for same intent should track individual amounts."""
        total_intent_amount = 1000.0
        intent = PaymentIntent(
            freight_token_id=508,
            amount=total_intent_amount,
            currency="USD",
            risk_tier=RiskTier.LOW,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(intent)
        db_session.commit()

        # Create three settlements (20/70/10 split)
        settlement_amounts = [200.0, 700.0, 100.0]
        for i, (event, amount) in enumerate(
            zip(
                ["PICKUP_CONFIRMED", "POD_CONFIRMED", "CLAIM_WINDOW_CLOSED"],
                settlement_amounts,
            )
        ):
            milestone = MilestoneSettlement(
                payment_intent_id=intent.id,
                event_type=event,
                amount=amount,
                currency="USD",
                status=PaymentStatus.PENDING,
                created_at=datetime.utcnow(),
            )
            db_session.add(milestone)
        db_session.commit()

        # Verify sum of settlements equals intent amount
        settlements = (
            db_session.query(MilestoneSettlement)
            .filter(MilestoneSettlement.payment_intent_id == intent.id)
            .all()
        )
        total_settled = sum(s.amount for s in settlements)
        assert abs(total_settled - total_intent_amount) < 0.01
