"""Risk metrics computation module.

Computes Maggie-style aggregate metrics from RiskEvaluation rows and persists them
as RiskModelMetrics records.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.risk.db_models import RiskEvaluation, RiskModelMetrics


def evaluate_red_flags(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Apply Maggie's red-flag rules to computed metrics.

    Returns:
        {
            "has_failures": bool,
            "has_warnings": bool,
            "fail_messages": List[str],
            "warning_messages": List[str],
        }
    """
    fail_messages: List[str] = []
    warning_messages: List[str] = []

    # FAIL: Blind Spot – Critical Incident Recall < 0.50
    if metrics.get("critical_incident_recall", 1.0) < 0.50:
        fail_messages.append("FAIL: Critical Incident Recall < 50% (Too many missed losses)")

    # FAIL: Spam Cannon – Ops Workload % > 15
    if metrics.get("ops_workload_percent", 0.0) > 15.0:
        fail_messages.append("FAIL: Ops Workload > 15% (Too many shipments flagged HIGH)")

    # FAIL: Calibration – Non-monotonic
    if not metrics.get("calibration_monotonic", True):
        fail_messages.append("FAIL: Risk bands not monotonic (LOW <= MEDIUM <= HIGH)")

    # FAIL: Calibration – Poor separation
    if metrics.get("calibration_ratio_high_vs_low", 2.0) < 2.0:
        fail_messages.append("FAIL: High/Low incident rate ratio < 2.0 (poor separation)")

    # WARN: Value Leak – Loss Value Coverage < 0.50
    if metrics.get("loss_value_coverage_pct", 1.0) < 0.50:
        warning_messages.append("WARN: Loss Value Coverage < 50% (high-value losses slipping through)")

    return {
        "has_failures": len(fail_messages) > 0,
        "has_warnings": len(warning_messages) > 0,
        "fail_messages": fail_messages,
        "warning_messages": warning_messages,
    }


