"""
ChainIQ Options Engine

Better Options Advisor: suggests alternative routes and payment rails
to reduce risk while considering cost, ETA, and risk appetite.

Sunny: update suggest_options_for_shipment to support a risk_appetite parameter.

1) Change the function signature to:

def suggest_options_for_shipment(
    shipment_id: str,
    limit: int = 5,
    risk_appetite: str = "balanced",
) -> Dict[str, Any]:

2) Validate risk_appetite:
   - If not in {"conservative", "balanced", "aggressive"}, default to "balanced".

3) After computing current_risk_score and assembling candidate route_options and payment_options:

   - For each candidate option, you should already have:
       - new_risk_score (int)
       - risk_delta = current_risk_score - new_risk_score
       - cost_delta_usd, eta_delta_days, etc.

   - Implement simple filtering rules:

     if risk_appetite == "conservative":
         - Keep only options where risk_delta >= 10
         - For route options, also require eta_delta_days <= 3 (no extreme delays)
         - For payment options, require new_risk_score <= current_risk_score
     elif risk_appetite == "balanced":
         - Keep options where risk_delta >= 5
         - Allow moderate eta/cost penalties (no extra filtering beyond existing logic)
     elif risk_appetite == "aggressive":
         - Keep options where risk_delta >= -5
         - But require some positive "reward":
           - For routes: cost_delta_usd <= 0 (same or cheaper) OR eta_delta_days <= 0 (same or faster)
           - For payment rails: fees_delta_usd <= 0 OR faster settlement_speed vs current

4) Apply the filters to both route_options and payment_options before limiting to `limit`.

5) Sort options according to risk_appetite:

   - Conservative:
       - Sort by risk_score ascending (safest first), then cost_delta_usd ascending.
   - Balanced:
       - Sort by risk_delta descending (greatest improvement first).
   - Aggressive:
       - Sort by a simple reward metric (e.g. cost_savings_usd descending, then risk_score ascending).

6) Include risk_appetite in the returned dictionary so the API layer can populate OptionsAdvisorResponse.
"""

from typing import Any, Dict, List


def suggest_options_for_shipment(
    shipment_id: str,
    limit: int = 5,
    risk_appetite: str = "balanced",
) -> Dict[str, Any]:
    """
    Suggest better route and payment rail options for a shipment.

    Args:
        shipment_id: Shipment identifier
        limit: Maximum number of options to return per category
        risk_appetite: Risk tolerance level ("conservative", "balanced", "aggressive")

    Returns:
        Dictionary containing current state, route options, payment options, and risk_appetite
    """

    # Validate risk_appetite
    if risk_appetite not in {"conservative", "balanced", "aggressive"}:
        risk_appetite = "balanced"

    # NOTE: Fetch current shipment data from storage/database
    # For now, using mock data structure
    current_risk_score = 75
    current_route = "IR-RU"
    current_carrier_id = "CARRIER-001"
    current_payment_rail = "SWIFT"

    # Generate candidate route options (mock data - replace with real logic)
    candidate_routes = [
        {
            "option_id": f"ROUTE-{current_route.replace('-', '')}-ALT1",
            "route": "IR-TR-EU",
            "carrier_id": "CARRIER-002",
            "risk_score": 45,
            "cost_delta_usd": 200.0,
            "eta_delta_days": 2,
            "notes": ["Route via Turkey to EU gateway"],
        },
        {
            "option_id": f"ROUTE-{current_route.replace('-', '')}-ALT2",
            "route": "IR-AE-EU",
            "carrier_id": "CARRIER-003",
            "risk_score": 50,
            "cost_delta_usd": 150.0,
            "eta_delta_days": 1,
            "notes": ["Route via UAE to EU gateway"],
        },
        {
            "option_id": f"ROUTE-{current_route.replace('-', '')}-ALT3",
            "route": "IR-IN-EU",
            "carrier_id": "CARRIER-004",
            "risk_score": 55,
            "cost_delta_usd": -50.0,
            "eta_delta_days": 4,
            "notes": ["Route via India (slower but cheaper)"],
        },
        {
            "option_id": f"ROUTE-{current_route.replace('-', '')}-ALT4",
            "route": "IR-CN-RU",
            "carrier_id": "CARRIER-005",
            "risk_score": 80,
            "cost_delta_usd": -200.0,
            "eta_delta_days": -1,
            "notes": ["Direct route via China (cheaper, faster, higher risk)"],
        },
    ]

    # Generate candidate payment options (mock data - replace with real logic)
    candidate_payments = [
        {
            "option_id": f"PAYMENT-{current_payment_rail.replace('-', '')}-ALT1",
            "payment_rail": "USDC-Polygon",
            "risk_score": 40,
            "fees_delta_usd": -100.0,
            "settlement_speed": "T+0",
            "notes": ["Stablecoin on Polygon (fast, low fees)"],
        },
        {
            "option_id": f"PAYMENT-{current_payment_rail.replace('-', '')}-ALT2",
            "payment_rail": "USDC-Ethereum",
            "risk_score": 42,
            "fees_delta_usd": 50.0,
            "settlement_speed": "T+0",
            "notes": ["Stablecoin on Ethereum (fast, higher gas)"],
        },
        {
            "option_id": f"PAYMENT-{current_payment_rail.replace('-', '')}-ALT3",
            "payment_rail": "ACH",
            "risk_score": 65,
            "fees_delta_usd": -80.0,
            "settlement_speed": "T+3",
            "notes": ["ACH transfer (cheaper, slower)"],
        },
        {
            "option_id": f"PAYMENT-{current_payment_rail.replace('-', '')}-ALT4",
            "payment_rail": "Wire",
            "risk_score": 70,
            "fees_delta_usd": 0.0,
            "settlement_speed": "T+1",
            "notes": ["Bank wire (similar to SWIFT)"],
        },
    ]

    # Calculate risk_delta for all options
    for route in candidate_routes:
        route["risk_delta"] = current_risk_score - route["risk_score"]

    for payment in candidate_payments:
        payment["risk_delta"] = current_risk_score - payment["risk_score"]

    # Apply filtering based on risk_appetite
    filtered_routes = _filter_route_options(candidate_routes, risk_appetite, current_risk_score)
    filtered_payments = _filter_payment_options(candidate_payments, risk_appetite, current_risk_score)

    # Sort based on risk_appetite
    sorted_routes = _sort_options(filtered_routes, risk_appetite, option_type="route")
    sorted_payments = _sort_options(filtered_payments, risk_appetite, option_type="payment")

    # Limit results
    route_options = sorted_routes[:limit]
    payment_options = sorted_payments[:limit]

    return {
        "shipment_id": shipment_id,
        "current_risk_score": current_risk_score,
        "current_route": current_route,
        "current_carrier_id": current_carrier_id,
        "current_payment_rail": current_payment_rail,
        "route_options": route_options,
        "payment_options": payment_options,
        "risk_appetite": risk_appetite,
    }


