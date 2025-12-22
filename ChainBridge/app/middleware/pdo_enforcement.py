"""PDO Enforcement Middleware.

Implements server-side PDO enforcement gates per PDO Enforcement Model v1 (LOCKED doctrine).

ENFORCEMENT BOUNDARIES:
1. Agent execution endpoints
2. ChainPay settlement initiation
3. External actuation endpoints (webhooks, chain calls)

INVARIANTS (non-negotiable):
- Validate PDO BEFORE any side effects
- Fail closed (no soft bypasses)
- No environment-based skips
- All failures logged for audit

ERROR RESPONSES:
- HTTP 403 Forbidden: PDO validation failed (enforcement block)
- HTTP 409 Conflict: PDO hash mismatch or integrity failure

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
        "outcome": outcome,
        "valid": result.valid,
        "error_count": len(result.errors),
        "request_path": request_path,
        "request_method": request_method,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

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