def compute_and_persist_risk_metrics(
    session: Session,
    model_version: Optional[str] = None,
    window_days: Optional[int] = None,
) -> Optional[RiskModelMetrics]:
    """Compute aggregate risk metrics from RiskEvaluation rows and persist a RiskModelMetrics record.

    Args:
        session: SQLAlchemy session bound to our SQLite/DB.
        model_version: Optional filter; if provided, only include evaluations for that model_version.
        window_days: Optional lookback window; if provided, only include evaluations with timestamp >= now - window_days.

    Returns:
        The created RiskModelMetrics ORM instance, or None if no evaluations matched.
    """
    query = session.query(RiskEvaluation)

    if model_version is not None:
        query = query.filter(RiskEvaluation.model_version == model_version)

    if window_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        query = query.filter(RiskEvaluation.timestamp >= cutoff)

    rows: List[RiskEvaluation] = query.all()

    if not rows:
        return None

    # Basic counts
    eval_count = len(rows)
    scores = [r.risk_score for r in rows]
    avg_score = sum(scores) / eval_count if eval_count > 0 else 0.0

    # Percentiles
    sorted_scores = sorted(scores)
    p50_score = sorted_scores[int(len(sorted_scores) * 0.50)] if sorted_scores else None
    p90_score = sorted_scores[int(len(sorted_scores) * 0.90)] if sorted_scores else None
    p99_score = sorted_scores[min(int(len(sorted_scores) * 0.99), len(sorted_scores) - 1)] if sorted_scores else None

    # Band counts
    band_counts: Dict[str, int] = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for r in rows:
        band = r.risk_band.upper() if r.risk_band else "LOW"
        if band in band_counts:
            band_counts[band] += 1
        else:
            band_counts[band] = 1

    count_high = band_counts.get("HIGH", 0)
    count_medium = band_counts.get("MEDIUM", 0)
    count_low = band_counts.get("LOW", 0)

    # Ops workload
    ops_workload_percent = (count_high / eval_count) * 100 if eval_count > 0 else 0.0

    # Incident rates per band
    incidents_low = sum(1 for r in rows if r.risk_band and r.risk_band.upper() == "LOW" and r.is_incident)
    incidents_medium = sum(1 for r in rows if r.risk_band and r.risk_band.upper() == "MEDIUM" and r.is_incident)
    incidents_high = sum(1 for r in rows if r.risk_band and r.risk_band.upper() == "HIGH" and r.is_incident)

    incident_rate_low = incidents_low / max(count_low, 1)
    incident_rate_medium = incidents_medium / max(count_medium, 1)
    incident_rate_high = incidents_high / max(count_high, 1)

    # Critical Incident Recall (Loss Recall)
    total_losses = sum(1 for r in rows if r.is_loss)
    caught_losses = sum(1 for r in rows if r.is_loss and r.risk_band and r.risk_band.upper() == "HIGH")
    critical_incident_recall = caught_losses / total_losses if total_losses > 0 else 1.0

    # High Risk Precision
    high_risk_precision = incidents_high / max(count_high, 1)

    # Loss Value Coverage
    total_loss_value_all = sum(r.loss_value or 0.0 for r in rows if r.is_loss)
    total_loss_value_captured = sum(r.loss_value or 0.0 for r in rows if r.is_loss and r.risk_band and r.risk_band.upper() == "HIGH")
    loss_value_coverage_pct = total_loss_value_captured / total_loss_value_all if total_loss_value_all > 0 else 1.0

    # Calibration
    calibration_monotonic = incident_rate_low <= incident_rate_medium <= incident_rate_high
    calibration_ratio_high_vs_low = incident_rate_high / max(incident_rate_low, 0.001)

    # Red flags
    metrics_dict = {
        "critical_incident_recall": critical_incident_recall,
        "ops_workload_percent": ops_workload_percent,
        "calibration_monotonic": calibration_monotonic,
        "calibration_ratio_high_vs_low": calibration_ratio_high_vs_low,
        "loss_value_coverage_pct": loss_value_coverage_pct,
    }
    red_flags = evaluate_red_flags(metrics_dict)

    # Determine model version for record
    if model_version:
        record_model_version = model_version
    else:
        # Use most common model version from rows
        version_counts: Dict[str, int] = {}
        for r in rows:
            v = r.model_version or "unknown"
            version_counts[v] = version_counts.get(v, 0) + 1
        record_model_version = max(version_counts, key=version_counts.get) if version_counts else "mixed"

    # Timestamps
    timestamps = [r.timestamp for r in rows if r.timestamp]
    window_start = min(timestamps) if timestamps else datetime.now(timezone.utc)
    window_end = max(timestamps) if timestamps else datetime.now(timezone.utc)

    # Create and persist record
    record = RiskModelMetrics(
        model_version=record_model_version,
        window_start=window_start,
        window_end=window_end,
        eval_count=eval_count,
        avg_score=avg_score,
        p50_score=p50_score,
        p90_score=p90_score,
        p99_score=p99_score,
        risk_band_counts=band_counts,
        critical_incident_recall=critical_incident_recall,
        high_risk_precision=high_risk_precision,
        ops_workload_percent=ops_workload_percent,
        incident_rate_low=incident_rate_low,
        incident_rate_medium=incident_rate_medium,
        incident_rate_high=incident_rate_high,
        calibration_monotonic=1 if calibration_monotonic else 0,
        calibration_ratio_high_vs_low=calibration_ratio_high_vs_low,
        loss_value_coverage_pct=loss_value_coverage_pct,
        has_failures=1 if red_flags["has_failures"] else 0,
        has_warnings=1 if red_flags["has_warnings"] else 0,
        fail_messages=red_flags["fail_messages"],
        warning_messages=red_flags["warning_messages"],
        data_freshness_ts=datetime.now(timezone.utc),
    )

    session.add(record)
    session.commit()
    session.refresh(record)

    return record
