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

# CODEX SYSTEM BRIEFING - CHAINBRIDGE MILESTONE IDENTITY + PROOFPACK V1.5
# You are hardening the payment + settlement identity model for ChainBridge.
#
# ChainBridge Mantra:
#   - No hacks, no lies, no shortcuts.
#   - IDs must be canonical, test-covered, and consistent across models, SSE, and APIs.
#
# High-level objectives:
# 1) Define and enforce a canonical milestone_id format across ChainPay, queue envelopes, and SSE.
# 2) Make the ProofPack endpoint pull from real payment milestone data, clearly labeling mock sections.
# 3) Enrich payment_state_changed events with truthful proofpack_hint metadata.

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.services.payout_engine import PayoutSchedule, get_payout_schedule

logger = logging.getLogger(__name__)

try:
    from core.payments.identity import (
        canonical_milestone_id,
        canonical_shipment_reference,
    )
except ModuleNotFoundError:  # pragma: no cover - defensive for isolated unit tests

    def canonical_milestone_id(shipment_reference: str, index: int) -> str:  # type: ignore[override]
        """
        Fallback milestone ID builder used when core ID helpers are unavailable.
        Always returns a non-empty canonical milestone identifier.
        """
        return f"{shipment_reference}-M{index}"

    def canonical_shipment_reference(
        shipment_reference: Optional[str] = None,
        freight_token_id: Optional[int] = None,
    ) -> str:  # type: ignore[override]
        """
        Fallback shipment reference builder used when core ID helpers are unavailable.
        Always returns a non-empty reference.
        """
        if shipment_reference:
            return shipment_reference
        if freight_token_id is not None:
            return f"FTK-{freight_token_id}"
        return "SHP-UNKNOWN"


def _safe_get(obj: Any, key: str, default: Any = 0.0) -> Any:
    """
    Return obj[key] if obj is a dict-like, otherwise if obj is numeric return it
    (useful when upstream sometimes returns a raw float). Otherwise return default.
    """
    from numbers import Number

    if isinstance(obj, dict):
        return obj.get(key, default)
    if isinstance(obj, Number):
        # treat the numeric as the desired value
        try:
            return obj if isinstance(obj, (int, float)) else float(str(obj))
        except (ValueError, TypeError):
            return default
    return default


class SettlementProvider(str, Enum):
    """Supported payment settlement providers.

    Provider identifiers intentionally align with audit/event payloads so
    downstream analytics can attribute settlements to the correct rail.
    """

    INTERNAL_LEDGER = "INTERNAL_LEDGER"
    CB_USDX = "CB_USDX"
    STRIPE = "STRIPE"
    ACH = "ACH"
    WIRE = "WIRE"


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


@dataclass(frozen=True)
class MilestoneReleasePlan:
    """Computed payout plan for a specific milestone event."""

    event_type: str
    risk_band: str
    percentage: float  # Stored as a percentage value (e.g., 20.0 for 20%)
    release_amount: float
    strategy: ReleaseStrategy
    delay_hours: Optional[int] = None
    claim_window_days: Optional[int] = None
    requires_manual_review: bool = False
    corridor_id: str = "USD_MXN"

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "risk_band": self.risk_band,
            "percentage": self.percentage,
            "release_amount": self.release_amount,
            "strategy": self.strategy.value,
            "delay_hours": self.delay_hours,
            "claim_window_days": self.claim_window_days,
            "requires_manual_review": self.requires_manual_review,
            "corridor_id": self.corridor_id,
        }


_DEFAULT_RISK_BAND = "MEDIUM"
_DEFAULT_CORRIDOR_ID = "USD_MXN"
_PAYOUT_EVENTS = {"pickup_confirmed", "mid_transit_verified", "settlement_released"}
_EVENT_ALIASES = {
    "pod_confirmed": "mid_transit_verified",
    "claim_window_closed": "settlement_released",
    "delivery_confirmed": "settlement_released",
}
_EVENT_STAGE = {
    "pickup_confirmed": "pickup",
    "mid_transit_verified": "delivered",
    "settlement_released": "claim",
}


