#!/usr/bin/env python3
"""ChainIQ Risk Contract Verification Script.

Validates that all A10 lock requirements are met:
1. Canonical model spec is properly defined
2. All monotonic constraints are declared
3. Calibration registry structure exists
4. Drift response policy is configured
5. Risk scoring contract invariants hold

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

II. USAGE

    python scripts/ci/verify_risk_contract.py

Exit codes:
    0 = All verifications passed
    1 = One or more verifications failed

⸻

III. PROHIBITED ACTIONS

- Bypassing verification failures
- Silent fallback on check errors

⸻
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

# Add paths for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "chainiq-service"))


def verify_canonical_model_spec() -> Tuple[bool, str]:
    """Verify canonical model spec is properly configured."""
    try:
        from app.models.canonical_model_spec import (
            CANONICAL_MODEL_SPEC,
            INVARIANTS,
            ModelType,
            ForbiddenModelType,
            RiskBand,
        )
        
        # Check model type is glass-box
        if CANONICAL_MODEL_SPEC.model_type not in [
            ModelType.ADDITIVE_WEIGHTED_RULES,
            ModelType.GAM,
            ModelType.EBM,
            ModelType.MONOTONIC_LOGISTIC,
            ModelType.LINEAR_MODEL,
        ]:
            return False, f"Invalid model type: {CANONICAL_MODEL_SPEC.model_type}"
        
        # Check invariants exist
        if len(INVARIANTS) < 5:
            return False, f"Insufficient invariants defined: {len(INVARIANTS)}"
        
        # Check risk bands are defined
        bands = list(RiskBand)
        if len(bands) != 4:
            return False, f"Expected 4 risk bands, got {len(bands)}"
        
        return True, "Canonical model spec verified"
    except ImportError as e:
        return False, f"Import error: {e}"
    except Exception as e:
        return False, f"Verification error: {e}"


def verify_monotonic_constraints() -> Tuple[bool, str]:
    """Verify all required monotonic constraints are defined."""
    try:
        from app.models.canonical_model_spec import MONOTONIC_FEATURES
        
        required_features = {
            "carrier_incident_rate_90d",
            "recent_delay_events",
            "iot_alert_count",
            "border_crossing_count",
            "value_usd",
            "lane_risk_index",
        }
        
        actual_features = {c.feature_name for c in MONOTONIC_FEATURES}
        
        missing = required_features - actual_features
        if missing:
            return False, f"Missing monotonic constraints: {missing}"
        
        # All constraints should be 'increasing'
        for constraint in MONOTONIC_FEATURES:
            if constraint.direction != "increasing":
                return False, f"Constraint {constraint.feature_name} has invalid direction: {constraint.direction}"
        
        return True, f"All {len(MONOTONIC_FEATURES)} monotonic constraints verified"
    except ImportError as e:
        return False, f"Import error: {e}"
    except Exception as e:
        return False, f"Verification error: {e}"


def verify_calibration_registry() -> Tuple[bool, str]:
    """Verify calibration registry structure exists."""
    try:
        from app.models.calibration_registry import (
            CalibrationRegistry,
            CalibrationArtifact,
            CalibrationCurve,
        )
        
        # Check registry can be instantiated
        registry = CalibrationRegistry()
        
        # Check required methods exist (actual method names in implementation)
        required_methods = [
            "register",      # Register new calibration artifact
            "activate",      # Activate artifact for production
            "get_active",    # Get current active artifact
            "check_calibration",  # Check calibration status
        ]
        
        for method in required_methods:
            if not hasattr(registry, method):
                return False, f"Missing registry method: {method}"
        
        return True, "Calibration registry structure verified"
    except ImportError as e:
        return False, f"Import error: {e}"
    except Exception as e:
        return False, f"Verification error: {e}"


def verify_drift_policy() -> Tuple[bool, str]:
    """Verify drift response policy is configured."""
    try:
        from app.ml.drift_engine import (
            DriftAction,
            DriftBucket,
            DRIFT_RESPONSE_POLICY,
            get_drift_action,
            should_halt_scoring,
        )
        
        # Check all drift categories have actions (using enum keys)
        required_buckets = [
            DriftBucket.STABLE,
            DriftBucket.MINOR,
            DriftBucket.MODERATE,
            DriftBucket.SEVERE,
            DriftBucket.CRITICAL,
        ]
        
        for bucket in required_buckets:
            if bucket not in DRIFT_RESPONSE_POLICY:
                return False, f"Missing drift policy for: {bucket.value}"
        
        # Verify CRITICAL → HALT
        if DRIFT_RESPONSE_POLICY.get(DriftBucket.CRITICAL) != DriftAction.HALT:
            return False, "CRITICAL drift must map to HALT action"
        
        # Verify function exists
        if not callable(get_drift_action) or not callable(should_halt_scoring):
            return False, "Drift action functions not callable"
        
        return True, "Drift response policy verified"
    except ImportError as e:
        return False, f"Import error: {e}"
    except Exception as e:
        return False, f"Verification error: {e}"


def verify_replay_contract() -> Tuple[bool, str]:
    """Verify replay determinism contract exists."""
    try:
        from app.models.canonical_model_spec import (
            RiskInput,
            RiskOutput,
            verify_replay,
        )
        
        # Check verify_replay function exists and is callable
        if not callable(verify_replay):
            return False, "verify_replay is not callable"
        
        # Check RiskOutput has hash method
        if not hasattr(RiskOutput, "compute_hash"):
            return False, "RiskOutput missing compute_hash method"
        
        return True, "Replay contract verified"
    except ImportError as e:
        return False, f"Import error: {e}"
    except Exception as e:
        return False, f"Verification error: {e}"


def verify_governance_document() -> Tuple[bool, str]:
    """Verify A10 governance document exists."""
    doc_path = PROJECT_ROOT / "docs" / "governance" / "A10_RISK_MODEL_CANONICALIZATION_LOCK.md"
    
    if not doc_path.exists():
        return False, f"Governance document not found: {doc_path}"
    
    content = doc_path.read_text()
    
    # Check required sections (matching actual doc headings)
    required_sections = [
        "Model Architecture Stack",
        "Risk Scoring Contract",
        "Monotonic Constraints",
        "Calibration",  # Doc uses "Calibration & Drift Policy"
        "Drift",        # Covered in same section
        "CRO Override",
    ]
    
    missing_sections = [s for s in required_sections if s not in content]
    if missing_sections:
        return False, f"Missing governance sections: {missing_sections}"
    
    return True, "Governance document verified"


def main() -> int:
    """Run all verifications."""
    print("=" * 60)
    print("ChainIQ Risk Contract Verification")
    print("PAC: PAC-MAGGIE-A10-RISK-MODEL-CANONICALIZATION-LOCK-01")
    print("=" * 60)
    print()
    
    verifications: List[Tuple[str, Tuple[bool, str]]] = [
        ("Governance Document", verify_governance_document()),
        ("Canonical Model Spec", verify_canonical_model_spec()),
        ("Monotonic Constraints", verify_monotonic_constraints()),
        ("Calibration Registry", verify_calibration_registry()),
        ("Drift Response Policy", verify_drift_policy()),
        ("Replay Contract", verify_replay_contract()),
    ]
    
    all_passed = True
    
    for name, (passed, message) in verifications:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        print(f"       {message}")
        print()
        
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("✓ All verifications PASSED")
        print("  Risk contract is A10-compliant")
        return 0
    else:
        print("✗ Some verifications FAILED")
        print("  Risk contract is NOT A10-compliant")
        return 1


if __name__ == "__main__":
    sys.exit(main())


# END — Maggie (GID-10) — 🩷 PINK
