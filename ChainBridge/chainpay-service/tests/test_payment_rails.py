"""
Unit tests for PaymentRail abstraction and InternalLedgerRail implementation.

Tests:
- InternalLedgerRail.process_settlement() executes successfully
- SettlementResult is properly structured and populated
- Reference IDs are generated in the correct format (INTERNAL_LEDGER:timestamp:id)
- Settlement provider is correctly identified
- Edge cases (zero amounts, missing fields) are handled gracefully
"""

from datetime import datetime
from sqlalchemy.orm import Session

from app.payment_rails import InternalLedgerRail, SettlementResult, SettlementProvider
from app.models import MilestoneSettlement, PaymentStatus


class TestInternalLedgerRailBasicExecution:
    """Test basic execution of InternalLedgerRail.process_settlement()."""

    def test_process_settlement_returns_settlement_result(self, db_session: Session) -> None:
        """process_settlement() should return a SettlementResult object."""
        rail = InternalLedgerRail(db_session)

        result = rail.process_settlement(
            milestone_id=1,
            amount=100.0,
            currency="USD",
            recipient_id="user_123",
        )

        assert isinstance(result, SettlementResult)

    def test_process_settlement_success_is_true(self, db_session: Session) -> None:
        """process_settlement() should return success=True."""
        rail = InternalLedgerRail(db_session)

        result = rail.process_settlement(
            milestone_id=1,
            amount=100.0,
            currency="USD",
            recipient_id="user_123",
        )

        assert result.success is True

    def test_process_settlement_provider_internal_ledger(self, db_session: Session) -> None:
        """process_settlement() should set provider to INTERNAL_LEDGER."""
        rail = InternalLedgerRail(db_session)

        result = rail.process_settlement(
            milestone_id=1,
            amount=100.0,
            currency="USD",
            recipient_id="user_123",
        )

        assert result.provider == SettlementProvider.INTERNAL_LEDGER

    def test_process_settlement_has_reference_id(self, db_session: Session) -> None:
        """process_settlement() should generate a reference_id."""
        rail = InternalLedgerRail(db_session)

        result = rail.process_settlement(
            milestone_id=42,
            amount=100.0,
            currency="USD",
            recipient_id="user_123",
        )

        assert result.reference_id is not None
        assert isinstance(result.reference_id, str)

    def test_process_settlement_reference_format(self, db_session: Session) -> None:
        """process_settlement() reference_id should follow INTERNAL_LEDGER:timestamp:id format."""
        rail = InternalLedgerRail(db_session)
        milestone_id = 99

        result = rail.process_settlement(
            milestone_id=milestone_id,
            amount=100.0,
            currency="USD",
            recipient_id="user_123",
        )

        ref_id = result.reference_id
        assert ref_id.startswith("INTERNAL_LEDGER:")
        parts = ref_id.split(":")
        assert len(parts) == 3
        assert parts[0] == "INTERNAL_LEDGER"
        assert parts[2] == str(milestone_id)


class TestSettlementResultStructure:
    """Test the SettlementResult dataclass structure and fields."""

    def test_settlement_result_has_success_field(self, db_session: Session) -> None:
        """SettlementResult should have success field."""
        rail = InternalLedgerRail(db_session)
        result = rail.process_settlement(1, 100.0, "USD")

        assert hasattr(result, "success")
        assert isinstance(result.success, bool)

    def test_settlement_result_has_provider_field(self, db_session: Session) -> None:
        """SettlementResult should have provider field."""
        rail = InternalLedgerRail(db_session)
        result = rail.process_settlement(1, 100.0, "USD")

        assert hasattr(result, "provider")
        assert isinstance(result.provider, SettlementProvider)

    def test_settlement_result_has_reference_id_field(self, db_session: Session) -> None:
        """SettlementResult should have reference_id field."""
        rail = InternalLedgerRail(db_session)
        result = rail.process_settlement(1, 100.0, "USD")

        assert hasattr(result, "reference_id")

    def test_settlement_result_has_message_field(self, db_session: Session) -> None:
        """SettlementResult should have message field."""
        rail = InternalLedgerRail(db_session)
        result = rail.process_settlement(1, 100.0, "USD")

        assert hasattr(result, "message")

    def test_settlement_result_has_error_field(self, db_session: Session) -> None:
        """SettlementResult should have error field."""
        rail = InternalLedgerRail(db_session)
        result = rail.process_settlement(1, 100.0, "USD")

        assert hasattr(result, "error")
        assert result.error is None  # No error on success

    def test_settlement_result_has_released_at_field(self, db_session: Session) -> None:
        """SettlementResult should have released_at field."""
        rail = InternalLedgerRail(db_session)
        result = rail.process_settlement(1, 100.0, "USD")

        assert hasattr(result, "released_at")
        assert isinstance(result.released_at, datetime)


class TestSettlementAmountHandling:
    """Test handling of various settlement amounts."""

    def test_process_settlement_zero_amount(self, db_session: Session) -> None:
        """process_settlement() should handle zero amount."""
        rail = InternalLedgerRail(db_session)

        result = rail.process_settlement(
            milestone_id=1,
            amount=0.0,
            currency="USD",
        )

        assert result.success is True

    def test_process_settlement_large_amount(self, db_session: Session) -> None:
        """process_settlement() should handle large amounts."""
        rail = InternalLedgerRail(db_session)

        result = rail.process_settlement(
            milestone_id=1,
            amount=999999999.99,
            currency="USD",
        )

        assert result.success is True

    def test_process_settlement_fractional_amount(self, db_session: Session) -> None:
        """process_settlement() should handle fractional amounts."""
        rail = InternalLedgerRail(db_session)

        result = rail.process_settlement(
            milestone_id=1,
            amount=123.456,
            currency="USD",
        )

        assert result.success is True

    def test_process_settlement_negative_amount(self, db_session: Session) -> None:
        """process_settlement() should handle negative amounts (refunds)."""
        rail = InternalLedgerRail(db_session)

        result = rail.process_settlement(
            milestone_id=1,
            amount=-50.0,
            currency="USD",
        )

        assert result.success is True