def _normalize_event_type(event_type: str) -> str:
    key = (event_type or "").strip().lower()
    return _EVENT_ALIASES.get(key, key)


def _normalize_risk_band(risk_band: Optional[str]) -> str:
    if not risk_band:
        return _DEFAULT_RISK_BAND
    normalized = risk_band.upper()
    if normalized not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        return _DEFAULT_RISK_BAND
    return normalized


def _risk_band_from_score(risk_score: float) -> str:
    if risk_score >= 0.85:
        return "CRITICAL"
    if risk_score >= 0.65:
        return "HIGH"
    if risk_score >= 0.35:
        return "MEDIUM"
    return "LOW"


def compute_milestone_release(
    *,
    risk_band: Optional[str] = None,
    event_type: str,
    base_total_amount: float,
    risk_score: Optional[float] = None,
    corridor_id: str = _DEFAULT_CORRIDOR_ID,
) -> MilestoneReleasePlan:
    """Return the release plan for a milestone given risk inputs + event."""

    normalized_event = _normalize_event_type(event_type)

    if normalized_event not in _PAYOUT_EVENTS:
        return MilestoneReleasePlan(
            event_type=normalized_event,
            risk_band=_normalize_risk_band(risk_band),
            percentage=0.0,
            release_amount=0.0,
            strategy=ReleaseStrategy.PENDING,
        )

    # Prefer risk_score mapping; fallback to risk_band override.
    try:
        schedule: PayoutSchedule
        if risk_score is not None:
            schedule = get_payout_schedule(corridor_id, risk_score)
        else:
            schedule = get_payout_schedule(corridor_id, 0.0, override_tier=_normalize_risk_band(risk_band))
    except Exception:
        fallback_band = _normalize_risk_band(risk_band) or _DEFAULT_RISK_BAND
        schedule = get_payout_schedule(_DEFAULT_CORRIDOR_ID, 0.0, override_tier=fallback_band)

    stage = _EVENT_STAGE[normalized_event]
    percent_map = {
        "pickup": schedule.pickup_percent,
        "delivered": schedule.delivered_percent,
        "claim": schedule.claim_percent,
    }
    percentage_raw = float(percent_map.get(stage, 0.0))

    strategy = ReleaseStrategy.IMMEDIATE
    delay_hours: Optional[int] = None

    if schedule.freeze_all_payouts:
        strategy = ReleaseStrategy.MANUAL_REVIEW
    elif schedule.requires_manual_review and stage == "claim":
        strategy = ReleaseStrategy.MANUAL_REVIEW
    elif stage == "claim" and schedule.claim_window_days > 0:
        strategy = ReleaseStrategy.DELAYED
        delay_hours = schedule.claim_window_days * 24

    total_amount = float(max(base_total_amount, 0.0))
    release_amount = round(total_amount * percentage_raw, 2)

    return MilestoneReleasePlan(
        event_type=normalized_event,
        risk_band=schedule.risk_tier,
        percentage=round(percentage_raw * 100, 2),
        release_amount=release_amount,
        strategy=strategy,
        delay_hours=delay_hours,
        claim_window_days=schedule.claim_window_days,
        requires_manual_review=schedule.requires_manual_review,
        corridor_id=corridor_id,
    )