def _filter_route_options(routes: List[Dict[str, Any]], risk_appetite: str, current_risk_score: int) -> List[Dict[str, Any]]:
    """
    Filter route options based on risk_appetite.

    Conservative: risk_delta >= 10, eta_delta_days <= 3
    Balanced: risk_delta >= 5
    Aggressive: risk_delta >= -5 AND (cost_delta_usd <= 0 OR eta_delta_days <= 0)
    """

    if risk_appetite == "conservative":
        return [r for r in routes if r["risk_delta"] >= 10 and r["eta_delta_days"] <= 3]
    elif risk_appetite == "balanced":
        return [r for r in routes if r["risk_delta"] >= 5]
    elif risk_appetite == "aggressive":
        return [r for r in routes if r["risk_delta"] >= -5 and (r["cost_delta_usd"] <= 0 or r["eta_delta_days"] <= 0)]

    return routes


def _filter_payment_options(payments: List[Dict[str, Any]], risk_appetite: str, current_risk_score: int) -> List[Dict[str, Any]]:
    """
    Filter payment options based on risk_appetite.

    Conservative: risk_score <= current_risk_score
    Balanced: risk_delta >= 5
    Aggressive: risk_delta >= -5 AND fees_delta_usd <= 0
    """

    if risk_appetite == "conservative":
        # Keep only options that don't increase risk
        return [p for p in payments if p["risk_score"] <= current_risk_score]
    elif risk_appetite == "balanced":
        return [p for p in payments if p["risk_delta"] >= 5]
    elif risk_appetite == "aggressive":
        return [p for p in payments if p["risk_delta"] >= -5 and p["fees_delta_usd"] <= 0]

    return payments


def _sort_options(options: List[Dict[str, Any]], risk_appetite: str, option_type: str) -> List[Dict[str, Any]]:
    """
    Sort options based on risk_appetite.

    Conservative: Sort by new_risk_score (safest first), then cost_delta
    Balanced: Sort by risk_delta descending (greatest improvement first)
    Aggressive: Sort by cost savings (for routes) or fees savings (for payments), then risk_score
    """

    if risk_appetite == "conservative":
        # Safest first, then cheapest
        return sorted(
            options,
            key=lambda x: (
                x["risk_score"],
                x.get("cost_delta_usd", x.get("fees_delta_usd", 0)),
            ),
        )
    elif risk_appetite == "balanced":
        # Greatest risk improvement first
        return sorted(options, key=lambda x: x["risk_delta"], reverse=True)
    elif risk_appetite == "aggressive":
        # Best cost savings first (negative delta = savings), then lowest risk
        if option_type == "route":
            return sorted(options, key=lambda x: (x["cost_delta_usd"], x["risk_score"]))
        else:  # payment
            return sorted(options, key=lambda x: (x["fees_delta_usd"], x["risk_score"]))

    return options
