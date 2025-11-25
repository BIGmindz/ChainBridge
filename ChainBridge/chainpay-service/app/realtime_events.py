# CODEX SYSTEM BRIEFING - CHAINBRIDGE PROOFPACK V1.0
# You are implementing backend support for a real "ProofPack" object tied to payment milestones.
# ChainBridge Mantra:
#   - No hacks, no lies, no shortcuts.
#   - Everything must be type-safe, test-covered, and ready for enterprise auditors.
#   - If a field is "TODO" today, it must be explicitly and truthfully marked as such.
#
# High-level goals:
# 1) Standardize payment milestone identity across:
#    - ChainPay models (PaymentIntent, PaymentMilestone, etc.)
#    - Payment queue envelope (whatever feeds usePaymentQueue on the frontend).
#    - SSE events of type "payment_state_changed".
#
# 2) Introduce a ProofPack schema and endpoint that returns structured JSON
#    for a given milestone, with realistic placeholder fields that we can
#    later back with real ChainIQ / ChainFreight / ChainPay data.
#
# 3) Ensure all of this is covered by tests and does NOT break existing APIs
#    used by ChainBoard or the Settlements UI.
#
# TASK 1: Standardize milestone IDs and freight_token_id across the payment domain.
#
# Files to inspect:
# - chainpay-service/app/models.py        # PaymentIntent, PaymentMilestone, etc.
# - chainpay-service/app/payment_rails.py # State transitions and settlement logic.
# - api/schemas/chainboard.py             # PaymentQueue envelope / schemas (if present).
# - api/realtime/bus.py + related tests   # payment_state_changed events.
#
# Requirements:
# - Define a canonical string ID format for payment milestones:
#       "<shipment_reference>-M<index>"
#   Example: "SHP-2025-042-M1"
#
# - Extend the PaymentMilestone model to include:
#       milestone_id: str (canonical format)
#       freight_token_id: Optional[int]
#
# - Ensure the payment queue envelope (whatever is serialized to the
#   chainboard UI) includes:
#       milestone_id: str
#       freight_token_id: Optional[int]
#
# - Ensure SSE events for type "payment_state_changed" include:
#       milestone_id: str
#       shipment_reference: str
#
# - Do NOT change the external route signatures unless absolutely required.
#   Only enrich existing payloads.
#
# - Update or create tests to assert:
#       - payment_state_changed events always contain milestone_id (str)
#       - The format matches "<shipment_reference>-M<index>".
#
# After implementing:
# - Update test_payment_events.py with a test that checks this canonical ID format.
#
# TASK 2: Implement ProofPack schema and endpoint.
#
# Files to work with:
# - api/schemas/chainboard.py         # Add ProofPack Pydantic models.
# - api/routes/chainboard_payments.py # If this doesn't exist, create a dedicated router
#                                     # for chainpay-related APIs under /api/chainboard/payments.
#
# Schema:
#   class ProofPack(BaseModel):
#       milestone_id: str
#       shipment_reference: str
#       corridor: str
#       customer_name: str
#       amount: float
#       currency: str
#       state: str                      # "blocked" | "released" | "settled" | etc.
#       freight_token_id: Optional[int]
#       last_updated: datetime
#       # Nested evidence fields (placeholders today):
#       documents: List[Dict[str, Any]] # e.g. [{"type": "POD", "id": "..."}]
#       iot_signals: List[Dict[str, Any]]
#       risk_assessment: Dict[str, Any]
#       audit_trail: List[Dict[str, Any]]
#
# Important:
# - Today, populate these fields using mock or existing data, but be explicit:
#       risk_assessment["source"] = "mock"
# - Do NOT pretend we have real ML or blockchain linkage yet.
#   Always label placeholders truthfully.
#
# Endpoint:
#   GET /api/chainboard/payments/proofpack/{milestone_id}
#
# Behavior:
# - Validate that milestone_id is in the canonical format.
# - Look up the corresponding PaymentIntent/Milestone in ChainPay.
# - Return a ProofPack instance with realistic but placeholder evidence structures.
# - If not found, return 404 with a clear JSON error.
#
# Tests:
# - Create api/tests/test_proofpack_api.py with tests that:
#     - Verify 200 and correct milestone_id for a known mock milestone.
#     - Verify 404 for unknown milestone.
#     - Assert that the response includes the required top-level fields.
#
# TASK 3: Wire proofpack hints into payment_state_changed events (v1.0 stub).
#
# Goal:
# - Add an optional "proofpack_hint" to payment_state_changed events so the UI
#   can show a "Proof available" indicator even before fetching.
#
# "proofpack_hint" structure:
#   {
#       "milestone_id": str,
#       "has_proofpack": bool,   # For now, always True if the milestone exists.
#       "version": "v1-alpha"
#   }
#
# Requirements:
# - When publishing payment_state_changed, include proofpack_hint as above.
# - Update tests to assert the presence and shape of proofpack_hint.
#
# Keep this simple and honest:
# - We are NOT computing real hashes yet.
# - This is just a hint for the UI.
#
# After completing Tasks 1–3:
# - Run: python -m pytest api/tests -v -q
# - Do NOT skip tests. If something is brittle, tighten the tests instead of
#   weakening them.

