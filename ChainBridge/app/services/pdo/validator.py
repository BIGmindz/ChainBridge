"""PDO Validation Service.

Implements deterministic validation of Proof Decision Outcomes (PDOs)
per the PDO Enforcement Model v1 (LOCKED doctrine).

DOCTRINE COMPLIANCE:
- No execution without PDO creation
- PDOs are immutable after execution
- A missing PDO implies an unauthorized decision
- CRO decisions are bound to PDO (PAC-RUBY-CRO-POLICY-ACTIVATION-01)

VALIDATION RULES:
A valid PDO must include ALL required fields:
- pdo_id: Globally unique identifier
- inputs_hash: SHA-256 hash of decision inputs
- policy_version: Reference to governing policy
- decision_hash: SHA-256 hash binding decision to inputs
- outcome: APPROVED | REJECTED | PENDING
- timestamp: ISO 8601 UTC timestamp
- signer: Identity of decision maker (agent or system)

CRO BINDING (Optional, enforced when present):
- cro_decision: APPROVE | TIGHTEN_TERMS | HOLD | ESCALATE
- cro_reasons: List of reason codes
- cro_evaluated_at: ISO 8601 timestamp

Author: Cody (GID-01) — Senior Backend Engineer
CRO Integration: Ruby (GID-12) — Chief Risk Officer
"""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PDO Schema Constants
# ---------------------------------------------------------------------------

PDO_ID_PATTERN = re.compile(r"^PDO-[A-Z0-9]{8,64}$")
"""Pattern for valid PDO identifiers: PDO-<uppercase alphanumeric 8-64 chars>"""

HASH_PATTERN = re.compile(r"^[a-f0-9]{64}$")
"""Pattern for SHA-256 hash strings (lowercase hex, 64 chars)"""

POLICY_VERSION_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+@v\d+(\.\d+)*$")
"""Pattern for policy version references: <policy-name>@v<major>.<minor>..."""

SIGNER_PATTERN = re.compile(r"^(agent|system|operator)::[a-zA-Z0-9_-]+$")
"""Pattern for signer identities: <type>::<identifier>"""


