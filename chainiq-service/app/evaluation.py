"""
ChainIQ v0.1 - Retrospective Pilot Evaluation

Production-ready tools for evaluating ChainIQ performance on historical customer data.
Used for the "Retrospective Brain Pilot" sales motion: "Give us 3-6 months of history;
we show where risk lived and how we would have treated it."

Author: Maggie (GID-10) - ML & Applied AI Lead
Mantra: "Code = Cash. Explain or Perish."
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

# Conditional pandas import
try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    pd = None

# Conditional sklearn import
try:
    from sklearn.metrics import confusion_matrix as sk_confusion_matrix
    from sklearn.metrics import roc_auc_score

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

from .schemas import ShipmentRiskContext
from .scoring import ChainIQScorer, get_default_scorer

# =============================================================================
# LOGGING (NO PII)
# =============================================================================

logger = logging.getLogger(__name__)


def _log_shape_only(df_or_list: Any, label: str = "data") -> None:
    """Log shape/count only, never contents (PII protection)."""
    if hasattr(df_or_list, "shape"):
        logger.info(f"{label}: shape={df_or_list.shape}")
    elif hasattr(df_or_list, "__len__"):
        logger.info(f"{label}: count={len(df_or_list)}")


# =============================================================================
# CANONICAL PILOT METRICS (Pydantic)
# =============================================================================


class RetrospectivePilotMetrics(BaseModel):
    """
    Canonical metrics from a retrospective pilot run.

    These are the numbers that go into sales decks and prospect conversations.
    Keep field names stable — downstream tooling depends on them.
    """

    # === CORE COUNTS ===
    total_shipments: int = Field(..., description="Total shipments analyzed")
    total_bad_events: int = Field(..., description="Shipments with bad outcomes (late/claims/fraud)")
    bad_event_rate: float = Field(..., description="Fraction of shipments with bad outcomes")

    # === MODEL PERFORMANCE METRICS ===
    auc_roc: Optional[float] = Field(None, ge=0.0, le=1.0, description="Area Under ROC Curve (0.5=random, 1.0=perfect)")
    lift_at_top_10pct: Optional[float] = Field(None, ge=0.0, description="Bad-event rate in top 10% risk / overall bad-event rate")
    capture_rate_top_10pct: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Fraction of all bad events found in top 10% risk tier"
    )
    precision_at_top_10pct: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Fraction of top 10% risk shipments that were actually bad"
    )

    # === BUSINESS IMPACT ===
    total_loss_usd: Optional[float] = Field(None, ge=0.0, description="Total realized loss across all bad events (from CSV)")
    hypothetical_savings_usd: Optional[float] = Field(
        None, ge=0.0, description="Estimated $ saved if top 10% risk shipments were intervened"
    )

    # === DIAGNOSTICS ===
    confusion_matrix: Optional[Dict[str, int]] = Field(None, description="Confusion matrix at chosen threshold: {tp, fp, tn, fn}")
    threshold_used: Optional[float] = Field(None, ge=0.0, le=100.0, description="Risk score threshold used for confusion matrix")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_shipments": 1250,
                "total_bad_events": 187,
                "bad_event_rate": 0.1496,
                "auc_roc": 0.78,
                "lift_at_top_10pct": 3.2,
                "capture_rate_top_10pct": 0.48,
                "precision_at_top_10pct": 0.48,
                "total_loss_usd": 425000.0,
                "hypothetical_savings_usd": 127500.0,
                "confusion_matrix": {"tp": 89, "fp": 36, "tn": 938, "fn": 98},
                "threshold_used": 60.0,
            }
        }
    )


class RetrospectivePilotReport(BaseModel):
    """
    Full retrospective pilot report container.

    This is the output of run_retrospective_pilot() — everything needed
    to generate a sales deck or internal analysis document.
    """

    tenant_id: str = Field(..., description="Customer/tenant identifier")
    model_version: Optional[str] = Field(None, description="ChainIQ model version used")
    metrics: RetrospectivePilotMetrics = Field(..., description="Core pilot metrics")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="When this report was generated")

    # === DISTRIBUTION BREAKDOWNS ===
    risk_distribution: Dict[str, int] = Field(
        default_factory=dict, description="Shipment counts by risk bucket (0-30, 30-60, 60-80, 80-100)"
    )
    decision_distribution: Dict[str, int] = Field(default_factory=dict, description="Shipment counts by recommended decision")

    # === SAMPLE DATA FOR REVIEW ===
    sample_high_risk: List[Dict[str, Any]] = Field(default_factory=list, description="Sample of highest-risk shipments for review")
    sample_false_positives: List[Dict[str, Any]] = Field(default_factory=list, description="High-risk predictions that turned out OK")
    sample_false_negatives: List[Dict[str, Any]] = Field(default_factory=list, description="Low-risk predictions that had bad outcomes")

    # === NOTES & WARNINGS ===
    notes: List[str] = Field(default_factory=list, description="Warnings, caveats, or notes about the analysis")


# =============================================================================
# CSV SCHEMA & LOADER
# =============================================================================

# Expected CSV columns for v0
REQUIRED_COLUMNS = ["shipment_id", "event_bad"]
OPTIONAL_COLUMNS = [
    "origin",
    "origin_country",
    "destination",
    "destination_country",
    "mode",
    "carrier_id",
    "carrier_code",
    "value_usd",
    "loss_usd",
    "planned_departure",
    "planned_arrival",
    "actual_departure",
    "actual_arrival",
]


def load_pilot_data_from_csv(path: Union[str, Path]) -> "pd.DataFrame":
    """
    Load and validate a pilot CSV file.

    Expected columns (v0):
        - shipment_id (str): Unique identifier for the shipment
        - event_bad (0/1 or bool): Whether shipment had a bad outcome
        - origin (str, optional): Origin location
        - destination (str, optional): Destination location
        - mode (str, optional): OCEAN/TRUCK/AIR/RAIL/INTERMODAL
        - carrier_id (str, optional): Carrier identifier
        - value_usd (float, optional): Cargo value in USD
        - loss_usd (float, optional): Realized loss amount if bad outcome

    Args:
        path: Path to CSV file

    Returns:
        DataFrame with validated columns

    Raises:
        ImportError: If pandas not available
        ValueError: If required columns missing
        FileNotFoundError: If CSV file doesn't exist
    """
    if not HAS_PANDAS:
        raise ImportError("pandas is required for CSV-based pilot analysis. Install: pip install pandas")

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Pilot CSV not found: {path}")

    df = pd.read_csv(path)
    _log_shape_only(df, "Loaded pilot CSV")

    # Validate required columns
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}. " f"Expected: {REQUIRED_COLUMNS}. " f"Found: {list(df.columns)}")

    # Normalize event_bad to boolean
    df["event_bad"] = df["event_bad"].astype(bool)

    # Log summary stats (no PII)
    logger.info(f"Pilot data: {len(df)} shipments, {df['event_bad'].sum()} bad events")

    return df


def validate_pilot_dataframe(df: "pd.DataFrame") -> List[str]:
    """
    Validate a pilot DataFrame and return warnings.

    Returns:
        List of warning messages (empty if all good)
    """
    warnings = []

    if len(df) < 50:
        warnings.append(f"Small dataset ({len(df)} shipments) — metrics may be unreliable")

    bad_rate = df["event_bad"].mean()
    if bad_rate < 0.01:
        warnings.append(f"Very low bad-event rate ({bad_rate:.1%}) — consider expanding outcome definition")
    if bad_rate > 0.5:
        warnings.append(f"High bad-event rate ({bad_rate:.1%}) — model may have limited lift opportunity")

    if "value_usd" not in df.columns:
        warnings.append("No value_usd column — hypothetical savings will use default values")

    if "loss_usd" not in df.columns:
        warnings.append("No loss_usd column — hypothetical savings based on value_usd estimates")

    return warnings


# =============================================================================
# BAD OUTCOME DEFINITION (Legacy support)
# =============================================================================


@dataclass
class BadOutcomeThresholds:
    """Configuration for what constitutes a 'bad' shipment outcome."""

    late_days: int = 3  # Late by > N days = bad
    damage_claim: bool = True  # Any damage claim = bad
    cost_overrun_pct: float = 0.15  # Cost > 15% over quote = bad


DEFAULT_BAD_THRESHOLDS = BadOutcomeThresholds()


def is_bad_outcome(
    row: dict,
    thresholds: BadOutcomeThresholds = DEFAULT_BAD_THRESHOLDS,
) -> bool:
    """
    Determine if a shipment had a 'bad' outcome based on actual results.

    Note: For v0 pilot CSV, prefer using the 'event_bad' column directly.
    This function is for deriving bad outcomes from raw operational data.

    Args:
        row: Dictionary with shipment outcome data
        thresholds: Thresholds for bad outcome determination

    Returns:
        True if bad outcome, False otherwise
    """
    # If event_bad is explicitly set, use it
    if "event_bad" in row:
        return bool(row["event_bad"])

    # Check late delivery
    late_days = row.get("late_days") or row.get("days_late", 0)
    if late_days > thresholds.late_days:
        return True

    # Check damage claim
    if thresholds.damage_claim and row.get("has_damage_claim", False):
        return True
    if thresholds.damage_claim and row.get("claim_amount_usd", 0) > 0:
        return True

    # Check cost overrun
    cost_overrun = row.get("cost_overrun_pct", 0)
    if cost_overrun > thresholds.cost_overrun_pct:
        return True

    return False


# =============================================================================
# DATA MAPPING
# =============================================================================


def map_row_to_context(
    row: Dict[str, Any],
    tenant_id: str = "retrospective-pilot",
) -> ShipmentRiskContext:
    """
    Map a pilot CSV row to ShipmentRiskContext.

    Handles common column naming variations gracefully.
    """
    # === SHIPMENT ID ===
    shipment_id = row.get("shipment_id") or row.get("id") or row.get("tracking_number")
    if not shipment_id:
        shipment_id = f"pilot-{hash(str(row)) % 100000}"

    # === MODE ===
    mode = str(row.get("mode", "TRUCK")).upper()
    if mode not in ["OCEAN", "TRUCK", "AIR", "RAIL", "INTERMODAL"]:
        mode = "TRUCK"

    # === GEOGRAPHY ===
    origin_country = str(
        row.get("origin_country") or row.get("origin_country_code") or row.get("shipper_country") or row.get("origin", "US")
    )[:2].upper()

    dest_country = str(
        row.get("destination_country")
        or row.get("dest_country")
        or row.get("destination_country_code")
        or row.get("consignee_country")
        or row.get("destination", "US")
    )[:2].upper()

    # === DATES ===
    planned_departure = _parse_datetime(row.get("planned_departure") or row.get("ship_date") or row.get("pickup_date"))
    planned_arrival = _parse_datetime(
        row.get("planned_arrival") or row.get("expected_delivery") or row.get("eta") or row.get("delivery_date")
    )

    if planned_departure is None:
        planned_departure = datetime(2024, 1, 1)
    if planned_arrival is None:
        planned_arrival = planned_departure

    # === OPTIONAL FIELDS ===
    actual_departure = _parse_datetime(row.get("actual_departure") or row.get("actual_ship_date"))
    actual_arrival = _parse_datetime(row.get("actual_arrival") or row.get("actual_delivery"))

    carrier_code = row.get("carrier_code") or row.get("carrier_id") or row.get("carrier") or row.get("scac")

    distance_km = _safe_float(row.get("distance_km") or row.get("distance_miles"))
    if row.get("distance_miles") and not row.get("distance_km"):
        distance_km = _safe_float(row.get("distance_miles")) * 1.60934

    value_usd = _safe_float(row.get("value_usd") or row.get("value") or row.get("cargo_value"))

    commodity_type = row.get("commodity_type") or row.get("commodity") or row.get("product_category")

    temp_controlled = row.get("temperature_controlled", False) or row.get("temp_controlled", False) or row.get("reefer", False)

    # Historical rates (may be pre-computed in customer data)
    lane_rate = _safe_float(row.get("prior_incident_rate_lane") or row.get("lane_delay_rate"))
    carrier_rate = _safe_float(row.get("prior_incident_rate_carrier") or row.get("carrier_delay_rate"))

    return ShipmentRiskContext(
        shipment_id=str(shipment_id),
        tenant_id=tenant_id,
        mode=mode,
        origin_country=origin_country,
        origin_region=row.get("origin_region") or row.get("origin_state"),
        destination_country=dest_country,
        destination_region=row.get("destination_region") or row.get("destination_state"),
        planned_departure=planned_departure,
        planned_arrival=planned_arrival,
        actual_departure=actual_departure,
        actual_arrival=actual_arrival,
        carrier_code=carrier_code,
        distance_km=distance_km,
        commodity_type=commodity_type,
        temperature_controlled=bool(temp_controlled),
        value_usd=value_usd,
        events=[],
        prior_incident_rate_lane=lane_rate,
        prior_incident_rate_carrier=carrier_rate,
    )


# Alias for backward compatibility
map_csv_row_to_context = map_row_to_context


def _parse_datetime(value: Any) -> Optional[datetime]:
    """Parse datetime from various formats."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value

    str_val = str(value).strip()
    if not str_val or str_val.lower() in ("nat", "nan", "none", "null", ""):
        return None

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%Y %H:%M",
        "%d-%m-%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(str_val, fmt)
        except ValueError:
            continue

    return None


