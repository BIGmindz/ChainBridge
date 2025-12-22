"""PDO Enforcement Middleware.

╔══════════════════════════════════════════════════════════════════════╗
║ EXECUTING AGENT: Cody (GID-01) — Senior Backend Engineer             ║
║ EXECUTING COLOR: 🟢 BLUE                                             ║
║ PAC: PAC-CODY-A6-ARCHITECTURE-ENFORCEMENT-WIRING-01                  ║
╚══════════════════════════════════════════════════════════════════════╝

Implements server-side PDO enforcement gates per PDO Enforcement Model v1 (LOCKED doctrine).

ENFORCEMENT BOUNDARIES:
1. Agent execution endpoints
2. ChainPay settlement initiation
3. External actuation endpoints (webhooks, chain calls)

CRO POLICY ENFORCEMENT (PAC-RUBY-CRO-POLICY-ACTIVATION-01):
- CRO decisions are bound to PDO and enforced at execution
- HOLD → HTTP 403 + CRO_HOLD reason
- ESCALATE → HTTP 409 + escalation_code
- All CRO decisions are logged for audit

INVARIANTS (non-negotiable):
- Validate PDO BEFORE any side effects
- Fail closed (no soft bypasses)
- No environment-based skips
- All failures logged for audit

ERROR RESPONSES:
- HTTP 403 Forbidden: PDO validation failed (enforcement block)
- HTTP 403 Forbidden: CRO HOLD decision
- HTTP 409 Conflict: PDO hash mismatch, integrity failure, or CRO ESCALATE

Author: Cody (GID-01) — Senior Backend Engineer
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from fastapi import HTTPException, Request, status
from pydantic import BaseModel

from app.services.pdo.validator import (
    PDOValidator,
    ValidationErrorCode,
    ValidationResult,
    SignatureVerificationResult,
    CROValidationResult,
    validate_pdo_with_cro,
    validate_pdo_with_signature_and_cro,
)

logger = logging.getLogger(__name__)

# Type variable for preserving function signatures
F = TypeVar("F", bound=Callable[..., Any])


# ---------------------------------------------------------------------------
# Error Response Schema
# ---------------------------------------------------------------------------


class PDOEnforcementError(BaseModel):
    """Structured error payload for PDO enforcement failures.

    Returned in HTTP 403/409 responses when PDO validation fails.
    """

    error: str = "PDO_ENFORCEMENT_FAILED"
    message: str
    pdo_id: Optional[str] = None
    errors: list[dict]
    enforcement_point: str
    timestamp: str


# ---------------------------------------------------------------------------
# Audit Logging
# ---------------------------------------------------------------------------


def _log_enforcement_event(
    *,
    enforcement_point: str,
    result: ValidationResult,
    request_path: str,
    request_method: str,
    outcome: str,
) -> None:
    """Log PDO enforcement event for audit trail.

    All enforcement decisions (pass or fail) are logged with structured data.
    Includes CRO decision data when present (PAC-RUBY-CRO-POLICY-ACTIVATION-01).

    Args:
        enforcement_point: Name of the enforcement boundary
        result: Validation result from PDOValidator
        request_path: HTTP request path
        request_method: HTTP request method
        outcome: "ALLOWED" or "BLOCKED"
    """
    log_data = {
        "event": "pdo_enforcement",
        "enforcement_point": enforcement_point,
        "pdo_id": result.pdo_id,
        "agent_id": result.agent_id if hasattr(result, 'agent_id') else None,
        "outcome": outcome,
        "valid": result.valid,
        "error_count": len(result.errors),
        "request_path": request_path,
        "request_method": request_method,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Include signature verification info if present
    if result.signature_result is not None:
        log_data["signature_verified"] = result.signature_result.verified
        log_data["signature_outcome"] = result.signature_result.outcome
        log_data["signature_is_unsigned"] = result.signature_result.is_unsigned
        log_data["signature_key_id"] = result.signature_result.key_id

    # Include CRO decision info if present (PAC-RUBY-CRO-POLICY-ACTIVATION-01)
    if result.cro_result is not None:
        log_data["cro_decision"] = result.cro_result.decision
        log_data["cro_reasons"] = list(result.cro_result.reasons)
        log_data["cro_blocks_execution"] = result.cro_result.blocks_execution
        log_data["cro_policy_version"] = result.cro_result.policy_version

    if result.errors:
        log_data["errors"] = [
            {"code": e.code.value, "field": e.field, "message": e.message}
            for e in result.errors
        ]

    if outcome == "BLOCKED":
        logger.warning("PDO enforcement blocked request: %s", json.dumps(log_data))
    else:
        logger.info("PDO enforcement allowed request: %s", json.dumps(log_data))


# ---------------------------------------------------------------------------
# Enforcement Gate Implementation
# ---------------------------------------------------------------------------


class PDOEnforcementGate:
    """PDO enforcement gate for FastAPI endpoints.

    Validates PDO in request body before allowing endpoint execution.
    Fail-closed: requests without valid PDO are blocked.

    USAGE:
        gate = PDOEnforcementGate("settlement_initiation")

        @router.post("/settlements/initiate")
        async def initiate_settlement(
            request: Request,
            payload: SettlementRequest,
            _pdo_enforced: None = Depends(gate.enforce),
        ):
            # Only executes if PDO is valid
            ...

    INVARIANTS:
        - enforce() MUST be called before any side effects
        - No bypass mechanisms exist
        - All failures are logged
    """

    def __init__(self, enforcement_point: str):
        """Initialize enforcement gate.

        Args:
            enforcement_point: Name identifying this enforcement boundary
                              (used in logs and error responses)
        """
        self.enforcement_point = enforcement_point
        self._validator = PDOValidator()

    async def enforce(self, request: Request) -> None:
        """FastAPI Dependency that enforces PDO validation.

        Extract PDO from request body and validate. Raise HTTPException
        if validation fails.

        Args:
            request: FastAPI Request object

        Raises:
            HTTPException: 403 if PDO missing or invalid format
            HTTPException: 409 if PDO hash integrity check fails
        """
        # Extract PDO from request body
        pdo_data = await self._extract_pdo(request)

        # Validate PDO
        result = self._validator.validate(pdo_data)

        # Log enforcement decision
        _log_enforcement_event(
            enforcement_point=self.enforcement_point,
            result=result,
            request_path=str(request.url.path),
            request_method=request.method,
            outcome="ALLOWED" if result.valid else "BLOCKED",
        )

        # Block if invalid
        if not result.valid:
            self._raise_enforcement_error(result, request)

    async def _extract_pdo(self, request: Request) -> Optional[dict]:
        """Extract PDO from request body.

        PDO is expected in request body under "pdo" key.

        Args:
            request: FastAPI Request object

        Returns:
            PDO dictionary if found, None otherwise
        """
        try:
            body = await request.json()
            if isinstance(body, dict):
                return body.get("pdo")
            return None
        except Exception:
            # JSON parse failure - PDO is missing
            return None

    def _raise_enforcement_error(
        self, result: ValidationResult, request: Request
    ) -> None:
        """Raise HTTPException for enforcement failure.

        Chooses appropriate status code:
        - 409 Conflict for hash/integrity failures
        - 403 Forbidden for all other validation failures

        Args:
            result: Failed validation result
            request: Original request (for error context)

        Raises:
            HTTPException: Always raises
        """
        # Check if any error is a hash/integrity issue
        integrity_codes = {
            ValidationErrorCode.HASH_MISMATCH,
            ValidationErrorCode.INTEGRITY_FAILURE,
        }
        has_integrity_error = any(e.code in integrity_codes for e in result.errors)

        status_code = (
            status.HTTP_409_CONFLICT if has_integrity_error
            else status.HTTP_403_FORBIDDEN
        )

        error_response = PDOEnforcementError(
            message=f"PDO enforcement failed at {self.enforcement_point}",
            pdo_id=result.pdo_id,
            errors=[
                {"code": e.code.value, "field": e.field, "message": e.message}
                for e in result.errors
            ],
            enforcement_point=self.enforcement_point,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        raise HTTPException(
            status_code=status_code,
            detail=error_response.model_dump(),
        )


# ---------------------------------------------------------------------------
# Decorator-style Enforcement (Alternative API)
# ---------------------------------------------------------------------------


def require_valid_pdo(enforcement_point: str) -> Callable[[F], F]:
    """Decorator to enforce PDO validation on an endpoint.

    Alternative to dependency injection for simpler cases.

    USAGE:
        @router.post("/execute")
        @require_valid_pdo("agent_execution")
        async def execute_action(request: Request, payload: ExecuteRequest):
            ...

    Args:
        enforcement_point: Name identifying this enforcement boundary

    Returns:
        Decorator function
    """
    gate = PDOEnforcementGate(enforcement_point)

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Find request in args or kwargs
            request = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None:
                raise RuntimeError(
                    f"@require_valid_pdo requires 'request: Request' parameter "
                    f"in endpoint {func.__name__}"
                )

            await gate.enforce(request)
            return await func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


# ---------------------------------------------------------------------------
# Pre-configured Enforcement Gates
# ---------------------------------------------------------------------------

# Agent execution enforcement
agent_execution_gate = PDOEnforcementGate("agent_execution")

# Settlement initiation enforcement
settlement_initiation_gate = PDOEnforcementGate("settlement_initiation")

# Webhook actuation enforcement
webhook_actuation_gate = PDOEnforcementGate("webhook_actuation")

# External chain call enforcement
chain_call_gate = PDOEnforcementGate("chain_call")


# ---------------------------------------------------------------------------
# Signature-Enforcing Gate (FAIL-CLOSED)
# ---------------------------------------------------------------------------
# This gate validates both PDO schema AND cryptographic signature.
# Invalid signatures block execution (fail-closed).
# Unsigned PDOs are REJECTED (no legacy mode).
# ---------------------------------------------------------------------------


class SignatureEnforcementGate:
    """PDO enforcement gate with signature verification.

    Extends PDOEnforcementGate to include cryptographic signature verification.
    This gate enforces FAIL-CLOSED behavior for ALL signature verification failures.

    DOCTRINE (PDO_SIGNING_MODEL_V1 - LOCKED):
    - Invalid signature → BLOCK (HTTP 403)
    - Unsigned PDO → BLOCK (HTTP 403) - NO legacy pass-through
    - Expired PDO → BLOCK (HTTP 403)
    - Replayed nonce → BLOCK (HTTP 403)
    - Signer mismatch → BLOCK (HTTP 403)
    - All failures logged for audit

    USAGE:
        gate = SignatureEnforcementGate("settlement_initiation")

        @router.post("/settlements/initiate")
        async def initiate_settlement(
            request: Request,
            _pdo_enforced: None = Depends(gate.enforce),
        ):
            # Only executes if PDO is valid AND signature verifies
            ...
    """

    def __init__(self, enforcement_point: str):
        """Initialize signature enforcement gate.

        Args:
            enforcement_point: Name identifying this enforcement boundary
        """
        self.enforcement_point = enforcement_point
        self._validator = PDOValidator()

    async def enforce(self, request: Request) -> None:
        """FastAPI Dependency with signature-verified PDO enforcement.

        Validates PDO schema AND cryptographic signature.
        Raises HTTPException if either check fails.

        Args:
            request: FastAPI Request object

        Raises:
            HTTPException: 403 if PDO missing, invalid, or signature fails
            HTTPException: 409 if PDO hash integrity check fails
        """
        # Extract PDO from request body
        pdo_data = await self._extract_pdo(request)

        # Validate PDO WITH signature verification
        result = self._validator.validate_with_signature(pdo_data)

        # Log enforcement decision with signature info
        _log_enforcement_event(
            enforcement_point=self.enforcement_point,
            result=result,
            request_path=str(request.url.path),
            request_method=request.method,
            outcome="ALLOWED" if result.valid else "BLOCKED",
        )

        # Block if invalid
        if not result.valid:
            self._raise_enforcement_error(result, request)

    async def _extract_pdo(self, request: Request) -> Optional[dict]:
        """Extract PDO from request body."""
        try:
            body = await request.json()
            if isinstance(body, dict):
                return body.get("pdo")
            return None
        except Exception:
            return None

    def _raise_enforcement_error(
        self, result: ValidationResult, request: Request
    ) -> None:
        """Raise HTTPException for enforcement failure.

        Chooses appropriate status code:
        - 409 Conflict for hash/integrity failures
        - 403 Forbidden for all other validation failures (including signature)
        """
        integrity_codes = {
            ValidationErrorCode.HASH_MISMATCH,
            ValidationErrorCode.INTEGRITY_FAILURE,
        }
        has_integrity_error = any(e.code in integrity_codes for e in result.errors)

        status_code = (
            status.HTTP_409_CONFLICT if has_integrity_error
            else status.HTTP_403_FORBIDDEN
        )

        error_response = PDOEnforcementError(
            message=f"PDO enforcement failed at {self.enforcement_point}",
            pdo_id=result.pdo_id,
            errors=[
                {"code": e.code.value, "field": e.field, "message": e.message}
                for e in result.errors
            ],
            enforcement_point=self.enforcement_point,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        raise HTTPException(
            status_code=status_code,
            detail=error_response.model_dump(),
        )


# Pre-configured Signature Enforcement Gates
# Use these for endpoints requiring cryptographic verification
signature_agent_execution_gate = SignatureEnforcementGate("agent_execution")
signature_settlement_gate = SignatureEnforcementGate("settlement_initiation")
signature_webhook_gate = SignatureEnforcementGate("webhook_actuation")
signature_chain_call_gate = SignatureEnforcementGate("chain_call")


# ---------------------------------------------------------------------------
# CRO Policy Enforcement Gates (PAC-RUBY-CRO-POLICY-ACTIVATION-01)
# ---------------------------------------------------------------------------
# These gates enforce CRO policy decisions bound to PDO.
# HOLD and ESCALATE decisions block execution (fail-closed).
# ---------------------------------------------------------------------------


class CROEnforcementGate:
    """PDO enforcement gate with CRO policy enforcement.

    Validates PDO schema AND enforces CRO policy decisions.
    HOLD and ESCALATE decisions block execution (fail-closed).

    DOCTRINE (PAC-RUBY-CRO-POLICY-ACTIVATION-01):
    - HOLD → BLOCK (HTTP 403)
    - ESCALATE → BLOCK (HTTP 409 with escalation_code)
    - TIGHTEN_TERMS → ALLOW (with modified terms)
    - APPROVE → ALLOW (normal execution)
    - All decisions logged for audit

    USAGE:
        gate = CROEnforcementGate("settlement_initiation")

        @router.post("/settlements/initiate")
        async def initiate_settlement(
            request: Request,
            _pdo_enforced: None = Depends(gate.enforce),
        ):
            # Only executes if PDO is valid AND CRO allows
            ...
    """

    def __init__(self, enforcement_point: str):
        """Initialize CRO enforcement gate.

        Args:
            enforcement_point: Name identifying this enforcement boundary
        """
        self.enforcement_point = enforcement_point
        self._validator = PDOValidator()

    async def enforce(self, request: Request) -> None:
        """FastAPI Dependency with CRO policy-enforced PDO validation.

        Validates PDO schema AND enforces CRO policy decisions.
        Raises HTTPException if validation fails or CRO blocks execution.

        Args:
            request: FastAPI Request object

        Raises:
            HTTPException: 403 if PDO missing, invalid, or CRO HOLD
            HTTPException: 409 if PDO hash integrity fails or CRO ESCALATE
        """
        # Extract PDO from request body
        pdo_data = await self._extract_pdo(request)

        # Validate PDO WITH CRO enforcement
        result = validate_pdo_with_cro(pdo_data)

        # Log enforcement decision with CRO info
        _log_enforcement_event(
            enforcement_point=self.enforcement_point,
            result=result,
            request_path=str(request.url.path),
            request_method=request.method,
            outcome="ALLOWED" if result.valid else "BLOCKED",
        )

        # Block if invalid
        if not result.valid:
            self._raise_enforcement_error(result, request)

    async def _extract_pdo(self, request: Request) -> Optional[dict]:
        """Extract PDO from request body."""
        try:
            body = await request.json()
            if isinstance(body, dict):
                return body.get("pdo")
            return None
        except Exception:
            return None

    def _raise_enforcement_error(
        self, result: ValidationResult, request: Request
    ) -> None:
        """Raise HTTPException for enforcement failure.

        Chooses appropriate status code:
        - 409 Conflict for hash/integrity failures or CRO ESCALATE
        - 403 Forbidden for all other failures (including CRO HOLD)
        """
        integrity_codes = {
            ValidationErrorCode.HASH_MISMATCH,
            ValidationErrorCode.INTEGRITY_FAILURE,
        }
        has_integrity_error = any(e.code in integrity_codes for e in result.errors)

        # CRO ESCALATE maps to 409 Conflict
        has_escalate = (
            result.cro_result is not None
            and result.cro_result.decision == "ESCALATE"
        )

        status_code = (
            status.HTTP_409_CONFLICT if (has_integrity_error or has_escalate)
            else status.HTTP_403_FORBIDDEN
        )

        # Build error response with CRO details
        error_details = [
            {"code": e.code.value, "field": e.field, "message": e.message}
            for e in result.errors
        ]

        # Add CRO-specific fields to response
        cro_info = {}
        if result.cro_result is not None:
            cro_info = {
                "cro_decision": result.cro_result.decision,
                "cro_reasons": list(result.cro_result.reasons),
                "escalation_code": (
                    f"CRO-{result.cro_result.decision}-{result.pdo_id or 'UNKNOWN'}"
                    if result.cro_result.decision == "ESCALATE"
                    else None
                ),
            }

        error_response = PDOEnforcementError(
            message=f"PDO enforcement failed at {self.enforcement_point}",
            pdo_id=result.pdo_id,
            errors=error_details,
            enforcement_point=self.enforcement_point,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Merge CRO info into response
        response_dict = error_response.model_dump()
        response_dict.update(cro_info)

        raise HTTPException(
            status_code=status_code,
            detail=response_dict,
        )


class CROSignatureEnforcementGate:
    """PDO enforcement gate with both signature verification AND CRO policy enforcement.

    Full enforcement including:
    1. PDO schema validation
    2. Cryptographic signature verification (fail-closed)
    3. CRO policy enforcement (fail-closed for HOLD/ESCALATE)

    DOCTRINE:
    - Invalid signature → BLOCK (HTTP 403)
    - Unsigned PDO → BLOCK (HTTP 403)
    - CRO HOLD → BLOCK (HTTP 403)
    - CRO ESCALATE → BLOCK (HTTP 409)
    - All decisions logged for audit

    USAGE:
        gate = CROSignatureEnforcementGate("settlement_initiation")

        @router.post("/settlements/initiate")
        async def initiate_settlement(
            request: Request,
            _pdo_enforced: None = Depends(gate.enforce),
        ):
            # Only executes if PDO valid, signature verified, AND CRO allows
            ...
    """

    def __init__(self, enforcement_point: str):
        """Initialize CRO + signature enforcement gate.

        Args:
            enforcement_point: Name identifying this enforcement boundary
        """
        self.enforcement_point = enforcement_point
        self._validator = PDOValidator()

    async def enforce(self, request: Request) -> None:
        """FastAPI Dependency with signature + CRO policy enforcement.

        Validates PDO schema, signature, AND CRO policy decisions.
        Raises HTTPException if any check fails.

        Args:
            request: FastAPI Request object

        Raises:
            HTTPException: 403 if PDO/signature invalid or CRO HOLD
            HTTPException: 409 if integrity fails or CRO ESCALATE
        """
        # Extract PDO from request body
        pdo_data = await self._extract_pdo(request)

        # Validate PDO WITH signature AND CRO enforcement
        result = validate_pdo_with_signature_and_cro(pdo_data)

        # Log enforcement decision
        _log_enforcement_event(
            enforcement_point=self.enforcement_point,
            result=result,
            request_path=str(request.url.path),
            request_method=request.method,
            outcome="ALLOWED" if result.valid else "BLOCKED",
        )

        # Block if invalid
        if not result.valid:
            self._raise_enforcement_error(result, request)

    async def _extract_pdo(self, request: Request) -> Optional[dict]:
        """Extract PDO from request body."""
        try:
            body = await request.json()
            if isinstance(body, dict):
                return body.get("pdo")
            return None
        except Exception:
            return None

    def _raise_enforcement_error(
        self, result: ValidationResult, request: Request
    ) -> None:
        """Raise HTTPException for enforcement failure."""
        integrity_codes = {
            ValidationErrorCode.HASH_MISMATCH,
            ValidationErrorCode.INTEGRITY_FAILURE,
        }
        has_integrity_error = any(e.code in integrity_codes for e in result.errors)

        # CRO ESCALATE maps to 409 Conflict
        has_escalate = (
            result.cro_result is not None
            and result.cro_result.decision == "ESCALATE"
        )

        status_code = (
            status.HTTP_409_CONFLICT if (has_integrity_error or has_escalate)
            else status.HTTP_403_FORBIDDEN
        )

        # Build error response with CRO details
        error_details = [
            {"code": e.code.value, "field": e.field, "message": e.message}
            for e in result.errors
        ]

        cro_info = {}
        if result.cro_result is not None:
            cro_info = {
                "cro_decision": result.cro_result.decision,
                "cro_reasons": list(result.cro_result.reasons),
                "escalation_code": (
                    f"CRO-{result.cro_result.decision}-{result.pdo_id or 'UNKNOWN'}"
                    if result.cro_result.decision == "ESCALATE"
                    else None
                ),
            }

        error_response = PDOEnforcementError(
            message=f"PDO enforcement failed at {self.enforcement_point}",
            pdo_id=result.pdo_id,
            errors=error_details,
            enforcement_point=self.enforcement_point,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        response_dict = error_response.model_dump()
        response_dict.update(cro_info)

        raise HTTPException(
            status_code=status_code,
            detail=response_dict,
        )


# Pre-configured CRO Enforcement Gates
# Use these for endpoints requiring CRO policy enforcement
cro_agent_execution_gate = CROEnforcementGate("agent_execution")
cro_settlement_gate = CROEnforcementGate("settlement_initiation")
cro_webhook_gate = CROEnforcementGate("webhook_actuation")
cro_chain_call_gate = CROEnforcementGate("chain_call")

# Full enforcement gates (signature + CRO)
cro_signature_agent_gate = CROSignatureEnforcementGate("agent_execution")
cro_signature_settlement_gate = CROSignatureEnforcementGate("settlement_initiation")
cro_signature_webhook_gate = CROSignatureEnforcementGate("webhook_actuation")
cro_signature_chain_call_gate = CROSignatureEnforcementGate("chain_call")


# ---------------------------------------------------------------------------
# A6 Architecture Enforcement Gates (PAC-CODY-A6-ARCHITECTURE-ENFORCEMENT-WIRING-01)
# ---------------------------------------------------------------------------
# These gates enforce A1-A5 Architecture Locks:
# - Agent GID format validation
# - Authority signature requirements
# - Settlement blocking when CRO requires authorization
# ---------------------------------------------------------------------------


class A6EnforcementGate:
    """Settlement gate with A6 Architecture Lock enforcement.

    Enforces A1-A5 Architecture Locks at settlement boundary:
    - A1: Agent GID must be valid format (GID-NN)
    - A2: Authority signature required when CRO blocks execution
    - A3: Proof lineage must be forward-only

    DOCTRINE (FAIL-CLOSED per PAC-CODY-A6-ARCHITECTURE-ENFORCEMENT-WIRING-01):
    - Invalid GID → BLOCK (HTTP 403)
    - Missing authority when required → BLOCK (HTTP 403)
    - Broken proof lineage → BLOCK (HTTP 409)

    USAGE:
        gate = A6EnforcementGate("settlement_initiation")

        @router.post("/settlements/initiate")
        async def initiate_settlement(
            request: Request,
            _a6_enforced: None = Depends(gate.enforce),
        ):
            # Only executes if A6 constraints are satisfied
            ...
    """

    def __init__(self, enforcement_point: str):
        """Initialize A6 enforcement gate.

        Args:
            enforcement_point: Name identifying this enforcement boundary
        """
        self.enforcement_point = enforcement_point
        self._validator = PDOValidator()

    async def enforce(self, request: Request) -> None:
        """FastAPI Dependency with A6 architecture enforcement.

        Validates PDO schema AND enforces A6 Architecture Lock constraints.
        Raises HTTPException if validation fails or A6 constraints violated.

        Args:
            request: FastAPI Request object

        Raises:
            HTTPException: 403 if GID invalid or authority missing
            HTTPException: 409 if proof lineage broken
        """
        from app.services.pdo.validator import validate_pdo_a6_enforcement

        # Extract PDO from request body
        pdo_data = await self._extract_pdo(request)

        # First validate base PDO
        base_result = self._validator.validate(pdo_data)
        if not base_result.valid:
            _log_enforcement_event(
                enforcement_point=self.enforcement_point,
                result=base_result,
                request_path=str(request.url.path),
                request_method=request.method,
                outcome="BLOCKED",
            )
            self._raise_enforcement_error(base_result, request)

        # Then validate A6 enforcement constraints
        a6_result = validate_pdo_a6_enforcement(pdo_data)

        # Log enforcement decision
        _log_enforcement_event(
            enforcement_point=f"{self.enforcement_point}_a6",
            result=a6_result,
            request_path=str(request.url.path),
            request_method=request.method,
            outcome="ALLOWED" if a6_result.valid else "BLOCKED",
        )

        # Block if A6 constraints violated
        if not a6_result.valid:
            self._raise_enforcement_error(a6_result, request)

    async def _extract_pdo(self, request: Request) -> Optional[dict]:
        """Extract PDO from request body."""
        try:
            body = await request.json()
            if isinstance(body, dict):
                return body.get("pdo")
            return None
        except Exception:
            return None

    def _raise_enforcement_error(
        self, result: ValidationResult, request: Request
    ) -> None:
        """Raise HTTPException for A6 enforcement failure.

        Chooses appropriate status code:
        - 409 Conflict for proof lineage violations
        - 403 Forbidden for GID/authority violations
        """
        lineage_codes = {
            ValidationErrorCode.PROOF_LINEAGE_BROKEN,
        }
        has_lineage_error = any(e.code in lineage_codes for e in result.errors)

        status_code = (
            status.HTTP_409_CONFLICT if has_lineage_error
            else status.HTTP_403_FORBIDDEN
        )

        error_details = [
            {"code": e.code.value, "field": e.field, "message": e.message}
            for e in result.errors
        ]

        error_response = PDOEnforcementError(
            error="A6_ARCHITECTURE_ENFORCEMENT_FAILED",
            message="A6 Architecture Lock constraints violated",
            pdo_id=result.pdo_id,
            errors=error_details,
            enforcement_point=self.enforcement_point,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        raise HTTPException(
            status_code=status_code,
            detail=error_response.model_dump(),
        )


# Pre-configured A6 Enforcement Gates
a6_settlement_gate = A6EnforcementGate("settlement_initiation")
a6_agent_execution_gate = A6EnforcementGate("agent_execution")


# ---------------------------------------------------------------------------
# Risk-Aware Enforcement Gates (Infrastructure Only)
# ---------------------------------------------------------------------------
# TODO(Ruby): Wire policy decisions to risk check results
# These gates extend PDO enforcement with risk metadata extraction and hooks.
# Currently pass-through — risk checks log but do not block.
# ---------------------------------------------------------------------------


class RiskAwareEnforcementGate:
    """PDO enforcement gate with risk metadata support.

    Extends PDOEnforcementGate to:
    1. Extract risk metadata from PDO
    2. Call risk check hooks
    3. Log risk data for audit

    INFRASTRUCTURE ONLY — Risk checks currently pass-through.
    TODO(Ruby): Implement actual risk policy decisions.

    USAGE:
        gate = RiskAwareEnforcementGate(
            "settlement_initiation",
            risk_hook=pre_settlement_risk_check,
        )

        @router.post("/settlements/initiate")
        async def initiate_settlement(
            request: Request,
            _pdo_enforced: None = Depends(gate.enforce),
        ):
            # Only executes if PDO is valid
            # Risk metadata is logged but does not block (pass-through)
            ...
    """

    def __init__(
        self,
        enforcement_point: str,
        risk_hook: Optional[Callable] = None,
    ):
        """Initialize risk-aware enforcement gate.

        Args:
            enforcement_point: Name identifying this enforcement boundary
            risk_hook: Optional risk check function to call after PDO validation
                      Signature: (pdo_id, risk_metadata) -> RiskCheckResult
        """
        self.enforcement_point = enforcement_point
        self._validator = PDOValidator()
        self._risk_hook = risk_hook

    async def enforce(self, request: Request) -> None:
        """FastAPI Dependency with risk-aware PDO enforcement.

        Validates PDO, extracts risk metadata, and calls risk hooks.
        Risk checks are logged but do not block (pass-through mode).

        Args:
            request: FastAPI Request object

        Raises:
            HTTPException: 403 if PDO missing or invalid format
            HTTPException: 409 if PDO hash integrity check fails
        """
        # Import here to avoid circular imports
        from app.services.pdo.validator import validate_pdo_with_risk
        from app.services.risk.interface import RiskCheckResult

        # Extract PDO from request body
        pdo_data = await self._extract_pdo(request)

        # Validate PDO and extract risk metadata
        result, risk_metadata = validate_pdo_with_risk(pdo_data)

        # Log enforcement decision with risk data
        _log_enforcement_event_with_risk(
            enforcement_point=self.enforcement_point,
            result=result,
            risk_metadata=risk_metadata,
            request_path=str(request.url.path),
            request_method=request.method,
            outcome="ALLOWED" if result.valid else "BLOCKED",
        )

        # Block if PDO validation failed
        if not result.valid:
            self._raise_enforcement_error(result, request)

        # Call risk hook if configured (pass-through mode)
        if self._risk_hook is not None:
            risk_result: RiskCheckResult = self._risk_hook(result.pdo_id, risk_metadata)
            # TODO(Ruby): Act on risk_result.decision
            # Currently logged only — no blocking based on risk
            logger.info(
                "Risk hook result: hook=%s pdo_id=%s decision=%s reason=%s",
                risk_result.hook_name,
                risk_result.pdo_id,
                risk_result.decision.value,
                risk_result.reason,
            )

    async def _extract_pdo(self, request: Request) -> Optional[dict]:
        """Extract PDO from request body."""
        try:
            body = await request.json()
            if isinstance(body, dict):
                return body.get("pdo")
            return None
        except Exception:
            return None

    def _raise_enforcement_error(
        self, result: ValidationResult, request: Request
    ) -> None:
        """Raise HTTPException for enforcement failure."""
        integrity_codes = {
            ValidationErrorCode.HASH_MISMATCH,
            ValidationErrorCode.INTEGRITY_FAILURE,
        }
        has_integrity_error = any(e.code in integrity_codes for e in result.errors)

        status_code = (
            status.HTTP_409_CONFLICT if has_integrity_error
            else status.HTTP_403_FORBIDDEN
        )

        error_response = PDOEnforcementError(
            message=f"PDO enforcement failed at {self.enforcement_point}",
            pdo_id=result.pdo_id,
            errors=[
                {"code": e.code.value, "field": e.field, "message": e.message}
                for e in result.errors
            ],
            enforcement_point=self.enforcement_point,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        raise HTTPException(
            status_code=status_code,
            detail=error_response.model_dump(),
        )


def _log_enforcement_event_with_risk(
    *,
    enforcement_point: str,
    result: ValidationResult,
    risk_metadata: Optional[Any],
    request_path: str,
    request_method: str,
    outcome: str,
) -> None:
    """Log PDO enforcement event with risk metadata for audit.

    Extended version of _log_enforcement_event that includes risk data.
    """
    log_data = {
        "event": "pdo_enforcement_with_risk",
        "enforcement_point": enforcement_point,
        "pdo_id": result.pdo_id,
        "outcome": outcome,
        "valid": result.valid,
        "error_count": len(result.errors),
        "request_path": request_path,
        "request_method": request_method,
        "has_risk_metadata": risk_metadata is not None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if risk_metadata:
        log_data["risk_score"] = risk_metadata.risk_score
        log_data["risk_band"] = risk_metadata.risk_band.value
        log_data["risk_source"] = risk_metadata.risk_source.value

    if result.errors:
        log_data["errors"] = [
            {"code": e.code.value, "field": e.field, "message": e.message}
            for e in result.errors
        ]

    if outcome == "BLOCKED":
        logger.warning("PDO enforcement blocked request: %s", json.dumps(log_data))
    else:
        logger.info("PDO enforcement allowed request (with risk): %s", json.dumps(log_data))


# ---------------------------------------------------------------------------
# Pre-configured Risk-Aware Gates
# ---------------------------------------------------------------------------
# TODO(Ruby): Wire actual risk hooks when policy is ready


def _get_risk_aware_execution_gate() -> RiskAwareEnforcementGate:
    """Factory for risk-aware agent execution gate.

    Lazy import to avoid circular dependencies.
    """
    from app.services.risk.interface import pre_execution_risk_check
    return RiskAwareEnforcementGate(
        "agent_execution",
        risk_hook=pre_execution_risk_check,
    )


def _get_risk_aware_settlement_gate() -> RiskAwareEnforcementGate:
    """Factory for risk-aware settlement gate.

    Lazy import to avoid circular dependencies.
    """
    from app.services.risk.interface import pre_settlement_risk_check
    return RiskAwareEnforcementGate(
        "settlement_initiation",
        risk_hook=pre_settlement_risk_check,
    )


# Lazy-initialized risk-aware gates
# Use these for endpoints that need risk metadata logging
risk_aware_execution_gate: Optional[RiskAwareEnforcementGate] = None
risk_aware_settlement_gate: Optional[RiskAwareEnforcementGate] = None


def get_risk_aware_execution_gate() -> RiskAwareEnforcementGate:
    """Get or create the risk-aware execution gate."""
    global risk_aware_execution_gate
    if risk_aware_execution_gate is None:
        risk_aware_execution_gate = _get_risk_aware_execution_gate()
    return risk_aware_execution_gate


def get_risk_aware_settlement_gate() -> RiskAwareEnforcementGate:
    """Get or create the risk-aware settlement gate."""
    global risk_aware_settlement_gate
    if risk_aware_settlement_gate is None:
        risk_aware_settlement_gate = _get_risk_aware_settlement_gate()
    return risk_aware_settlement_gate


# ═══════════════════════════════════════════════════════════════════════════
# END — Cody (GID-01) — 🔵
# ═══════════════════════════════════════════════════════════════════════════
