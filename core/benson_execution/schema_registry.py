# ═══════════════════════════════════════════════════════════════════════════════
# BensonExecution — Schema Registry
# PAC-BENSON-EXEC-C01: BENSON EXECUTION GENESIS & IDENTITY INSTANTIATION
# Agent: Benson Execution (GID-00-EXEC) — Deterministic Execution Engine
# ═══════════════════════════════════════════════════════════════════════════════

"""
Benson Execution Schema Registry — Immutable Schema Enforcement

PURPOSE:
    Bind schema validation at execution ingress.
    All PACs must validate against the canonical schema before admission.

SCHEMA INVARIANTS:
    INV-BENSON-SCHEMA-001: Schema version is immutable
    INV-BENSON-SCHEMA-002: No PAC admitted without schema validation
    INV-BENSON-SCHEMA-003: Schema validation is deterministic
    INV-BENSON-SCHEMA-004: Schema cannot be modified at runtime

SUPPORTED SCHEMAS:
    - CHAINBRIDGE_PAC_SCHEMA_v1.0.0

ENFORCEMENT:
    - Invalid schema version → REJECT
    - Schema validation failure → REJECT
    - Missing schema reference → REJECT
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA VERSION CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

BENSON_SCHEMA_REGISTRY_VERSION = "1.0.0"
CURRENT_PAC_SCHEMA_VERSION = "1.0.0"
CURRENT_PAC_SCHEMA_ID = f"CHAINBRIDGE_PAC_SCHEMA_v{CURRENT_PAC_SCHEMA_VERSION}"


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA VALIDATION STATUS
# ═══════════════════════════════════════════════════════════════════════════════

class SchemaValidationStatus(Enum):
    """Schema validation result status."""
    
    VALID = "VALID"
    INVALID = "INVALID"
    UNKNOWN_SCHEMA = "UNKNOWN_SCHEMA"
    MISSING_SCHEMA_REF = "MISSING_SCHEMA_REF"


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA VALIDATION ERROR
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SchemaValidationError:
    """
    Immutable record of a schema validation error.
    
    Attributes:
        field_path: JSON path to the invalid field
        message: Human-readable error message
        expected_type: Expected type or value
        actual_type: Actual type or value found
    """
    
    field_path: str
    message: str
    expected_type: Optional[str] = None
    actual_type: Optional[str] = None
    
    def __str__(self) -> str:
        parts = [f"[{self.field_path}] {self.message}"]
        if self.expected_type:
            parts.append(f"expected={self.expected_type}")
        if self.actual_type:
            parts.append(f"actual={self.actual_type}")
        return " ".join(parts)


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA VALIDATION RESULT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SchemaValidationResult:
    """
    Immutable result of schema validation.
    
    Attributes:
        status: Validation status enum
        schema_id: The schema ID used for validation
        pac_id: The PAC ID that was validated
        errors: Tuple of validation errors (empty if valid)
        schema_hash: Hash of the schema used
        validation_timestamp: When validation occurred
    """
    
    status: SchemaValidationStatus
    schema_id: str
    pac_id: str
    errors: Tuple[SchemaValidationError, ...] = field(default_factory=tuple)
    schema_hash: Optional[str] = None
    validation_timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    
    @property
    def is_valid(self) -> bool:
        return self.status == SchemaValidationStatus.VALID
    
    @property
    def is_rejected(self) -> bool:
        return self.status != SchemaValidationStatus.VALID
    
    @property
    def error_count(self) -> int:
        return len(self.errors)


# ═══════════════════════════════════════════════════════════════════════════════
# PAC SCHEMA DEFINITION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PACSchemaField:
    """Definition of a single field in the PAC schema."""
    
    name: str
    field_type: str  # "string", "integer", "boolean", "object", "array"
    required: bool = True
    description: str = ""
    pattern: Optional[str] = None  # Regex pattern for strings
    enum_values: Optional[FrozenSet[str]] = None


@dataclass(frozen=True)
class PACSchemaBlock:
    """Definition of a block in the PAC schema."""
    
    block_number: int
    block_name: str
    required: bool = True
    fields: Tuple[PACSchemaField, ...] = field(default_factory=tuple)
    description: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL PAC SCHEMA V1.0.0
# ═══════════════════════════════════════════════════════════════════════════════

METADATA_FIELDS = (
    PACSchemaField(
        name="pac_id",
        field_type="string",
        required=True,
        pattern=r"^PAC-[A-Z][A-Z0-9]*(-[A-Z0-9]+)+$",
        description="Canonical PAC identifier",
    ),
    PACSchemaField(
        name="pac_version",
        field_type="string",
        required=True,
        pattern=r"^\d+\.\d+\.\d+$",
        description="Semantic version",
    ),
    PACSchemaField(
        name="classification",
        field_type="string",
        required=True,
        enum_values=frozenset(["CONSTITUTIONAL", "OPERATIONAL", "TACTICAL", "DIAGNOSTIC"]),
        description="PAC classification level",
    ),
    PACSchemaField(
        name="governance_tier",
        field_type="string",
        required=True,
        enum_values=frozenset(["LAW", "POLICY", "GUIDELINE"]),
        description="Governance enforcement tier",
    ),
    PACSchemaField(
        name="issuer_gid",
        field_type="string",
        required=True,
        pattern=r"^GID-\d{2}(-[A-Z]+)?$",
        description="Governance ID of issuer",
    ),
    PACSchemaField(
        name="issuer_role",
        field_type="string",
        required=True,
        description="Role of the issuer",
    ),
    PACSchemaField(
        name="issued_at",
        field_type="string",
        required=True,
        pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?$",
        description="ISO8601 timestamp",
    ),
    PACSchemaField(
        name="scope",
        field_type="string",
        required=True,
        description="Scope of the PAC",
    ),
    PACSchemaField(
        name="fail_closed",
        field_type="boolean",
        required=True,
        description="Whether to fail closed on error",
    ),
    PACSchemaField(
        name="schema_version",
        field_type="string",
        required=True,
        pattern=r"^CHAINBRIDGE_PAC_SCHEMA_v\d+\.\d+\.\d+$",
        description="Schema version reference",
    ),
)

FINAL_STATE_FIELDS = (
    PACSchemaField(
        name="execution_blocking",
        field_type="boolean",
        required=True,
        description="Whether this PAC blocks execution",
    ),
    PACSchemaField(
        name="promotion_eligible",
        field_type="boolean",
        required=True,
        description="Whether this PAC is eligible for promotion",
    ),
)

LEDGER_COMMIT_FIELDS = (
    PACSchemaField(
        name="ordering_attested",
        field_type="boolean",
        required=True,
        description="Ordering has been attested",
    ),
    PACSchemaField(
        name="immutability_attested",
        field_type="boolean",
        required=True,
        description="Immutability has been attested",
    ),
)

# Canonical schema blocks
CANONICAL_PAC_BLOCKS: Tuple[PACSchemaBlock, ...] = (
    PACSchemaBlock(0, "METADATA", True, METADATA_FIELDS, "PAC metadata and identity"),
    PACSchemaBlock(1, "PAC_ADMISSION_CHECK", True, (), "Admission decision"),
    PACSchemaBlock(2, "RUNTIME_ACTIVATION_ACK", True, (), "Runtime activation acknowledgement"),
    PACSchemaBlock(3, "GOVERNANCE_MODE_DECLARATION", True, (), "Governance mode"),
    PACSchemaBlock(4, "AGENT_ACTIVATION_ACK", True, (), "Agent identity lock"),
    PACSchemaBlock(5, "EXECUTION_LANE", True, (), "Execution lane assignment"),
    PACSchemaBlock(6, "CONTEXT", True, (), "Contextual information"),
    PACSchemaBlock(7, "GOAL_STATE", True, (), "Target goal state"),
    PACSchemaBlock(8, "CONSTRAINTS_AND_GUARDRAILS", True, (), "Operational constraints"),
    PACSchemaBlock(9, "INVARIANTS_ENFORCED", True, (), "Enforced invariants"),
    PACSchemaBlock(10, "TASKS_AND_PLAN", True, (), "Execution tasks"),
    PACSchemaBlock(11, "FILE_AND_CODE_TARGETS", True, (), "Target files and code"),
    PACSchemaBlock(12, "INTERFACES_AND_CONTRACTS", True, (), "API contracts"),
    PACSchemaBlock(13, "SECURITY_AND_THREAT_MODEL", True, (), "Security considerations"),
    PACSchemaBlock(14, "TESTING_AND_VERIFICATION", True, (), "Testing requirements"),
    PACSchemaBlock(15, "QA_AND_ACCEPTANCE_CRITERIA", True, (), "Acceptance criteria"),
    PACSchemaBlock(16, "WRAP_REQUIREMENT", True, (), "WRAP obligation"),
    PACSchemaBlock(17, "FAILURE_AND_ROLLBACK", True, (), "Failure handling"),
    PACSchemaBlock(18, "FINAL_STATE_DECLARATION", True, FINAL_STATE_FIELDS, "Final state"),
    PACSchemaBlock(19, "LEDGER_COMMIT_AND_ATTESTATION", True, LEDGER_COMMIT_FIELDS, "Ledger commit"),
)


# ═══════════════════════════════════════════════════════════════════════════════
# BENSON SCHEMA REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class BensonSchemaRegistry:
    """
    Immutable schema registry for PAC validation at execution boundary.
    
    This registry is locked at initialization and cannot be modified.
    All schema validation is deterministic with no interpretation.
    
    INVARIANTS:
        - Schema definitions are immutable after initialization
        - No runtime schema modification allowed
        - Validation is pure function (same input → same output)
    """
    
    VERSION = BENSON_SCHEMA_REGISTRY_VERSION
    
    def __init__(self) -> None:
        """Initialize the schema registry (locked after init)."""
        self._schemas: Dict[str, Tuple[PACSchemaBlock, ...]] = {
            CURRENT_PAC_SCHEMA_ID: CANONICAL_PAC_BLOCKS,
        }
        self._schema_hashes: Dict[str, str] = {}
        self._locked = False
        
        # Compute schema hashes
        for schema_id, blocks in self._schemas.items():
            self._schema_hashes[schema_id] = self._compute_schema_hash(blocks)
        
        # Lock the registry
        self._locked = True
    
    def _compute_schema_hash(self, blocks: Tuple[PACSchemaBlock, ...]) -> str:
        """Compute deterministic hash of schema definition."""
        schema_repr = []
        for block in blocks:
            block_repr = f"{block.block_number}:{block.block_name}:{block.required}"
            for fld in block.fields:
                field_repr = f"{fld.name}:{fld.field_type}:{fld.required}"
                if fld.pattern:
                    field_repr += f":{fld.pattern}"
                if fld.enum_values:
                    field_repr += f":{sorted(fld.enum_values)}"
                block_repr += f"|{field_repr}"
            schema_repr.append(block_repr)
        
        combined = "||".join(schema_repr)
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    @property
    def supported_schemas(self) -> FrozenSet[str]:
        """Get set of supported schema IDs."""
        return frozenset(self._schemas.keys())
    
    def is_supported(self, schema_id: str) -> bool:
        """Check if a schema ID is supported."""
        return schema_id in self._schemas
    
    def get_schema_hash(self, schema_id: str) -> Optional[str]:
        """Get the hash of a schema (for audit)."""
        return self._schema_hashes.get(schema_id)
    
    def validate(self, pac: Dict[str, Any]) -> SchemaValidationResult:
        """
        Validate a PAC document against its declared schema.
        
        Args:
            pac: The PAC document as a dictionary
            
        Returns:
            SchemaValidationResult with validation status and errors
        """
        errors: List[SchemaValidationError] = []
        
        # Extract PAC ID for result
        pac_id = pac.get("metadata", {}).get("pac_id", "UNKNOWN")
        
        # Check for schema reference
        schema_ref = pac.get("metadata", {}).get("schema_version")
        if not schema_ref:
            return SchemaValidationResult(
                status=SchemaValidationStatus.MISSING_SCHEMA_REF,
                schema_id="",
                pac_id=pac_id,
                errors=(SchemaValidationError(
                    field_path="metadata.schema_version",
                    message="Schema version reference is required",
                ),),
            )
        
        # Check if schema is supported
        if schema_ref not in self._schemas:
            return SchemaValidationResult(
                status=SchemaValidationStatus.UNKNOWN_SCHEMA,
                schema_id=schema_ref,
                pac_id=pac_id,
                errors=(SchemaValidationError(
                    field_path="metadata.schema_version",
                    message=f"Unknown schema version: {schema_ref}",
                    expected_type=str(self.supported_schemas),
                    actual_type=schema_ref,
                ),),
            )
        
        # Get schema definition
        schema_blocks = self._schemas[schema_ref]
        schema_hash = self._schema_hashes[schema_ref]
        
        # Validate metadata (BLOCK 0)
        metadata = pac.get("metadata")
        if metadata is None:
            errors.append(SchemaValidationError(
                field_path="metadata",
                message="METADATA block is required",
            ))
        elif isinstance(metadata, dict):
            errors.extend(self._validate_block_fields(
                metadata, schema_blocks[0].fields, "metadata"
            ))
        
        # Validate blocks
        blocks = pac.get("blocks", {})
        if not isinstance(blocks, dict):
            errors.append(SchemaValidationError(
                field_path="blocks",
                message="'blocks' must be a dictionary",
                expected_type="dict",
                actual_type=type(blocks).__name__,
            ))
        else:
            errors.extend(self._validate_blocks(blocks, schema_blocks))
        
        # Determine status
        status = SchemaValidationStatus.VALID if not errors else SchemaValidationStatus.INVALID
        
        return SchemaValidationResult(
            status=status,
            schema_id=schema_ref,
            pac_id=pac_id,
            errors=tuple(errors),
            schema_hash=schema_hash,
        )
    
    def _validate_block_fields(
        self,
        data: Dict[str, Any],
        fields: Tuple[PACSchemaField, ...],
        path_prefix: str,
    ) -> List[SchemaValidationError]:
        """Validate fields within a block."""
        import re
        errors = []
        
        for fld in fields:
            field_path = f"{path_prefix}.{fld.name}"
            value = data.get(fld.name)
            
            # Check required
            if fld.required and value is None:
                errors.append(SchemaValidationError(
                    field_path=field_path,
                    message=f"Required field '{fld.name}' is missing",
                ))
                continue
            
            if value is None:
                continue  # Optional field not present
            
            # Type validation
            if fld.field_type == "string" and not isinstance(value, str):
                errors.append(SchemaValidationError(
                    field_path=field_path,
                    message=f"Field '{fld.name}' must be a string",
                    expected_type="string",
                    actual_type=type(value).__name__,
                ))
                continue
            
            if fld.field_type == "boolean" and not isinstance(value, bool):
                errors.append(SchemaValidationError(
                    field_path=field_path,
                    message=f"Field '{fld.name}' must be a boolean",
                    expected_type="boolean",
                    actual_type=type(value).__name__,
                ))
                continue
            
            if fld.field_type == "integer" and not isinstance(value, int):
                errors.append(SchemaValidationError(
                    field_path=field_path,
                    message=f"Field '{fld.name}' must be an integer",
                    expected_type="integer",
                    actual_type=type(value).__name__,
                ))
                continue
            
            # Pattern validation
            if fld.pattern and isinstance(value, str):
                if not re.match(fld.pattern, value):
                    errors.append(SchemaValidationError(
                        field_path=field_path,
                        message=f"Field '{fld.name}' does not match pattern",
                        expected_type=fld.pattern,
                        actual_type=value,
                    ))
            
            # Enum validation
            if fld.enum_values and value not in fld.enum_values:
                errors.append(SchemaValidationError(
                    field_path=field_path,
                    message=f"Field '{fld.name}' must be one of allowed values",
                    expected_type=str(fld.enum_values),
                    actual_type=str(value),
                ))
        
        return errors
    
    def _validate_blocks(
        self,
        blocks: Dict[str, Any],
        schema_blocks: Tuple[PACSchemaBlock, ...],
    ) -> List[SchemaValidationError]:
        """Validate all PAC blocks against schema."""
        errors = []
        
        for schema_block in schema_blocks:
            block_key = str(schema_block.block_number)
            block_data = blocks.get(block_key) or blocks.get(schema_block.block_number)
            
            if schema_block.required and block_data is None:
                errors.append(SchemaValidationError(
                    field_path=f"blocks.{block_key}",
                    message=f"Required block {schema_block.block_number} ({schema_block.block_name}) is missing",
                ))
                continue
            
            if block_data is None:
                continue  # Optional block not present
            
            # Validate block fields if defined
            if schema_block.fields and isinstance(block_data, dict):
                errors.extend(self._validate_block_fields(
                    block_data, schema_block.fields, f"blocks.{block_key}"
                ))
        
        return errors


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

_SCHEMA_REGISTRY_INSTANCE: Optional[BensonSchemaRegistry] = None


def get_benson_schema_registry() -> BensonSchemaRegistry:
    """Get the singleton BensonSchemaRegistry instance."""
    global _SCHEMA_REGISTRY_INSTANCE
    if _SCHEMA_REGISTRY_INSTANCE is None:
        _SCHEMA_REGISTRY_INSTANCE = BensonSchemaRegistry()
    return _SCHEMA_REGISTRY_INSTANCE
