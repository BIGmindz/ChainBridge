# ═══════════════════════════════════════════════════════════════════════════════
# PAC/WRAP/BER Schema Hardening — Canonical Schema Definitions
# PAC-BENSON-P24: CONTROL PLANE CORE HARDENING
# Agent: ALEX (GID-08) — Canonical Law & Invariants
# ═══════════════════════════════════════════════════════════════════════════════

"""
Canonical Schema Registry — Enterprise-Grade Schema Enforcement

PURPOSE:
    Define and enforce canonical schemas for PAC, WRAP, and BER artifacts.
    All control plane documents must validate against these schemas.

SCHEMA VERSIONS:
    - CHAINBRIDGE_CANONICAL_PAC_SCHEMA@v1.0.0
    - CHAINBRIDGE_CANONICAL_WRAP_SCHEMA@v1.0.0
    - CHAINBRIDGE_CANONICAL_BER_SCHEMA@v1.0.0

INVARIANTS:
    INV-SCHEMA-001: All PACs must validate against PAC schema
    INV-SCHEMA-002: All WRAPs must validate against WRAP schema
    INV-SCHEMA-003: All BERs must validate against BER schema
    INV-SCHEMA-004: Schema versions are immutable once published
    INV-SCHEMA-005: No schema field may be removed (only added)
    INV-SCHEMA-006: Required fields cannot become optional

EXECUTION MODE: PARALLEL
LANE: GOVERNANCE (GID-08)
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA VERSION CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

SCHEMA_REGISTRY_VERSION = "1.0.0"

PAC_SCHEMA_VERSION = "1.0.0"
PAC_SCHEMA_ID = f"CHAINBRIDGE_CANONICAL_PAC_SCHEMA@v{PAC_SCHEMA_VERSION}"

WRAP_SCHEMA_VERSION = "1.0.0"
WRAP_SCHEMA_ID = f"CHAINBRIDGE_CANONICAL_WRAP_SCHEMA@v{WRAP_SCHEMA_VERSION}"

BER_SCHEMA_VERSION = "1.0.0"
BER_SCHEMA_ID = f"CHAINBRIDGE_CANONICAL_BER_SCHEMA@v{BER_SCHEMA_VERSION}"


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class SchemaError(Exception):
    """Base exception for schema errors."""
    pass


class SchemaValidationError(SchemaError):
    """Raised when document fails schema validation."""
    
    def __init__(self, document_type: str, document_id: str, errors: List[str]):
        self.document_type = document_type
        self.document_id = document_id
        self.errors = errors
        error_list = "; ".join(errors[:5])  # Limit to first 5 errors
        if len(errors) > 5:
            error_list += f" (+{len(errors) - 5} more)"
        super().__init__(
            f"SCHEMA_VALIDATION_FAILED: {document_type} '{document_id}' "
            f"failed validation: {error_list}"
        )


class SchemaMutationError(SchemaError):
    """Raised when attempting to mutate immutable schema."""
    
    def __init__(self, schema_id: str, mutation_type: str):
        self.schema_id = schema_id
        self.mutation_type = mutation_type
        super().__init__(
            f"SCHEMA_MUTATION_FORBIDDEN: Cannot {mutation_type} on "
            f"schema '{schema_id}'. Schemas are immutable (INV-SCHEMA-004)."
        )


class SchemaBreakingChangeError(SchemaError):
    """Raised when schema change would break compatibility."""
    
    def __init__(self, schema_id: str, breaking_change: str):
        self.schema_id = schema_id
        self.breaking_change = breaking_change
        super().__init__(
            f"SCHEMA_BREAKING_CHANGE: '{breaking_change}' on schema '{schema_id}' "
            f"is forbidden (INV-SCHEMA-005, INV-SCHEMA-006)."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# FIELD DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

class FieldType(str, Enum):
    """Supported field types."""
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    ENUM = "enum"
    TIMESTAMP = "timestamp"
    HASH = "hash"
    GID = "gid"


@dataclass(frozen=True)
class SchemaField:
    """
    Definition of a schema field.
    
    frozen=True ensures field definitions are immutable.
    """
    name: str
    field_type: FieldType
    required: bool
    description: str
    enum_values: Optional[FrozenSet[str]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    
    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate a value against this field definition."""
        # Check required
        if value is None:
            if self.required:
                return False, f"Required field '{self.name}' is missing"
            return True, None
        
        # Type validation
        if self.field_type == FieldType.STRING:
            if not isinstance(value, str):
                return False, f"Field '{self.name}' must be string, got {type(value).__name__}"
            if self.min_length and len(value) < self.min_length:
                return False, f"Field '{self.name}' must be at least {self.min_length} chars"
            if self.max_length and len(value) > self.max_length:
                return False, f"Field '{self.name}' must be at most {self.max_length} chars"
            if self.pattern and not re.match(self.pattern, value):
                return False, f"Field '{self.name}' must match pattern '{self.pattern}'"
        
        elif self.field_type == FieldType.INTEGER:
            if not isinstance(value, int):
                return False, f"Field '{self.name}' must be integer"
        
        elif self.field_type == FieldType.BOOLEAN:
            if not isinstance(value, bool):
                return False, f"Field '{self.name}' must be boolean"
        
        elif self.field_type == FieldType.ARRAY:
            if not isinstance(value, list):
                return False, f"Field '{self.name}' must be array"
        
        elif self.field_type == FieldType.OBJECT:
            if not isinstance(value, dict):
                return False, f"Field '{self.name}' must be object"
        
        elif self.field_type == FieldType.ENUM:
            if self.enum_values and value not in self.enum_values:
                return False, f"Field '{self.name}' must be one of {self.enum_values}"
        
        elif self.field_type == FieldType.TIMESTAMP:
            if not isinstance(value, str):
                return False, f"Field '{self.name}' must be ISO timestamp string"
            # Basic ISO timestamp validation
            if not re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", value):
                return False, f"Field '{self.name}' must be ISO timestamp format"
        
        elif self.field_type == FieldType.HASH:
            if not isinstance(value, str):
                return False, f"Field '{self.name}' must be hash string"
            if not re.match(r"^[a-f0-9]{64}$", value):
                return False, f"Field '{self.name}' must be 64-char hex hash"
        
        elif self.field_type == FieldType.GID:
            if not isinstance(value, str):
                return False, f"Field '{self.name}' must be GID string"
            if not re.match(r"^GID-\d{2}$", value):
                return False, f"Field '{self.name}' must be GID format (GID-XX)"
        
        return True, None


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CanonicalSchema:
    """
    Canonical schema definition.
    
    INV-SCHEMA-004: Schema versions are immutable once published
    """
    schema_id: str
    version: str
    description: str
    fields: Tuple[SchemaField, ...]
    invariants: Tuple[str, ...]
    
    @property
    def required_fields(self) -> FrozenSet[str]:
        """Get set of required field names."""
        return frozenset(f.name for f in self.fields if f.required)
    
    @property
    def all_fields(self) -> FrozenSet[str]:
        """Get set of all field names."""
        return frozenset(f.name for f in self.fields)
    
    def validate(self, document: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate document against this schema.
        
        Returns (is_valid, list_of_errors).
        """
        errors: List[str] = []
        
        # Check for unknown fields
        doc_fields = set(document.keys())
        unknown = doc_fields - self.all_fields
        for field_name in unknown:
            errors.append(f"Unknown field: '{field_name}'")
        
        # Validate each field
        for field_def in self.fields:
            value = document.get(field_def.name)
            is_valid, error = field_def.validate(value)
            if not is_valid and error:
                errors.append(error)
        
        return len(errors) == 0, errors
    
    def compute_schema_hash(self) -> str:
        """Compute deterministic hash of schema definition."""
        schema_data = {
            "schema_id": self.schema_id,
            "version": self.version,
            "fields": [
                {
                    "name": f.name,
                    "type": f.field_type.value,
                    "required": f.required,
                }
                for f in self.fields
            ],
        }
        return hashlib.sha256(
            json.dumps(schema_data, sort_keys=True).encode()
        ).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# PAC SCHEMA DEFINITION
# ═══════════════════════════════════════════════════════════════════════════════

PAC_SCHEMA = CanonicalSchema(
    schema_id=PAC_SCHEMA_ID,
    version=PAC_SCHEMA_VERSION,
    description="Canonical schema for Production Acceptance Certificate (PAC)",
    fields=(
        SchemaField("pac_id", FieldType.STRING, True, "Unique PAC identifier", pattern=r"^PAC-[A-Z]+-P?\d+(-[A-Z]+)?$"),
        SchemaField("issuer", FieldType.STRING, True, "PAC issuer name"),
        SchemaField("authority", FieldType.ENUM, True, "Issuer authority level", enum_values=frozenset({"FINAL", "PROVISIONAL", "DELEGATED"})),
        SchemaField("scope", FieldType.STRING, True, "Execution scope description"),
        SchemaField("execution_mode", FieldType.ENUM, True, "Execution mode", enum_values=frozenset({"PARALLEL", "SEQUENTIAL"})),
        SchemaField("governance_mode", FieldType.ENUM, True, "Governance mode", enum_values=frozenset({"FAIL_CLOSED", "FAIL_OPEN", "ADVISORY"})),
        SchemaField("drift_tolerance", FieldType.ENUM, True, "Drift tolerance", enum_values=frozenset({"ZERO", "LOW", "MEDIUM"})),
        SchemaField("fail_mode", FieldType.ENUM, True, "Failure mode", enum_values=frozenset({"HARD_FAIL", "SOFT_FAIL", "WARN"})),
        SchemaField("activated_agents", FieldType.ARRAY, True, "List of activated agent GIDs"),
        SchemaField("authorized_domains", FieldType.ARRAY, True, "Authorized execution domains"),
        SchemaField("non_goals", FieldType.ARRAY, False, "Explicit non-goals"),
        SchemaField("supersedes", FieldType.STRING, False, "PAC ID this supersedes"),
        SchemaField("created_at", FieldType.TIMESTAMP, True, "Creation timestamp"),
        SchemaField("pac_hash", FieldType.HASH, True, "PAC content hash"),
    ),
    invariants=(
        "INV-PAC-001: pac_id must be unique",
        "INV-PAC-002: issuer must be authorized",
        "INV-PAC-003: activated_agents must be valid GIDs",
        "INV-PAC-004: pac_hash must match content",
    ),
)


# ═══════════════════════════════════════════════════════════════════════════════
# WRAP SCHEMA DEFINITION
# ═══════════════════════════════════════════════════════════════════════════════

WRAP_SCHEMA = CanonicalSchema(
    schema_id=WRAP_SCHEMA_ID,
    version=WRAP_SCHEMA_VERSION,
    description="Canonical schema for Work Result Acknowledgment Package (WRAP)",
    fields=(
        SchemaField("wrap_id", FieldType.STRING, True, "Unique WRAP identifier"),
        SchemaField("pac_id", FieldType.STRING, True, "Reference to parent PAC"),
        SchemaField("agent_gid", FieldType.GID, True, "Submitting agent GID"),
        SchemaField("execution_summary", FieldType.STRING, True, "Summary of work performed"),
        SchemaField("artifacts", FieldType.ARRAY, True, "List of produced artifacts"),
        SchemaField("test_results", FieldType.OBJECT, False, "Test execution results"),
        SchemaField("coverage", FieldType.OBJECT, False, "Coverage metrics"),
        SchemaField("evidence_hashes", FieldType.ARRAY, True, "Hashes of evidence artifacts"),
        SchemaField("training_signals", FieldType.ARRAY, True, "Training signals emitted"),
        SchemaField("positive_closure", FieldType.OBJECT, True, "Positive closure attestation"),
        SchemaField("submitted_at", FieldType.TIMESTAMP, True, "Submission timestamp"),
        SchemaField("wrap_hash", FieldType.HASH, True, "WRAP content hash"),
    ),
    invariants=(
        "INV-WRAP-001: wrap_id must be unique",
        "INV-WRAP-002: pac_id must reference valid PAC",
        "INV-WRAP-003: agent_gid must be in PAC activated_agents",
        "INV-WRAP-004: evidence_hashes must be verifiable",
        "INV-WRAP-005: positive_closure is MANDATORY",
    ),
)


# ═══════════════════════════════════════════════════════════════════════════════
# BER SCHEMA DEFINITION
# ═══════════════════════════════════════════════════════════════════════════════

BER_SCHEMA = CanonicalSchema(
    schema_id=BER_SCHEMA_ID,
    version=BER_SCHEMA_VERSION,
    description="Canonical schema for BENSON Execution Report (BER)",
    fields=(
        SchemaField("ber_id", FieldType.STRING, True, "Unique BER identifier"),
        SchemaField("pac_id", FieldType.STRING, True, "Reference to parent PAC"),
        SchemaField("wrap_ids", FieldType.ARRAY, True, "List of included WRAP IDs"),
        SchemaField("issuer", FieldType.GID, True, "BER issuer (must be GID-00)"),
        SchemaField("ber_classification", FieldType.ENUM, True, "BER finality", enum_values=frozenset({"PROVISIONAL", "BINDING", "FINAL"})),
        SchemaField("execution_binding", FieldType.BOOLEAN, True, "Whether execution is binding"),
        SchemaField("settlement_effect", FieldType.ENUM, True, "Settlement effect", enum_values=frozenset({"NONE", "BINDING"})),
        SchemaField("review_gate_status", FieldType.ENUM, True, "RG-01 status", enum_values=frozenset({"PASS", "FAIL", "PENDING"})),
        SchemaField("self_review_gate_status", FieldType.ENUM, True, "BSRG-01 status", enum_values=frozenset({"PASS", "FAIL", "PENDING"})),
        SchemaField("invariant_violations", FieldType.ARRAY, True, "List of invariant violations (must be empty for PASS)"),
        SchemaField("training_signals", FieldType.ARRAY, True, "Aggregated training signals"),
        SchemaField("positive_closures", FieldType.ARRAY, True, "Aggregated positive closures"),
        SchemaField("ledger_commit_hash", FieldType.HASH, False, "Ledger commit hash (required for BINDING)"),
        SchemaField("pre_execution_hash", FieldType.HASH, True, "Pre-execution state hash"),
        SchemaField("post_execution_hash", FieldType.HASH, True, "Post-execution state hash"),
        SchemaField("issued_at", FieldType.TIMESTAMP, True, "Issuance timestamp"),
        SchemaField("ber_hash", FieldType.HASH, True, "BER content hash"),
    ),
    invariants=(
        "INV-BER-001: ber_id must be unique",
        "INV-BER-002: issuer must be GID-00",
        "INV-BER-003: wrap_ids must reference valid WRAPs",
        "INV-BER-004: BINDING requires ledger_commit_hash",
        "INV-BER-005: invariant_violations must be empty for PASS",
        "INV-BER-006: execution_binding must be explicit",
        "INV-BER-007: training_signals MANDATORY",
        "INV-BER-008: positive_closures MANDATORY",
    ),
)


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class SchemaRegistry:
    """
    Central registry for canonical schemas.
    
    INV-SCHEMA-004: Schema versions are immutable once published
    """
    
    _instance: Optional["SchemaRegistry"] = None
    
    def __new__(cls) -> "SchemaRegistry":
        """Singleton pattern for registry."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._schemas: Dict[str, CanonicalSchema] = {}
            cls._instance._initialized = False
        return cls._instance
    
    def initialize(self) -> None:
        """Initialize with canonical schemas."""
        if self._initialized:
            return
        
        self.register(PAC_SCHEMA)
        self.register(WRAP_SCHEMA)
        self.register(BER_SCHEMA)
        
        self._initialized = True
    
    def register(self, schema: CanonicalSchema) -> None:
        """
        Register a schema. Cannot overwrite existing schemas.
        
        INV-SCHEMA-004: Schema versions are immutable once published
        """
        if schema.schema_id in self._schemas:
            raise SchemaMutationError(schema.schema_id, "register (duplicate)")
        
        self._schemas[schema.schema_id] = schema
    
    def get(self, schema_id: str) -> Optional[CanonicalSchema]:
        """Get schema by ID."""
        return self._schemas.get(schema_id)
    
    def validate_pac(self, document: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate document against PAC schema."""
        return PAC_SCHEMA.validate(document)
    
    def validate_wrap(self, document: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate document against WRAP schema."""
        return WRAP_SCHEMA.validate(document)
    
    def validate_ber(self, document: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate document against BER schema."""
        return BER_SCHEMA.validate(document)
    
    def validate_document(
        self, document_type: str, document: Dict[str, Any]
    ) -> None:
        """
        Validate document and raise on failure.
        
        Args:
            document_type: One of "PAC", "WRAP", "BER"
            document: Document to validate
            
        Raises:
            SchemaValidationError if validation fails
        """
        if document_type == "PAC":
            is_valid, errors = self.validate_pac(document)
            doc_id = document.get("pac_id", "UNKNOWN")
        elif document_type == "WRAP":
            is_valid, errors = self.validate_wrap(document)
            doc_id = document.get("wrap_id", "UNKNOWN")
        elif document_type == "BER":
            is_valid, errors = self.validate_ber(document)
            doc_id = document.get("ber_id", "UNKNOWN")
        else:
            raise ValueError(f"Unknown document type: {document_type}")
        
        if not is_valid:
            raise SchemaValidationError(document_type, doc_id, errors)
    
    def list_schemas(self) -> List[str]:
        """List all registered schema IDs."""
        return list(self._schemas.keys())


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA EVOLUTION GUARD
# ═══════════════════════════════════════════════════════════════════════════════

class SchemaEvolutionGuard:
    """
    Guards against breaking schema changes.
    
    INV-SCHEMA-005: No schema field may be removed (only added)
    INV-SCHEMA-006: Required fields cannot become optional
    """
    
    @staticmethod
    def check_evolution(
        old_schema: CanonicalSchema, new_schema: CanonicalSchema
    ) -> Tuple[bool, List[str]]:
        """
        Check if schema evolution is safe (non-breaking).
        
        Returns (is_safe, list_of_breaking_changes).
        """
        breaking_changes: List[str] = []
        
        # INV-SCHEMA-005: No field removal
        old_fields = old_schema.all_fields
        new_fields = new_schema.all_fields
        removed = old_fields - new_fields
        for field_name in removed:
            breaking_changes.append(f"Field removal: '{field_name}'")
        
        # INV-SCHEMA-006: Required fields cannot become optional
        old_required = old_schema.required_fields
        new_required = new_schema.required_fields
        became_optional = old_required - new_required
        for field_name in became_optional:
            if field_name in new_fields:  # Still exists, just optional now
                breaking_changes.append(
                    f"Required→Optional: '{field_name}'"
                )
        
        return len(breaking_changes) == 0, breaking_changes
    
    @staticmethod
    def enforce_evolution(
        old_schema: CanonicalSchema, new_schema: CanonicalSchema
    ) -> None:
        """Enforce safe schema evolution, raise on breaking changes."""
        is_safe, breaking_changes = SchemaEvolutionGuard.check_evolution(
            old_schema, new_schema
        )
        
        if not is_safe:
            raise SchemaBreakingChangeError(
                new_schema.schema_id,
                "; ".join(breaking_changes),
            )


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def get_schema_registry() -> SchemaRegistry:
    """Get initialized schema registry."""
    registry = SchemaRegistry()
    registry.initialize()
    return registry


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Version constants
    "SCHEMA_REGISTRY_VERSION",
    "PAC_SCHEMA_VERSION",
    "PAC_SCHEMA_ID",
    "WRAP_SCHEMA_VERSION",
    "WRAP_SCHEMA_ID",
    "BER_SCHEMA_VERSION",
    "BER_SCHEMA_ID",
    
    # Exceptions
    "SchemaError",
    "SchemaValidationError",
    "SchemaMutationError",
    "SchemaBreakingChangeError",
    
    # Field definitions
    "FieldType",
    "SchemaField",
    "CanonicalSchema",
    
    # Canonical schemas
    "PAC_SCHEMA",
    "WRAP_SCHEMA",
    "BER_SCHEMA",
    
    # Registry
    "SchemaRegistry",
    "get_schema_registry",
    
    # Evolution guard
    "SchemaEvolutionGuard",
]
