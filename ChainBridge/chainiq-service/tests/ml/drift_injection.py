"""ChainIQ Drift Injection Scenarios — Phase 2 Failure Drill Support.

Provides deterministic drift injection for ML failure drills.
Each scenario is reproducible with fixed seeds and documented parameters.

════════════════════════════════════════════════════════════════════════════════
🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷
GID-10 — MAGGIE (ML & APPLIED AI)
PAC-MAGGIE-G1-PHASE-2-RISK-MODEL-DRIFT-FAILURE-DRILLS-01
🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷
════════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np


class DriftScenario(str, Enum):
    """Enumeration of drift injection scenarios."""

    # ML-01: Feature distribution drift
    GRADUAL_MEAN_SHIFT = "GRADUAL_MEAN_SHIFT"
    SUDDEN_MEAN_SHIFT = "SUDDEN_MEAN_SHIFT"
    VARIANCE_EXPLOSION = "VARIANCE_EXPLOSION"
    DISTRIBUTION_MODE_CHANGE = "DISTRIBUTION_MODE_CHANGE"

    # ML-02: Calibration decay
    CALIBRATION_DRIFT_MILD = "CALIBRATION_DRIFT_MILD"
    CALIBRATION_DRIFT_SEVERE = "CALIBRATION_DRIFT_SEVERE"
    CALIBRATION_DRIFT_CRITICAL = "CALIBRATION_DRIFT_CRITICAL"

    # ML-04: Adversarial perturbation
    ADVERSARIAL_OUTLIERS = "ADVERSARIAL_OUTLIERS"
    ADVERSARIAL_BOUNDARY = "ADVERSARIAL_BOUNDARY"
    ADVERSARIAL_FEATURE_FLIP = "ADVERSARIAL_FEATURE_FLIP"


@dataclass
class InjectionConfig:
    """Configuration for a drift injection scenario."""

    scenario: DriftScenario
    seed: int = 42  # Reproducibility
    severity: float = 1.0  # Multiplier for drift magnitude
    affected_features: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class InjectedDrift:
    """Result of drift injection with original and modified stats."""

    config: InjectionConfig
    baseline_stats: Dict[str, Dict[str, float]]
    modified_stats: Dict[str, Dict[str, float]]
    expected_drift_bucket: str
    expected_action: str
    injection_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# =============================================================================
# BASELINE FEATURE DISTRIBUTIONS
# =============================================================================

def get_canonical_baseline() -> Dict[str, Dict[str, float]]:
    """Return canonical baseline feature statistics for ChainIQ risk model.

    These represent production-stable distributions.
    """
    return {
        "carrier_incident_rate_90d": {
            "mean": 0.05,
            "std": 0.02,
            "count": 50000,
            "min": 0.0,
            "max": 0.25,
        },
        "recent_delay_events": {
            "mean": 1.2,
            "std": 0.8,
            "count": 50000,
            "min": 0,
            "max": 10,
        },
        "iot_alert_count": {
            "mean": 0.3,
            "std": 0.5,
            "count": 50000,
            "min": 0,
            "max": 15,
        },
        "border_crossing_count": {
            "mean": 1.5,
            "std": 1.0,
            "count": 50000,
            "min": 0,
            "max": 8,
        },
        "value_usd": {
            "mean": 75000,
            "std": 30000,
            "count": 50000,
            "min": 1000,
            "max": 500000,
        },
        "lane_risk_index": {
            "mean": 0.35,
            "std": 0.15,
            "count": 50000,
            "min": 0.0,
            "max": 1.0,
        },
        "eta_deviation_hours": {
            "mean": 4.0,
            "std": 3.0,
            "count": 50000,
            "min": -24,
            "max": 72,
        },
        "shipper_reliability_score": {
            "mean": 0.82,
            "std": 0.12,
            "count": 50000,
            "min": 0.0,
            "max": 1.0,
        },
    }


# =============================================================================
# ML-01: FEATURE DISTRIBUTION DRIFT SCENARIOS
# =============================================================================

def inject_gradual_mean_shift(
    baseline: Dict[str, Dict[str, float]],
    severity: float = 1.0,
    affected_features: Optional[List[str]] = None,
) -> Dict[str, Dict[str, float]]:
    """Inject gradual mean shift (typical real-world drift).

    Simulates gradual distribution shift over time, e.g., seasonal changes.

    Args:
        baseline: Baseline feature statistics
        severity: Drift multiplier (1.0 = ~2 std shift, 2.0 = ~4 std shift)
        affected_features: Features to drift (None = all)

    Returns:
        Modified feature statistics
    """
    modified = {}
    targets = affected_features or list(baseline.keys())

    for feature, stats in baseline.items():
        if feature in targets:
            std = stats.get("std", 1.0)
            shift = 2.0 * std * severity  # 2 std shift per severity unit

            modified[feature] = {
                **stats,
                "mean": stats["mean"] + shift,
                "std": stats["std"] * (1.0 + 0.3 * severity),  # Slight variance increase
                "count": int(stats["count"] * 0.2),  # Smaller recent window
            }
        else:
            modified[feature] = stats.copy()

    return modified


def inject_sudden_mean_shift(
    baseline: Dict[str, Dict[str, float]],
    severity: float = 1.0,
    affected_features: Optional[List[str]] = None,
) -> Dict[str, Dict[str, float]]:
    """Inject sudden/abrupt mean shift (covariate shift).

    Simulates sudden regime change, e.g., new carrier entering market.

    Args:
        baseline: Baseline feature statistics
        severity: Drift multiplier (1.0 = ~5 std shift)
        affected_features: Features to drift (None = all)

    Returns:
        Modified feature statistics
    """
    modified = {}
    targets = affected_features or list(baseline.keys())

    for feature, stats in baseline.items():
        if feature in targets:
            std = stats.get("std", 1.0)
            shift = 5.0 * std * severity  # 5 std shift — severe

            modified[feature] = {
                **stats,
                "mean": stats["mean"] + shift,
                "std": stats["std"] * 0.5,  # Tighter distribution (concentrated shift)
                "count": int(stats["count"] * 0.05),  # Very recent small window
            }
        else:
            modified[feature] = stats.copy()

    return modified


def inject_variance_explosion(
    baseline: Dict[str, Dict[str, float]],
    severity: float = 1.0,
    affected_features: Optional[List[str]] = None,
) -> Dict[str, Dict[str, float]]:
    """Inject variance explosion (increased uncertainty).

    Simulates increased variability, e.g., supply chain disruption.

    Args:
        baseline: Baseline feature statistics
        severity: Variance multiplier (1.0 = 3x variance, 2.0 = 9x variance)
        affected_features: Features to drift (None = all)

    Returns:
        Modified feature statistics
    """
    modified = {}
    targets = affected_features or list(baseline.keys())

    for feature, stats in baseline.items():
        if feature in targets:
            variance_mult = 3.0 ** severity

            modified[feature] = {
                **stats,
                "mean": stats["mean"],  # Mean unchanged
                "std": stats["std"] * np.sqrt(variance_mult),
                "count": int(stats["count"] * 0.1),
            }
        else:
            modified[feature] = stats.copy()

    return modified


# =============================================================================
# ML-02: CALIBRATION DECAY SCENARIOS
# =============================================================================

def generate_calibration_decay_mild() -> Dict[str, float]:
    """Generate mild calibration decay metrics (ECE ~6%).

    Returns:
        Calibration metrics dictionary
    """
    return {
        "ece": 0.06,  # Above 5% threshold
        "mce": 0.12,
        "brier_score": 0.22,
        "expected_action": "RECALIBRATE",
    }


def generate_calibration_decay_severe() -> Dict[str, float]:
    """Generate severe calibration decay metrics (ECE ~12%).

    Returns:
        Calibration metrics dictionary
    """
    return {
        "ece": 0.12,  # Well above threshold
        "mce": 0.28,
        "brier_score": 0.32,
        "expected_action": "RECALIBRATE",
    }


def generate_calibration_decay_critical() -> Dict[str, float]:
    """Generate critical calibration decay metrics (ECE >15%).

    Returns:
        Calibration metrics dictionary
    """
    return {
        "ece": 0.18,  # Critical threshold
        "mce": 0.40,
        "brier_score": 0.45,
        "expected_action": "HALT",
    }


# =============================================================================
# ML-04: ADVERSARIAL PERTURBATION SCENARIOS
# =============================================================================

def inject_adversarial_outliers(
    baseline: Dict[str, Dict[str, float]],
    severity: float = 1.0,
    affected_features: Optional[List[str]] = None,
) -> Dict[str, Dict[str, float]]:
    """Inject adversarial outlier values (extreme points).

    Simulates adversarial attack with extreme feature values.

    Args:
        baseline: Baseline feature statistics
        severity: Extremity multiplier (1.0 = 20 std, 2.0 = 40 std)
        affected_features: Features to attack (None = all)

    Returns:
        Modified feature statistics
    """
    modified = {}
    targets = affected_features or list(baseline.keys())

    for feature, stats in baseline.items():
        if feature in targets:
            std = stats.get("std", 1.0)
            extreme_shift = 20.0 * std * severity

            modified[feature] = {
                **stats,
                "mean": stats["mean"] + extreme_shift,
                "std": stats["std"] * 0.1,  # Very tight (concentrated attack)
                "count": 10,  # Small attack batch
            }
        else:
            modified[feature] = stats.copy()

    return modified


def inject_adversarial_boundary(
    baseline: Dict[str, Dict[str, float]],
) -> Dict[str, Dict[str, float]]:
    """Inject adversarial values at decision boundaries.

    Targets risk band boundaries to exploit threshold weaknesses.

    Returns:
        Modified feature statistics
    """
    # Target boundary-sensitive features
    modified = baseline.copy()

    # Push lane_risk_index to boundary (0.5 = medium/high boundary)
    if "lane_risk_index" in modified:
        modified["lane_risk_index"] = {
            **baseline["lane_risk_index"],
            "mean": 0.5,  # Exactly at boundary
            "std": 0.001,  # Extremely tight
            "count": 100,
        }

    # Push value_usd to $100k boundary
    if "value_usd" in modified:
        modified["value_usd"] = {
            **baseline["value_usd"],
            "mean": 99999.99,  # Just below threshold
            "std": 0.01,
            "count": 100,
        }

    return modified


# =============================================================================
# SCENARIO FACTORY
# =============================================================================

def create_drift_scenario(
    scenario: DriftScenario,
    severity: float = 1.0,
    affected_features: Optional[List[str]] = None,
) -> InjectedDrift:
    """Factory function to create drift injection scenarios.

    Args:
        scenario: Type of drift scenario
        severity: Magnitude multiplier
        affected_features: Specific features to affect (None = defaults)

    Returns:
        InjectedDrift with baseline and modified statistics
    """
    baseline = get_canonical_baseline()
    config = InjectionConfig(
        scenario=scenario,
        severity=severity,
        affected_features=affected_features or [],
    )

    # ML-01 scenarios
    if scenario == DriftScenario.GRADUAL_MEAN_SHIFT:
        modified = inject_gradual_mean_shift(baseline, severity, affected_features)
        expected_bucket = "MODERATE" if severity < 1.5 else "SEVERE"
        expected_action = "ALERT" if severity < 1.5 else "ESCALATE"
        config.description = f"Gradual mean shift ({severity:.1f}x severity)"

    elif scenario == DriftScenario.SUDDEN_MEAN_SHIFT:
        modified = inject_sudden_mean_shift(baseline, severity, affected_features)
        expected_bucket = "SEVERE" if severity < 1.5 else "CRITICAL"
        expected_action = "ESCALATE" if severity < 1.5 else "HALT"
        config.description = f"Sudden mean shift ({severity:.1f}x severity)"

    elif scenario == DriftScenario.VARIANCE_EXPLOSION:
        modified = inject_variance_explosion(baseline, severity, affected_features)
        expected_bucket = "MODERATE" if severity < 1.5 else "SEVERE"
        expected_action = "ALERT" if severity < 1.5 else "ESCALATE"
        config.description = f"Variance explosion ({severity:.1f}x severity)"

    # ML-04 scenarios
    elif scenario == DriftScenario.ADVERSARIAL_OUTLIERS:
        modified = inject_adversarial_outliers(baseline, severity, affected_features)
        expected_bucket = "CRITICAL"
        expected_action = "HALT"
        config.description = f"Adversarial outliers ({severity:.1f}x severity)"

    elif scenario == DriftScenario.ADVERSARIAL_BOUNDARY:
        modified = inject_adversarial_boundary(baseline)
        expected_bucket = "MODERATE"  # Less detectable
        expected_action = "ALERT"
        config.description = "Adversarial boundary attack"

    else:
        raise ValueError(f"Unknown scenario: {scenario}")

    return InjectedDrift(
        config=config,
        baseline_stats=baseline,
        modified_stats=modified,
        expected_drift_bucket=expected_bucket,
        expected_action=expected_action,
    )


# =============================================================================
# EVIDENCE GENERATION
# =============================================================================

def generate_drill_evidence(
    drill_id: str,
    scenario: DriftScenario,
    injected: InjectedDrift,
    actual_bucket: str,
    actual_action: str,
) -> Dict[str, Any]:
    """Generate evidence artifact for audit trail.

    Args:
        drill_id: Failure drill identifier (e.g., "ML-01")
        scenario: Drift scenario used
        injected: Injection results
        actual_bucket: Observed drift bucket
        actual_action: Observed action

    Returns:
        Evidence dictionary for WRAP
    """
    return {
        "drill_id": drill_id,
        "scenario": scenario.value,
        "severity": injected.config.severity,
        "timestamp": injected.injection_timestamp,
        "expected": {
            "bucket": injected.expected_drift_bucket,
            "action": injected.expected_action,
        },
        "actual": {
            "bucket": actual_bucket,
            "action": actual_action,
        },
        "passed": (
            actual_bucket == injected.expected_drift_bucket
            or (  # Allow more severe buckets
                _bucket_severity(actual_bucket) >= _bucket_severity(injected.expected_drift_bucket)
            )
        ),
        "affected_features": injected.config.affected_features,
        "sample_stats": {
            "baseline_count": sum(
                s.get("count", 0) for s in injected.baseline_stats.values()
            ),
            "modified_count": sum(
                s.get("count", 0) for s in injected.modified_stats.values()
            ),
        },
    }


def _bucket_severity(bucket: str) -> int:
    """Get numeric severity of drift bucket for comparison."""
    severity_order = {
        "STABLE": 0,
        "MINOR": 1,
        "MODERATE": 2,
        "SEVERE": 3,
        "CRITICAL": 4,
    }
    return severity_order.get(bucket, 0)
