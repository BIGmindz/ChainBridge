"""ChainIQ Calibration Registry.

Manages calibration artifacts for risk models, ensuring calibration curves
are versioned, stored, and validated according to A10 lock requirements.

════════════════════════════════════════════════════════════════════════════════
🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷
GID-10 — MAGGIE (ML & APPLIED AI)
PAC-MAGGIE-A10-RISK-MODEL-CANONICALIZATION-LOCK-01
🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷
════════════════════════════════════════════════════════════════════════════════

I. EXECUTING AGENT (MANDATORY)

EXECUTING AGENT: MAGGIE
GID: GID-10
EXECUTING COLOR: 🩷 PINK — ML & Applied AI Lane

⸻

II. CALIBRATION POLICY (LOCKED)

- Calibration curves stored as versioned artifacts
- Recalibration triggers when ECE > 5%
- All calibration metadata tracked for audit

⸻

III. PROHIBITED ACTIONS

- Unversioned calibration artifacts
- Auto-recalibration without approval
- Silent calibration failures

⸻
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# CALIBRATION CONSTANTS (LOCKED)
# =============================================================================

# Expected Calibration Error threshold for recalibration trigger
ECE_RECALIBRATION_THRESHOLD = 0.05  # 5%

# Brier score threshold for concern
BRIER_SCORE_THRESHOLD = 0.25

# Calibration artifact storage location
CALIBRATION_STORAGE_PATH = Path("chainiq-service/calibration/")


class CalibrationStatus(str, Enum):
    """Status of a calibration artifact."""
    
    ACTIVE = "ACTIVE"  # Currently in use
    ARCHIVED = "ARCHIVED"  # Previous version, kept for audit
    PENDING = "PENDING"  # Awaiting validation
    INVALID = "INVALID"  # Failed validation


class CalibrationAction(str, Enum):
    """Actions based on calibration check."""
    
    CONTINUE = "CONTINUE"  # Calibration acceptable
    MONITOR = "MONITOR"  # Slight drift, watch closely
    RECALIBRATE = "RECALIBRATE"  # Recalibration needed
    HALT = "HALT"  # Critical miscalibration


# =============================================================================
# CALIBRATION DATA STRUCTURES
# =============================================================================

@dataclass
class CalibrationBin:
    """Single bin in a calibration curve."""
    
    bin_start: float  # Predicted probability start
    bin_end: float  # Predicted probability end
    predicted_mean: float  # Mean predicted probability in bin
    observed_mean: float  # Mean observed outcome in bin
    count: int  # Number of samples in bin
    
    @property
    def calibration_error(self) -> float:
        """Absolute calibration error for this bin."""
        return abs(self.predicted_mean - self.observed_mean)


@dataclass
class CalibrationCurve:
    """Full calibration curve with metadata."""
    
    bins: List[CalibrationBin]
    n_bins: int
    total_samples: int
    
    def get_bin_for_prediction(self, prediction: float) -> Optional[CalibrationBin]:
        """Get the calibration bin for a prediction."""
        for bin_ in self.bins:
            if bin_.bin_start <= prediction < bin_.bin_end:
                return bin_
        # Edge case: prediction == 1.0
        if prediction == 1.0 and self.bins:
            return self.bins[-1]
        return None


@dataclass
class CalibrationMetrics:
    """Calibration quality metrics."""
    
    ece: float  # Expected Calibration Error
    mce: float  # Maximum Calibration Error
    brier_score: float
    
    # Per-band calibration (for risk bands)
    band_ece: Dict[str, float] = field(default_factory=dict)
    
    def needs_recalibration(self) -> bool:
        """Check if recalibration is needed based on ECE threshold."""
        return self.ece > ECE_RECALIBRATION_THRESHOLD
    
    def get_action(self) -> CalibrationAction:
        """Determine action based on calibration metrics."""
        if self.ece > 0.15:  # 15% ECE is critical
            return CalibrationAction.HALT
        elif self.ece > ECE_RECALIBRATION_THRESHOLD:
            return CalibrationAction.RECALIBRATE
        elif self.ece > 0.03:  # 3% ECE warrants monitoring
            return CalibrationAction.MONITOR
        return CalibrationAction.CONTINUE


@dataclass
class CalibrationArtifact:
    """Complete calibration artifact for a model version.
    
    REQUIRED FIELDS (per A10 Lock):
    - model_version
    - calibration_date
    - calibration_dataset_hash
    - observed_vs_predicted_curve
    - brier_score
    - ece_score
    """
    
    # Identity (required, no defaults)
    artifact_id: str
    model_version: str
    
    # Timing (required, no defaults)
    calibration_date: str  # ISO-8601 UTC
    valid_from: str  # ISO-8601 UTC
    
    # Data lineage (required, no defaults)
    calibration_dataset_hash: str
    calibration_dataset_size: int
    
    # Optional timing
    valid_until: Optional[str] = None  # ISO-8601 UTC, None = indefinite
    
    # Calibration data (with defaults)
    calibration_curve: CalibrationCurve = field(default_factory=lambda: CalibrationCurve([], 0, 0))
    metrics: CalibrationMetrics = field(default_factory=lambda: CalibrationMetrics(0.0, 0.0, 0.0))
    
    # Status
    status: CalibrationStatus = CalibrationStatus.PENDING
    
    # Audit
    created_by: str = "system"
    approved_by: Optional[str] = None
    approval_timestamp: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Validate artifact on creation."""
        if not self.model_version:
            raise ValueError("model_version is required")
        if not self.calibration_dataset_hash:
            raise ValueError("calibration_dataset_hash is required")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "artifact_id": self.artifact_id,
            "model_version": self.model_version,
            "calibration_date": self.calibration_date,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "calibration_dataset_hash": self.calibration_dataset_hash,
            "calibration_dataset_size": self.calibration_dataset_size,
            "calibration_curve": {
                "n_bins": self.calibration_curve.n_bins,
                "total_samples": self.calibration_curve.total_samples,
                "bins": [
                    {
                        "bin_start": b.bin_start,
                        "bin_end": b.bin_end,
                        "predicted_mean": b.predicted_mean,
                        "observed_mean": b.observed_mean,
                        "count": b.count,
                    }
                    for b in self.calibration_curve.bins
                ],
            },
            "metrics": {
                "ece": self.metrics.ece,
                "mce": self.metrics.mce,
                "brier_score": self.metrics.brier_score,
                "band_ece": self.metrics.band_ece,
            },
            "status": self.status.value,
            "created_by": self.created_by,
            "approved_by": self.approved_by,
            "approval_timestamp": self.approval_timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CalibrationArtifact":
        """Create artifact from dictionary."""
        curve_data = data.get("calibration_curve", {})
        bins = [
            CalibrationBin(
                bin_start=b["bin_start"],
                bin_end=b["bin_end"],
                predicted_mean=b["predicted_mean"],
                observed_mean=b["observed_mean"],
                count=b["count"],
            )
            for b in curve_data.get("bins", [])
        ]
        curve = CalibrationCurve(
            bins=bins,
            n_bins=curve_data.get("n_bins", len(bins)),
            total_samples=curve_data.get("total_samples", 0),
        )
        
        metrics_data = data.get("metrics", {})
        metrics = CalibrationMetrics(
            ece=metrics_data.get("ece", 0.0),
            mce=metrics_data.get("mce", 0.0),
            brier_score=metrics_data.get("brier_score", 0.0),
            band_ece=metrics_data.get("band_ece", {}),
        )
        
        return cls(
            artifact_id=data["artifact_id"],
            model_version=data["model_version"],
            calibration_date=data["calibration_date"],
            valid_from=data["valid_from"],
            valid_until=data.get("valid_until"),
            calibration_dataset_hash=data["calibration_dataset_hash"],
            calibration_dataset_size=data.get("calibration_dataset_size", 0),
            calibration_curve=curve,
            metrics=metrics,
            status=CalibrationStatus(data.get("status", "PENDING")),
            created_by=data.get("created_by", "system"),
            approved_by=data.get("approved_by"),
            approval_timestamp=data.get("approval_timestamp"),
        )
    
    def compute_artifact_hash(self) -> str:
        """Compute hash for artifact integrity."""
        content = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