# chainpay-service/app/realtime_events.py
"""
Real-Time Payment Events
=========================

Integration with ChainBoard SSE event bus for Smart Settlements.
Emits payment_state_changed events when milestones transition between states.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _emit_payment_event(
    *,
    shipment_reference: str,
    milestone_id: str,
    milestone_name: str,
    from_state: str,
    to_state: str,
    amount: float,
    currency: str = "USD",
    reason: Optional[str] = None,
    freight_token_id: Optional[int] = None,
    proofpack_hint: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Emit payment state change event to Control Tower SSE bus.

    This function is called synchronously from ChainPay service but publishes
    to the async event bus running in the main ChainBoard API server.

    Args:
        shipment_reference: Shipment ID (e.g., SHP-2025-027)
        milestone_id: Canonical milestone identifier "<shipment_reference>-M<index>"
        milestone_name: Human-readable milestone name
        from_state: Previous PaymentStatus value
        to_state: New PaymentStatus value
        amount: Settlement amount
        currency: ISO 4217 currency code
        reason: Optional reason for state change
        freight_token_id: Optional freight token correlation identifier
        proofpack_hint: Optional structure indicating proofpack availability
    """
    try:
        # Import here to avoid circular dependencies
        # ChainBoard realtime bus is available if running in the same process
        try:
            from api.realtime.bus import publish_event

            # Map state transitions to event kinds
            event_kind = _map_transition_to_event_kind(from_state, to_state)

            # Build payload
            payload = {
                "event_kind": event_kind,
                "shipment_reference": shipment_reference,
                "milestone_id": milestone_id,
                "milestone_name": milestone_name,
                "from_state": from_state,
                "to_state": to_state,
                "amount": amount,
                "currency": currency,
            }

            if reason:
                payload["reason"] = reason
            if freight_token_id is not None:
                payload["freight_token_id"] = freight_token_id
            if proofpack_hint is not None:
                payload["proofpack_hint"] = proofpack_hint

            # Publish event (fire-and-forget in background)
            # Use asyncio.create_task if we have an event loop, otherwise skip
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(
                        publish_event(
                            type="payment_state_changed",
                            source="payments",
                            key=shipment_reference,
                            payload=payload,
                        )
                    )
                    logger.info(
                        f"Payment event published: {shipment_reference} milestone {milestone_id} "
                        f"{from_state} → {to_state}"
                    )
                else:
                    # No event loop - likely in tests or standalone ChainPay
                    logger.debug(
                        f"Skipping payment event (no event loop): {shipment_reference} "
                        f"{from_state} → {to_state}"
                    )
            except RuntimeError:
                # No event loop - likely in tests or standalone ChainPay
                logger.debug(
                    f"Skipping payment event (no event loop): {shipment_reference} "
                    f"{from_state} → {to_state}"
                )

        except ImportError:
            # ChainBoard realtime bus not available - likely standalone ChainPay service
            logger.debug(
                f"ChainBoard realtime bus not available, skipping event: "
                f"{shipment_reference} {from_state} → {to_state}"
            )

    except Exception as e:
        # Never crash ChainPay due to event bus issues
        logger.error(
            f"Failed to emit payment event for {shipment_reference}: {e}",
            exc_info=True
        )


def _map_transition_to_event_kind(from_state: str, to_state: str) -> str:
    """
    Map payment status transition to PaymentEventKind.

    Args:
        from_state: Previous status
        to_state: New status

    Returns:
        PaymentEventKind value as string
    """
    # Normalize to lowercase
    from_state = from_state.lower()
    to_state = to_state.lower()

    # pending → approved/delayed = became eligible (created and ready for release)
    if from_state == "pending" and to_state in ("approved", "delayed"):
        return "milestone_became_eligible"

    # Any state → approved = released (funds approved for disbursement)
    if to_state == "approved":
        return "milestone_released"

    # Any state → settled = settled (funds disbursed)
    if to_state == "settled":
        return "milestone_settled"

    # Any state → rejected/cancelled = blocked
    if to_state in ("rejected", "cancelled"):
        return "milestone_blocked"

    # Blocked → any other state = unblocked
    if from_state in ("rejected", "cancelled") and to_state not in ("rejected", "cancelled"):
        return "milestone_unblocked"

    # Default: treat as "became eligible"
    return "milestone_became_eligible"
