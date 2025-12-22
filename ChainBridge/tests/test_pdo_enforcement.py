"""PDO Enforcement Gate Tests.

Tests the PDO Validation Service and Enforcement Middleware.

Requirements validated:
1. Requests without PDO → blocked (HTTP 403)
2. Requests with invalid PDO → blocked (HTTP 403/409)
3. Requests with valid PDO → allowed (HTTP 2xx)
4. PDO validation failures are logged (audit trail)

DOCTRINE: PDO Enforcement Model v1 (LOCKED)
- No execution without a valid PDO
- No agent can bypass enforcement
- Violations are surfaced deterministically

Author: Cody (GID-01) — Senior Backend Engineer
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.middleware.pdo_enforcement import (
    PDOEnforcementError,
    PDOEnforcementGate,
    require_valid_pdo,
    settlement_initiation_gate,
    agent_execution_gate,
    webhook_actuation_gate,
    CROEnforcementGate,
    CROSignatureEnforcementGate,
    cro_settlement_gate,
)
from app.services.pdo.validator import (
    PDOOutcome,
    PDOValidator,
    ValidationErrorCode,
    ValidationResult,
    compute_decision_hash,
    validate_pdo_with_cro,
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


def _make_invalid_pdo_missing_fields() -> dict[str, Any]:
    """Create a PDO missing required fields."""
    return {
        "pdo_id": "PDO-TEST12345678",
        # Missing: inputs_hash, policy_version, decision_hash, outcome, timestamp, signer
    }


def _make_invalid_pdo_bad_format() -> dict[str, Any]:
    """Create a PDO with invalid format in fields."""
    return {
        "pdo_id": "invalid-pdo-id",  # Should start with PDO-
        "inputs_hash": "not-a-hash",  # Not 64-char hex
        "policy_version": "invalid",  # Missing @v<version>
        "decision_hash": "abc",  # Not 64-char hex
        "outcome": "MAYBE",  # Invalid outcome
        "timestamp": "not-a-timestamp",  # Invalid ISO format
        "signer": "anonymous",  # Missing type prefix
    }


def _make_invalid_pdo_hash_mismatch() -> dict[str, Any]:
    """Create a PDO with hash integrity failure."""
    pdo = _make_valid_pdo()
    # Tamper with inputs_hash after decision_hash was computed
    pdo["inputs_hash"] = hashlib.sha256(b"tampered_inputs").hexdigest()
    return pdo


class TestPayload(BaseModel):
    """Test request payload with PDO."""
    action: str
    pdo: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Test App Setup
# ---------------------------------------------------------------------------


def create_test_app() -> FastAPI:
    """Create FastAPI app with PDO-enforced endpoints."""
    app = FastAPI()

    # Test endpoint using Depends() pattern
    @app.post("/settlement/initiate")
    async def initiate_settlement(
        request: Request,
        _pdo_enforced: None = Depends(settlement_initiation_gate.enforce),
    ) -> dict:
        return {"status": "settlement_initiated", "enforced": True}

    # Test endpoint using Depends() with custom gate
    @app.post("/agent/execute")
    async def execute_agent_action(
        request: Request,
        _pdo_enforced: None = Depends(agent_execution_gate.enforce),
    ) -> dict:
        return {"status": "executed", "enforced": True}

    # Test endpoint using decorator pattern
    @app.post("/webhook/process")
    @require_valid_pdo("webhook_processing")
    async def process_webhook(request: Request) -> dict:
        return {"status": "processed", "enforced": True}

    # Control endpoint (no PDO enforcement)
    @app.post("/public/health")
    async def health_check() -> dict:
        return {"status": "healthy"}

    return app


@pytest.fixture
def test_client() -> TestClient:
    """Test client for PDO-enforced app."""
    app = create_test_app()
    return TestClient(app)


# ---------------------------------------------------------------------------
# PDO Validator Unit Tests
# ---------------------------------------------------------------------------


class TestPDOValidator:
    """Unit tests for PDOValidator service."""

    def test_valid_pdo_passes_validation(self):
        """Valid PDO with all required fields passes validation."""
        validator = PDOValidator()
        pdo = _make_valid_pdo()

        result = validator.validate(pdo)

        assert result.valid is True
        assert len(result.errors) == 0
        assert result.pdo_id == pdo["pdo_id"]

    def test_missing_pdo_fails_validation(self):
        """None PDO fails validation with appropriate error."""
        validator = PDOValidator()

        result = validator.validate(None)

        assert result.valid is False
        assert len(result.errors) > 0
        assert any(e.code == ValidationErrorCode.MISSING_FIELD for e in result.errors)

    def test_empty_pdo_fails_validation(self):
        """Empty dict PDO fails validation for all required fields."""
        validator = PDOValidator()

        result = validator.validate({})

        assert result.valid is False
        # Should have errors for all required fields
        assert len(result.errors) >= 7  # 7 required fields

    def test_pdo_missing_fields_fails_validation(self):
        """PDO missing some required fields fails validation."""
        validator = PDOValidator()
        pdo = _make_invalid_pdo_missing_fields()

        result = validator.validate(pdo)

        assert result.valid is False
        missing_errors = [e for e in result.errors if e.code == ValidationErrorCode.MISSING_FIELD]
        assert len(missing_errors) >= 6  # Missing 6 required fields

    def test_pdo_invalid_format_fails_validation(self):
        """PDO with invalid field formats fails validation."""
        validator = PDOValidator()
        pdo = _make_invalid_pdo_bad_format()

        result = validator.validate(pdo)

        assert result.valid is False
        format_errors = [e for e in result.errors if e.code == ValidationErrorCode.INVALID_FORMAT]
        assert len(format_errors) >= 4  # Multiple format issues

    def test_pdo_hash_mismatch_fails_validation(self):
        """PDO with hash integrity failure fails validation."""
        validator = PDOValidator()
        pdo = _make_invalid_pdo_hash_mismatch()

        result = validator.validate(pdo)

        assert result.valid is False
        hash_errors = [e for e in result.errors if e.code == ValidationErrorCode.HASH_MISMATCH]
        assert len(hash_errors) == 1

    def test_pdo_outcome_approved(self):
        """PDO with APPROVED outcome passes."""
        validator = PDOValidator()
        pdo = _make_valid_pdo(outcome="APPROVED")

        result = validator.validate(pdo)

        assert result.valid is True

    def test_pdo_outcome_rejected(self):
        """PDO with REJECTED outcome passes."""
        validator = PDOValidator()
        pdo = _make_valid_pdo(outcome="REJECTED")

        result = validator.validate(pdo)

        assert result.valid is True

    def test_pdo_outcome_pending(self):
        """PDO with PENDING outcome passes."""
        validator = PDOValidator()
        pdo = _make_valid_pdo(outcome="PENDING")

        result = validator.validate(pdo)

        assert result.valid is True

    def test_pdo_invalid_outcome_fails(self):
        """PDO with invalid outcome fails validation."""
        validator = PDOValidator()
        pdo = _make_valid_pdo()
        pdo["outcome"] = "INVALID_OUTCOME"
        # Recompute hash to isolate outcome validation
        pdo["decision_hash"] = compute_decision_hash(
            pdo["inputs_hash"], pdo["policy_version"], "INVALID_OUTCOME"
        )

        result = validator.validate(pdo)

        assert result.valid is False
        outcome_errors = [e for e in result.errors if e.code == ValidationErrorCode.INVALID_OUTCOME]
        assert len(outcome_errors) == 1


# ---------------------------------------------------------------------------
# Enforcement Gate Integration Tests
# ---------------------------------------------------------------------------


class TestPDOEnforcementGate:
    """Integration tests for PDO enforcement gates."""

    def test_request_without_pdo_blocked(self, test_client: TestClient):
        """PAC Requirement: Requests without PDO → blocked."""
        response = test_client.post(
            "/settlement/initiate",
            json={"action": "initiate"}
        )

        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"] == "PDO_ENFORCEMENT_FAILED"

    def test_request_with_invalid_pdo_blocked_403(self, test_client: TestClient):
        """PAC Requirement: Requests with invalid PDO → blocked (403)."""
        response = test_client.post(
            "/settlement/initiate",
            json={
                "action": "initiate",
                "pdo": _make_invalid_pdo_missing_fields()
            }
        )

        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["error"] == "PDO_ENFORCEMENT_FAILED"
        assert len(data["detail"]["errors"]) > 0

    def test_request_with_hash_mismatch_blocked_409(self, test_client: TestClient):
        """Requests with hash integrity failure → blocked (409 Conflict)."""
        response = test_client.post(
            "/settlement/initiate",
            json={
                "action": "initiate",
                "pdo": _make_invalid_pdo_hash_mismatch()
            }
        )

        assert response.status_code == 409
        data = response.json()
        assert data["detail"]["error"] == "PDO_ENFORCEMENT_FAILED"

    def test_request_with_valid_pdo_allowed(self, test_client: TestClient):
        """PAC Requirement: Requests with valid PDO → allowed."""
        response = test_client.post(
            "/settlement/initiate",
            json={
                "action": "initiate",
                "pdo": _make_valid_pdo()
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "settlement_initiated"
        assert data["enforced"] is True

    def test_agent_execution_gate(self, test_client: TestClient):
        """Agent execution gate enforces PDO."""
        # Without PDO
        response = test_client.post(
            "/agent/execute",
            json={"action": "execute"}
        )
        assert response.status_code == 403

        # With valid PDO
        response = test_client.post(
            "/agent/execute",
            json={
                "action": "execute",
                "pdo": _make_valid_pdo(
                    pdo_id="PDO-AGENTEXEC001",
                    signer="agent::executor",
                )
            }
        )
        assert response.status_code == 200

    def test_decorator_pattern_enforces_pdo(self, test_client: TestClient):
        """Decorator pattern enforces PDO validation."""
        # Without PDO
        response = test_client.post(
            "/webhook/process",
            json={"action": "process"}
        )
        assert response.status_code == 403

        # With valid PDO
        response = test_client.post(
            "/webhook/process",
            json={
                "action": "process",
                "pdo": _make_valid_pdo(
                    pdo_id="PDO-WEBHOOK00001",
                    signer="system::webhook_handler",
                )
            }
        )
        assert response.status_code == 200

    def test_unenforced_endpoint_allows_without_pdo(self, test_client: TestClient):
        """Endpoints without enforcement allow requests without PDO."""
        response = test_client.post(
            "/public/health",
            json={}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


# ---------------------------------------------------------------------------
# Audit Logging Tests
# ---------------------------------------------------------------------------


class TestPDOAuditLogging:
    """Tests for PDO enforcement audit logging."""

    def test_enforcement_blocked_logged(self, test_client: TestClient, caplog):
        """PAC Requirement: PDO validation failures are logged."""
        with caplog.at_level(logging.WARNING):
            response = test_client.post(
                "/settlement/initiate",
                json={"action": "initiate"}  # No PDO
            )

        assert response.status_code == 403
        # Check log contains enforcement event
        assert any("pdo_enforcement" in record.message for record in caplog.records)
        assert any("BLOCKED" in record.message for record in caplog.records)

    def test_enforcement_allowed_logged(self, test_client: TestClient, caplog):
        """Successful PDO enforcement is logged at INFO level."""
        with caplog.at_level(logging.INFO):
            response = test_client.post(
                "/settlement/initiate",
                json={
                    "action": "initiate",
                    "pdo": _make_valid_pdo()
                }
            )

        assert response.status_code == 200
        # Check log contains enforcement event
        assert any("pdo_enforcement" in record.message for record in caplog.records)
        assert any("ALLOWED" in record.message for record in caplog.records)

    def test_enforcement_point_in_log(self, test_client: TestClient, caplog):
        """Enforcement point name is included in audit logs."""
        with caplog.at_level(logging.WARNING):
            test_client.post(
                "/settlement/initiate",
                json={"action": "initiate"}
            )

        assert any("settlement_initiation" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# Edge Case Tests
# ---------------------------------------------------------------------------


class TestPDOEnforcementEdgeCases:
    """Edge case tests for PDO enforcement."""

    def test_malformed_json_body_blocked(self, test_client: TestClient):
        """Malformed JSON body is blocked (cannot extract PDO)."""
        response = test_client.post(
            "/settlement/initiate",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )

        # Should be 403 (blocked, no PDO) or 422 (validation error)
        assert response.status_code in (403, 422)

    def test_empty_request_body_blocked(self, test_client: TestClient):
        """Empty request body is blocked."""
        response = test_client.post(
            "/settlement/initiate",
            json=None
        )

        # Should be blocked - no PDO
        assert response.status_code in (403, 422)

    def test_pdo_null_value_blocked(self, test_client: TestClient):
        """PDO field with null value is blocked."""
        response = test_client.post(
            "/settlement/initiate",
            json={"action": "initiate", "pdo": None}
        )

        assert response.status_code == 403

    def test_error_response_structure(self, test_client: TestClient):
        """Verify error response follows PDOEnforcementError schema."""
        response = test_client.post(
            "/settlement/initiate",
            json={"action": "initiate"}
        )

        assert response.status_code == 403
        data = response.json()["detail"]

        # Verify schema fields
        assert "error" in data
        assert "message" in data
        assert "errors" in data
        assert "enforcement_point" in data
        assert "timestamp" in data

        # Verify values
        assert data["error"] == "PDO_ENFORCEMENT_FAILED"
        assert data["enforcement_point"] == "settlement_initiation"
        assert isinstance(data["errors"], list)


# ---------------------------------------------------------------------------
# Invariant Tests (Doctrine Compliance)
# ---------------------------------------------------------------------------


class TestPDOEnforcementInvariants:
    """Tests validating PDO enforcement invariants per doctrine."""

    def test_no_bypass_with_empty_pdo(self, test_client: TestClient):
        """Cannot bypass enforcement with empty PDO."""
        response = test_client.post(
            "/settlement/initiate",
            json={"action": "initiate", "pdo": {}}
        )
        assert response.status_code == 403

    def test_no_bypass_with_partial_pdo(self, test_client: TestClient):
        """Cannot bypass enforcement with partial PDO."""
        response = test_client.post(
            "/settlement/initiate",
            json={
                "action": "initiate",
                "pdo": {"pdo_id": "PDO-TEST12345678"}  # Only one field
            }
        )
        assert response.status_code == 403

    def test_no_bypass_with_tampered_hash(self, test_client: TestClient):
        """Cannot bypass enforcement with tampered decision hash."""
        pdo = _make_valid_pdo()
        pdo["decision_hash"] = "a" * 64  # Tamper with hash
        response = test_client.post(
            "/settlement/initiate",
            json={"action": "initiate", "pdo": pdo}
        )
        assert response.status_code == 409  # Hash mismatch

    def test_deterministic_validation(self, test_client: TestClient):
        """Same input produces same validation result deterministically."""
        pdo = _make_valid_pdo(pdo_id="PDO-DETERMINISTIC")

        # Run same request multiple times
        for _ in range(3):
            response = test_client.post(
                "/settlement/initiate",
                json={"action": "initiate", "pdo": pdo}
            )
            assert response.status_code == 200

        # Invalid PDO also deterministic
        invalid_pdo = _make_invalid_pdo_missing_fields()
        for _ in range(3):
            response = test_client.post(
                "/settlement/initiate",
                json={"action": "initiate", "pdo": invalid_pdo}
            )
            assert response.status_code == 403


# ---------------------------------------------------------------------------
# Helper Function Tests
# ---------------------------------------------------------------------------


class TestComputeDecisionHash:
    """Tests for decision hash computation."""

    def test_compute_decision_hash_deterministic(self):
        """Decision hash computation is deterministic."""
        inputs_hash = "a" * 64
        policy_version = "test_policy@v1.0.0"
        outcome = "APPROVED"

        hash1 = compute_decision_hash(inputs_hash, policy_version, outcome)
        hash2 = compute_decision_hash(inputs_hash, policy_version, outcome)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_compute_decision_hash_changes_with_inputs(self):
        """Different inputs produce different decision hashes."""
        policy_version = "test_policy@v1.0.0"
        outcome = "APPROVED"

        hash1 = compute_decision_hash("a" * 64, policy_version, outcome)
        hash2 = compute_decision_hash("b" * 64, policy_version, outcome)

        assert hash1 != hash2

    def test_compute_decision_hash_changes_with_outcome(self):
        """Different outcomes produce different decision hashes."""
        inputs_hash = "a" * 64
        policy_version = "test_policy@v1.0.0"

        hash_approved = compute_decision_hash(inputs_hash, policy_version, "APPROVED")
        hash_rejected = compute_decision_hash(inputs_hash, policy_version, "REJECTED")

        assert hash_approved != hash_rejected

# ---------------------------------------------------------------------------
# CRO Enforcement Gate Tests (PAC-RUBY-CRO-POLICY-ACTIVATION-01)
# ---------------------------------------------------------------------------


def _make_valid_pdo_with_cro(
    pdo_id: str = "PDO-CROTEST12345",
    outcome: str = "APPROVED",
    cro_decision: str = "APPROVE",
    cro_reasons: list[str] = None,
) -> dict[str, Any]:
    """Create a valid PDO with CRO decision fields."""
    pdo = _make_valid_pdo(pdo_id=pdo_id, outcome=outcome)
    pdo["cro_decision"] = cro_decision
    pdo["cro_reasons"] = cro_reasons or ["ALL_CHECKS_PASSED"]
    pdo["cro_evaluated_at"] = datetime.now(timezone.utc).isoformat()
    pdo["cro_policy_version"] = "cro_policy@v1.0.0"
    return pdo


def create_cro_test_app() -> FastAPI:
    """Create FastAPI app with CRO-enforced endpoints."""
    app = FastAPI()

    # Test endpoint using CRO enforcement gate
    @app.post("/cro/settlement/initiate")
    async def cro_initiate_settlement(
        request: Request,
        _pdo_enforced: None = Depends(cro_settlement_gate.enforce),
    ) -> dict:
        return {"status": "settlement_initiated", "cro_enforced": True}

    return app


@pytest.fixture
def cro_test_client() -> TestClient:
    """Test client for CRO-enforced app."""
    app = create_cro_test_app()
    return TestClient(app)


class TestCROEnforcementGate:
    """Integration tests for CRO enforcement gates."""

    def test_cro_approve_allows_execution(self, cro_test_client: TestClient):
        """PAC Requirement: CRO APPROVE allows execution."""
        pdo = _make_valid_pdo_with_cro(cro_decision="APPROVE")
        response = cro_test_client.post(
            "/cro/settlement/initiate",
            json={"action": "initiate", "pdo": pdo}
        )

        assert response.status_code == 200
        assert response.json()["cro_enforced"] is True

    def test_cro_tighten_terms_allows_execution(self, cro_test_client: TestClient):
        """PAC Requirement: CRO TIGHTEN_TERMS allows execution."""
        pdo = _make_valid_pdo_with_cro(
            cro_decision="TIGHTEN_TERMS",
            cro_reasons=["NEW_CARRIER_INSUFFICIENT_TENURE"],
        )
        response = cro_test_client.post(
            "/cro/settlement/initiate",
            json={"action": "initiate", "pdo": pdo}
        )

        assert response.status_code == 200

    def test_cro_hold_blocks_execution_403(self, cro_test_client: TestClient):
        """PAC Requirement: CRO HOLD blocks execution (HTTP 403)."""
        pdo = _make_valid_pdo_with_cro(
            cro_decision="HOLD",
            cro_reasons=["MISSING_CARRIER_PROFILE"],
        )
        response = cro_test_client.post(
            "/cro/settlement/initiate",
            json={"action": "initiate", "pdo": pdo}
        )

        assert response.status_code == 403
        data = response.json()["detail"]
        assert data["cro_decision"] == "HOLD"
        assert "MISSING_CARRIER_PROFILE" in data["cro_reasons"]

    def test_cro_escalate_blocks_execution_409(self, cro_test_client: TestClient):
        """PAC Requirement: CRO ESCALATE blocks execution (HTTP 409)."""
        pdo = _make_valid_pdo_with_cro(
            cro_decision="ESCALATE",
            cro_reasons=["DATA_QUALITY_BELOW_THRESHOLD"],
        )
        response = cro_test_client.post(
            "/cro/settlement/initiate",
            json={"action": "initiate", "pdo": pdo}
        )

        assert response.status_code == 409
        data = response.json()["detail"]
        assert data["cro_decision"] == "ESCALATE"
        assert "escalation_code" in data
        assert data["escalation_code"].startswith("CRO-ESCALATE-")

    def test_cro_invalid_decision_blocked(self, cro_test_client: TestClient):
        """Invalid CRO decision is blocked."""
        pdo = _make_valid_pdo_with_cro(cro_decision="INVALID_DECISION")
        response = cro_test_client.post(
            "/cro/settlement/initiate",
            json={"action": "initiate", "pdo": pdo}
        )

        assert response.status_code == 403
        data = response.json()["detail"]
        assert any(e["code"] == "CRO_DECISION_INVALID" for e in data["errors"])

    def test_pdo_without_cro_decision_passes(self, cro_test_client: TestClient):
        """PDO without CRO decision passes (backward compatible)."""
        pdo = _make_valid_pdo()  # No CRO fields
        response = cro_test_client.post(
            "/cro/settlement/initiate",
            json={"action": "initiate", "pdo": pdo}
        )

        assert response.status_code == 200


class TestCROValidation:
    """Tests for CRO validation functions."""

    def test_validate_pdo_with_cro_approve(self):
        """PAC Requirement: validate_pdo_with_cro returns valid for APPROVE."""
        pdo = _make_valid_pdo_with_cro(cro_decision="APPROVE")

        result = validate_pdo_with_cro(pdo)

        assert result.valid is True
        assert result.cro_result is not None
        assert result.cro_result.decision == "APPROVE"
        assert result.cro_result.blocks_execution is False

    def test_validate_pdo_with_cro_hold(self):
        """PAC Requirement: validate_pdo_with_cro returns invalid for HOLD."""
        pdo = _make_valid_pdo_with_cro(
            cro_decision="HOLD",
            cro_reasons=["MISSING_LANE_PROFILE"],
        )

        result = validate_pdo_with_cro(pdo)

        assert result.valid is False
        assert result.cro_result is not None
        assert result.cro_result.decision == "HOLD"
        assert result.cro_result.blocks_execution is True
        assert any(e.code == ValidationErrorCode.CRO_BLOCKS_EXECUTION for e in result.errors)

    def test_validate_pdo_with_cro_escalate(self):
        """PAC Requirement: validate_pdo_with_cro returns invalid for ESCALATE."""
        pdo = _make_valid_pdo_with_cro(
            cro_decision="ESCALATE",
            cro_reasons=["DATA_QUALITY_BELOW_THRESHOLD"],
        )

        result = validate_pdo_with_cro(pdo)

        assert result.valid is False
        assert result.cro_result is not None
        assert result.cro_result.decision == "ESCALATE"
        assert result.cro_result.blocks_execution is True

    def test_validate_pdo_with_cro_tighten(self):
        """PAC Requirement: validate_pdo_with_cro returns valid for TIGHTEN_TERMS."""
        pdo = _make_valid_pdo_with_cro(
            cro_decision="TIGHTEN_TERMS",
            cro_reasons=["NEW_CARRIER_INSUFFICIENT_TENURE"],
        )

        result = validate_pdo_with_cro(pdo)

        assert result.valid is True
        assert result.cro_result is not None
        assert result.cro_result.decision == "TIGHTEN_TERMS"
        assert result.cro_result.blocks_execution is False

    def test_cro_result_includes_policy_version(self):
        """PAC Requirement: CRO decision includes policy version in result."""
        pdo = _make_valid_pdo_with_cro(cro_decision="APPROVE")

        result = validate_pdo_with_cro(pdo)

        assert result.cro_result is not None
        assert result.cro_result.policy_version == "cro_policy@v1.0.0"


class TestCROAuditLogging:
    """Tests for CRO enforcement audit logging."""

    def test_cro_blocked_logged(self, cro_test_client: TestClient, caplog):
        """PAC Requirement: CRO blocking decisions are logged."""
        pdo = _make_valid_pdo_with_cro(
            cro_decision="HOLD",
            cro_reasons=["MISSING_CARRIER_PROFILE"],
        )

        with caplog.at_level(logging.WARNING):
            response = cro_test_client.post(
                "/cro/settlement/initiate",
                json={"action": "initiate", "pdo": pdo}
            )

        assert response.status_code == 403
        # Check CRO decision is logged
        assert any("cro_decision" in record.message.lower() for record in caplog.records)

    def test_cro_allowed_logged(self, cro_test_client: TestClient, caplog):
        """CRO allowing decisions are logged at INFO level."""
        pdo = _make_valid_pdo_with_cro(cro_decision="APPROVE")

        with caplog.at_level(logging.INFO):
            response = cro_test_client.post(
                "/cro/settlement/initiate",
                json={"action": "initiate", "pdo": pdo}
            )

        assert response.status_code == 200
        assert any("pdo_enforcement" in record.message for record in caplog.records)