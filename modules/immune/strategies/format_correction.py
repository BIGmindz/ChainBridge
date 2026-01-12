"""
Format Correction Remediation Strategy
======================================

PAC-SYS-P162-FORMAT-CORRECTION-STRATEGY: The Universal Translator.

This strategy handles validation errors caused by format mismatches - where
the data is present but in the wrong format. It can:

1. Normalize dates to ISO-8601 format
2. Strip whitespace and control characters
3. Normalize case for enum fields (uppercase)
4. Fix numeric string formats (currency amounts, percentages)

Governance Model:
    - IF Input can be unambiguously mapped to Schema Format → TRANSFORM
    - IF Ambiguous (e.g., 01/02/2023 could be Jan 2 or Feb 1) → REQUEST_CLARIFICATION

Invariants:
    - INV-IMMUNE-002: Semantic Preservation - meaning must not change
    - Never guess ambiguous dates (DD/MM vs MM/DD)
    - Always preserve the semantic intent of the original data

Author: Benson (GID-00)
Classification: IMMUNE_STRATEGY_IMPLEMENTATION
Attestation: MASTER-BER-P162-STRATEGY
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
import re
import time

from ..remediator import (
    RemediationStrategy,
    RemediationResult,
)


@dataclass
class FormatFix:
    """A single format correction operation."""
    field_path: str
    original_value: Any
    corrected_value: Any
    fix_type: str  # "date_iso", "trim_whitespace", "uppercase", "numeric"
    confidence: float = 1.0


class FormatCorrectionStrategy(RemediationStrategy):
    """
    Strategy for fixing format/type validation errors.
    
    This is the second concrete implementation of the Immune System.
    It acts as a Universal Translator, converting "dialect" variations
    into the canonical format expected by the schema.
    
    Supported Corrections:
        - Date formats → ISO-8601 (YYYY-MM-DD)
        - Whitespace → Trimmed
        - Enum/Code values → UPPERCASE
        - Numeric strings → Proper decimals
        - Currency codes → Uppercase, trimmed
    
    Ambiguity Handling:
        Dates like "01/02/2023" are REJECTED as ambiguous.
        Only unambiguous formats are auto-corrected.
    """
    
    # Known enum fields that should be uppercase
    UPPERCASE_FIELDS: Set[str] = {
        "currency", "currency_code",
        "country", "country_code", 
        "document_type", "id_type",
        "status", "state",
        "payment_method", "payment_type",
        "shipping_method", "shipping_type",
        "priority", "risk_level",
        "hs_code", "tariff_code",
    }
    
    # Fields that contain dates
    DATE_FIELDS: Set[str] = {
        "date", "timestamp", "datetime",
        "created_at", "updated_at", "deleted_at",
        "birth_date", "date_of_birth", "dob",
        "expiry_date", "expiration_date", "expires_at",
        "issue_date", "issued_at",
        "departure_date", "arrival_date",
        "ship_date", "delivery_date",
    }
    
    # Unambiguous date formats (day > 12 or year first)
    # Format: (regex pattern, strptime format, description)
    SAFE_DATE_PATTERNS: List[Tuple[str, str, str]] = [
        # ISO-8601 formats (always safe)
        (r"^\d{4}-\d{2}-\d{2}$", "%Y-%m-%d", "ISO date"),
        (r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", None, "ISO datetime"),
        (r"^\d{4}/\d{2}/\d{2}$", "%Y/%m/%d", "Year-first slash"),
        
        # European formats with day > 12 (unambiguous)
        (r"^(\d{2})/(\d{2})/(\d{4})$", None, "DD/MM/YYYY or MM/DD/YYYY"),
        (r"^(\d{2})-(\d{2})-(\d{4})$", None, "DD-MM-YYYY or MM-DD-YYYY"),
        
        # Written months (always unambiguous)
        (r"^\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}$", 
         None, "D Month YYYY"),
        (r"^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}$",
         None, "Month D, YYYY"),
    ]
    
    # Ambiguous date patterns (reject these)
    AMBIGUOUS_DATE_PATTERNS: List[str] = [
        r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$",  # Could be MM/DD or DD/MM
        r"^(\d{1,2})-(\d{1,2})-(\d{2,4})$",  # Could be MM-DD or DD-MM
    ]
    
    @property
    def strategy_id(self) -> str:
        return "format_correction_strategy"
    
    @property
    def handles_gates(self) -> List[str]:
        return ["validation", "biometric", "aml", "customs"]
    
    @property
    def handles_errors(self) -> List[str]:
        return [
            "FORMAT_ERROR",
            "TYPE_ERROR",
            "value_error",
            "type_error",
            "date_from_datetime_parsing",
            "datetime_parsing",
            "enum",
            "string_type",
            "value_error.date",
            "value_error.datetime",
            "type_error.enum",
        ]
    
    def can_handle(self, gate: str, error_code: str, context: Dict[str, Any]) -> bool:
        """Check if this strategy can handle the error."""
        # Direct error code match
        error_lower = error_code.lower()
        if any(e in error_lower for e in ["format", "type", "date", "enum", "string"]):
            return True
        
        # Check error message for format-related issues
        error_msg = context.get("error_message", "").lower()
        format_indicators = [
            "invalid format", "invalid date", "invalid datetime",
            "not a valid", "could not parse", "type error",
            "expected", "enum", "must be"
        ]
        return any(indicator in error_msg for indicator in format_indicators)
    
    def estimate_success(self, gate: str, error_code: str, context: Dict[str, Any]) -> float:
        """Estimate success probability."""
        # Check what kind of format errors we're dealing with
        errors = context.get("errors", [])
        
        if not errors:
            # No structured error info, lower confidence
            return 0.4
        
        fixable = 0
        ambiguous = 0
        
        for err in errors:
            if isinstance(err, dict):
                loc = err.get("loc", [])
                field_name = loc[-1] if loc else ""
                err_type = err.get("type", "").lower()
                input_val = err.get("input", "")
                
                if self._is_date_field(field_name) or "date" in err_type:
                    if self._is_date_ambiguous(str(input_val)):
                        ambiguous += 1
                    else:
                        fixable += 1
                elif self._is_uppercase_field(field_name) or "enum" in err_type:
                    fixable += 1
                elif "string" in err_type or "type" in err_type:
                    fixable += 1
        
        total = fixable + ambiguous
        if total == 0:
            return 0.5
        
        return 0.3 + (0.6 * fixable / total)  # 0.3 to 0.9
    
    def execute(self, original_data: Dict[str, Any], context: Dict[str, Any]) -> RemediationResult:
        """
        Attempt to fix format errors.
        
        Process:
        1. Identify fields with format issues
        2. Apply appropriate normalization
        3. Return corrected data or explanation of ambiguities
        """
        start_time = time.time()
        
        errors = context.get("errors", [])
        fixes: List[FormatFix] = []
        ambiguous: List[str] = []
        unfixable: List[str] = []
        
        for err in errors:
            if not isinstance(err, dict):
                continue
            
            loc = err.get("loc", [])
            field_path = ".".join(str(l) for l in loc)
            field_name = str(loc[-1]) if loc else ""
            err_type = err.get("type", "").lower()
            input_val = err.get("input")
            
            # Get the original value from the data
            original_val = self._get_nested_value(original_data, loc)
            if original_val is None:
                original_val = input_val
            
            # Try to fix based on field type
            fix = None
            
            # Date fields
            if self._is_date_field(field_name) or "date" in err_type:
                fix = self._fix_date(field_path, original_val)
                if fix is None and original_val:
                    if self._is_date_ambiguous(str(original_val)):
                        ambiguous.append(f"{field_path} (ambiguous date format)")
                    else:
                        unfixable.append(field_path)
            
            # Uppercase/enum fields
            elif self._is_uppercase_field(field_name) or "enum" in err_type:
                fix = self._fix_uppercase(field_path, original_val)
            
            # String trimming (for any string type error)
            elif "string" in err_type or "type" in err_type:
                fix = self._fix_string(field_path, original_val)
            
            if fix:
                fixes.append(fix)
        
        # Also scan original data for common issues
        additional_fixes = self._scan_for_format_issues(original_data)
        fixes.extend(additional_fixes)
        
        # Apply fixes
        if fixes:
            corrected_data = self._apply_fixes(original_data, fixes)
            
            explanation_parts = [f"Corrected {len(fixes)} format issue(s):"]
            for fix in fixes[:5]:  # Show first 5
                explanation_parts.append(f"  {fix.field_path}: '{fix.original_value}' → '{fix.corrected_value}'")
            if len(fixes) > 5:
                explanation_parts.append(f"  ... and {len(fixes) - 5} more")
            
            if ambiguous:
                explanation_parts.append(f"Ambiguous fields requiring clarification: {ambiguous}")
            
            return RemediationResult(
                success=True,
                strategy_used=self.strategy_id,
                original_error=context.get("error_message", "Format errors"),
                corrected_data=corrected_data,
                explanation="\n".join(explanation_parts),
                confidence=0.9 if not ambiguous else 0.7,
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        # No fixes possible
        explanation = "Could not auto-correct format issues."
        if ambiguous:
            explanation += f" Ambiguous formats requiring clarification: {ambiguous}"
        if unfixable:
            explanation += f" Unfixable fields: {unfixable}"
        
        return RemediationResult(
            success=False,
            strategy_used=self.strategy_id,
            original_error=context.get("error_message", "Format errors"),
            explanation=explanation,
            confidence=0.0,
            execution_time_ms=(time.time() - start_time) * 1000
        )
    
    def _is_date_field(self, field_name: str) -> bool:
        """Check if field name suggests a date."""
        name_lower = field_name.lower()
        return (
            name_lower in self.DATE_FIELDS or
            "date" in name_lower or
            "time" in name_lower or
            name_lower.endswith("_at")
        )
    
    def _is_uppercase_field(self, field_name: str) -> bool:
        """Check if field should be uppercase."""
        name_lower = field_name.lower()
        return (
            name_lower in self.UPPERCASE_FIELDS or
            "code" in name_lower or
            "type" in name_lower or
            "status" in name_lower
        )
    
    def _is_date_ambiguous(self, value: str) -> bool:
        """Check if date format is ambiguous (DD/MM vs MM/DD)."""
        value = value.strip()
        
        # Check for ambiguous patterns
        for pattern in self.AMBIGUOUS_DATE_PATTERNS:
            match = re.match(pattern, value)
            if match:
                # Extract day and month candidates
                groups = match.groups()
                if len(groups) >= 2:
                    a, b = int(groups[0]), int(groups[1])
                    # Ambiguous if both could be month (1-12)
                    if a <= 12 and b <= 12:
                        return True
        
        return False
    
    def _fix_date(self, field_path: str, value: Any) -> Optional[FormatFix]:
        """Attempt to fix date format to ISO-8601."""
        if value is None:
            return None
        
        original = str(value).strip()
        if not original:
            return None
        
        # Already ISO format?
        if re.match(r"^\d{4}-\d{2}-\d{2}$", original):
            return None  # Already correct
        
        # Check if ambiguous first
        if self._is_date_ambiguous(original):
            return None  # Don't guess
        
        # Try to parse unambiguous formats
        parsed_date = None
        
        # Year-first formats (always unambiguous)
        year_first_patterns = [
            (r"^(\d{4})/(\d{2})/(\d{2})$", "%Y/%m/%d"),
            (r"^(\d{4})\.(\d{2})\.(\d{2})$", "%Y.%m.%d"),
        ]
        
        for pattern, fmt in year_first_patterns:
            if re.match(pattern, original):
                try:
                    parsed_date = datetime.strptime(original, fmt)
                    break
                except ValueError:
                    continue
        
        # Day > 12 patterns (unambiguous)
        if not parsed_date:
            match = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$", original)
            if match:
                a, b, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                # If first number > 12, it must be day (European format)
                if a > 12 and b <= 12:
                    try:
                        parsed_date = datetime(year, b, a)
                    except ValueError:
                        pass
                # If second number > 12, it must be day (US format)
                elif b > 12 and a <= 12:
                    try:
                        parsed_date = datetime(year, a, b)
                    except ValueError:
                        pass
        
        # Try dateutil for written months (always unambiguous)
        if not parsed_date:
            try:
                from dateutil import parser as dateutil_parser
                # Only parse if it contains month names
                if re.search(r'[A-Za-z]{3,}', original):
                    parsed_date = dateutil_parser.parse(original, dayfirst=False)
            except (ImportError, ValueError):
                pass
        
        if parsed_date:
            iso_date = parsed_date.strftime("%Y-%m-%d")
            return FormatFix(
                field_path=field_path,
                original_value=original,
                corrected_value=iso_date,
                fix_type="date_iso",
                confidence=0.95
            )
        
        return None
    
    def _fix_uppercase(self, field_path: str, value: Any) -> Optional[FormatFix]:
        """Fix enum/code fields to uppercase."""
        if value is None:
            return None
        
        original = str(value).strip()
        if not original:
            return None
        
        corrected = original.upper().strip()
        
        # Also remove any extra whitespace
        corrected = " ".join(corrected.split())
        
        if corrected != original:
            return FormatFix(
                field_path=field_path,
                original_value=original,
                corrected_value=corrected,
                fix_type="uppercase",
                confidence=0.95
            )
        
        return None
    
    def _fix_string(self, field_path: str, value: Any) -> Optional[FormatFix]:
        """Fix string issues (trim whitespace, control chars)."""
        if value is None:
            return None
        
        original = str(value)
        
        # Strip whitespace and control characters
        corrected = original.strip()
        # Remove control characters (except newlines in multi-line fields)
        corrected = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', corrected)
        # Normalize internal whitespace
        corrected = " ".join(corrected.split())
        
        if corrected != original:
            return FormatFix(
                field_path=field_path,
                original_value=original,
                corrected_value=corrected,
                fix_type="trim_whitespace",
                confidence=0.98
            )
        
        return None
    
    def _scan_for_format_issues(self, data: Dict[str, Any], prefix: str = "") -> List[FormatFix]:
        """Scan data structure for common format issues."""
        fixes = []
        
        for key, value in data.items():
            field_path = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                fixes.extend(self._scan_for_format_issues(value, field_path))
            elif isinstance(value, str):
                # Check for leading/trailing whitespace
                if value != value.strip():
                    fix = self._fix_string(field_path, value)
                    if fix:
                        fixes.append(fix)
                
                # Check uppercase fields
                if self._is_uppercase_field(key):
                    fix = self._fix_uppercase(field_path, value)
                    if fix:
                        fixes.append(fix)
        
        return fixes
    
    def _get_nested_value(self, data: Dict[str, Any], path: List) -> Any:
        """Get value from nested dict using path."""
        current = data
        for key in path:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return None
        return current
    
    def _apply_fixes(self, original_data: Dict[str, Any], fixes: List[FormatFix]) -> Dict[str, Any]:
        """Apply format fixes to create corrected data."""
        import copy
        corrected = copy.deepcopy(original_data)
        
        for fix in fixes:
            parts = fix.field_path.split(".")
            target = corrected
            
            # Navigate to parent
            for part in parts[:-1]:
                if part not in target:
                    target[part] = {}
                target = target[part]
            
            # Apply fix
            if parts[-1] in target or fix.original_value is not None:
                target[parts[-1]] = fix.corrected_value
        
        return corrected


# =============================================================================
# STRATEGY DEPLOYMENT COMPLETE
# =============================================================================
#
# FormatCorrectionStrategy is now available:
#
#     from modules.immune.strategies import FormatCorrectionStrategy
#     engine.register_strategy(FormatCorrectionStrategy())
#
# Capabilities:
#   - Date normalization: "2023/12/25" → "2023-12-25"
#   - Whitespace trim: "  USD  " → "USD"
#   - Case normalization: "usd" → "USD"
#   - Ambiguity detection: "01/02/2023" → REQUEST_CLARIFICATION
#
# Attestation: MASTER-BER-P162-STRATEGY
# Ledger: ATTEST: FORMAT_CORRECTION_ACTIVE
# =============================================================================
