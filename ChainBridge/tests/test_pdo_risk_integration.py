"""PDO Risk Integration Tests.

Tests the risk-aware PDO validation and enforcement infrastructure.
Verifies that risk metadata is accepted and logged, hooks execute,
and no false denials occur (pass-through mode).

Requirements validated:
1. PDO without risk metadata still passes
2. PDO with risk metadata is logged
3. Hooks execute deterministically
4. No false denials occur (risk checks allow all)

DOCTRINE: PDO Enforcement Model v1 (LOCKED)
- Risk metadata is READ-ONLY input
- No policy decisions implemented yet
- Infrastructure only — pass-through mode

Author: Cody (GID-01) — Senior Backend Engineer
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

from app.services.pdo.validator import (
    PDOValidator,
    ValidationResult,
    compute_decision_hash,
    validate_pdo_with_risk,
)
from app.services.risk.interface import (
    RiskBand,
    RiskCheckDecision,
    RiskCheckResult,
    RiskMetadata,
    RiskSource,
    extract_risk_metadata,
    pre_execution_risk_check,
    pre_settlement_risk_check,
)
from app.middleware.pdo_enforcement import (
    RiskAwareEnforcementGate,
    get_risk_aware_execution_gate,
    get_risk_aware_settlement_gate,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


def _make_valid_pdo(
    pdo_id: str = "PDO-TEST12345678",
    outcome: str = "APPROVED",
    policy_version: str = "settlement_policy@v1.0.0",
    signer: str = "system::chainpay",
) -> dict[str, Any]:
    """Create a valid PDO with correct hash integrity."""
    inputs_hash = hashlib.sha256(b"test_inputs").hexdigest()
    decision_hash = compute_decision_hash(inputs_hash, policy_version, outcome)
    timestamp = datetime.now(timezone.utc).isoformat()

    return {
        "pdo_id": pdo_id,
        "inputs_hash": inputs_hash,
        "policy_version": policy_version,
        "decision_hash": decision_hash,
        "outcome": outcome,
        "timestamp": timestamp,
        "signer": signer,
    }


def _make_valid_pdo_with_risk(
    risk_score: float = 0.35,
    risk_band: str = "LOW",
    risk_source: str = "chainiq",
) -> dict[str, Any]:
    """Create a valid PDO with risk metadata attached."""
    pdo = _make_valid_pdo(pdo_id="PDO-RISKTEST0001")
    pdo["risk_score"] = risk_score
    pdo["risk_band"] = risk_band
    pdo["risk_source"] = risk_source
    pdo["risk_assessed_at"] = datetime.now(timezone.utc).isoformat()
    pdo["risk_factors"] = {"counterparty_history": "good", "amount_band": "medium"}
    return pdo


# ---------------------------------------------------------------------------
# Test App Setup
# ---------------------------------------------------------------------------


def create_risk_aware_test_app() -> FastAPI:
    """Create FastAPI app with risk-aware PDO-enforced endpoints."""
    app = FastAPI()

    # Get risk-aware gates
    execution_gate = get_risk_aware_execution_gate()
    settlement_gate = get_risk_aware_settlement_gate()

    @app.post("/execute/risk-aware")
    async def execute_with_risk(
        request: Request,
        _pdo_enforced: None = Depends(execution_gate.enforce),
    ) -> dict:
        return {"status": "executed", "risk_aware": True}

    @app.post("/settlement/risk-aware")
    async def settlement_with_risk(
        request: Request,
        _pdo_enforced: None = Depends(settlement_gate.enforce),
    ) -> dict:
        return {"status": "settlement_initiated", "risk_aware": True}

    return app


@pytest.fixture
def risk_aware_client() -> TestClient:
    """Test client for risk-aware PDO-enforced app."""
    app = create_risk_aware_test_app()
    return TestClient(app)


# ---------------------------------------------------------------------------
# Risk Metadata Extraction Tests
# ---------------------------------------------------------------------------


class TestRiskMetadataExtraction:
    """Tests for risk metadata extraction from PDO data."""

    def test_extract_risk_metadata_when_present(self):
        """Risk metadata is extracted when present in PDO."""
        pdo = _make_valid_pdo_with_risk(
            risk_score=0.65,
            risk_band="MEDIUM",
            risk_source="chainiq",
        )

        risk_metadata = extract_risk_metadata(pdo)

        assert risk_metadata is not None
        assert risk_metadata.risk_score == 0.65
        assert risk_metadata.risk_band == RiskBand.MEDIUM
        assert risk_metadata.risk_source == RiskSource.CHAINIQ
        assert risk_metadata.assessed_at is not None
        assert risk_metadata.raw_factors is not None

    def test_extract_risk_metadata_returns_none_when_absent(self):
        """None is returned when PDO has no risk metadata."""
        pdo = _make_valid_pdo()  # No risk fields

        risk_metadata = extract_risk_metadata(pdo)

        assert risk_metadata is None

    def test_extract_risk_metadata_handles_none_pdo(self):
        """None PDO returns None risk metadata."""
        risk_metadata = extract_risk_metadata(None)

        assert risk_metadata is None

    def test_extract_risk_metadata_partial_fields(self):
        """Partial risk fields are extracted with defaults."""
        pdo = _make_valid_pdo()
        pdo["risk_score"] = 0.5  # Only score, no band/source

        risk_metadata = extract_risk_metadata(pdo)

        assert risk_metadata is not None
        assert risk_metadata.risk_score == 0.5
        assert risk_metadata.risk_band == RiskBand.UNKNOWN
        assert risk_metadata.risk_source == RiskSource.UNKNOWN

    def test_extract_risk_metadata_invalid_score_warns(self, caplog):
        """Invalid risk_score logs warning but still extracts."""
        pdo = _make_valid_pdo()
        pdo["risk_score"] = 1.5  # Out of bounds
        pdo["risk_band"] = "LOW"

        with caplog.at_level(logging.WARNING):
            risk_metadata = extract_risk_metadata(pdo)

        assert risk_metadata is not None
        assert risk_metadata.risk_score == 1.5
        assert any("out of expected bounds" in record.message for record in caplog.records)

    def test_extract_risk_metadata_unknown_band_warns(self, caplog):
        """Unknown risk_band logs warning and uses UNKNOWN."""
        pdo = _make_valid_pdo()
        pdo["risk_band"] = "EXTREME"  # Not in enum

        with caplog.at_level(logging.WARNING):
            risk_metadata = extract_risk_metadata(pdo)

        assert risk_metadata is not None
        assert risk_metadata.risk_band == RiskBand.UNKNOWN

    def test_extract_risk_metadata_all_bands(self):
        """All valid risk bands are extracted correctly."""
        for band in ["LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN"]:
            pdo = _make_valid_pdo()
            pdo["risk_band"] = band

            risk_metadata = extract_risk_metadata(pdo)

            assert risk_metadata is not None
            assert risk_metadata.risk_band == RiskBand(band)

    def test_extract_risk_metadata_all_sources(self):
        """All valid risk sources are extracted correctly."""
        for source in ["chainiq", "manual", "external", "policy_engine", "unknown"]:
            pdo = _make_valid_pdo()
            pdo["risk_source"] = source

            risk_metadata = extract_risk_metadata(pdo)

            assert risk_metadata is not None
            assert risk_metadata.risk_source == RiskSource(source)


# ---------------------------------------------------------------------------
# Risk Check Hook Tests
# ---------------------------------------------------------------------------


class TestRiskCheckHooks:
    """Tests for pre-execution and pre-settlement risk check hooks."""

    def test_pre_execution_risk_check_always_allows(self):
        """pre_execution_risk_check always returns ALLOW (pass-through)."""
        pdo = _make_valid_pdo_with_risk()
        risk_metadata = extract_risk_metadata(pdo)

        result = pre_execution_risk_check(pdo["pdo_id"], risk_metadata)

        assert result.decision == RiskCheckDecision.ALLOW
        assert result.allowed is True
        assert result.pdo_id == pdo["pdo_id"]
        assert result.risk_metadata == risk_metadata
        assert "pass-through" in result.reason.lower()

    def test_pre_settlement_risk_check_always_allows(self):
        """pre_settlement_risk_check always returns ALLOW (pass-through)."""
        pdo = _make_valid_pdo_with_risk()
        risk_metadata = extract_risk_metadata(pdo)

        result = pre_settlement_risk_check(pdo["pdo_id"], risk_metadata)

        assert result.decision == RiskCheckDecision.ALLOW
        assert result.allowed is True
        assert result.pdo_id == pdo["pdo_id"]
        assert "pass-through" in result.reason.lower()

    def test_risk_check_with_none_metadata(self):
        """Risk checks handle None risk metadata gracefully."""
        result = pre_execution_risk_check("PDO-TEST00000001", None)

        assert result.decision == RiskCheckDecision.ALLOW
        assert result.risk_metadata is None

    def test_risk_check_with_none_pdo_id(self):
        """Risk checks handle None PDO ID gracefully."""
        risk_metadata = RiskMetadata(risk_score=0.5, risk_band=RiskBand.MEDIUM)

        result = pre_execution_risk_check(None, risk_metadata)

        assert result.decision == RiskCheckDecision.ALLOW
        assert result.pdo_id is None

    def test_risk_check_deterministic(self):
        """Same inputs produce same risk check result."""
        pdo = _make_valid_pdo_with_risk()
        risk_metadata = extract_risk_metadata(pdo)

        results = [
            pre_execution_risk_check(pdo["pdo_id"], risk_metadata)
            for _ in range(3)
        ]

        # All results should have same decision
        assert all(r.decision == RiskCheckDecision.ALLOW for r in results)
        assert all(r.pdo_id == pdo["pdo_id"] for r in results)

    def test_risk_check_logs_invocation(self, caplog):
        """Risk check hooks log their invocation."""
        pdo = _make_valid_pdo_with_risk()
        risk_metadata = extract_risk_metadata(pdo)

        with caplog.at_level(logging.INFO):
            pre_execution_risk_check(pdo["pdo_id"], risk_metadata)

        assert any("risk_check" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# Risk-Aware Validation Tests
# ---------------------------------------------------------------------------


class TestRiskAwareValidation:
    """Tests for validate_pdo_with_risk function."""

    def test_pdo_without_risk_passes_validation(self):
        """PDO without risk metadata passes validation normally."""
        pdo = _make_valid_pdo()

        result, risk_metadata = validate_pdo_with_risk(pdo)

        assert result.valid is True
        assert risk_metadata is None

    def test_pdo_with_risk_passes_validation(self):
        """PDO with risk metadata passes validation and extracts risk."""
        pdo = _make_valid_pdo_with_risk()

        result, risk_metadata = validate_pdo_with_risk(pdo)

        assert result.valid is True
        assert risk_metadata is not None
        assert risk_metadata.risk_score is not None

    def test_invalid_pdo_with_risk_fails_validation(self):
        """Invalid PDO fails validation regardless of risk metadata."""
        pdo = {"pdo_id": "PDO-TEST12345678"}  # Missing required fields
        pdo["risk_score"] = 0.5

        result, risk_metadata = validate_pdo_with_risk(pdo)

        assert result.valid is False
        # Risk metadata may or may not be extracted depending on fields present

    def test_risk_metadata_does_not_affect_validation(self):
        """Risk metadata has no impact on PDO validation outcome."""
        # Valid PDO with high risk
        pdo_high_risk = _make_valid_pdo_with_risk(risk_score=0.99, risk_band="CRITICAL")
        result_high, _ = validate_pdo_with_risk(pdo_high_risk)

        # Valid PDO with low risk
        pdo_low_risk = _make_valid_pdo_with_risk(risk_score=0.01, risk_band="LOW")
        result_low, _ = validate_pdo_with_risk(pdo_low_risk)

        # Both should pass - risk doesn't affect validation
        assert result_high.valid is True
        assert result_low.valid is True

    def test_risk_metadata_logged_during_validation(self, caplog):
        """Risk metadata is logged during validation."""
        pdo = _make_valid_pdo_with_risk()

        with caplog.at_level(logging.INFO):
            validate_pdo_with_risk(pdo)

        assert any("risk_metadata" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# Risk-Aware Enforcement Gate Tests
# ---------------------------------------------------------------------------


class TestRiskAwareEnforcementGate:
    """Tests for RiskAwareEnforcementGate class."""

    def test_valid_pdo_without_risk_allowed(self, risk_aware_client: TestClient):
        """Valid PDO without risk metadata is allowed."""
        response = risk_aware_client.post(
            "/execute/risk-aware",
            json={"action": "test", "pdo": _make_valid_pdo()}
        )

        assert response.status_code == 200
        assert response.json()["risk_aware"] is True

    def test_valid_pdo_with_risk_allowed(self, risk_aware_client: TestClient):
        """Valid PDO with risk metadata is allowed (pass-through)."""
        response = risk_aware_client.post(
            "/execute/risk-aware",
            json={"action": "test", "pdo": _make_valid_pdo_with_risk()}
        )

        assert response.status_code == 200

    def test_high_risk_pdo_still_allowed(self, risk_aware_client: TestClient):
        """High risk PDO is still allowed (pass-through mode, no denials)."""
        pdo = _make_valid_pdo_with_risk(
            risk_score=0.99,
            risk_band="CRITICAL",
        )

        response = risk_aware_client.post(
            "/execute/risk-aware",
            json={"action": "test", "pdo": pdo}
        )

        # Pass-through mode: no denials based on risk
        assert response.status_code == 200

    def test_invalid_pdo_still_blocked(self, risk_aware_client: TestClient):
        """Invalid PDO is still blocked (PDO validation unchanged)."""
        response = risk_aware_client.post(
            "/execute/risk-aware",
            json={"action": "test"}  # No PDO
        )

        assert response.status_code == 403

    def test_settlement_gate_with_risk(self, risk_aware_client: TestClient):
        """Settlement gate with risk metadata works correctly."""
        pdo = _make_valid_pdo_with_risk()
        pdo["pdo_id"] = "PDO-SETTLEMENT001"

        response = risk_aware_client.post(
            "/settlement/risk-aware",
            json={"action": "initiate", "pdo": pdo}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "settlement_initiated"


# ---------------------------------------------------------------------------
# No False Denials Tests (Pass-Through Mode)
# ---------------------------------------------------------------------------


class TestNoFalseDenials:
    """Tests ensuring no false denials occur in pass-through mode."""

    def test_all_risk_bands_allowed(self, risk_aware_client: TestClient):
        """All risk bands are allowed in pass-through mode."""
        for band in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            pdo = _make_valid_pdo_with_risk(risk_band=band)
            pdo["pdo_id"] = f"PDO-BAND{band}0001"

            response = risk_aware_client.post(
                "/execute/risk-aware",
                json={"pdo": pdo}
            )

            assert response.status_code == 200, f"Risk band {band} was incorrectly denied"

    def test_all_risk_scores_allowed(self, risk_aware_client: TestClient):
        """All risk scores are allowed in pass-through mode."""
        for score in [0.0, 0.25, 0.5, 0.75, 1.0]:
            pdo = _make_valid_pdo_with_risk(risk_score=score)
            pdo["pdo_id"] = f"PDO-SCORE{int(score*100):03d}"

            response = risk_aware_client.post(
                "/execute/risk-aware",
                json={"pdo": pdo}
            )

            assert response.status_code == 200, f"Risk score {score} was incorrectly denied"

    def test_all_risk_sources_allowed(self, risk_aware_client: TestClient):
        """All risk sources are allowed in pass-through mode."""
        for idx, source in enumerate(["chainiq", "manual", "external", "policy_engine"]):
            pdo = _make_valid_pdo_with_risk(risk_source=source)
            pdo["pdo_id"] = f"PDO-RISKSRC{idx:04d}"  # Valid PDO ID format

            response = risk_aware_client.post(
                "/execute/risk-aware",
                json={"pdo": pdo}
            )

            assert response.status_code == 200, f"Risk source {source} was incorrectly denied"


# ---------------------------------------------------------------------------
# Audit Logging Tests
# ---------------------------------------------------------------------------


class TestRiskAuditLogging:
    """Tests for risk metadata audit logging."""

    def test_risk_metadata_logged_on_enforcement(self, risk_aware_client: TestClient, caplog):
        """Risk metadata is logged during enforcement."""
        pdo = _make_valid_pdo_with_risk()

        with caplog.at_level(logging.INFO):
            risk_aware_client.post(
                "/execute/risk-aware",
                json={"pdo": pdo}
            )

        # Should have enforcement log with risk data
        assert any("risk" in record.message.lower() for record in caplog.records)

    def test_risk_hook_result_logged(self, risk_aware_client: TestClient, caplog):
        """Risk hook result is logged after execution."""
        pdo = _make_valid_pdo_with_risk()

        with caplog.at_level(logging.INFO):
            risk_aware_client.post(
                "/execute/risk-aware",
                json={"pdo": pdo}
            )

        # Should have risk hook result log
        assert any("risk hook result" in record.message.lower() for record in caplog.records)