class PaymentRail(ABC):
    """Abstract payment rail contract.

    Rails unify how ChainPay settles milestones, allowing swaps between
    InternalLedgerRail and future assets (e.g., CB-USDx) without touching
    business logic. See CHAINPAY_ONCHAIN_SETTLEMENT.md and
    CHAINPAY_CB_USDX_PRODUCT_MAP.md for the on-chain evolution.
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
        """Return the provider this rail handles.

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
        from .models import PaymentScheduleItem as PaymentScheduleItemModel

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

            old_status = milestone.status.value if milestone.status else "unknown"
            milestone.status = PaymentStatus.APPROVED
            milestone.reference = reference_id

            self.db.add(milestone)
            self.db.commit()
            self.db.refresh(milestone)

            payment_intent = milestone.payment_intent
            freight_token_id = milestone.freight_token_id or (payment_intent.freight_token_id if payment_intent else None)
            shipment_ref = milestone.shipment_reference
            if not shipment_ref:
                from core.payments.identity import canonical_shipment_reference
                try:
                    shipment_ref = canonical_shipment_reference(
                        shipment_reference=(getattr(payment_intent, "shipment_reference", None) if payment_intent else None),
                        freight_token_id=freight_token_id,
                    )
                except ValueError:
                    shipment_ref = f"SHP-{milestone.payment_intent_id:04d}"

            milestone_index = 1
            if milestone.schedule_item_id:
                schedule_item = (
                    self.db.query(PaymentScheduleItemModel).filter(PaymentScheduleItemModel.id == milestone.schedule_item_id).first()
                )
                if schedule_item and schedule_item.sequence:
                    milestone_index = schedule_item.sequence

            canonical_id = milestone.milestone_identifier or canonical_milestone_id(shipment_ref, milestone_index)
            milestone.milestone_identifier = canonical_id
            milestone.shipment_reference = shipment_ref
            milestone.freight_token_id = freight_token_id
            proofpack_hint = {
                "milestone_id": canonical_id,
                "has_proofpack": True,
                "version": "v1-alpha",
            }

            logger.info(
                f"Internal ledger settlement approved: milestone_id={milestone_id}, "
                f"amount={amount} {currency}, reference={reference_id}"
            )

            # Emit real-time payment event
            try:
                from .realtime_events import _emit_payment_event

                _emit_payment_event(
                    shipment_reference=shipment_ref,
                    milestone_id=canonical_id,
                    milestone_name=milestone.event_type.replace("_", " ").title(),
                    from_state=old_status,
                    to_state="approved",
                    amount=amount,
                    currency=currency,
                    reason="Low risk shipment - immediate release",
                    freight_token_id=freight_token_id,
                    proofpack_hint=proofpack_hint,
                )
            except Exception as emit_err:
                # Never fail settlement due to event emission issues
                logger.warning(f"Failed to emit payment event for milestone {milestone_id}: {emit_err}")

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