def _safe_float(value: Any) -> Optional[float]:
    """Safely convert to float, handling NaN."""
    if value is None:
        return None
    try:
        f = float(value)
        return f if not np.isnan(f) else None
    except (ValueError, TypeError):
        return None


# =============================================================================
# METRICS COMPUTATION
# =============================================================================

DEFAULT_VALUE_USD = 10000.0  # Default cargo value when not specified
INTERVENTION_EFFECTIVENESS = 0.50  # Assume 50% of bad outcomes avoidable with early intervention


def compute_pilot_metrics(
    risk_scores: List[float],
    actuals: List[bool],
    values: List[float],
    losses: List[float],
    threshold: float = 60.0,
) -> RetrospectivePilotMetrics:
    """
    Compute canonical pilot metrics from scores and labels.

    Args:
        risk_scores: Predicted risk scores (0-100)
        actuals: True labels (True if bad outcome)
        values: Shipment values in USD
        losses: Realized losses in USD (0 if no loss)
        threshold: Risk score threshold for confusion matrix

    Returns:
        RetrospectivePilotMetrics with all computed values
    """
    scores = np.array(risk_scores)
    labels = np.array(actuals, dtype=bool)
    vals = np.array(values)
    loss_arr = np.array(losses)

    n = len(scores)
    n_bad = int(labels.sum())
    bad_rate = float(labels.mean()) if n > 0 else 0.0

    # Initialize metrics with required fields
    metrics = RetrospectivePilotMetrics(
        total_shipments=n,
        total_bad_events=n_bad,
        bad_event_rate=bad_rate,
    )

    if n == 0 or n_bad == 0:
        return metrics

    # === AUC-ROC ===
    if HAS_SKLEARN:
        try:
            metrics.auc_roc = float(roc_auc_score(labels, scores / 100))
        except ValueError:
            metrics.auc_roc = 0.5
    else:
        # Simple approximation if sklearn unavailable
        metrics.auc_roc = None

    # === TOP 10% METRICS ===
    top_10_threshold = float(np.percentile(scores, 90))
    top_10_mask = scores >= top_10_threshold
    top_10_count = int(top_10_mask.sum())

    if top_10_count > 0:
        # Precision at top 10%: what fraction of top 10% are actually bad?
        metrics.precision_at_top_10pct = float(labels[top_10_mask].mean())

        # Capture rate: what fraction of all bad events are in top 10%?
        bad_in_top_10 = int(labels[top_10_mask].sum())
        metrics.capture_rate_top_10pct = bad_in_top_10 / n_bad

        # Lift: how much better than random?
        if bad_rate > 0:
            metrics.lift_at_top_10pct = metrics.precision_at_top_10pct / bad_rate

    # === BUSINESS METRICS ===
    metrics.total_loss_usd = float(loss_arr[labels].sum()) if loss_arr.any() else None

    # Hypothetical savings: if we intervened on top 10% risk shipments
    # Assume INTERVENTION_EFFECTIVENESS of losses could be avoided
    top_10_bad_mask = top_10_mask & labels
    if metrics.total_loss_usd and metrics.total_loss_usd > 0:
        loss_in_top_10 = float(loss_arr[top_10_bad_mask].sum())
    else:
        # Fallback: use value_usd as proxy for potential loss
        loss_in_top_10 = float(vals[top_10_bad_mask].sum()) * 0.1  # Assume 10% of value at risk

    metrics.hypothetical_savings_usd = loss_in_top_10 * INTERVENTION_EFFECTIVENESS

    # === CONFUSION MATRIX ===
    predictions_binary = scores >= threshold
    if HAS_SKLEARN:
        cm = sk_confusion_matrix(labels, predictions_binary)
        tn, fp, fn, tp = cm.ravel()
    else:
        tp = int(((predictions_binary) & (labels)).sum())
        fp = int(((predictions_binary) & (~labels)).sum())
        tn = int(((~predictions_binary) & (~labels)).sum())
        fn = int(((~predictions_binary) & (labels)).sum())

    metrics.confusion_matrix = {"tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn)}
    metrics.threshold_used = threshold

    return metrics


# Legacy alias
def compute_evaluation_metrics(
    predictions: List[float],
    actuals: List[bool],
    values: List[float],
    intervention_effectiveness: float = 0.5,
) -> RetrospectivePilotMetrics:
    """Legacy wrapper for compute_pilot_metrics."""
    losses = [0.0] * len(predictions)
    return compute_pilot_metrics(predictions, actuals, values, losses, threshold=60.0)


# =============================================================================
# MAIN PILOT RUNNER
# =============================================================================


def run_retrospective_pilot(
    data: Union["pd.DataFrame", List[Dict[str, Any]]],
    tenant_id: str,
    scorer: Optional[ChainIQScorer] = None,
    threshold: float = 60.0,
) -> RetrospectivePilotReport:
    """
    Run a full retrospective pilot analysis.

    This is the main entry point for the "give us 3-6 months of history" sales motion.

    Args:
        data: DataFrame or list of dicts with shipment history
        tenant_id: Customer identifier (for logging/partitioning)
        scorer: ChainIQ scorer instance (uses default heuristic if None)
        threshold: Risk score threshold for confusion matrix (default 60)

    Returns:
        RetrospectivePilotReport with metrics and distributions
    """
    # Convert DataFrame to list of dicts if needed
    if HAS_PANDAS and isinstance(data, pd.DataFrame):
        records = data.to_dict(orient="records")
        warnings = validate_pilot_dataframe(data)
    else:
        records = list(data)
        warnings = []

    _log_shape_only(records, "Processing pilot data")

    # Initialize scorer
    if scorer is None:
        scorer = get_default_scorer()

    # Build contexts from rows
    contexts = [map_row_to_context(row, tenant_id) for row in records]

    # Score all shipments
    assessments = scorer.score_batch(contexts)

    # Extract arrays for metrics computation
    risk_scores = [a.risk_score for a in assessments]
    actuals = [is_bad_outcome(row) for row in records]
    values = [_safe_float(row.get("value_usd")) or DEFAULT_VALUE_USD for row in records]
    losses = [_safe_float(row.get("loss_usd")) or 0.0 for row in records]

    # Compute metrics
    metrics = compute_pilot_metrics(risk_scores, actuals, values, losses, threshold)

    # Compute distributions
    risk_distribution = {"0-30": 0, "30-60": 0, "60-80": 0, "80-100": 0}
    for score in risk_scores:
        if score < 30:
            risk_distribution["0-30"] += 1
        elif score < 60:
            risk_distribution["30-60"] += 1
        elif score < 80:
            risk_distribution["60-80"] += 1
        else:
            risk_distribution["80-100"] += 1

    decision_distribution = {"APPROVE": 0, "TIGHTEN_TERMS": 0, "HOLD": 0, "ESCALATE": 0}
    for a in assessments:
        if a.decision in decision_distribution:
            decision_distribution[a.decision] += 1

    # Sample data for review
    sorted_by_risk = sorted(zip(assessments, actuals, records), key=lambda x: -x[0].risk_score)

    # Top 10 highest risk
    sample_high_risk = [
        {
            "shipment_id": a.shipment_id,
            "risk_score": a.risk_score,
            "decision": a.decision,
            "actual_bad": actual,
            "summary": a.summary_reason,
        }
        for a, actual, _ in sorted_by_risk[:10]
    ]

    # False positives (high risk, good outcome)
    false_positives = [(a, actual, row) for a, actual, row in sorted_by_risk if a.risk_score >= 60 and not actual][:5]
    sample_fps = [
        {
            "shipment_id": a.shipment_id,
            "risk_score": a.risk_score,
            "predicted": a.decision,
            "top_factors": [f.human_label for f in a.top_factors[:3]],
        }
        for a, _, _ in false_positives
    ]

    # False negatives (low risk, bad outcome)
    false_negatives = [(a, actual, row) for a, actual, row in sorted_by_risk if a.risk_score < 40 and actual][:5]
    sample_fns = [
        {
            "shipment_id": a.shipment_id,
            "risk_score": a.risk_score,
            "predicted": a.decision,
            "actual_outcome": "BAD",
        }
        for a, _, _ in false_negatives
    ]

    # Build report
    return RetrospectivePilotReport(
        tenant_id=tenant_id,
        model_version=scorer.model.version,
        metrics=metrics,
        generated_at=datetime.utcnow(),
        risk_distribution=risk_distribution,
        decision_distribution=decision_distribution,
        sample_high_risk=sample_high_risk,
        sample_false_positives=sample_fps,
        sample_false_negatives=sample_fns,
        notes=warnings,
    )


def run_retrospective_from_csv(
    csv_path: Union[str, Path],
    tenant_id: str,
    scorer: Optional[ChainIQScorer] = None,
    threshold: float = 60.0,
) -> RetrospectivePilotReport:
    """
    Run retrospective pilot from CSV file path.

    Convenience wrapper that handles loading and validation.

    Args:
        csv_path: Path to pilot CSV file
        tenant_id: Customer identifier
        scorer: ChainIQ scorer instance (optional)
        threshold: Risk score threshold for confusion matrix

    Returns:
        RetrospectivePilotReport
    """
    df = load_pilot_data_from_csv(csv_path)
    return run_retrospective_pilot(df, tenant_id, scorer, threshold)


# =============================================================================
# MARKDOWN SUMMARY BUILDER
# =============================================================================


def build_markdown_summary(report: RetrospectivePilotReport) -> str:
    """
    Build a human-readable markdown summary for sales decks.

    This output is designed to be copy-pasted into presentations
    or shared directly with prospects.

    Args:
        report: RetrospectivePilotReport from run_retrospective_pilot()

    Returns:
        Markdown-formatted string
    """
    m = report.metrics

    lines = [
        "# ChainIQ Retrospective Pilot Report",
        "",
        f"**Tenant:** {report.tenant_id}  ",
        f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}  ",
        f"**Model Version:** {report.model_version or 'default'}",
        "",
        "---",
        "",
        "## Overview",
        "",
        f"We analyzed **{m.total_shipments:,}** historical shipments to evaluate how ChainIQ's "
        f"risk scoring would have performed on your freight network.",
        "",
        f"- **Bad Events Found:** {m.total_bad_events:,} shipments ({m.bad_event_rate:.1%} of total)",
    ]

    if m.total_loss_usd:
        lines.append(f"- **Total Realized Loss:** ${m.total_loss_usd:,.0f}")

    lines.extend(
        [
            "",
            "---",
            "",
            "## Key Metrics",
            "",
        ]
    )

    # AUC-ROC interpretation
    if m.auc_roc is not None:
        auc_quality = "excellent" if m.auc_roc >= 0.85 else "good" if m.auc_roc >= 0.75 else "moderate" if m.auc_roc >= 0.65 else "limited"
        lines.extend(
            [
                f"### Model Discrimination (AUC-ROC): **{m.auc_roc:.2f}**",
                "",
                f"This indicates **{auc_quality}** ability to distinguish high-risk from low-risk shipments. "
                f"(0.5 = random guessing, 1.0 = perfect prediction)",
                "",
            ]
        )

    # Lift and capture
    if m.lift_at_top_10pct is not None:
        lines.extend(
            [
                f"### Risk Concentration (Lift @ Top 10%): **{m.lift_at_top_10pct:.1f}x**",
                "",
                f"The top 10% highest-risk shipments have **{m.lift_at_top_10pct:.1f}x** the bad-event rate "
                f"of the overall population. This means ChainIQ effectively concentrates risk.",
                "",
            ]
        )

    if m.capture_rate_top_10pct is not None:
        lines.extend(
            [
                f"### Bad Event Capture Rate: **{m.capture_rate_top_10pct:.0%}**",
                "",
                f"By focusing on just the top 10% of risk-scored shipments, we would have caught "
                f"**{m.capture_rate_top_10pct:.0%}** of all bad events before they happened.",
                "",
            ]
        )

    # Business impact
    if m.hypothetical_savings_usd is not None and m.hypothetical_savings_usd > 0:
        lines.extend(
            [
                f"### Hypothetical Savings: **${m.hypothetical_savings_usd:,.0f}**",
                "",
                f"If we had intervened on the top 10% highest-risk shipments that eventually had bad outcomes, "
                f"we estimate approximately **${m.hypothetical_savings_usd:,.0f}** in losses could have been "
                f"avoided or mitigated.",
                "",
            ]
        )

    # Risk distribution
    lines.extend(
        [
            "---",
            "",
            "## Risk Score Distribution",
            "",
            "| Risk Tier | Shipments | Interpretation |",
            "|-----------|-----------|----------------|",
            f"| 0-30 (Low) | {report.risk_distribution.get('0-30', 0):,} | Safe to auto-approve |",
            f"| 30-60 (Medium) | {report.risk_distribution.get('30-60', 0):,} | Standard processing |",
            f"| 60-80 (High) | {report.risk_distribution.get('60-80', 0):,} | Tighten terms |",
            f"| 80-100 (Critical) | {report.risk_distribution.get('80-100', 0):,} | Hold/Escalate |",
            "",
        ]
    )

    # Decision distribution
    lines.extend(
        [
            "## Recommended Actions Distribution",
            "",
            "| Decision | Count |",
            "|----------|-------|",
        ]
    )
    for decision, count in report.decision_distribution.items():
        lines.append(f"| {decision} | {count:,} |")

    # Confusion matrix
    if m.confusion_matrix:
        cm = m.confusion_matrix
        precision = cm["tp"] / (cm["tp"] + cm["fp"]) if (cm["tp"] + cm["fp"]) > 0 else 0
        recall = cm["tp"] / (cm["tp"] + cm["fn"]) if (cm["tp"] + cm["fn"]) > 0 else 0

        lines.extend(
            [
                "",
                "---",
                "",
                f"## Model Performance at Threshold {m.threshold_used:.0f}",
                "",
                "| | Predicted Bad | Predicted Good |",
                "|---|--------------|----------------|",
                f"| **Actually Bad** | {cm['tp']} (TP) | {cm['fn']} (FN) |",
                f"| **Actually Good** | {cm['fp']} (FP) | {cm['tn']} (TN) |",
                "",
                f"- **Precision:** {precision:.1%} (of flagged shipments, how many were actually bad)",
                f"- **Recall:** {recall:.1%} (of bad shipments, how many did we catch)",
                "",
            ]
        )

    # What this means
    lines.extend(
        [
            "---",
            "",
            "## What This Means for You",
            "",
        ]
    )

    if m.lift_at_top_10pct and m.lift_at_top_10pct >= 2.0:
        lines.extend(
            [
                f"✅ **ChainIQ can meaningfully concentrate risk.** The top 10% risk tier has "
                f"{m.lift_at_top_10pct:.1f}x the problem rate of your overall shipments.",
                "",
            ]
        )

    if m.capture_rate_top_10pct and m.capture_rate_top_10pct >= 0.30:
        lines.extend(
            [
                f"✅ **Targeted intervention is viable.** By focusing operator attention on just 10% "
                f"of shipments, you could address {m.capture_rate_top_10pct:.0%} of problems.",
                "",
            ]
        )

    if m.hypothetical_savings_usd and m.hypothetical_savings_usd > 10000:
        lines.extend(
            [
                f"✅ **Real dollar impact.** Estimated ${m.hypothetical_savings_usd:,.0f} in "
                f"avoidable losses identified in this historical period alone.",
                "",
            ]
        )

    # Notes/warnings
    if report.notes:
        lines.extend(
            [
                "---",
                "",
                "## Notes & Caveats",
                "",
            ]
        )
        for note in report.notes:
            lines.append(f"- {note}")

    lines.extend(
        [
            "",
            "---",
            "",
            "*Report generated by ChainIQ v0.1 — Glass-Box Risk Brain*  ",
            '*"Code = Cash. Explain or Perish."*',
        ]
    )

    return "\n".join(lines)


# =============================================================================
# JSON EXPORT
# =============================================================================


def export_report_to_json(report: RetrospectivePilotReport, output_path: Union[str, Path]) -> None:
    """Export retrospective report to JSON file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(report.model_dump_json(indent=2))


# =============================================================================
# LEGACY COMPATIBILITY ALIASES
# =============================================================================

# Keep old dataclass names as aliases for backward compatibility
EvaluationMetrics = RetrospectivePilotMetrics
RetrospectiveReport = RetrospectivePilotReport
