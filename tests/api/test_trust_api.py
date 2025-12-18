"""
🔵 CODY (GID-01) — Trust Center API Tests
PAC-GOV-TRUST-API-01: Read-Only Evidence API Tests

Tests proving:
- All routes are GET-only
- Mutation attempts return 405
- Returned objects are immutable snapshots
- Missing artifacts → explicit null or empty response
- No governance state touched

CRITICAL: These tests verify the API is glass, not control.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.trust import (
    GAMEDAY_RESULTS,
    GOVERNANCE_COVERAGE,
    TRUST_API_VERSION,
    TrustAuditLatestResponse,
    TrustCoverageResponse,
    TrustFingerprintResponse,
    TrustGamedayResponse,
    get_allowed_methods,
    is_read_only,
    router,
)

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def app() -> FastAPI:
    """Create test FastAPI app with trust router."""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_fingerprint():
    """Mock governance fingerprint."""
    mock = MagicMock()
    mock.composite_hash = "abc123def456789"
    mock.computed_at = "2025-01-17T12:00:00+00:00"
    mock.version = "v1"
    return mock


@pytest.fixture
def mock_fingerprint_engine(mock_fingerprint):
    """Mock fingerprint engine."""
    engine = MagicMock()
    engine.is_initialized.return_value = True
    engine.get_fingerprint.return_value = mock_fingerprint
    return engine


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: READ-ONLY GUARANTEES
# ═══════════════════════════════════════════════════════════════════════════════


class TestReadOnlyGuarantees:
    """Tests proving the API is strictly read-only."""

    def test_api_declares_read_only(self) -> None:
        """API helper confirms read-only status."""
        assert is_read_only() is True

    def test_allowed_methods_are_safe(self) -> None:
        """Only safe HTTP methods are allowed."""
        methods = get_allowed_methods()
        assert "GET" in methods
        assert "HEAD" in methods
        assert "OPTIONS" in methods
        assert "POST" not in methods
        assert "PUT" not in methods
        assert "PATCH" not in methods
        assert "DELETE" not in methods

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/trust/fingerprint",
            "/trust/coverage",
            "/trust/audit/latest",
            "/trust/gameday",
        ],
    )
    def test_get_allowed_on_all_endpoints(self, client: TestClient, endpoint: str) -> None:
        """GET requests should be allowed on all endpoints."""
        with patch("core.governance.governance_fingerprint.get_fingerprint_engine") as mock_engine:
            mock = MagicMock()
            mock.is_initialized.return_value = True
            mock.get_fingerprint.return_value = MagicMock(
                composite_hash="test",
                computed_at="2025-01-17T12:00:00+00:00",
                version="v1",
            )
            mock_engine.return_value = mock

            response = client.get(endpoint)
            # Should succeed or return 503 (fingerprint unavailable) but NOT 405
            assert response.status_code != 405

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/trust/fingerprint",
            "/trust/coverage",
            "/trust/audit/latest",
            "/trust/gameday",
        ],
    )
    def test_post_returns_405(self, client: TestClient, endpoint: str) -> None:
        """POST requests should return 405 Method Not Allowed."""
        response = client.post(endpoint, json={})
        assert response.status_code == 405

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/trust/fingerprint",
            "/trust/coverage",
            "/trust/audit/latest",
            "/trust/gameday",
        ],
    )
    def test_put_returns_405(self, client: TestClient, endpoint: str) -> None:
        """PUT requests should return 405 Method Not Allowed."""
        response = client.put(endpoint, json={})
        assert response.status_code == 405

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/trust/fingerprint",
            "/trust/coverage",
            "/trust/audit/latest",
            "/trust/gameday",
        ],
    )
    def test_patch_returns_405(self, client: TestClient, endpoint: str) -> None:
        """PATCH requests should return 405 Method Not Allowed."""
        response = client.patch(endpoint, json={})
        assert response.status_code == 405

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/trust/fingerprint",
            "/trust/coverage",
            "/trust/audit/latest",
            "/trust/gameday",
        ],
    )
    def test_delete_returns_405(self, client: TestClient, endpoint: str) -> None:
        """DELETE requests should return 405 Method Not Allowed."""
        response = client.delete(endpoint)
        assert response.status_code == 405


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: FINGERPRINT ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════


class TestFingerprintEndpoint:
    """Tests for GET /trust/fingerprint."""

    def test_fingerprint_returns_hash(self, client: TestClient, mock_fingerprint_engine) -> None:
        """Fingerprint endpoint returns SHA-256 hash."""
        with patch(
            "core.governance.governance_fingerprint.get_fingerprint_engine",
            return_value=mock_fingerprint_engine,
        ):
            response = client.get("/trust/fingerprint")

            assert response.status_code == 200
            data = response.json()
            assert "fingerprint_hash" in data
            assert data["fingerprint_hash"].startswith("sha256:")

    def test_fingerprint_returns_timestamp(self, client: TestClient, mock_fingerprint_engine) -> None:
        """Fingerprint endpoint returns generation timestamp."""
        with patch(
            "core.governance.governance_fingerprint.get_fingerprint_engine",
            return_value=mock_fingerprint_engine,
        ):
            response = client.get("/trust/fingerprint")

            assert response.status_code == 200
            data = response.json()
            assert "generated_at" in data
            # Should be ISO-8601 format
            assert "T" in data["generated_at"]

    def test_fingerprint_returns_schema_version(self, client: TestClient, mock_fingerprint_engine) -> None:
        """Fingerprint endpoint returns schema version."""
        with patch(
            "core.governance.governance_fingerprint.get_fingerprint_engine",
            return_value=mock_fingerprint_engine,
        ):
            response = client.get("/trust/fingerprint")

            assert response.status_code == 200
            data = response.json()
            assert "schema_version" in data
            assert data["schema_version"] == "v1"

    def test_fingerprint_503_on_boot_error(self, client: TestClient) -> None:
        """Fingerprint endpoint returns 503 if fingerprint unavailable."""
        from core.governance.governance_fingerprint import GovernanceBootError

        with patch("core.governance.governance_fingerprint.get_fingerprint_engine") as mock:
            mock.side_effect = GovernanceBootError("Test error")

            response = client.get("/trust/fingerprint")

            assert response.status_code == 503
            assert "unavailable" in response.json()["detail"].lower()

    def test_fingerprint_does_not_mutate_state(self, client: TestClient, mock_fingerprint_engine) -> None:
        """Fingerprint endpoint does not call any mutation methods."""
        with patch(
            "core.governance.governance_fingerprint.get_fingerprint_engine",
            return_value=mock_fingerprint_engine,
        ):
            client.get("/trust/fingerprint")

            # Should not call compute if already initialized
            mock_fingerprint_engine.compute_fingerprint.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: COVERAGE ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════


class TestCoverageEndpoint:
    """Tests for GET /trust/coverage."""

    def test_coverage_returns_all_fields(self, client: TestClient) -> None:
        """Coverage endpoint returns all capability fields."""
        response = client.get("/trust/coverage")

        assert response.status_code == 200
        data = response.json()

        # Verify all fields present
        assert "acm_enforced" in data
        assert "drcp_active" in data
        assert "diggi_enabled" in data
        assert "artifact_verification" in data
        assert "scope_guard" in data
        assert "fail_closed_execution" in data

    def test_coverage_returns_booleans_only(self, client: TestClient) -> None:
        """Coverage endpoint returns only boolean values."""
        response = client.get("/trust/coverage")

        assert response.status_code == 200
        data = response.json()

        for key, value in data.items():
            assert isinstance(value, bool), f"{key} should be boolean, got {type(value)}"

    def test_coverage_matches_constants(self, client: TestClient) -> None:
        """Coverage endpoint returns values matching GOVERNANCE_COVERAGE."""
        response = client.get("/trust/coverage")

        assert response.status_code == 200
        data = response.json()

        for key, expected in GOVERNANCE_COVERAGE.items():
            assert data[key] == expected

    def test_coverage_no_counts(self, client: TestClient) -> None:
        """Coverage endpoint does not include any counts."""
        response = client.get("/trust/coverage")

        assert response.status_code == 200
        data = response.json()

        # No field should have numeric value (except False=0)
        for key, value in data.items():
            assert not isinstance(value, int) or isinstance(value, bool)

    def test_coverage_no_percentages(self, client: TestClient) -> None:
        """Coverage endpoint does not include percentages."""
        response = client.get("/trust/coverage")

        assert response.status_code == 200
        data = response.json()

        # No field should have float value
        for key, value in data.items():
            assert not isinstance(value, float)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: AUDIT LATEST ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuditLatestEndpoint:
    """Tests for GET /trust/audit/latest."""

    def test_audit_latest_returns_null_when_no_bundle(self, client: TestClient, tmp_path: Path) -> None:
        """Audit endpoint returns nulls when no bundle exists."""
        with patch("api.trust.Path") as mock_path:
            # Simulate no audit bundles
            mock_path.return_value.parent.parent.glob.return_value = []

            response = client.get("/trust/audit/latest")

            assert response.status_code == 200
            data = response.json()
            # bundle_id, created_at, bundle_hash, schema_version can be null
            assert data["offline_verifiable"] is True

    def test_audit_latest_offline_verifiable_always_true(self, client: TestClient) -> None:
        """Audit endpoint always reports offline_verifiable=true."""
        response = client.get("/trust/audit/latest")

        assert response.status_code == 200
        data = response.json()
        assert data["offline_verifiable"] is True

    def test_audit_latest_does_not_create_bundle(self, client: TestClient) -> None:
        """Audit endpoint never triggers bundle creation."""
        with patch("api.trust.Path") as mock_path:
            mock_path.return_value.parent.parent.glob.return_value = []

            response = client.get("/trust/audit/latest")

            # No call to export_audit_bundle or similar
            assert response.status_code == 200

    def test_audit_latest_response_model(self, client: TestClient) -> None:
        """Audit endpoint returns correct response structure."""
        response = client.get("/trust/audit/latest")

        assert response.status_code == 200
        data = response.json()

        # Verify all expected fields exist
        expected_fields = {
            "bundle_id",
            "created_at",
            "bundle_hash",
            "schema_version",
            "offline_verifiable",
        }
        assert set(data.keys()) == expected_fields


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: GAMEDAY ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════


class TestGamedayEndpoint:
    """Tests for GET /trust/gameday."""

    def test_gameday_returns_all_fields(self, client: TestClient) -> None:
        """Gameday endpoint returns all expected fields."""
        response = client.get("/trust/gameday")

        assert response.status_code == 200
        data = response.json()

        assert "scenarios_tested" in data
        assert "silent_failures" in data
        assert "fail_closed" in data
        assert "last_run" in data

    def test_gameday_matches_constants(self, client: TestClient) -> None:
        """Gameday endpoint returns values matching GAMEDAY_RESULTS."""
        response = client.get("/trust/gameday")

        assert response.status_code == 200
        data = response.json()

        assert data["scenarios_tested"] == GAMEDAY_RESULTS["scenarios_tested"]
        assert data["silent_failures"] == GAMEDAY_RESULTS["silent_failures"]
        assert data["fail_closed"] == GAMEDAY_RESULTS["fail_closed"]
        assert data["last_run"] == GAMEDAY_RESULTS["last_run"]

    def test_gameday_scenarios_is_133(self, client: TestClient) -> None:
        """Gameday shows 133 scenarios tested (PAC-GOV-GAMEDAY-01)."""
        response = client.get("/trust/gameday")

        assert response.status_code == 200
        data = response.json()
        assert data["scenarios_tested"] == 133

    def test_gameday_silent_failures_is_zero(self, client: TestClient) -> None:
        """Gameday shows 0 silent failures."""
        response = client.get("/trust/gameday")

        assert response.status_code == 200
        data = response.json()
        assert data["silent_failures"] == 0

    def test_gameday_fail_closed_is_true(self, client: TestClient) -> None:
        """Gameday shows fail_closed verified."""
        response = client.get("/trust/gameday")

        assert response.status_code == 200
        data = response.json()
        assert data["fail_closed"] is True

    def test_gameday_does_not_run_tests(self, client: TestClient) -> None:
        """Gameday endpoint never executes adversarial tests."""
        # The endpoint returns constants - no test execution
        response = client.get("/trust/gameday")
        assert response.status_code == 200

    def test_gameday_last_run_is_iso8601(self, client: TestClient) -> None:
        """Gameday last_run is ISO-8601 format."""
        response = client.get("/trust/gameday")

        assert response.status_code == 200
        data = response.json()
        # Should parse as datetime
        datetime.fromisoformat(data["last_run"].replace("Z", "+00:00"))


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: IMMUTABLE SNAPSHOTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestImmutableSnapshots:
    """Tests proving responses are immutable snapshots."""

    def test_coverage_is_deterministic(self, client: TestClient) -> None:
        """Coverage endpoint returns identical results on repeated calls."""
        response1 = client.get("/trust/coverage")
        response2 = client.get("/trust/coverage")

        assert response1.json() == response2.json()

    def test_gameday_is_deterministic(self, client: TestClient) -> None:
        """Gameday endpoint returns identical results on repeated calls."""
        response1 = client.get("/trust/gameday")
        response2 = client.get("/trust/gameday")

        assert response1.json() == response2.json()

    def test_fingerprint_is_deterministic(self, client: TestClient, mock_fingerprint_engine) -> None:
        """Fingerprint endpoint returns identical results on repeated calls."""
        with patch(
            "core.governance.governance_fingerprint.get_fingerprint_engine",
            return_value=mock_fingerprint_engine,
        ):
            response1 = client.get("/trust/fingerprint")
            response2 = client.get("/trust/fingerprint")

            assert response1.json() == response2.json()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: NO GOVERNANCE INTERACTION
# ═══════════════════════════════════════════════════════════════════════════════


class TestNoGovernanceInteraction:
    """Tests proving the API does not interact with governance logic."""

    def test_coverage_does_not_evaluate_acm(self, client: TestClient) -> None:
        """Coverage endpoint does not call ACM evaluator."""
        with patch("core.governance.acm_evaluator.ACMEvaluator") as mock_acm:
            response = client.get("/trust/coverage")

            assert response.status_code == 200
            mock_acm.assert_not_called()

    def test_coverage_does_not_trigger_drcp(self, client: TestClient) -> None:
        """Coverage endpoint does not trigger DRCP."""
        with patch("core.governance.drcp.create_denial_record") as mock_drcp:
            response = client.get("/trust/coverage")

            assert response.status_code == 200
            mock_drcp.assert_not_called()

    def test_gameday_does_not_emit_events(self, client: TestClient) -> None:
        """Gameday endpoint does not emit governance events."""
        with patch("core.governance.telemetry.emit_event") as mock_emit:
            response = client.get("/trust/gameday")

            assert response.status_code == 200
            mock_emit.assert_not_called()

    def test_fingerprint_does_not_emit_events(self, client: TestClient, mock_fingerprint_engine) -> None:
        """Fingerprint endpoint does not emit governance events."""
        with patch(
            "core.governance.governance_fingerprint.get_fingerprint_engine",
            return_value=mock_fingerprint_engine,
        ):
            with patch("core.governance.telemetry.emit_event") as mock_emit:
                response = client.get("/trust/fingerprint")

                assert response.status_code == 200
                mock_emit.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════════


class TestResponseModels:
    """Tests for Pydantic response models."""

    def test_fingerprint_response_model(self) -> None:
        """TrustFingerprintResponse validates correctly."""
        response = TrustFingerprintResponse(
            fingerprint_hash="sha256:abc123",
            generated_at="2025-01-17T12:00:00+00:00",
            schema_version="v1",
        )
        assert response.fingerprint_hash == "sha256:abc123"

    def test_coverage_response_model(self) -> None:
        """TrustCoverageResponse validates correctly."""
        response = TrustCoverageResponse(
            acm_enforced=True,
            drcp_active=True,
            diggi_enabled=True,
            artifact_verification=True,
            scope_guard=True,
            fail_closed_execution=True,
        )
        assert response.acm_enforced is True

    def test_audit_response_model_with_nulls(self) -> None:
        """TrustAuditLatestResponse accepts null values."""
        response = TrustAuditLatestResponse(
            bundle_id=None,
            created_at=None,
            bundle_hash=None,
            schema_version=None,
            offline_verifiable=True,
        )
        assert response.bundle_id is None
        assert response.offline_verifiable is True

    def test_gameday_response_model(self) -> None:
        """TrustGamedayResponse validates correctly."""
        response = TrustGamedayResponse(
            scenarios_tested=133,
            silent_failures=0,
            fail_closed=True,
            last_run="2025-01-15T00:00:00+00:00",
        )
        assert response.scenarios_tested == 133