class CbUsdxRail(PaymentRail):
    """CB-USDx payment rail (V1 stub).

    V1 behavior: no real XRPL calls. We tag settlements as CB-USDx and
    finalize them in the internal ledger tables so audit and analytics
    flows can consume rail metadata. Future PACs will replace the stubbed
    ledger write with actual on-chain submission as defined in
    CHAINPAY_ONCHAIN_SETTLEMENT.md.
    """

    def __init__(self, db: Session):
        self.db = db

    def process_settlement(
        self,
        milestone_id: int,
        amount: float,
        currency: str,
        recipient_id: Optional[str] = None,
    ) -> SettlementResult:
        from .models import MilestoneSettlement as MilestoneSettlementModel
        from .models import PaymentScheduleItem as PaymentScheduleItemModel
        from .models import PaymentStatus

        try:
            milestone = self.db.query(MilestoneSettlementModel).filter(MilestoneSettlementModel.id == milestone_id).first()

            if not milestone:
                return SettlementResult(
                    success=False,
                    provider=SettlementProvider.CB_USDX,
                    error=f"Milestone {milestone_id} not found",
                    message="Settlement failed: milestone not found",
                )

            reference_id = f"CB_USDX:{datetime.utcnow().isoformat()}:{milestone_id}"

            old_status = milestone.status.value if milestone.status else "unknown"
            milestone.status = PaymentStatus.APPROVED
            milestone.provider = SettlementProvider.CB_USDX.value
            milestone.reference = reference_id

            # Maintain canonical identifiers for downstream analytics
            payment_intent = milestone.payment_intent
            freight_token_id = milestone.freight_token_id or (payment_intent.freight_token_id if payment_intent else None)
            shipment_ref = milestone.shipment_reference or (getattr(payment_intent, "shipment_reference", None) if payment_intent else None)
            if not shipment_ref:
                try:
                    shipment_ref = canonical_shipment_reference(
                        shipment_reference=(getattr(payment_intent, "shipment_reference", None) if payment_intent else None),
                        freight_token_id=freight_token_id,
                    )
                except Exception:
                    shipment_ref = f"SHP-{milestone.payment_intent_id:04d}"

            milestone_index = 1
            if milestone.schedule_item_id:
                schedule_item = (
                    self.db.query(PaymentScheduleItemModel).filter(PaymentScheduleItemModel.id == milestone.schedule_item_id).first()
                )
                if schedule_item and schedule_item.sequence:
                    milestone_index = schedule_item.sequence

            canonical_id = milestone.milestone_identifier or canonical_milestone_id(shipment_ref, milestone_index)
            milestone.milestone_identifier = canonical_id
            milestone.shipment_reference = shipment_ref
            milestone.freight_token_id = freight_token_id

            self.db.add(milestone)
            self.db.commit()
            self.db.refresh(milestone)

            logger.info(
                "CB-USDx stub settlement approved: milestone_id=%s, amount=%s %s, reference=%s",
                milestone_id,
                amount,
                currency,
                reference_id,
            )

            proofpack_hint = {
                "milestone_id": canonical_id,
                "token_type": "CB-USDx",
                "has_proofpack": True,
                "version": "v1-alpha",
            }

            try:
                from .realtime_events import _emit_payment_event

                _emit_payment_event(
                    shipment_reference=shipment_ref,
                    milestone_id=canonical_id,
                    milestone_name=milestone.event_type.replace("_", " ").title(),
                    from_state=old_status,
                    to_state="approved",
                    amount=amount,
                    currency=currency,
                    reason="CB-USDx stub settlement",
                    freight_token_id=freight_token_id,
                    proofpack_hint=proofpack_hint,
                )
            except Exception as emit_err:
                logger.warning(f"Failed to emit CB-USDx payment event for milestone {milestone_id}: {emit_err}")

            return SettlementResult(
                success=True,
                provider=SettlementProvider.CB_USDX,
                reference_id=reference_id,
                message=f"CB-USDx settlement approved: {amount} {currency}",
                released_at=datetime.utcnow(),
            )

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "CB-USDx settlement failed: milestone_id=%s, error=%s",
                milestone_id,
                str(exc),
            )
            return SettlementResult(
                success=False,
                provider=SettlementProvider.CB_USDX,
                error=str(exc),
                message="Settlement processing failed",
            )

    def get_provider(self) -> SettlementProvider:
        return SettlementProvider.CB_USDX


def should_release_now(risk_score: float, event_type: str) -> ReleaseStrategy:
    """
    Determine if a payment should be released immediately or delayed based on
    risk score and event type.

    Args:
        risk_score: Risk score from 0.0 (low risk) to 1.0 (high risk)
        event_type: Shipment event type (PICKUP_CONFIRMED, POD_CONFIRMED, CLAIM_WINDOW_CLOSED)

    Returns:
        ReleaseStrategy indicating when/how to release the payment
    """
    normalized_event = (event_type or "").strip().upper().replace("-", "_")
    risk_score = max(0.0, min(1.0, risk_score))

    # Align with documented tiers: LOW <0.33, MEDIUM <0.67, HIGH >=0.67.
    if risk_score < 0.33:
        return ReleaseStrategy.IMMEDIATE

    if risk_score < 0.67:
        if normalized_event in {"POD_CONFIRMED", "DELIVERY_CONFIRMED"}:
            return ReleaseStrategy.IMMEDIATE
        return ReleaseStrategy.DELAYED

    # For very high scores (>=0.90) we require manual review for all events.
    if risk_score >= 0.9:
        return ReleaseStrategy.MANUAL_REVIEW

    # High tier default: gate pickup, review everything else.
    if normalized_event in {"PICKUP_CONFIRMED", "PICKUP"}:
        return ReleaseStrategy.PENDING
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
        return None

    plan = compute_milestone_release(
        risk_score=risk_score,
        event_type=event_type,
        base_total_amount=1.0,
    )
    return plan.delay_hours
