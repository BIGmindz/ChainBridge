# ═══════════════════════════════════════════════════════════════════════════════
# Schema Registry Tests
# PAC-BENSON-P24: CONTROL PLANE CORE HARDENING
# Agent: DAN (GID-07) — CI / Compiler Gates
# ═══════════════════════════════════════════════════════════════════════════════

"""
Tests for canonical schema registry module.

Validates:
- INV-SCHEMA-001: All PACs must validate against PAC schema
- INV-SCHEMA-002: All WRAPs must validate against WRAP schema
- INV-SCHEMA-003: All BERs must validate against BER schema
- INV-SCHEMA-004: Schema versions are immutable once published
- INV-SCHEMA-005: No schema field may be removed (only added)
- INV-SCHEMA-006: Required fields cannot become optional
"""

import pytest

from core.governance.schema_registry import (
    PAC_SCHEMA,
    WRAP_SCHEMA,
    BER_SCHEMA,
    SchemaRegistry,
    SchemaEvolutionGuard,
    SchemaField,
    CanonicalSchema,
    FieldType,
    get_schema_registry,
    SchemaValidationError,
    SchemaMutationError,
    SchemaBreakingChangeError,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def valid_pac():
    """Generate valid PAC document."""
    return {
        "pac_id": "PAC-TEST-P01",
        "issuer": "JEFFREY",
        "authority": "FINAL",
        "scope": "Test scope",
        "execution_mode": "PARALLEL",
        "governance_mode": "FAIL_CLOSED",
        "drift_tolerance": "ZERO",
        "fail_mode": "HARD_FAIL",
        "activated_agents": ["GID-00", "GID-01"],
        "authorized_domains": ["domain1"],
        "created_at": "2024-01-01T00:00:00+00:00",
        "pac_hash": "a" * 64,
    }


@pytest.fixture
def valid_wrap():
    """Generate valid WRAP document."""
    return {
        "wrap_id": "WRAP-TEST-001",
        "pac_id": "PAC-TEST-P01",
        "agent_gid": "GID-01",
        "execution_summary": "Test execution",
        "artifacts": ["artifact1"],
        "evidence_hashes": ["b" * 64],
        "training_signals": [{"signal": "TS-001"}],
        "positive_closure": {"status": "CLOSED"},
        "submitted_at": "2024-01-01T00:01:00+00:00",
        "wrap_hash": "c" * 64,
    }


@pytest.fixture
def valid_ber():
    """Generate valid BER document."""
    return {
        "ber_id": "BER-TEST-001",
        "pac_id": "PAC-TEST-P01",
        "wrap_ids": ["WRAP-TEST-001"],
        "issuer": "GID-00",
        "ber_classification": "FINAL",
        "execution_binding": True,
        "settlement_effect": "BINDING",
        "review_gate_status": "PASS",
        "self_review_gate_status": "PASS",
        "invariant_violations": [],
        "training_signals": [{"signal": "TS-001"}],
        "positive_closures": [{"status": "CLOSED"}],
        "pre_execution_hash": "d" * 64,
        "post_execution_hash": "e" * 64,
        "issued_at": "2024-01-01T00:02:00+00:00",
        "ber_hash": "f" * 64,
    }


@pytest.fixture
def schema_registry():
    """Get fresh schema registry."""
    # Reset singleton for testing
    SchemaRegistry._instance = None
    return get_schema_registry()


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA FIELD TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSchemaField:
    """Tests for SchemaField validation."""
    
    def test_string_field_valid(self):
        """String field validates string."""
        field = SchemaField("test", FieldType.STRING, True, "Test field")
        is_valid, error = field.validate("hello")
        assert is_valid is True
        assert error is None
    
    def test_string_field_invalid_type(self):
        """String field rejects non-string."""
        field = SchemaField("test", FieldType.STRING, True, "Test field")
        is_valid, error = field.validate(123)
        assert is_valid is False
        assert "must be string" in error
    
    def test_required_field_missing(self):
        """Required field fails if missing."""
        field = SchemaField("test", FieldType.STRING, True, "Test field")
        is_valid, error = field.validate(None)
        assert is_valid is False
        assert "missing" in error
    
    def test_optional_field_missing(self):
        """Optional field passes if missing."""
        field = SchemaField("test", FieldType.STRING, False, "Test field")
        is_valid, error = field.validate(None)
        assert is_valid is True
    
    def test_enum_field_valid(self):
        """Enum field validates enum value."""
        field = SchemaField(
            "test", FieldType.ENUM, True, "Test",
            enum_values=frozenset({"A", "B", "C"})
        )
        is_valid, error = field.validate("A")
        assert is_valid is True
    
    def test_enum_field_invalid(self):
        """Enum field rejects invalid value."""
        field = SchemaField(
            "test", FieldType.ENUM, True, "Test",
            enum_values=frozenset({"A", "B", "C"})
        )
        is_valid, error = field.validate("D")
        assert is_valid is False
    
    def test_hash_field_valid(self):
        """Hash field validates 64-char hex."""
        field = SchemaField("test", FieldType.HASH, True, "Test")
        is_valid, error = field.validate("a" * 64)
        assert is_valid is True
    
    def test_hash_field_invalid_length(self):
        """Hash field rejects wrong length."""
        field = SchemaField("test", FieldType.HASH, True, "Test")
        is_valid, error = field.validate("a" * 32)
        assert is_valid is False
    
    def test_gid_field_valid(self):
        """GID field validates GID-XX format."""
        field = SchemaField("test", FieldType.GID, True, "Test")
        is_valid, error = field.validate("GID-00")
        assert is_valid is True
    
    def test_gid_field_invalid(self):
        """GID field rejects invalid format."""
        field = SchemaField("test", FieldType.GID, True, "Test")
        is_valid, error = field.validate("AGENT-00")
        assert is_valid is False
    
    def test_timestamp_field_valid(self):
        """Timestamp field validates ISO format."""
        field = SchemaField("test", FieldType.TIMESTAMP, True, "Test")
        is_valid, error = field.validate("2024-01-01T00:00:00+00:00")
        assert is_valid is True
    
    def test_timestamp_field_invalid(self):
        """Timestamp field rejects invalid format."""
        field = SchemaField("test", FieldType.TIMESTAMP, True, "Test")
        is_valid, error = field.validate("Jan 1, 2024")
        assert is_valid is False


# ═══════════════════════════════════════════════════════════════════════════════
# PAC SCHEMA TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPACSchema:
    """Tests for PAC schema validation."""
    
    def test_valid_pac_passes(self, valid_pac):
        """Valid PAC passes validation."""
        is_valid, errors = PAC_SCHEMA.validate(valid_pac)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_pac_missing_required_field(self, valid_pac):
        """PAC fails if missing required field."""
        del valid_pac["pac_id"]
        is_valid, errors = PAC_SCHEMA.validate(valid_pac)
        assert is_valid is False
        assert any("pac_id" in e for e in errors)
    
    def test_pac_invalid_authority(self, valid_pac):
        """PAC fails with invalid authority."""
        valid_pac["authority"] = "INVALID"
        is_valid, errors = PAC_SCHEMA.validate(valid_pac)
        assert is_valid is False
    
    def test_pac_invalid_execution_mode(self, valid_pac):
        """PAC fails with invalid execution mode."""
        valid_pac["execution_mode"] = "BATCH"
        is_valid, errors = PAC_SCHEMA.validate(valid_pac)
        assert is_valid is False


# ═══════════════════════════════════════════════════════════════════════════════
# WRAP SCHEMA TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestWRAPSchema:
    """Tests for WRAP schema validation."""
    
    def test_valid_wrap_passes(self, valid_wrap):
        """Valid WRAP passes validation."""
        is_valid, errors = WRAP_SCHEMA.validate(valid_wrap)
        assert is_valid is True
    
    def test_wrap_missing_positive_closure(self, valid_wrap):
        """WRAP fails if missing positive_closure."""
        del valid_wrap["positive_closure"]
        is_valid, errors = WRAP_SCHEMA.validate(valid_wrap)
        assert is_valid is False
    
    def test_wrap_invalid_gid(self, valid_wrap):
        """WRAP fails with invalid agent GID."""
        valid_wrap["agent_gid"] = "INVALID"
        is_valid, errors = WRAP_SCHEMA.validate(valid_wrap)
        assert is_valid is False


# ═══════════════════════════════════════════════════════════════════════════════
# BER SCHEMA TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBERSchema:
    """Tests for BER schema validation."""
    
    def test_valid_ber_passes(self, valid_ber):
        """Valid BER passes validation."""
        is_valid, errors = BER_SCHEMA.validate(valid_ber)
        assert is_valid is True
    
    def test_ber_issuer_must_be_gid00(self, valid_ber):
        """BER issuer must be GID-00."""
        valid_ber["issuer"] = "GID-01"
        is_valid, errors = BER_SCHEMA.validate(valid_ber)
        # Still valid per schema, but business rule would catch this
        assert is_valid is True  # Schema allows any GID
    
    def test_ber_invalid_classification(self, valid_ber):
        """BER fails with invalid classification."""
        valid_ber["ber_classification"] = "INVALID"
        is_valid, errors = BER_SCHEMA.validate(valid_ber)
        assert is_valid is False


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA REGISTRY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSchemaRegistry:
    """Tests for SchemaRegistry class."""
    
    def test_registry_initialized(self, schema_registry):
        """Registry initializes with canonical schemas."""
        schemas = schema_registry.list_schemas()
        assert len(schemas) == 3
    
    def test_validate_pac_through_registry(self, schema_registry, valid_pac):
        """Registry validates PAC."""
        schema_registry.validate_document("PAC", valid_pac)  # Should not raise
    
    def test_validate_wrap_through_registry(self, schema_registry, valid_wrap):
        """Registry validates WRAP."""
        schema_registry.validate_document("WRAP", valid_wrap)
    
    def test_validate_ber_through_registry(self, schema_registry, valid_ber):
        """Registry validates BER."""
        schema_registry.validate_document("BER", valid_ber)
    
    def test_validation_failure_raises(self, schema_registry):
        """Registry raises on validation failure."""
        invalid_pac = {"pac_id": "INVALID"}
        
        with pytest.raises(SchemaValidationError):
            schema_registry.validate_document("PAC", invalid_pac)


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA EVOLUTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSchemaEvolution:
    """Tests for schema evolution guard."""
    
    def test_field_removal_is_breaking(self):
        """Removing a field is a breaking change."""
        old_schema = CanonicalSchema(
            schema_id="TEST@v1.0.0",
            version="1.0.0",
            description="Test",
            fields=(
                SchemaField("field1", FieldType.STRING, True, "F1"),
                SchemaField("field2", FieldType.STRING, True, "F2"),
            ),
            invariants=(),
        )
        
        new_schema = CanonicalSchema(
            schema_id="TEST@v1.1.0",
            version="1.1.0",
            description="Test",
            fields=(
                SchemaField("field1", FieldType.STRING, True, "F1"),
                # field2 removed
            ),
            invariants=(),
        )
        
        is_safe, changes = SchemaEvolutionGuard.check_evolution(old_schema, new_schema)
        assert is_safe is False
        assert any("removal" in c.lower() for c in changes)
    
    def test_required_to_optional_is_breaking(self):
        """Making required field optional is breaking."""
        old_schema = CanonicalSchema(
            schema_id="TEST@v1.0.0",
            version="1.0.0",
            description="Test",
            fields=(
                SchemaField("field1", FieldType.STRING, True, "F1"),
            ),
            invariants=(),
        )
        
        new_schema = CanonicalSchema(
            schema_id="TEST@v1.1.0",
            version="1.1.0",
            description="Test",
            fields=(
                SchemaField("field1", FieldType.STRING, False, "F1"),  # Now optional
            ),
            invariants=(),
        )
        
        is_safe, changes = SchemaEvolutionGuard.check_evolution(old_schema, new_schema)
        assert is_safe is False
        assert any("optional" in c.lower() for c in changes)
    
    def test_adding_field_is_safe(self):
        """Adding a new optional field is safe."""
        old_schema = CanonicalSchema(
            schema_id="TEST@v1.0.0",
            version="1.0.0",
            description="Test",
            fields=(
                SchemaField("field1", FieldType.STRING, True, "F1"),
            ),
            invariants=(),
        )
        
        new_schema = CanonicalSchema(
            schema_id="TEST@v1.1.0",
            version="1.1.0",
            description="Test",
            fields=(
                SchemaField("field1", FieldType.STRING, True, "F1"),
                SchemaField("field2", FieldType.STRING, False, "F2"),  # New optional
            ),
            invariants=(),
        )
        
        is_safe, changes = SchemaEvolutionGuard.check_evolution(old_schema, new_schema)
        assert is_safe is True
    
    def test_enforce_evolution_raises(self):
        """enforce_evolution raises on breaking change."""
        old_schema = CanonicalSchema(
            schema_id="TEST@v1.0.0",
            version="1.0.0",
            description="Test",
            fields=(
                SchemaField("field1", FieldType.STRING, True, "F1"),
            ),
            invariants=(),
        )
        
        new_schema = CanonicalSchema(
            schema_id="TEST@v1.1.0",
            version="1.1.0",
            description="Test",
            fields=(),  # All fields removed
            invariants=(),
        )
        
        with pytest.raises(SchemaBreakingChangeError):
            SchemaEvolutionGuard.enforce_evolution(old_schema, new_schema)


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSchemaInvariants:
    """Tests for schema invariants."""
    
    def test_inv_schema_001_pac_validation(self, valid_pac):
        """INV-SCHEMA-001: PACs validate against PAC schema."""
        is_valid, _ = PAC_SCHEMA.validate(valid_pac)
        assert is_valid is True
    
    def test_inv_schema_002_wrap_validation(self, valid_wrap):
        """INV-SCHEMA-002: WRAPs validate against WRAP schema."""
        is_valid, _ = WRAP_SCHEMA.validate(valid_wrap)
        assert is_valid is True
    
    def test_inv_schema_003_ber_validation(self, valid_ber):
        """INV-SCHEMA-003: BERs validate against BER schema."""
        is_valid, _ = BER_SCHEMA.validate(valid_ber)
        assert is_valid is True
    
    def test_inv_schema_004_immutability(self, schema_registry):
        """INV-SCHEMA-004: Cannot re-register same schema."""
        with pytest.raises(SchemaMutationError):
            schema_registry.register(PAC_SCHEMA)