class TestSettlementCurrencyHandling:
    """Test handling of various currencies."""

    def test_process_settlement_usd_currency(self, db_session: Session) -> None:
        """process_settlement() should handle USD currency."""
        rail = InternalLedgerRail(db_session)

        result = rail.process_settlement(
            milestone_id=1,
            amount=100.0,
            currency="USD",
        )

        assert result.success is True

    def test_process_settlement_eur_currency(self, db_session: Session) -> None:
        """process_settlement() should handle EUR currency."""
        rail = InternalLedgerRail(db_session)

        result = rail.process_settlement(
            milestone_id=1,
            amount=100.0,
            currency="EUR",
        )

        assert result.success is True

    def test_process_settlement_gbp_currency(self, db_session: Session) -> None:
        """process_settlement() should handle GBP currency."""
        rail = InternalLedgerRail(db_session)

        result = rail.process_settlement(
            milestone_id=1,
            amount=100.0,
            currency="GBP",
        )

        assert result.success is True


class TestSettlementWithMilestoneDatabase:
    """Test process_settlement() with actual MilestoneSettlement records."""

    def test_process_settlement_updates_milestone_status(self, db_session: Session) -> None:
        """process_settlement() should update milestone status to APPROVED."""
        # Create a milestone
        milestone = MilestoneSettlement(
            payment_intent_id=1,
            event_type="POD_CONFIRMED",
            amount=100.0,
            currency="USD",
            status=PaymentStatus.PENDING,
        )
        db_session.add(milestone)
        db_session.commit()

        # Process settlement
        rail = InternalLedgerRail(db_session)
        result = rail.process_settlement(
            milestone_id=milestone.id,
            amount=100.0,
            currency="USD",
        )

        assert result.success is True

        # Verify milestone was updated
        db_session.refresh(milestone)
        assert milestone.status == PaymentStatus.APPROVED

    def test_process_settlement_sets_reference_on_milestone(self, db_session: Session) -> None:
        """process_settlement() should set reference on milestone."""
        milestone = MilestoneSettlement(
            payment_intent_id=1,
            event_type="POD_CONFIRMED",
            amount=100.0,
            currency="USD",
            status=PaymentStatus.PENDING,
        )
        db_session.add(milestone)
        db_session.commit()

        rail = InternalLedgerRail(db_session)
        result = rail.process_settlement(
            milestone_id=milestone.id,
            amount=100.0,
            currency="USD",
        )

        db_session.refresh(milestone)
        assert milestone.reference == result.reference_id

    def test_process_settlement_sets_provider_on_milestone(self, db_session: Session) -> None:
        """process_settlement() should set provider on milestone."""
        milestone = MilestoneSettlement(
            payment_intent_id=1,
            event_type="POD_CONFIRMED",
            amount=100.0,
            currency="USD",
            status=PaymentStatus.PENDING,
        )
        db_session.add(milestone)
        db_session.commit()

        rail = InternalLedgerRail(db_session)
        rail.process_settlement(
            milestone_id=milestone.id,
            amount=100.0,
            currency="USD",
        )

        db_session.refresh(milestone)
        assert milestone.provider == "INTERNAL_LEDGER"


class TestSettlementWithOptionalRecipient:
    """Test process_settlement() with and without recipient_id."""

    def test_process_settlement_without_recipient(self, db_session: Session) -> None:
        """process_settlement() should work without recipient_id."""
        rail = InternalLedgerRail(db_session)

        result = rail.process_settlement(
            milestone_id=1,
            amount=100.0,
            currency="USD",
        )

        assert result.success is True

    def test_process_settlement_with_recipient(self, db_session: Session) -> None:
        """process_settlement() should work with recipient_id."""
        rail = InternalLedgerRail(db_session)

        result = rail.process_settlement(
            milestone_id=1,
            amount=100.0,
            currency="USD",
            recipient_id="0x123abc",
        )

        assert result.success is True

    def test_process_settlement_with_empty_recipient(self, db_session: Session) -> None:
        """process_settlement() should handle empty string recipient_id."""
        rail = InternalLedgerRail(db_session)

        result = rail.process_settlement(
            milestone_id=1,
            amount=100.0,
            currency="USD",
            recipient_id="",
        )

        assert result.success is True


class TestMultipleSettlements:
    """Test processing multiple settlements in sequence."""

    def test_multiple_settlements_same_rail_instance(self, db_session: Session) -> None:
        """Multiple settlements through same rail instance should work."""
        rail = InternalLedgerRail(db_session)

        results = []
        for i in range(5):
            result = rail.process_settlement(
                milestone_id=i + 1,
                amount=100.0 * (i + 1),
                currency="USD",
            )
            results.append(result)

        # All should succeed
        assert all(r.success for r in results)

        # All should have unique reference IDs
        ref_ids = [r.reference_id for r in results]
        assert len(set(ref_ids)) == len(ref_ids)  # All unique

    def test_multiple_settlements_different_currencies(self, db_session: Session) -> None:
        """Multiple settlements with different currencies should work."""
        rail = InternalLedgerRail(db_session)
        currencies = ["USD", "EUR", "GBP", "JPY", "CHF"]

        results = []
        for i, currency in enumerate(currencies):
            result = rail.process_settlement(
                milestone_id=i + 1,
                amount=100.0,
                currency=currency,
            )
            results.append(result)

        assert all(r.success for r in results)
