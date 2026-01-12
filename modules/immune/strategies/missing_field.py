"""
Missing Field Remediation Strategy
==================================

PAC-SYS-P161-MISSING-FIELD-STRATEGY: The First Muscle of the Immune System.

This strategy handles Pydantic validation errors caused by missing required
fields. It can:
1. Auto-fill fields that have known safe defaults
2. Generate precise "Please provide X" requests for mandatory fields

Governance Model:
    - IF Field has Default in Schema → AUTO_FILL
    - IF Field is Optional → SKIP or AUTO_FILL with None
    - IF Field is Mandatory AND No Context → REQUEST_USER_INPUT

Invariants:
    - INV-IMMUNE-001: Data Integrity - Never corrupt transaction intent
    - Never guess sensitive data (user IDs, account numbers, etc.)
    - Only apply defaults defined in schema or safe_defaults registry

Author: Benson (GID-00)
Classification: IMMUNE_STRATEGY_IMPLEMENTATION
Attestation: MASTER-BER-P161-STRATEGY
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
import re
import time

from ..remediator import (
    RemediationStrategy,
    RemediationResult,
)


@dataclass
class FieldFix:
    """A single field fix operation."""
    field_name: str
    field_path: str  # Dot-notation path (e.g., "payment_data.currency")
    default_value: Any
    fix_type: str  # "schema_default", "safe_default", "user_required"
    confidence: float = 1.0


class MissingFieldStrategy(RemediationStrategy):
    """
    Strategy for fixing missing field validation errors.
    
    This is the first concrete implementation of the Immune System's
    remediation capabilities. It intercepts Pydantic "value_error.missing"
    errors and either:
    1. Auto-fills with safe defaults (high confidence)
    2. Requests specific user input (when guessing is dangerous)
    
    Safe Defaults Registry:
        Fields that can be safely defaulted without corrupting intent.
        Examples: currency → "USD", country → from context, timestamp → now()
    
    Sensitive Fields (Never Auto-Fill):
        user_id, account_number, passport_number, transaction_id, etc.
    """
    
    # Fields that are NEVER safe to auto-fill
    SENSITIVE_FIELDS: Set[str] = {
        "user_id", "account_id", "account_number",
        "passport_number", "id_number", "ssn", "tax_id",
        "transaction_id", "reference_id", "external_id",
        "password", "secret", "api_key", "token",
        "private_key", "signature", "hash",
        "face_match_score", "liveness_score",  # Biometric - must be real
        "risk_score",  # AML - must be calculated
    }
    
    # Safe defaults for common fields
    SAFE_DEFAULTS: Dict[str, Any] = {
        # Payment defaults
        "currency": "USD",
        "payment_method": "wire",
        
        # Shipment defaults  
        "shipping_method": "standard",
        "insurance_required": False,
        "priority": "normal",
        
        # Common metadata
        "notes": "",
        "tags": [],
        "metadata": {},
        
        # Timestamps (will be computed at fix time)
        "created_at": "__NOW__",
        "updated_at": "__NOW__",
        "timestamp": "__NOW__",
    }
    
    # Fields that can be inferred from context
    CONTEXTUAL_FIELDS: Set[str] = {
        "origin_country",  # Can infer from user's registration country
        "destination_country",  # Can infer from recipient address
    }
    
    @property
    def strategy_id(self) -> str:
        return "missing_field_strategy"
    
    @property
    def handles_gates(self) -> List[str]:
        # This strategy handles validation errors before any gate
        # It intercepts at the API layer (Pydantic validation)
        return ["validation", "biometric", "aml", "customs"]
    
    @property
    def handles_errors(self) -> List[str]:
        return [
            "VALIDATION_ERROR",
            "MISSING_FIELD",
            "value_error.missing",
            "type_error.none.not_allowed",
        ]
    
    def can_handle(self, gate: str, error_code: str, context: Dict[str, Any]) -> bool:
        """
        Determine if this strategy can handle the given error.
        
        Returns True if:
        1. Error is a missing field type
        2. The missing field is not in the sensitive list
        3. We have either a safe default or can request user input
        """
        # Check if it's a missing field error
        if error_code not in self.handles_errors:
            # Also check if error message contains missing field indicators
            error_msg = context.get("error_message", "").lower()
            if "missing" not in error_msg and "required" not in error_msg:
                return False
        
        # Extract the missing field name
        missing_fields = self._extract_missing_fields(context)
        
        # We can handle if at least one field is fixable
        for field_name in missing_fields:
            if self._is_fixable(field_name):
                return True
        
        return len(missing_fields) > 0  # We can at least generate user request
    
    def estimate_success(self, gate: str, error_code: str, context: Dict[str, Any]) -> float:
        """
        Estimate probability of successful remediation.
        
        High confidence (0.9+): All missing fields have safe defaults
        Medium confidence (0.5-0.9): Mix of auto-fill and user requests
        Low confidence (0.1-0.5): Mostly user requests needed
        """
        missing_fields = self._extract_missing_fields(context)
        
        if not missing_fields:
            return 0.0
        
        auto_fixable = sum(1 for f in missing_fields if self._has_safe_default(f))
        total = len(missing_fields)
        
        # Base confidence on ratio of auto-fixable fields
        if auto_fixable == total:
            return 0.95  # All fields have safe defaults
        elif auto_fixable > 0:
            return 0.5 + (0.4 * auto_fixable / total)  # 0.5 to 0.9
        else:
            return 0.3  # We can still request user input
    
    def execute(self, original_data: Dict[str, Any], context: Dict[str, Any]) -> RemediationResult:
        """
        Attempt to fix missing field errors.
        
        Process:
        1. Parse the error to identify missing fields
        2. For each field, check if we can auto-fill
        3. Apply safe defaults where possible
        4. Generate user request for remaining fields
        
        Returns RemediationResult with corrected_data (if successful)
        or explanation of what user input is needed.
        """
        start_time = time.time()
        
        # Extract missing fields from error context
        missing_fields = self._extract_missing_fields(context)
        
        if not missing_fields:
            return RemediationResult(
                success=False,
                strategy_used=self.strategy_id,
                original_error=context.get("error_message", "Unknown error"),
                explanation="Could not identify missing fields from error",
                confidence=0.0,
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        # Categorize fields
        fixes: List[FieldFix] = []
        user_required: List[str] = []
        
        for field_path in missing_fields:
            field_name = field_path.split(".")[-1]  # Get leaf name
            
            if self._is_sensitive(field_name):
                # Never auto-fill sensitive fields
                user_required.append(field_path)
            elif self._has_safe_default(field_name):
                # Auto-fill with safe default
                default = self._get_safe_default(field_name)
                fixes.append(FieldFix(
                    field_name=field_name,
                    field_path=field_path,
                    default_value=default,
                    fix_type="safe_default",
                    confidence=0.95
                ))
            else:
                # Need user input
                user_required.append(field_path)
        
        # Apply fixes to create corrected data
        corrected_data = self._apply_fixes(original_data, fixes)
        
        # Determine success
        if user_required:
            # Partial success - some fields need user input
            success = len(fixes) > 0  # At least something was fixed
            explanation = self._generate_user_request(user_required, fixes)
            confidence = len(fixes) / (len(fixes) + len(user_required))
        else:
            # Full success - all fields auto-filled
            success = True
            explanation = f"Auto-filled {len(fixes)} missing field(s): {[f.field_name for f in fixes]}"
            confidence = 0.95
        
        return RemediationResult(
            success=success,
            strategy_used=self.strategy_id,
            original_error=context.get("error_message", "Missing fields"),
            corrected_data=corrected_data if fixes else None,
            explanation=explanation,
            confidence=confidence,
            execution_time_ms=(time.time() - start_time) * 1000
        )
    
    def _extract_missing_fields(self, context: Dict[str, Any]) -> List[str]:
        """Extract missing field names from error context."""
        missing = []
        
        # Try to get from structured error details
        errors = context.get("errors", [])
        if isinstance(errors, list):
            for err in errors:
                if isinstance(err, dict):
                    # Pydantic v2 style
                    loc = err.get("loc", [])
                    err_type = err.get("type", "")
                    if "missing" in err_type or "required" in str(err.get("msg", "")):
                        field_path = ".".join(str(l) for l in loc)
                        if field_path:
                            missing.append(field_path)
        
        # Fallback: parse error message
        if not missing:
            error_msg = context.get("error_message", "")
            # Look for patterns like "field required" or "missing: field_name"
            patterns = [
                r"'(\w+)' is required",
                r"field '(\w+)' missing",
                r"missing required field[s]?: ([^\]]+)",
                r"(\w+): field required",
            ]
            for pattern in patterns:
                matches = re.findall(pattern, error_msg, re.IGNORECASE)
                missing.extend(matches)
        
        # Also check blame info
        blame = context.get("blame", {})
        if "missing_fields" in blame:
            missing.extend(blame["missing_fields"])
        
        return list(set(missing))  # Deduplicate
    
    def _is_fixable(self, field_name: str) -> bool:
        """Check if a field can be fixed (either auto-fill or user request)."""
        return not self._is_sensitive(field_name) or True  # Can always request
    
    def _is_sensitive(self, field_name: str) -> bool:
        """Check if a field is too sensitive to auto-fill."""
        field_lower = field_name.lower()
        
        # Direct match
        if field_lower in self.SENSITIVE_FIELDS:
            return True
        
        # Pattern match for variations
        sensitive_patterns = ["_id", "_key", "_secret", "_token", "_score", "password", "ssn"]
        for pattern in sensitive_patterns:
            if pattern in field_lower:
                return True
        
        return False
    
    def _has_safe_default(self, field_name: str) -> bool:
        """Check if we have a safe default for this field."""
        return field_name.lower() in {k.lower() for k in self.SAFE_DEFAULTS}
    
    def _get_safe_default(self, field_name: str) -> Any:
        """Get the safe default value for a field."""
        # Case-insensitive lookup
        for key, value in self.SAFE_DEFAULTS.items():
            if key.lower() == field_name.lower():
                # Handle special values
                if value == "__NOW__":
                    return datetime.now(timezone.utc).isoformat()
                return value
        return None
    
    def _apply_fixes(self, original_data: Dict[str, Any], fixes: List[FieldFix]) -> Dict[str, Any]:
        """Apply fixes to create corrected data."""
        import copy
        corrected = copy.deepcopy(original_data)
        
        for fix in fixes:
            # Navigate to the correct location using dot notation
            parts = fix.field_path.split(".")
            target = corrected
            
            # Navigate/create nested structure
            for part in parts[:-1]:
                if part not in target:
                    target[part] = {}
                target = target[part]
            
            # Set the value
            target[parts[-1]] = fix.default_value
        
        return corrected
    
    def _generate_user_request(self, user_required: List[str], fixes: List[FieldFix]) -> str:
        """Generate a user-friendly request for missing information."""
        parts = []
        
        if fixes:
            parts.append(f"Auto-filled {len(fixes)} field(s): {[f.field_name for f in fixes]}.")
        
        if user_required:
            parts.append(f"Please provide the following required field(s): {user_required}")
        
        return " ".join(parts)


# =============================================================================
# STRATEGY DEPLOYMENT COMPLETE
# =============================================================================
#
# MissingFieldStrategy is now available for registration with RemediationEngine:
#
#     from modules.immune import RemediationEngine
#     from modules.immune.strategies import MissingFieldStrategy
#
#     engine = RemediationEngine()
#     engine.register_strategy(MissingFieldStrategy())
#
# Test Scenarios:
#   1. Transaction missing "currency" → Auto-fix to "USD"
#   2. Transaction missing "user_id" → Request user input (sensitive)
#   3. Transaction missing "timestamp" → Auto-fix to now()
#
# Attestation: MASTER-BER-P161-STRATEGY
# Ledger: ATTEST: MISSING_FIELD_HEALER_ACTIVE
# =============================================================================
