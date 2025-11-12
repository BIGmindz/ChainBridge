"""
Payment rail abstraction layer for ChainPay v2.

This module defines the PaymentRail interface for processing settlements
through different payment providers (internal ledger, Stripe, ACH, etc.).

Smart Settlements feature:
- Determines if a payment should be released immediately or delayed
- Routes settlements through configured payment rails
- Supports multiple providers with unified interface
- Enables future integrations without changing core logic
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SettlementProvider(str, Enum):
    """Supported payment settlement providers."""

    INTERNAL_LEDGER = "internal_ledger"
    STRIPE = "stripe"
    ACH = "ach"
    WIRE = "wire"


class ReleaseStrategy(str, Enum):
    """Payment release timing strategy."""

    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    MANUAL_REVIEW = "manual_review"
    PENDING = "pending"


@dataclass
class SettlementResult:
    """Result of a settlement processing attempt."""

    success: bool
    provider: SettlementProvider
    reference_id: Optional[str] = None
    message: str = ""
    error: Optional[str] = None
    released_at: Optional[datetime] = None


class PaymentRail(ABC):
    """
    Abstract base class for payment settlement rails.

    Each implementation handles settlement processing through a specific provider,
    e.g., internal ledger, Stripe, ACH, etc. Subclasses must implement the
    process_settlement() method.
    """

    @abstractmethod
    def process_settlement(
        self,
        milestone_id: int,
        amount: float,
        currency: str,
        recipient_id: Optional[str] = None,
    ) -> SettlementResult:
        """
        Process a settlement through the payment rail.

        Args:
            milestone_id: ID of the MilestoneSettlement record
            amount: Settlement amount in the specified currency
            currency: ISO 4217 currency code (e.g., 'USD')
            recipient_id: Optional recipient identifier (e.g., wallet address, bank account)

        Returns:
            SettlementResult with success status and transaction details
        """
        pass

    def get_provider(self) -> SettlementProvider:
        """
        Return the provider this rail handles.

        Returns:
            SettlementProvider enum value
        """
        raise NotImplementedError


class InternalLedgerRail(PaymentRail):
    """
    Internal ledger payment rail for ChainBridge.

    Represents an internal accounting system that tracks settlements
    within the ChainBridge ecosystem without external payment processing.

    Future enhancement: Connect to distributed ledger or blockchain
    for immutable settlement recording.
    """

    def __init__(self, db: Session):
        """
        Initialize internal ledger rail.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def process_settlement(
        self,
        milestone_id: int,
        amount: float,
        currency: str,
        recipient_id: Optional[str] = None,
    ) -> SettlementResult:
        """
        Process settlement through internal ledger.

        In v2, this:
        1. Records the settlement in internal ledger tables
        2. Marks the milestone as APPROVED
        3. Generates a reference ID
        4. Logs the transaction for audit

        Args:
            milestone_id: ID of the MilestoneSettlement record
            amount: Settlement amount
            currency: Currency code
            recipient_id: Optional recipient identifier

        Returns:
            SettlementResult indicating success
        """
        from .models import MilestoneSettlement as MilestoneSettlementModel

        try:
            milestone = self.db.query(MilestoneSettlementModel).filter(MilestoneSettlementModel.id == milestone_id).first()

            if not milestone:
                return SettlementResult(
                    success=False,
                    provider=SettlementProvider.INTERNAL_LEDGER,
                    error=f"Milestone {milestone_id} not found",
                    message="Settlement failed: milestone not found",
                )

            # Generate reference ID (INTERNAL_LEDGER:timestamp:milestone_id)
            reference_id = f"INTERNAL_LEDGER:{datetime.utcnow().isoformat()}:{milestone_id}"

            # Mark milestone as APPROVED (v2: will be marked SETTLED when funds actually transfer)
            from .models import PaymentStatus

            milestone.status = PaymentStatus.APPROVED
            milestone.reference = reference_id

            self.db.add(milestone)
            self.db.commit()
            self.db.refresh(milestone)

            logger.info(
                f"Internal ledger settlement approved: milestone_id={milestone_id}, "
                f"amount={amount} {currency}, reference={reference_id}"
            )

            return SettlementResult(
                success=True,
                provider=SettlementProvider.INTERNAL_LEDGER,
                reference_id=reference_id,
                message=f"Settlement approved: {amount} {currency}",
                released_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Internal ledger settlement failed: milestone_id={milestone_id}, error={str(e)}")
            return SettlementResult(
                success=False,
                provider=SettlementProvider.INTERNAL_LEDGER,
                error=str(e),
                message="Settlement processing failed",
            )

    def get_provider(self) -> SettlementProvider:
        """Return the provider this rail handles."""
        return SettlementProvider.INTERNAL_LEDGER


def should_release_now(risk_score: float, event_type: str) -> ReleaseStrategy:
    """
    Determine if a payment should be released immediately or delayed based on
    risk score and event type.

    Release rules (v2 Smart Settlements):
    - LOW risk (< 0.33):
      * PICKUP_CONFIRMED: IMMEDIATE (20%)
      * POD_CONFIRMED: IMMEDIATE (70%)
      * CLAIM_WINDOW_CLOSED: IMMEDIATE (10%)

    - MEDIUM risk (0.33-0.67):
      * PICKUP_CONFIRMED: DELAYED (10%)
      * POD_CONFIRMED: IMMEDIATE (70%)
      * CLAIM_WINDOW_CLOSED: DELAYED (20%)

    - HIGH risk (> 0.67):
      * PICKUP_CONFIRMED: PENDING (0%)
      * POD_CONFIRMED: MANUAL_REVIEW (80%)
      * CLAIM_WINDOW_CLOSED: MANUAL_REVIEW (20%)

    Args:
        risk_score: Risk score from 0.0 (low risk) to 1.0 (high risk)
        event_type: Shipment event type (PICKUP_CONFIRMED, POD_CONFIRMED, CLAIM_WINDOW_CLOSED)

    Returns:
        ReleaseStrategy indicating when/how to release the payment
    """
    if risk_score < 0.33:
        # LOW RISK: All events released immediately
        return ReleaseStrategy.IMMEDIATE

    elif risk_score < 0.67:
        # MEDIUM RISK: Release immediately at POD, delay others
        if event_type == "POD_CONFIRMED":
            return ReleaseStrategy.IMMEDIATE
        else:
            return ReleaseStrategy.DELAYED

    else:
        # HIGH RISK: POD and CLAIM require manual review
        if event_type == "PICKUP_CONFIRMED":
            return ReleaseStrategy.PENDING  # Don't release yet
        else:
            return ReleaseStrategy.MANUAL_REVIEW


def get_release_delay_hours(risk_score: float, event_type: str, release_strategy: ReleaseStrategy) -> Optional[int]:
    """
    Get the number of hours to delay a payment based on strategy.

    Args:
        risk_score: Risk score
        event_type: Shipment event type
        release_strategy: The release strategy determined by should_release_now()

    Returns:
        Number of hours to delay, or None if immediate/pending
    """
    if release_strategy == ReleaseStrategy.IMMEDIATE:
        return None  # Release immediately

    elif release_strategy == ReleaseStrategy.DELAYED:
        # MEDIUM risk non-POD events: delay 24 hours
        return 24

    elif release_strategy == ReleaseStrategy.MANUAL_REVIEW:
        # HIGH risk: delay indefinitely until manual approval
        return None  # Don't auto-release

    else:  # PENDING
        return None  # Don't release yet