# =============================================================================
# CALIBRATION REGISTRY
# =============================================================================

class CalibrationRegistry:
    """Registry for managing calibration artifacts.
    
    Provides:
    - Artifact storage and retrieval
    - Version management
    - Validation checks
    - Audit trail
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize registry.
        
        Args:
            storage_path: Path to store calibration artifacts
        """
        self.storage_path = storage_path or CALIBRATION_STORAGE_PATH
        self._artifacts: Dict[str, CalibrationArtifact] = {}
        self._active_by_model: Dict[str, str] = {}  # model_version -> artifact_id
    
    def register(self, artifact: CalibrationArtifact) -> None:
        """Register a new calibration artifact.
        
        Args:
            artifact: Calibration artifact to register
        """
        if artifact.artifact_id in self._artifacts:
            raise ValueError(f"Artifact {artifact.artifact_id} already registered")
        
        self._artifacts[artifact.artifact_id] = artifact
        logger.info(
            f"Registered calibration artifact {artifact.artifact_id} "
            f"for model {artifact.model_version}"
        )
    
    def activate(self, artifact_id: str, approved_by: str) -> None:
        """Activate a calibration artifact for production use.
        
        Args:
            artifact_id: ID of artifact to activate
            approved_by: ID of approver
        """
        if artifact_id not in self._artifacts:
            raise ValueError(f"Artifact {artifact_id} not found")
        
        artifact = self._artifacts[artifact_id]
        
        # Deactivate previous active artifact for this model
        if artifact.model_version in self._active_by_model:
            old_id = self._active_by_model[artifact.model_version]
            if old_id in self._artifacts:
                self._artifacts[old_id].status = CalibrationStatus.ARCHIVED
        
        # Activate new artifact
        artifact.status = CalibrationStatus.ACTIVE
        artifact.approved_by = approved_by
        artifact.approval_timestamp = datetime.now(timezone.utc).isoformat()
        
        self._active_by_model[artifact.model_version] = artifact_id
        
        logger.info(
            f"Activated calibration artifact {artifact_id} "
            f"for model {artifact.model_version}, approved by {approved_by}"
        )
    
    def get_active(self, model_version: str) -> Optional[CalibrationArtifact]:
        """Get active calibration artifact for a model version.
        
        Args:
            model_version: Model version to look up
            
        Returns:
            Active calibration artifact or None
        """
        artifact_id = self._active_by_model.get(model_version)
        if artifact_id:
            return self._artifacts.get(artifact_id)
        return None
    
    def check_calibration(self, model_version: str) -> Tuple[CalibrationAction, str]:
        """Check calibration status for a model version.
        
        Args:
            model_version: Model version to check
            
        Returns:
            Tuple of (action, message)
        """
        artifact = self.get_active(model_version)
        
        if artifact is None:
            return CalibrationAction.HALT, f"No active calibration for {model_version}"
        
        action = artifact.metrics.get_action()
        
        if action == CalibrationAction.HALT:
            message = f"CRITICAL: ECE={artifact.metrics.ece:.2%} exceeds limits"
        elif action == CalibrationAction.RECALIBRATE:
            message = f"Recalibration needed: ECE={artifact.metrics.ece:.2%} > {ECE_RECALIBRATION_THRESHOLD:.0%}"
        elif action == CalibrationAction.MONITOR:
            message = f"Monitoring: ECE={artifact.metrics.ece:.2%}"
        else:
            message = f"Calibration acceptable: ECE={artifact.metrics.ece:.2%}"
        
        return action, message
    
    def list_artifacts(
        self, 
        model_version: Optional[str] = None,
        status: Optional[CalibrationStatus] = None,
    ) -> List[CalibrationArtifact]:
        """List calibration artifacts with optional filters.
        
        Args:
            model_version: Filter by model version
            status: Filter by status
            
        Returns:
            List of matching artifacts
        """
        results = list(self._artifacts.values())
        
        if model_version:
            results = [a for a in results if a.model_version == model_version]
        
        if status:
            results = [a for a in results if a.status == status]
        
        return results
    
    def save_to_disk(self) -> None:
        """Persist registry to disk."""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        for artifact_id, artifact in self._artifacts.items():
            filepath = self.storage_path / f"{artifact_id}.json"
            with open(filepath, "w") as f:
                json.dump(artifact.to_dict(), f, indent=2)
        
        # Save index
        index = {
            "active_by_model": self._active_by_model,
            "artifact_ids": list(self._artifacts.keys()),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(self.storage_path / "index.json", "w") as f:
            json.dump(index, f, indent=2)
        
        logger.info(f"Saved {len(self._artifacts)} calibration artifacts to {self.storage_path}")
    
    def load_from_disk(self) -> None:
        """Load registry from disk."""
        if not self.storage_path.exists():
            logger.warning(f"Calibration storage path {self.storage_path} does not exist")
            return
        
        index_path = self.storage_path / "index.json"
        if not index_path.exists():
            logger.warning("No calibration index found")
            return
        
        with open(index_path) as f:
            index = json.load(f)
        
        self._active_by_model = index.get("active_by_model", {})
        
        for artifact_id in index.get("artifact_ids", []):
            filepath = self.storage_path / f"{artifact_id}.json"
            if filepath.exists():
                with open(filepath) as f:
                    data = json.load(f)
                    artifact = CalibrationArtifact.from_dict(data)
                    self._artifacts[artifact_id] = artifact
        
        logger.info(f"Loaded {len(self._artifacts)} calibration artifacts from {self.storage_path}")


# =============================================================================
# CALIBRATION COMPUTATION UTILITIES
# =============================================================================

def compute_ece(
    predictions: List[float],
    actuals: List[int],
    n_bins: int = 10,
) -> Tuple[float, CalibrationCurve]:
    """Compute Expected Calibration Error.
    
    ECE = Σ (|bin_accuracy - bin_confidence| * bin_weight)
    
    Args:
        predictions: Predicted probabilities
        actuals: Actual binary outcomes (0 or 1)
        n_bins: Number of calibration bins
        
    Returns:
        Tuple of (ECE value, CalibrationCurve)
    """
    if len(predictions) != len(actuals):
        raise ValueError("predictions and actuals must have same length")
    
    if not predictions:
        return 0.0, CalibrationCurve([], 0, 0)
    
    # Create bins
    bin_boundaries = [i / n_bins for i in range(n_bins + 1)]
    bins = []
    
    total_samples = len(predictions)
    weighted_error = 0.0
    
    for i in range(n_bins):
        bin_start = bin_boundaries[i]
        bin_end = bin_boundaries[i + 1]
        
        # Find samples in this bin
        mask = [(bin_start <= p < bin_end) or (i == n_bins - 1 and p == 1.0) 
                for p in predictions]
        
        bin_preds = [p for p, m in zip(predictions, mask) if m]
        bin_acts = [a for a, m in zip(actuals, mask) if m]
        
        if bin_preds:
            pred_mean = sum(bin_preds) / len(bin_preds)
            obs_mean = sum(bin_acts) / len(bin_acts)
            count = len(bin_preds)
            
            bins.append(CalibrationBin(
                bin_start=bin_start,
                bin_end=bin_end,
                predicted_mean=pred_mean,
                observed_mean=obs_mean,
                count=count,
            ))
            
            # Weight by fraction of total samples
            weight = count / total_samples
            weighted_error += abs(pred_mean - obs_mean) * weight
    
    curve = CalibrationCurve(
        bins=bins,
        n_bins=n_bins,
        total_samples=total_samples,
    )
    
    return weighted_error, curve


def compute_brier_score(predictions: List[float], actuals: List[int]) -> float:
    """Compute Brier Score.
    
    Brier = (1/N) * Σ (prediction - actual)²
    
    Args:
        predictions: Predicted probabilities
        actuals: Actual binary outcomes (0 or 1)
        
    Returns:
        Brier score (lower is better)
    """
    if len(predictions) != len(actuals):
        raise ValueError("predictions and actuals must have same length")
    
    if not predictions:
        return 0.0
    
    squared_errors = [(p - a) ** 2 for p, a in zip(predictions, actuals)]
    return sum(squared_errors) / len(squared_errors)


# =============================================================================
# GLOBAL REGISTRY INSTANCE
# =============================================================================

# Singleton registry for calibration artifacts
_registry: Optional[CalibrationRegistry] = None


def get_calibration_registry() -> CalibrationRegistry:
    """Get the global calibration registry instance."""
    global _registry
    if _registry is None:
        _registry = CalibrationRegistry()
    return _registry


# END — Maggie (GID-10) — 🩷 PINK
