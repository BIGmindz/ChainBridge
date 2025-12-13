"""
ChainIQ ML Data Ingestion Module

Orchestrates the complete pipeline from raw event logs to training-ready ShipmentTrainingRow objects.
This module is ONLY used during offline training data preparation.

Key Functions:
- derive_had_claim: Compute claim label from events
- derive_had_dispute: Compute dispute label from events
- derive_severe_delay: Compute severe delay label from events
- build_training_rows_from_events: Convert event stream to training rows
- backfill_training_data: Main entry point for batch ingestion

Status: v0.2.1 - Real data ingestion pipeline (PAC-005)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from app.ml.datasets import ShipmentTrainingRow
from app.ml.event_parsing import (
    EventType,
    ParsedEvent,
    compute_transit_times,
    count_event_types,
    extract_event_timestamps,
    extract_sensor_readings,
    group_events_by_shipment,
    parse_event_log,
)

# Label Derivation Rules
# ======================


def derive_had_claim(events: Sequence[ParsedEvent]) -> bool:
    """
    Determine if shipment resulted in an insurance claim.

    Rule: True if any CLAIM_FILED event exists in the event stream.

    Args:
        events: Chronologically sorted events for a single shipment

    Returns:
        True if claim was filed, False otherwise

    Example:
        >>> events = [
        ...     ParsedEvent("e1", "shp1", EventType.CLAIM_FILED, datetime(2024, 1, 1), {}),
        ... ]
        >>> derive_had_claim(events)
        True
    """
    return any(event.event_type == EventType.CLAIM_FILED for event in events)


def derive_had_dispute(events: Sequence[ParsedEvent]) -> bool:
    """
    Determine if shipment resulted in a payment dispute.

    Rule: True if any DISPUTE_OPENED event exists in the event stream.

    Args:
        events: Chronologically sorted events for a single shipment

    Returns:
        True if dispute was opened, False otherwise

    Example:
        >>> events = [
        ...     ParsedEvent("e1", "shp1", EventType.DISPUTE_OPENED, datetime(2024, 1, 1), {}),
        ... ]
        >>> derive_had_dispute(events)
        True
    """
    return any(event.event_type == EventType.DISPUTE_OPENED for event in events)


def derive_severe_delay(events: Sequence[ParsedEvent]) -> bool:
    """
    Determine if shipment had a severe delay (>48 hours late).

    Rule: True if (delivered_at - eta) > 48 hours OR if delivered_at is None
           (undelivered shipments are considered severely delayed).

    ALEX Governance: 48-hour threshold is canonical per RSI_THRESHOLD_POLICY

    Args:
        events: Chronologically sorted events for a single shipment

    Returns:
        True if severely delayed, False otherwise

    Example:
        >>> events = [
        ...     ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED,
        ...                 datetime(2024, 1, 1), {"eta": "2024-01-03T00:00:00Z"}),
        ...     ParsedEvent("e2", "shp1", EventType.SHIPMENT_DELIVERED,
        ...                 datetime(2024, 1, 6), {}),  # 3 days late = 72 hours
        ... ]
        >>> derive_severe_delay(events)
        True
    """
    from datetime import timezone

    timestamps = extract_event_timestamps(events)

    # If no delivery timestamp, consider severely delayed (shipment lost/stuck)
    if timestamps["delivered_at"] is None:
        return True

    # If no ETA, cannot determine delay - default to False (no data)
    if timestamps["eta"] is None:
        return False

    # Ensure both timestamps are timezone-aware for comparison
    delivered_at = timestamps["delivered_at"]
    eta = timestamps["eta"]

    # Make timestamps timezone-aware if they aren't already (assume UTC)
    if delivered_at.tzinfo is None:
        delivered_at = delivered_at.replace(tzinfo=timezone.utc)
    if eta.tzinfo is None:
        eta = eta.replace(tzinfo=timezone.utc)

    # Calculate deviation directly (more reliable than compute_transit_times)
    deviation_hours = (delivered_at - eta).total_seconds() / 3600

    # If ETA deviation > 48 hours, consider severely delayed
    return deviation_hours > 48.0


def derive_loss_amount(events: Sequence[ParsedEvent]) -> float:
    """
    Extract total loss/claim amount from events.

    Rule:
    - Sum ALL approved amounts (multi-claim shipments)
    - If no approvals, use max filed amount (pending claims)

    Args:
        events: Chronologically sorted events for a single shipment

    Returns:
        Total loss amount in USD (0.0 if no claims)

    Example:
        >>> events = [
        ...     ParsedEvent("e1", "shp1", EventType.CLAIM_FILED,
        ...                 datetime(2024, 1, 1), {"claim_amount": 500.0}),
        ...     ParsedEvent("e2", "shp1", EventType.CLAIM_APPROVED,
        ...                 datetime(2024, 1, 5), {"approved_amount": 450.0}),
        ... ]
        >>> derive_loss_amount(events)
        450.0
    """
    # First, check for approved amounts (actual payouts)
    # For multi-claim shipments, sum all approved amounts
    approved_amounts = []
    for event in events:
        if event.event_type == EventType.CLAIM_APPROVED:
            if "approved_amount" in event.payload:
                approved_amounts.append(float(event.payload["approved_amount"]))

    if approved_amounts:
        # Sum all approved claims for multi-claim shipments
        return sum(approved_amounts)

    # Fall back to filed amounts if no approvals yet
    # Use max filed amount (pending claims - conservative estimate)
    filed_amounts = []
    for event in events:
        if event.event_type == EventType.CLAIM_FILED:
            if "claim_amount" in event.payload:
                filed_amounts.append(float(event.payload["claim_amount"]))

    # Return max filed amount (most likely final claim)
    return max(filed_amounts) if filed_amounts else 0.0


def derive_is_known_anomaly(events: Sequence[ParsedEvent]) -> bool:
    """
    Determine if shipment is a known anomaly (for anomaly model training).

    Rule: True if shipment has any of:
    - Multiple route deviations (>3)
    - Custody gaps
    - Temperature violations
    - Sensor offline for >6 hours
    - Cancelled shipment

    Args:
        events: Chronologically sorted events for a single shipment

    Returns:
        True if known anomaly, False otherwise

    Example:
        >>> events = [
        ...     ParsedEvent("e1", "shp1", EventType.ROUTE_DEVIATION, datetime(2024, 1, 1), {}),
        ...     ParsedEvent("e2", "shp1", EventType.ROUTE_DEVIATION, datetime(2024, 1, 2), {}),
        ...     ParsedEvent("e3", "shp1", EventType.ROUTE_DEVIATION, datetime(2024, 1, 3), {}),
        ...     ParsedEvent("e4", "shp1", EventType.ROUTE_DEVIATION, datetime(2024, 1, 4), {}),
        ... ]
        >>> derive_is_known_anomaly(events)
        True
    """
    event_counts = count_event_types(events)

    # Multiple route deviations
    if event_counts.get(EventType.ROUTE_DEVIATION, 0) > 3:
        return True

    # Custody gap (chain of custody broken)
    if event_counts.get(EventType.CUSTODY_GAP, 0) > 0:
        return True

    # Temperature violations
    if event_counts.get(EventType.TEMPERATURE_VIOLATION, 0) > 0:
        return True

    # Sensor offline events
    if event_counts.get(EventType.SENSOR_OFFLINE, 0) > 0:
        return True

    # Cancelled shipment
    if event_counts.get(EventType.SHIPMENT_CANCELLED, 0) > 0:
        return True

    return False


# Feature Extraction from Events
# ================================


def extract_features_from_events(
    shipment_id: str,
    events: Sequence[ParsedEvent],
) -> dict[str, Any]:
    """
    Extract all features needed for ShipmentTrainingRow from event stream.

    Args:
        shipment_id: Unique shipment identifier
        events: Chronologically sorted events for this shipment

    Returns:
        Dictionary with all features required by ShipmentTrainingRow

    Example:
        >>> events = [
        ...     ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED,
        ...                 datetime(2024, 1, 1), {"eta": "2024-01-03T00:00:00Z"}),
        ...     ParsedEvent("e2", "shp1", EventType.SHIPMENT_DELIVERED,
        ...                 datetime(2024, 1, 5), {}),
        ... ]
        >>> features = extract_features_from_events("shp1", events)
        >>> features["shipment_id"]
        'shp1'
    """
    # Get timestamps and transit times
    timestamps = extract_event_timestamps(events)
    transit_times = compute_transit_times(events)
    event_counts = count_event_types(events)
    sensor_readings = extract_sensor_readings(events)

    # Core transit features with defaults (48h rule per ALEX governance)
    # Note: transit_times values can be None, so we need explicit checks
    planned_transit_hours = transit_times.get("planned_transit_hours")
    if planned_transit_hours is None:
        planned_transit_hours = 48.0  # Default 48h per ALEX policy

    actual_transit_hours = transit_times.get("actual_transit_hours")
    if actual_transit_hours is None:
        actual_transit_hours = planned_transit_hours  # Use planned if no actual

    eta_deviation_hours = transit_times.get("eta_deviation_hours")
    if eta_deviation_hours is None:
        eta_deviation_hours = 0.0  # Default to no deviation

    # Route features
    num_route_deviations = event_counts.get(EventType.ROUTE_DEVIATION, 0)
    max_route_deviation_km = 0.0
    for event in events:
        if event.event_type == EventType.ROUTE_DEVIATION:
            if "deviation_km" in event.payload:
                max_route_deviation_km = max(max_route_deviation_km, float(event.payload["deviation_km"]))

    # Handoff/dwell features
    handoff_count = event_counts.get(EventType.HANDOFF_COMPLETED, 0)
    dwell_starts = [e for e in events if e.event_type == EventType.DWELL_START]
    dwell_ends = [e for e in events if e.event_type == EventType.DWELL_END]

    total_dwell_hours = 0.0
    max_single_dwell_hours = 0.0
    for start, end in zip(dwell_starts, dwell_ends):
        dwell_duration = (end.timestamp - start.timestamp).total_seconds() / 3600
        total_dwell_hours += dwell_duration
        max_single_dwell_hours = max(max_single_dwell_hours, dwell_duration)

    # Custody features
    max_custody_gap_hours = 0.0
    for event in events:
        if event.event_type == EventType.CUSTODY_GAP:
            if "gap_hours" in event.payload:
                max_custody_gap_hours = max(max_custody_gap_hours, float(event.payload["gap_hours"]))

    # IoT/sensor features
    temps = sensor_readings["temperatures"]
    temp_mean = sum(temps) / len(temps) if temps else 20.0  # Default 20°C
    temp_std = 0.0
    if len(temps) > 1:
        mean = temp_mean
        variance = sum((t - mean) ** 2 for t in temps) / len(temps)
        temp_std = variance**0.5

    temp_violations = event_counts.get(EventType.TEMPERATURE_VIOLATION, 0)
    temp_out_of_range_pct = min(100.0, temp_violations * 10.0)  # Rough approximation

    sensor_offline_events = event_counts.get(EventType.SENSOR_OFFLINE, 0)
    sensor_uptime_pct = max(0.0, 100.0 - sensor_offline_events * 5.0)  # Rough approximation

    # Documentation features
    missing_docs = event_counts.get(EventType.MISSING_DOCUMENTATION, 0) > 0

    # Historical/carrier features (simulated for now)
    delay_flag = event_counts.get(EventType.DELAY_DETECTED, 0) > 0
    prior_losses_flag = False  # Would come from historical lookup
    carrier_on_time_pct_90d = 85.0  # Simulated (would come from carrier DB)
    shipper_on_time_pct_90d = 90.0  # Simulated (would come from shipper DB)

    # Sentiment features (simulated for now)
    lane_sentiment_score = 0.7  # Simulated (would come from sentiment API)
    sentiment_trend_7d = 0.0  # Simulated
    sentiment_volatility_30d = 0.1  # Simulated
    macro_logistics_sentiment_score = 0.8  # Simulated

    # Build feature dictionary
    features = {
        "shipment_id": shipment_id,
        "planned_transit_hours": planned_transit_hours,
        "actual_transit_hours": actual_transit_hours,
        "eta_deviation_hours": eta_deviation_hours,
        "num_route_deviations": num_route_deviations,
        "max_route_deviation_km": max_route_deviation_km,
        "handoff_count": handoff_count,
        "total_dwell_hours": total_dwell_hours,
        "max_single_dwell_hours": max_single_dwell_hours,
        "max_custody_gap_hours": max_custody_gap_hours,
        "temp_mean": temp_mean,
        "temp_std": temp_std,
        "temp_out_of_range_pct": temp_out_of_range_pct,
        "sensor_uptime_pct": sensor_uptime_pct,
        "missing_required_docs": missing_docs,
        "delay_flag": delay_flag,
        "prior_losses_flag": prior_losses_flag,
        "carrier_on_time_pct_90d": carrier_on_time_pct_90d,
        "shipper_on_time_pct_90d": shipper_on_time_pct_90d,
        "lane_sentiment_score": lane_sentiment_score,
        "sentiment_trend_7d": sentiment_trend_7d,
        "sentiment_volatility_30d": sentiment_volatility_30d,
        "macro_logistics_sentiment_score": macro_logistics_sentiment_score,
    }

    return features


# Training Row Factory
# ====================


def build_training_rows_from_events(
    event_records: Sequence[dict[str, Any]],
    *,
    filter_incomplete: bool = True,
) -> list[ShipmentTrainingRow]:
    """
    Convert raw event log records into training-ready ShipmentTrainingRow objects.

    This is the main entry point for the ingestion pipeline:
    1. Parse raw events
    2. Group by shipment
    3. Extract features from each shipment's event stream
    4. Derive labels (claim, dispute, delay)
    5. Build ShipmentTrainingRow objects

    Args:
        event_records: List of raw event dictionaries
        filter_incomplete: If True, skip shipments without delivery events

    Returns:
        List of ShipmentTrainingRow objects ready for training

    Example:
        >>> events = [
        ...     {"event_id": "e1", "shipment_id": "shp1", "event_type": "SHIPMENT_CREATED",
        ...      "timestamp": "2024-01-01T00:00:00Z", "payload": {"eta": "2024-01-03T00:00:00Z"}},
        ...     {"event_id": "e2", "shipment_id": "shp1", "event_type": "SHIPMENT_DELIVERED",
        ...      "timestamp": "2024-01-05T00:00:00Z", "payload": {}},
        ...     {"event_id": "e3", "shipment_id": "shp1", "event_type": "CLAIM_FILED",
        ...      "timestamp": "2024-01-06T00:00:00Z", "payload": {"claim_amount": 500.0}},
        ... ]
        >>> rows = build_training_rows_from_events(events)
        >>> len(rows)
        1
        >>> rows[0].had_claim
        True
        >>> rows[0].severe_delay
        True
    """
    # Step 1: Parse all events
    parsed_events = []
    for record in event_records:
        try:
            event = parse_event_log(record)
            parsed_events.append(event)
        except (ValueError, KeyError) as e:
            print(f"⚠ Skipping invalid event: {e}")
            continue

    print(f"✓ Parsed {len(parsed_events)} events")

    # Step 2: Group by shipment
    grouped = group_events_by_shipment(parsed_events)
    print(f"✓ Grouped into {len(grouped)} shipments")

    # Step 3: Build training rows
    training_rows = []
    skipped = 0

    for shipment_id, events in grouped.items():
        # Filter incomplete shipments (no delivery event)
        if filter_incomplete:
            timestamps = extract_event_timestamps(events)
            if timestamps["delivered_at"] is None:
                skipped += 1
                continue

        # Extract features dict
        features_dict = extract_features_from_events(shipment_id, events)

        # Derive labels
        had_claim = derive_had_claim(events)
        had_dispute = derive_had_dispute(events)
        severe_delay = derive_severe_delay(events)
        loss_amount = derive_loss_amount(events) if had_claim else None
        is_known_anomaly = derive_is_known_anomaly(events)

        # Build ShipmentFeaturesV0 object from extracted features
        # Note: Many fields are placeholders until we have real production data
        from app.models.features import ShipmentFeaturesV0

        # Handle None values with fallback defaults
        planned_transit = features_dict["planned_transit_hours"]
        if planned_transit is None:
            planned_transit = 48.0

        actual_transit = features_dict["actual_transit_hours"]
        if actual_transit is None:
            actual_transit = planned_transit

        eta_deviation = features_dict["eta_deviation_hours"]
        if eta_deviation is None:
            eta_deviation = 0.0

        features = ShipmentFeaturesV0(
            # Identifiers (placeholders for now)
            shipment_id=features_dict["shipment_id"],
            corridor="US-US",  # Placeholder
            origin_country="US",
            destination_country="US",
            mode="truck",
            commodity_category="general",
            financing_type="OA",
            counterparty_risk_bucket="medium",
            # Operational/transit (from events)
            planned_transit_hours=planned_transit,
            actual_transit_hours=actual_transit,
            eta_deviation_hours=eta_deviation,
            num_route_deviations=features_dict["num_route_deviations"],
            max_route_deviation_km=features_dict["max_route_deviation_km"],
            total_dwell_hours=features_dict["total_dwell_hours"],
            max_single_dwell_hours=features_dict["max_single_dwell_hours"],
            handoff_count=features_dict["handoff_count"],
            max_custody_gap_hours=features_dict["max_custody_gap_hours"],
            delay_flag=1 if features_dict["delay_flag"] else 0,
            # IoT/condition monitoring
            has_iot_telemetry=1,  # Assume yes if we have sensor data
            temp_mean=features_dict["temp_mean"],
            temp_std=features_dict["temp_std"],
            temp_min=features_dict["temp_mean"] - 5.0,  # Approximation
            temp_max=features_dict["temp_mean"] + 5.0,
            temp_out_of_range_pct=features_dict["temp_out_of_range_pct"],
            sensor_uptime_pct=features_dict["sensor_uptime_pct"],
            # Documentation (placeholders)
            doc_count=5,  # Placeholder
            missing_required_docs=1 if features_dict["missing_required_docs"] else 0,
            duplicate_doc_flag=0,
            doc_inconsistency_flag=0,
            doc_age_days=1.0,
            collateral_value=50000.0,
            collateral_value_bucket="medium",
            # Carrier/historical (from extracted features + placeholders)
            carrier_on_time_pct_90d=features_dict["carrier_on_time_pct_90d"],
            shipper_on_time_pct_90d=features_dict["shipper_on_time_pct_90d"],
            corridor_disruption_index_90d=0.25,  # Placeholder
            prior_exceptions_count_180d=2,  # Placeholder
            prior_losses_flag=1 if features_dict["prior_losses_flag"] else 0,
            carrier_risk_bucket="medium",
            shipper_risk_bucket="low",
            lane_volume_90d=500,
            lane_incident_rate_90d=0.05,
            # Sentiment (from extracted features + placeholder provider)
            lane_sentiment_score=features_dict["lane_sentiment_score"],
            macro_logistics_sentiment_score=features_dict["macro_logistics_sentiment_score"],
            sentiment_trend_7d=features_dict["sentiment_trend_7d"],
            sentiment_volatility_30d=features_dict["sentiment_volatility_30d"],
            sentiment_provider="backfill_stub_v0.2",  # Placeholder
        )

        # Get latest event timestamp as recorded_at
        latest_timestamp = max(e.timestamp for e in events)

        # Build training row
        row = ShipmentTrainingRow(
            features=features,
            had_claim=had_claim,
            had_dispute=had_dispute,
            severe_delay=severe_delay,
            loss_amount=loss_amount,
            is_known_anomaly=is_known_anomaly,
            anomaly_type=None,  # Not classified yet
            recorded_at=latest_timestamp,
            data_source="backfill",
        )

        training_rows.append(row)

    print(f"✓ Built {len(training_rows)} training rows")
    if skipped > 0:
        print(f"  (Skipped {skipped} incomplete shipments)")

    # Print summary stats
    if training_rows:
        claims = sum(1 for r in training_rows if r.had_claim)
        disputes = sum(1 for r in training_rows if r.had_dispute)
        delays = sum(1 for r in training_rows if r.severe_delay)
        bad_outcomes = sum(1 for r in training_rows if r.bad_outcome)

        print("\nLabel distribution:")
        print(f"  Claims:       {claims} ({claims/len(training_rows)*100:.1f}%)")
        print(f"  Disputes:     {disputes} ({disputes/len(training_rows)*100:.1f}%)")
        print(f"  Severe delays: {delays} ({delays/len(training_rows)*100:.1f}%)")
        print(f"  Bad outcomes: {bad_outcomes} ({bad_outcomes/len(training_rows)*100:.1f}%)")

    return training_rows


# Backfill Entry Point
# =====================


def backfill_training_data(
    input_path: str | Path,
    output_path: str | Path,
    *,
    filter_incomplete: bool = True,
) -> int:
    """
    Main entry point for backfilling training data from raw event logs.

    Reads JSONL file with raw events, processes them, and writes training rows to output.

    Args:
        input_path: Path to input JSONL file (one event per line)
        output_path: Path to output JSONL file (one training row per line)
        filter_incomplete: If True, skip shipments without delivery events

    Returns:
        Number of training rows written

    Example:
        >>> # Assuming events.jsonl exists
        >>> count = backfill_training_data("events.jsonl", "training_rows.jsonl")
        >>> print(f"Wrote {count} training rows")
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    print(f"\n{'='*60}")
    print("ChainIQ ML Training Data Backfill")
    print(f"{'='*60}")
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print(f"{'='*60}\n")

    # Read input events
    print("[1/3] Reading event logs...")
    event_records = []
    with open(input_path, "r") as f:
        for line in f:
            if line.strip():
                event_records.append(json.loads(line))
    print(f"✓ Read {len(event_records)} event records")

    # Build training rows
    print("\n[2/3] Building training rows...")
    training_rows = build_training_rows_from_events(event_records, filter_incomplete=filter_incomplete)

    # Write output
    print(f"\n[3/3] Writing training data to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        for row in training_rows:
            # Convert to dict and write as JSON
            row_dict = {
                "shipment_id": row.shipment_id,
                "planned_transit_hours": row.planned_transit_hours,
                "actual_transit_hours": row.actual_transit_hours,
                "eta_deviation_hours": row.eta_deviation_hours,
                "num_route_deviations": row.num_route_deviations,
                "max_route_deviation_km": row.max_route_deviation_km,
                "handoff_count": row.handoff_count,
                "total_dwell_hours": row.total_dwell_hours,
                "max_single_dwell_hours": row.max_single_dwell_hours,
                "max_custody_gap_hours": row.max_custody_gap_hours,
                "temp_mean": row.temp_mean,
                "temp_std": row.temp_std,
                "temp_out_of_range_pct": row.temp_out_of_range_pct,
                "sensor_uptime_pct": row.sensor_uptime_pct,
                "missing_required_docs": row.missing_required_docs,
                "delay_flag": row.delay_flag,
                "prior_losses_flag": row.prior_losses_flag,
                "carrier_on_time_pct_90d": row.carrier_on_time_pct_90d,
                "shipper_on_time_pct_90d": row.shipper_on_time_pct_90d,
                "lane_sentiment_score": row.lane_sentiment_score,
                "sentiment_trend_7d": row.sentiment_trend_7d,
                "sentiment_volatility_30d": row.sentiment_volatility_30d,
                "macro_logistics_sentiment_score": row.macro_logistics_sentiment_score,
                "had_claim": row.had_claim,
                "had_dispute": row.had_dispute,
                "severe_delay": row.severe_delay,
                "is_known_anomaly": row.is_known_anomaly,
            }
            f.write(json.dumps(row_dict) + "\n")

    print(f"✓ Wrote {len(training_rows)} training rows")
    print(f"\n{'='*60}")
    print("Backfill complete!")
    print(f"{'='*60}")

    return len(training_rows)


# CLI helper
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("ChainIQ ML Training Data Backfill")
        print("=" * 60)
        print("\nUsage:")
        print("  python -m app.ml.ingestion <input.jsonl> <output.jsonl>")
        print("\nExample:")
        print("  python -m app.ml.ingestion logs/events.jsonl data/training_rows.jsonl")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    count = backfill_training_data(input_file, output_file)
    sys.exit(0 if count > 0 else 1)
