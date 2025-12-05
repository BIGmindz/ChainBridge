"""
ChainIQ Option Sandbox

Simulates risk scoring for alternative routes and payment rails without persisting results.

Business Purpose:
- Test "what-if" scenarios safely before committing to changes
- Validate Better Options Advisor recommendations
- Enable operator confidence in option selection

Design Principles:
- Read-only: No database writes during simulation
- Isolated: Uses existing risk engine without side effects
- Transparent: Clear notes about simulation vs. production scoring
"""

import logging
from typing import Any, Dict, Literal

# These imports will work when simulation.py is in chainiq-service/
# and imported as: from ..simulation import ...
try:
    from .app.risk_engine import calculate_risk_score
    from .app.schemas import SimulationResultResponse
    from .storage import (
        get_latest_risk_for_shipment,
        load_shipment_context_for_simulation,
    )
except ImportError:
    # Fallback for direct execution or different import context
    from storage import (
        get_latest_risk_for_shipment,
        load_shipment_context_for_simulation,
    )

    from app.risk_engine import calculate_risk_score
    from app.schemas import SimulationResultResponse

logger = logging.getLogger(__name__)


def simulate_option_for_shipment(
    shipment_id: str,
    option_type: Literal["route", "payment_rail"],
    option_id: str,
) -> SimulationResultResponse:
    """
    Run a sandbox risk simulation for a selected option.

    This function performs a non-persisting risk assessment to show the impact
    of selecting an alternative route or payment rail.

    Args:
        shipment_id: Shipment identifier
        option_type: Type of option ("route" or "payment_rail")
        option_id: Identifier of the specific option to simulate

    Returns:
        SimulationResultResponse with baseline vs. simulated risk metrics

    Raises:
        ValueError: If shipment not found or option invalid

    Example:
        >>> result = simulate_option_for_shipment(
        ...     shipment_id="SHP-001",
        ...     option_type="route",
        ...     option_id="ROUTE-SAFER-001"
        ... )
        >>> result.risk_delta > 0  # Option is safer
        True

    Note:
        This function does NOT persist any results to the database.
        It's a pure sandbox operation for testing options.
    """
    logger.info(
        "Starting simulation for %s: option_type=%s, option_id=%s",
        shipment_id,
        option_type,
        option_id,
    )

    # Step 1: Load baseline shipment context
    try:
        context = load_shipment_context_for_simulation(shipment_id)
    except ValueError as exc:
        logger.warning("Failed to load context for simulation: %s", str(exc))
        raise

    # Step 2: Get baseline risk (from latest scoring or compute it)
    baseline_risk_data = get_latest_risk_for_shipment(shipment_id)

    if baseline_risk_data:
        baseline_risk_score = baseline_risk_data["risk_score"]
        baseline_severity = baseline_risk_data["severity"]
    else:
        # No previous scoring - compute baseline from context
        baseline_risk_score, baseline_severity, _, _ = calculate_risk_score(
            route=context["route"],
            carrier_id=context["carrier_id"],
            shipment_value_usd=context["shipment_value_usd"],
            days_in_transit=context["days_in_transit"],
            expected_days=context["expected_days"],
            documents_complete=context["documents_complete"],
            shipper_payment_score=context["shipper_payment_score"],
        )

    # Step 3: Apply option changes to create simulated context
    simulated_context = context.copy()
    notes: list[str] = [
        "Sandbox simulation only - no data persisted",
        f"Simulated option: {option_id}",
    ]

    if option_type == "route":
        # Parse option_id to extract route and carrier changes
        # Format: ROUTE-{route}-{carrier_id} or similar
        # For v0, we'll use a simple heuristic based on option_id naming
        simulated_context = _apply_route_option(simulated_context, option_id, notes)
    elif option_type == "payment_rail":
        # Apply payment rail changes
        simulated_context = _apply_payment_rail_option(simulated_context, option_id, notes)
    else:
        raise ValueError(f"Unknown option_type: {option_type}")

    # Step 4: Run risk scoring on simulated context (NO PERSISTENCE)
    simulated_risk_score, simulated_severity, _, _ = calculate_risk_score(
        route=simulated_context["route"],
        carrier_id=simulated_context["carrier_id"],
        shipment_value_usd=simulated_context["shipment_value_usd"],
        days_in_transit=simulated_context["days_in_transit"],
        expected_days=simulated_context["expected_days"],
        documents_complete=simulated_context["documents_complete"],
        shipper_payment_score=simulated_context["shipper_payment_score"],
    )

    # Step 5: Compute delta (positive = safer)
    risk_delta = baseline_risk_score - simulated_risk_score

    logger.info(
        "Simulation complete for %s: baseline=%d, simulated=%d, delta=%d",
        shipment_id,
        baseline_risk_score,
        simulated_risk_score,
        risk_delta,
    )

    return SimulationResultResponse(
        shipment_id=shipment_id,
        option_type=option_type,
        option_id=option_id,
        baseline_risk_score=baseline_risk_score,
        simulated_risk_score=simulated_risk_score,
        baseline_severity=baseline_severity,
        simulated_severity=simulated_severity,
        risk_delta=risk_delta,
        notes=notes,
    )


def _apply_route_option(
    context: Dict[str, Any],
    option_id: str,
    notes: list[str],
) -> Dict[str, Any]:
    """
    Apply route option changes to simulation context.

    For v0, we use heuristic parsing of option_id.
    In production, this would look up the option in the options engine.

    Args:
        context: Current shipment context
        option_id: Route option identifier
        notes: List to append simulation notes

    Returns:
        Modified context dict
    """
    # Heuristic: option_id like "ROUTE-DE-UK-CARRIER-002"
    # Extract route and carrier if possible
    if option_id.startswith("ROUTE-"):
        parts = option_id.split("-")
        if len(parts) >= 3:
            # Extract route (e.g., "DE-UK" from "ROUTE-DE-UK-...")
            route = f"{parts[1]}-{parts[2]}"
            context["route"] = route
            notes.append(f"Simulated route change: {route}")

            # Extract carrier if present
            if "CARRIER" in option_id:
                carrier_idx = parts.index("CARRIER")
                if carrier_idx + 1 < len(parts):
                    carrier_id = f"CARRIER-{parts[carrier_idx + 1]}"
                    context["carrier_id"] = carrier_id
                    notes.append(f"Simulated carrier change: {carrier_id}")
    else:
        # Fallback: apply a generic safer route
        # For v0, we'll just use a low-risk route
        context["route"] = "US-CA"
        notes.append("Simulated generic safer route: US-CA")

    return context


def _apply_payment_rail_option(
    context: Dict[str, Any],
    option_id: str,
    notes: list[str],
) -> Dict[str, Any]:
    """
    Apply payment rail option changes to simulation context.

    For v0, payment rail changes don't directly affect the current risk engine
    (which focuses on route/carrier/docs). This is a placeholder for future
    payment rail risk factors.

    Args:
        context: Current shipment context
        option_id: Payment rail option identifier
        notes: List to append simulation notes

    Returns:
        Modified context dict (unchanged for v0)
    """
    # For v0, payment rail doesn't impact the existing risk_engine factors
    # In the future, we could add payment_rail_risk_factor to the scoring
    notes.append(f"Payment rail simulation not yet implemented: {option_id}")
    notes.append("Risk score unchanged (payment rail not in current risk model)")

    return context