class PDOOutcome(str, Enum):
    """Valid PDO outcome states."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PENDING = "PENDING"


class ValidationErrorCode(str, Enum):
    """Deterministic error codes for PDO validation failures."""

    MISSING_FIELD = "MISSING_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    INVALID_OUTCOME = "INVALID_OUTCOME"
    INVALID_TIMESTAMP = "INVALID_TIMESTAMP"
    HASH_MISMATCH = "HASH_MISMATCH"
    INTEGRITY_FAILURE = "INTEGRITY_FAILURE"
    # Signature verification error codes (fail-closed)
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    UNSUPPORTED_ALGORITHM = "UNSUPPORTED_ALGORITHM"
    UNKNOWN_KEY_ID = "UNKNOWN_KEY_ID"
    MALFORMED_SIGNATURE = "MALFORMED_SIGNATURE"
    UNSIGNED_PDO = "UNSIGNED_PDO"  # FAIL - signature is mandatory
    EXPIRED_PDO = "EXPIRED_PDO"  # FAIL - PDO has expired
    REPLAY_DETECTED = "REPLAY_DETECTED"  # FAIL - nonce already used
    SIGNER_MISMATCH = "SIGNER_MISMATCH"  # FAIL - key doesn't match agent_id
    # CRO policy error codes (PAC-RUBY-CRO-POLICY-ACTIVATION-01)
    CRO_DECISION_INVALID = "CRO_DECISION_INVALID"
    CRO_BLOCKS_EXECUTION = "CRO_BLOCKS_EXECUTION"


@dataclass(frozen=True)
class ValidationError:
    """Immutable validation error record."""

    code: ValidationErrorCode
    field: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    """Immutable validation result.

    Attributes:
        valid: True if PDO passed all validation checks
        errors: List of validation errors (empty if valid)
        pdo_id: The PDO ID that was validated (for audit logging)
        signature_result: Signature verification result (if verification was performed)
        cro_result: CRO policy evaluation result (if CRO validation was performed)
    """

    valid: bool
    errors: tuple[ValidationError, ...]
    pdo_id: Optional[str]
    signature_result: Optional["SignatureVerificationResult"] = None
    cro_result: Optional["CROValidationResult"] = None

    def __bool__(self) -> bool:
        """Allow truthiness check: if validation_result: ..."""
        return self.valid


@dataclass(frozen=True)
class SignatureVerificationResult:
    """Summary of signature verification outcome.

    Attached to ValidationResult when signature verification is performed.
    """

    verified: bool
    outcome: str  # VerificationOutcome value
    is_unsigned: bool
    allows_execution: bool
    key_id: Optional[str]
    reason: str


@dataclass(frozen=True)
class CROValidationResult:
    """Summary of CRO policy evaluation outcome.

    Attached to ValidationResult when CRO validation is performed.
    PAC-RUBY-CRO-POLICY-ACTIVATION-01
    """

    decision: str  # CRODecision value
    reasons: tuple[str, ...]
    blocks_execution: bool
    policy_version: str
    evaluated_at: str


# ---------------------------------------------------------------------------
# PDO Validator Service
# ---------------------------------------------------------------------------


class PDOValidator:
    """Stateless PDO validation service.

    Implements deterministic validation per PDO Enforcement Model v1.
    All methods are pure functions with no side effects.

    USAGE:
        validator = PDOValidator()
        result = validator.validate(pdo_data)
        if not result:
            # Handle validation failure
            for error in result.errors:
                log_error(error)

    INVARIANTS:
        - validate() always returns ValidationResult
        - No exceptions raised for invalid PDOs (fail deterministically)
        - No external dependencies or I/O
    """

    # Required fields per PDO Enforcement Model v1
    REQUIRED_FIELDS = frozenset({
        "pdo_id",
        "inputs_hash",
        "policy_version",
        "decision_hash",
        "outcome",
        "timestamp",
        "signer",
    })

    def validate(self, pdo_data: Optional[dict]) -> ValidationResult:
        """Validate a PDO against enforcement rules.

        Args:
            pdo_data: Dictionary containing PDO fields (may be None)

        Returns:
            ValidationResult with valid=True if all checks pass,
            otherwise valid=False with list of errors.

        INVARIANTS:
            - Never raises exceptions for invalid input
            - Returns deterministic result for same input
            - No side effects
        """
        errors: List[ValidationError] = []
        pdo_id: Optional[str] = None

        # Null/missing PDO is immediate failure
        if pdo_data is None:
            errors.append(
                ValidationError(
                    code=ValidationErrorCode.MISSING_FIELD,
                    field="pdo",
                    message="PDO is required but was not provided",
                )
            )
            return ValidationResult(valid=False, errors=tuple(errors), pdo_id=None)

        # Validate required fields exist
        for field in self.REQUIRED_FIELDS:
            if field not in pdo_data or pdo_data[field] is None:
                errors.append(
                    ValidationError(
                        code=ValidationErrorCode.MISSING_FIELD,
                        field=field,
                        message=f"Required field '{field}' is missing or null",
                    )
                )

        # If missing required fields, return early (can't validate further)
        if errors:
            pdo_id = pdo_data.get("pdo_id") if isinstance(pdo_data.get("pdo_id"), str) else None
            return ValidationResult(valid=False, errors=tuple(errors), pdo_id=pdo_id)

        # Extract and validate individual fields
        pdo_id = str(pdo_data["pdo_id"])
        errors.extend(self._validate_pdo_id(pdo_id))
        errors.extend(self._validate_inputs_hash(str(pdo_data["inputs_hash"])))
        errors.extend(self._validate_policy_version(str(pdo_data["policy_version"])))
        errors.extend(self._validate_decision_hash(str(pdo_data["decision_hash"])))
        errors.extend(self._validate_outcome(str(pdo_data["outcome"])))
        errors.extend(self._validate_timestamp(pdo_data["timestamp"]))
        errors.extend(self._validate_signer(str(pdo_data["signer"])))

        # Validate hash integrity (decision_hash binds inputs to outcome)
        if not errors:
            errors.extend(self._validate_hash_integrity(pdo_data))

        return ValidationResult(
            valid=len(errors) == 0,
            errors=tuple(errors),
            pdo_id=pdo_id,
        )

    def validate_with_signature(self, pdo_data: Optional[dict]) -> ValidationResult:
        """Validate a PDO including signature verification.

        Extends validate() to include cryptographic signature verification.
        Signature verification runs AFTER schema validation passes.

        DOCTRINE (Fail-Closed):
        - Invalid signature → FAIL (execution blocked)
        - Unsigned PDO → FAIL (signature is mandatory)
        - Expired PDO → FAIL
        - Replay detected → FAIL
        - Signer mismatch → FAIL

        Args:
            pdo_data: Dictionary containing PDO fields (must include signature)

        Returns:
            ValidationResult with signature_result attached
        """
        # First, perform schema validation
        schema_result = self.validate(pdo_data)

        # If schema validation failed, return immediately (no signature check)
        if not schema_result.valid:
            return schema_result

        # Perform signature verification
        from app.services.pdo.signing import (
            verify_pdo_signature,
            log_verification_result,
            VerificationOutcome,
        )

        # Extract agent_id for audit logging
        agent_id = pdo_data.get("agent_id") if pdo_data else None

        sig_result = verify_pdo_signature(pdo_data)
        log_verification_result(sig_result, context="pdo_validation", agent_id=agent_id)

        # Build signature summary for result
        sig_summary = SignatureVerificationResult(
            verified=sig_result.is_valid,
            outcome=sig_result.outcome.value,
            is_unsigned=sig_result.is_unsigned,
            allows_execution=sig_result.allows_execution,
            key_id=sig_result.key_id,
            reason=sig_result.reason,
        )

        # Determine overall validity
        # DOCTRINE: Fail-closed for ALL non-VALID outcomes
        errors_list = list(schema_result.errors)

        if not sig_result.allows_execution:
            # Map verification outcome to validation error
            error_code_map = {
                VerificationOutcome.INVALID_SIGNATURE: ValidationErrorCode.INVALID_SIGNATURE,
                VerificationOutcome.UNSUPPORTED_ALGORITHM: ValidationErrorCode.UNSUPPORTED_ALGORITHM,
                VerificationOutcome.UNKNOWN_KEY_ID: ValidationErrorCode.UNKNOWN_KEY_ID,
                VerificationOutcome.MALFORMED_SIGNATURE: ValidationErrorCode.MALFORMED_SIGNATURE,
                VerificationOutcome.UNSIGNED_PDO: ValidationErrorCode.UNSIGNED_PDO,
                VerificationOutcome.EXPIRED_PDO: ValidationErrorCode.EXPIRED_PDO,
                VerificationOutcome.REPLAY_DETECTED: ValidationErrorCode.REPLAY_DETECTED,
                VerificationOutcome.SIGNER_MISMATCH: ValidationErrorCode.SIGNER_MISMATCH,
            }
            error_code = error_code_map.get(
                sig_result.outcome,
                ValidationErrorCode.INVALID_SIGNATURE,
            )
            errors_list.append(
                ValidationError(
                    code=error_code,
                    field="signature",
                    message=sig_result.reason,
                )
            )

        return ValidationResult(
            valid=len(errors_list) == 0,
            errors=tuple(errors_list),
            pdo_id=schema_result.pdo_id,
            signature_result=sig_summary,
        )

    def _validate_pdo_id(self, pdo_id: str) -> List[ValidationError]:
        """Validate PDO identifier format."""
        if not PDO_ID_PATTERN.match(pdo_id):
            return [
                ValidationError(
                    code=ValidationErrorCode.INVALID_FORMAT,
                    field="pdo_id",
                    message=f"pdo_id must match pattern PDO-<ALPHANUMERIC>, got: {pdo_id[:50]}",
                )
            ]
        return []

    def _validate_inputs_hash(self, inputs_hash: str) -> List[ValidationError]:
        """Validate inputs_hash is valid SHA-256."""
        if not HASH_PATTERN.match(inputs_hash.lower()):
            return [
                ValidationError(
                    code=ValidationErrorCode.INVALID_FORMAT,
                    field="inputs_hash",
                    message="inputs_hash must be a 64-character lowercase hex string (SHA-256)",
                )
            ]
        return []

    def _validate_policy_version(self, policy_version: str) -> List[ValidationError]:
        """Validate policy_version format."""
        if not POLICY_VERSION_PATTERN.match(policy_version):
            return [
                ValidationError(
                    code=ValidationErrorCode.INVALID_FORMAT,
                    field="policy_version",
                    message=f"policy_version must match <name>@v<version>, got: {policy_version[:50]}",
                )
            ]
        return []

    def _validate_decision_hash(self, decision_hash: str) -> List[ValidationError]:
        """Validate decision_hash is valid SHA-256."""
        if not HASH_PATTERN.match(decision_hash.lower()):
            return [
                ValidationError(
                    code=ValidationErrorCode.INVALID_FORMAT,
                    field="decision_hash",
                    message="decision_hash must be a 64-character lowercase hex string (SHA-256)",
                )
            ]
        return []

    def _validate_outcome(self, outcome: str) -> List[ValidationError]:
        """Validate outcome is a known PDO outcome."""
        try:
            PDOOutcome(outcome.upper())
            return []
        except ValueError:
            valid_outcomes = ", ".join(o.value for o in PDOOutcome)
            return [
                ValidationError(
                    code=ValidationErrorCode.INVALID_OUTCOME,
                    field="outcome",
                    message=f"outcome must be one of [{valid_outcomes}], got: {outcome}",
                )
            ]

    def _validate_timestamp(self, timestamp: object) -> List[ValidationError]:
        """Validate timestamp is ISO 8601 UTC format."""
        if isinstance(timestamp, datetime):
            return []

        if not isinstance(timestamp, str):
            return [
                ValidationError(
                    code=ValidationErrorCode.INVALID_TIMESTAMP,
                    field="timestamp",
                    message=f"timestamp must be ISO 8601 string or datetime, got: {type(timestamp).__name__}",
                )
            ]

        try:
            # Parse ISO 8601 format
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return []
        except ValueError:
            return [
                ValidationError(
                    code=ValidationErrorCode.INVALID_TIMESTAMP,
                    field="timestamp",
                    message=f"timestamp must be valid ISO 8601, got: {timestamp[:50]}",
                )
            ]

    def _validate_signer(self, signer: str) -> List[ValidationError]:
        """Validate signer identity format."""
        if not SIGNER_PATTERN.match(signer):
            return [
                ValidationError(
                    code=ValidationErrorCode.INVALID_FORMAT,
                    field="signer",
                    message=f"signer must match <type>::<identifier>, got: {signer[:50]}",
                )
            ]
        return []

    def _validate_hash_integrity(self, pdo_data: dict) -> List[ValidationError]:
        """Validate decision_hash correctly binds inputs to outcome.

        The decision_hash must be SHA-256(inputs_hash + policy_version + outcome).
        This ensures the decision is cryptographically bound to its inputs.
        """
        inputs_hash = str(pdo_data["inputs_hash"]).lower()
        policy_version = str(pdo_data["policy_version"])
        outcome = str(pdo_data["outcome"]).upper()
        declared_hash = str(pdo_data["decision_hash"]).lower()

        # Compute expected hash
        binding_data = f"{inputs_hash}|{policy_version}|{outcome}"
        expected_hash = hashlib.sha256(binding_data.encode("utf-8")).hexdigest()

        if declared_hash != expected_hash:
            return [
                ValidationError(
                    code=ValidationErrorCode.HASH_MISMATCH,
                    field="decision_hash",
                    message="decision_hash does not match computed binding hash (inputs_hash|policy_version|outcome)",
                )
            ]
        return []


# ---------------------------------------------------------------------------
# Module-level singleton for convenience
# ---------------------------------------------------------------------------

_validator = PDOValidator()


def validate_pdo(pdo_data: Optional[dict]) -> ValidationResult:
    """Validate a PDO using the module-level validator.

    This is a convenience function for the common case.
    For advanced usage, instantiate PDOValidator directly.

    Args:
        pdo_data: Dictionary containing PDO fields

    Returns:
        ValidationResult indicating pass/fail with any errors
    """
    return _validator.validate(pdo_data)


def validate_pdo_with_signature(pdo_data: Optional[dict]) -> ValidationResult:
    """Validate a PDO with signature verification.

    DOCTRINE (Fail-Closed per PDO_SIGNING_MODEL_V1 - LOCKED):
    - Invalid signature → FAIL (execution blocked)
    - Unsigned PDO → FAIL (signature is MANDATORY)
    - Expired PDO → FAIL
    - Replay detected → FAIL
    - Signer mismatch → FAIL

    Args:
        pdo_data: Dictionary containing PDO fields (must include signature)

    Returns:
        ValidationResult with signature_result attached
    """
    return _validator.validate_with_signature(pdo_data)


def compute_decision_hash(inputs_hash: str, policy_version: str, outcome: str) -> str:
    """Compute the decision_hash for a PDO.

    Helper function to generate the correct decision_hash when creating PDOs.

    Args:
        inputs_hash: SHA-256 hash of inputs (lowercase hex)
        policy_version: Policy reference (e.g., "settlement-policy@v1.0")
        outcome: Decision outcome (APPROVED, REJECTED, PENDING)

    Returns:
        SHA-256 hash (lowercase hex) binding inputs to outcome
    """
    binding_data = f"{inputs_hash.lower()}|{policy_version}|{outcome.upper()}"
    return hashlib.sha256(binding_data.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Risk-Aware Validation (Infrastructure Only)
# ---------------------------------------------------------------------------
# TODO(Ruby): Wire risk thresholds and policy decisions
# The following functions provide risk metadata extraction during PDO validation.
# Risk metadata is OPTIONAL — PDOs without risk fields remain fully valid.
# ---------------------------------------------------------------------------


def validate_pdo_with_risk(pdo_data: Optional[dict]) -> tuple["ValidationResult", Optional[Any]]:
    """Validate PDO and extract risk metadata if present.

    Extended validation that also captures risk metadata for downstream hooks.
    Risk metadata is OPTIONAL — its absence does not affect validation.

    TODO(Ruby): Integrate with CRO policy engine

    Args:
        pdo_data: Dictionary containing PDO fields (may include risk fields)

    Returns:
        Tuple of (ValidationResult, RiskMetadata or None)
    """
    # Import here to avoid circular imports
    from app.services.risk.interface import (
        RiskMetadata,
        extract_risk_metadata,
        log_risk_metadata_with_pdo,
    )

    # Validate PDO (risk fields are ignored by core validation)
    result = _validator.validate(pdo_data)

    # Extract risk metadata (optional, never fails validation)
    risk_metadata: Optional[RiskMetadata] = extract_risk_metadata(pdo_data)

    # Log risk metadata alongside PDO for audit
    log_risk_metadata_with_pdo(result.pdo_id, risk_metadata, context="pdo_validation")

    return result, risk_metadata


# ---------------------------------------------------------------------------
# CRO Policy Validation (PAC-RUBY-CRO-POLICY-ACTIVATION-01)
# ---------------------------------------------------------------------------
# CRO policy decisions are bound to PDO and enforced at execution time.
# HOLD and ESCALATE decisions block execution (fail-closed).
# ---------------------------------------------------------------------------


def validate_pdo_with_cro(pdo_data: Optional[dict]) -> ValidationResult:
    """Validate PDO and enforce CRO policy decisions.

    CRO policy decisions are bound to PDO metadata and enforced deterministically.
    HOLD and ESCALATE decisions block execution (fail-closed).

    DOCTRINE (PAC-RUBY-CRO-POLICY-ACTIVATION-01):
    - CRO decision overrides base RiskBand if more restrictive
    - HOLD → execution blocked
    - ESCALATE → execution blocked
    - TIGHTEN_TERMS → execution with modified terms
    - APPROVE → execution proceeds normally

    Args:
        pdo_data: Dictionary containing PDO fields (may include CRO decision)

    Returns:
        ValidationResult with cro_result attached
    """
    # First perform base validation
    base_result = _validator.validate(pdo_data)

    if not base_result.valid:
        return base_result

    # Extract CRO decision from PDO if present
    cro_decision = pdo_data.get("cro_decision") if pdo_data else None
    cro_reasons = pdo_data.get("cro_reasons", []) if pdo_data else []
    cro_evaluated_at = pdo_data.get("cro_evaluated_at") if pdo_data else None

    # If no CRO decision present, return base result (pass-through)
    if cro_decision is None:
        return base_result

    # Valid CRO decisions
    valid_cro_decisions = {"APPROVE", "TIGHTEN_TERMS", "HOLD", "ESCALATE"}

    errors_list = list(base_result.errors)

    # Validate CRO decision format
    if cro_decision not in valid_cro_decisions:
        errors_list.append(
            ValidationError(
                code=ValidationErrorCode.CRO_DECISION_INVALID,
                field="cro_decision",
                message=f"Invalid CRO decision: {cro_decision}. Must be one of: {valid_cro_decisions}",
            )
        )
        return ValidationResult(
            valid=False,
            errors=tuple(errors_list),
            pdo_id=base_result.pdo_id,
            signature_result=base_result.signature_result,
        )

    # Check if CRO decision blocks execution
    blocks_execution = cro_decision in ("HOLD", "ESCALATE")

    if blocks_execution:
        reason_str = ", ".join(cro_reasons) if cro_reasons else "CRO policy violation"
        errors_list.append(
            ValidationError(
                code=ValidationErrorCode.CRO_BLOCKS_EXECUTION,
                field="cro_decision",
                message=f"CRO decision '{cro_decision}' blocks execution: {reason_str}",
            )
        )

    # Build CRO validation result
    cro_result = CROValidationResult(
        decision=cro_decision,
        reasons=tuple(cro_reasons) if cro_reasons else (),
        blocks_execution=blocks_execution,
        policy_version=pdo_data.get("cro_policy_version", "cro_policy@v1.0.0") if pdo_data else "cro_policy@v1.0.0",
        evaluated_at=cro_evaluated_at or "",
    )

    # Log CRO validation
    logger.info(
        "CRO validation: pdo_id=%s decision=%s blocks=%s reasons=%s",
        base_result.pdo_id,
        cro_decision,
        blocks_execution,
        cro_reasons,
    )

    return ValidationResult(
        valid=len(errors_list) == 0,
        errors=tuple(errors_list),
        pdo_id=base_result.pdo_id,
        signature_result=base_result.signature_result,
        cro_result=cro_result,
    )


def validate_pdo_with_signature_and_cro(pdo_data: Optional[dict]) -> ValidationResult:
    """Validate PDO with both signature verification and CRO policy enforcement.

    Full validation including:
    1. Schema validation
    2. Signature verification (fail-closed)
    3. CRO policy enforcement (fail-closed for HOLD/ESCALATE)

    Args:
        pdo_data: Dictionary containing PDO fields

    Returns:
        ValidationResult with signature_result and cro_result attached
    """
    # First validate with signature
    sig_result = _validator.validate_with_signature(pdo_data)

    if not sig_result.valid:
        return sig_result

    # Extract CRO decision from PDO if present
    cro_decision = pdo_data.get("cro_decision") if pdo_data else None
    cro_reasons = pdo_data.get("cro_reasons", []) if pdo_data else []
    cro_evaluated_at = pdo_data.get("cro_evaluated_at") if pdo_data else None

    # If no CRO decision present, return signature result
    if cro_decision is None:
        return sig_result

    # Valid CRO decisions
    valid_cro_decisions = {"APPROVE", "TIGHTEN_TERMS", "HOLD", "ESCALATE"}

    errors_list = list(sig_result.errors)

    # Validate CRO decision format
    if cro_decision not in valid_cro_decisions:
        errors_list.append(
            ValidationError(
                code=ValidationErrorCode.CRO_DECISION_INVALID,
                field="cro_decision",
                message=f"Invalid CRO decision: {cro_decision}. Must be one of: {valid_cro_decisions}",
            )
        )
        return ValidationResult(
            valid=False,
            errors=tuple(errors_list),
            pdo_id=sig_result.pdo_id,
            signature_result=sig_result.signature_result,
        )

    # Check if CRO decision blocks execution
    blocks_execution = cro_decision in ("HOLD", "ESCALATE")

    if blocks_execution:
        reason_str = ", ".join(cro_reasons) if cro_reasons else "CRO policy violation"
        errors_list.append(
            ValidationError(
                code=ValidationErrorCode.CRO_BLOCKS_EXECUTION,
                field="cro_decision",
                message=f"CRO decision '{cro_decision}' blocks execution: {reason_str}",
            )
        )

    # Build CRO validation result
    cro_result = CROValidationResult(
        decision=cro_decision,
        reasons=tuple(cro_reasons) if cro_reasons else (),
        blocks_execution=blocks_execution,
        policy_version=pdo_data.get("cro_policy_version", "cro_policy@v1.0.0") if pdo_data else "cro_policy@v1.0.0",
        evaluated_at=cro_evaluated_at or "",
    )

    # Log CRO validation
    logger.info(
        "CRO validation (with signature): pdo_id=%s decision=%s blocks=%s reasons=%s",
        sig_result.pdo_id,
        cro_decision,
        blocks_execution,
        cro_reasons,
    )

    return ValidationResult(
        valid=len(errors_list) == 0,
        errors=tuple(errors_list),
        pdo_id=sig_result.pdo_id,
        signature_result=sig_result.signature_result,
        cro_result=cro_result,
    )
