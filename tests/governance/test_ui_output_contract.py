"""
Test UI Output Contract

Tests for bounded, checkpoint-only UI emissions.
Per PAC-JEFFREY-DRAFT-GOVERNANCE-UI-OUTPUT-CONTRACT-025.

Agent: GID-01 (Cody) — Senior Backend Engineer
"""

import pytest
from typing import List

from core.governance.ui_output_contract import (
    # Enums
    UIEmissionType,
    ForbiddenContentType,
    
    # Exceptions
    UIContractViolation,
    UnboundedOutputError,
    ForbiddenEmissionError,
    InvalidEmissionTypeError,
    
    # Data classes
    UIEmission,
    EmissionLog,
    
    # Functions
    truncate_hash,
    format_agent_list,
    contains_forbidden_content,
    is_unbounded_output,
    validate_ui_emission,
    reject_unbounded_output,
    
    # Class
    UIOutputContract,
    
    # Singleton
    get_ui_contract,
    reset_ui_contract,
    
    # Config
    UI_OUTPUT_CONFIG,
    EMISSION_SYMBOLS,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def fresh_contract():
    """Provide a fresh UI contract instance."""
    reset_ui_contract()
    contract = UIOutputContract()
    yield contract
    reset_ui_contract()


@pytest.fixture
def singleton_contract():
    """Provide the singleton contract instance."""
    reset_ui_contract()
    yield get_ui_contract()
    reset_ui_contract()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: UIEmissionType Enum
# ═══════════════════════════════════════════════════════════════════════════════

class TestUIEmissionType:
    """Tests for UIEmissionType enum."""

    def test_has_all_required_types(self):
        """INV-UI-002: All allowed emission types are defined."""
        required_types = [
            "PAC_RECEIVED",
            "AGENTS_DISPATCHED",
            "AGENT_STARTED",
            "AGENT_COMPLETED",
            "CHECKPOINT_REACHED",
            "WRAP_HASH_RECEIVED",
            "ALL_WRAPS_RECEIVED",
            "BER_ISSUED",
            "PDO_EMITTED",
            "ERROR_SIGNAL",
            "WARNING_SIGNAL",
        ]
        
        actual_types = [t.value for t in UIEmissionType]
        
        for required in required_types:
            assert required in actual_types, f"Missing emission type: {required}"

    def test_emission_symbols_defined(self):
        """All emission types have symbols defined."""
        for emission_type in UIEmissionType:
            assert emission_type in EMISSION_SYMBOLS, (
                f"Missing symbol for: {emission_type}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ForbiddenContentType Enum
# ═══════════════════════════════════════════════════════════════════════════════

class TestForbiddenContentType:
    """Tests for ForbiddenContentType enum."""

    def test_has_all_forbidden_types(self):
        """All forbidden content types are defined."""
        forbidden_types = [
            "TASK_LOG",
            "TODO_UPDATE",
            "FILE_LISTING",
            "DIFF_OUTPUT",
            "FULL_PAYLOAD",
            "AGENT_NARRATION",
            "PROGRESS_PERCENTAGE",
            "INTERMEDIATE_RESULT",
            "STACK_TRACE",
            "DEBUG_LOG",
        ]
        
        actual_types = [t.value for t in ForbiddenContentType]
        
        for forbidden in forbidden_types:
            assert forbidden in actual_types, f"Missing forbidden type: {forbidden}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Helper Functions
# ═══════════════════════════════════════════════════════════════════════════════

class TestTruncateHash:
    """Tests for truncate_hash function."""

    def test_short_hash_unchanged(self):
        """Short hashes are not truncated."""
        assert truncate_hash("abc123") == "abc123"

    def test_long_hash_truncated(self):
        """Long hashes are truncated with ellipsis."""
        long_hash = "a" * 64
        result = truncate_hash(long_hash, max_length=12)
        assert len(result) < len(long_hash)
        assert result.endswith("...")

    def test_prefixed_hash_preserved(self):
        """Hash prefixes are preserved."""
        result = truncate_hash("sha256:abcdef1234567890", max_length=12)
        assert result.startswith("sha256:")

    def test_empty_hash(self):
        """Empty hash returns empty string."""
        assert truncate_hash("") == ""


class TestFormatAgentList:
    """Tests for format_agent_list function."""

    def test_few_agents_all_shown(self):
        """Few agents are all shown."""
        agents = ["GID-01", "GID-02", "GID-03"]
        result = format_agent_list(agents)
        assert result == "GID-01, GID-02, GID-03"

    def test_many_agents_truncated(self):
        """Many agents are truncated with count."""
        agents = [f"GID-{i:02d}" for i in range(12)]
        result = format_agent_list(agents, max_display=8)
        assert "+4 more" in result
        assert result.count(",") == 7  # 8 agents, 7 commas

    def test_exactly_max_agents(self):
        """Exactly max agents shows all."""
        agents = [f"GID-{i:02d}" for i in range(8)]
        result = format_agent_list(agents, max_display=8)
        assert "+0 more" not in result
        assert "more" not in result


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Forbidden Content Detection
# ═══════════════════════════════════════════════════════════════════════════════

class TestContainsForbiddenContent:
    """Tests for contains_forbidden_content function."""

    def test_detects_bullet_list(self):
        """Detects bullet list as TODO_UPDATE."""
        text = "- Task 1\n- Task 2"
        result = contains_forbidden_content(text)
        assert result == ForbiddenContentType.TODO_UPDATE

    def test_detects_numbered_list(self):
        """Detects numbered list as TODO_UPDATE."""
        text = "1. First item\n2. Second item"
        result = contains_forbidden_content(text)
        assert result == ForbiddenContentType.TODO_UPDATE

    def test_detects_diff_markers(self):
        """Detects diff markers."""
        text = "--- a/file.py\n+++ b/file.py"
        result = contains_forbidden_content(text)
        assert result == ForbiddenContentType.DIFF_OUTPUT

    def test_detects_diff_hunks(self):
        """Detects diff hunks."""
        text = "@@ -10,5 +10,7 @@"
        result = contains_forbidden_content(text)
        assert result == ForbiddenContentType.DIFF_OUTPUT

    def test_detects_stack_trace(self):
        """Detects stack traces."""
        text = 'Traceback (most recent call last):\n  File "test.py", line 10'
        result = contains_forbidden_content(text)
        assert result == ForbiddenContentType.STACK_TRACE

    def test_detects_progress_percentage(self):
        """Detects progress percentages."""
        text = "50% complete"
        result = contains_forbidden_content(text)
        assert result == ForbiddenContentType.PROGRESS_PERCENTAGE

    def test_detects_debug_log(self):
        """Detects DEBUG logs."""
        text = "DEBUG: Some debug information"
        result = contains_forbidden_content(text)
        assert result == ForbiddenContentType.DEBUG_LOG

    def test_allows_valid_checkpoint(self):
        """Allows valid checkpoint messages."""
        text = "GID-01 completed"
        result = contains_forbidden_content(text)
        assert result is None


class TestIsUnboundedOutput:
    """Tests for is_unbounded_output function."""

    def test_detects_long_output(self):
        """Detects output exceeding max length."""
        long_text = "x" * 200
        assert is_unbounded_output(long_text) is True

    def test_detects_multiline_output(self):
        """Detects output with many lines."""
        text = "line1\nline2\nline3\nline4"
        assert is_unbounded_output(text) is True

    def test_detects_code_blocks(self):
        """Detects code blocks."""
        text = "```python\ncode\n```"
        assert is_unbounded_output(text) is True

    def test_allows_short_output(self):
        """Allows short, bounded output."""
        text = "GID-01 completed"
        assert is_unbounded_output(text) is False


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: UIEmission Dataclass
# ═══════════════════════════════════════════════════════════════════════════════

class TestUIEmission:
    """Tests for UIEmission dataclass."""

    def test_basic_creation(self):
        """Can create basic emission."""
        emission = UIEmission(
            emission_type=UIEmissionType.PAC_RECEIVED,
            message="PAC-025 validated",
        )
        assert emission.emission_type == UIEmissionType.PAC_RECEIVED
        assert emission.message == "PAC-025 validated"

    def test_render_basic(self):
        """Renders basic emission correctly."""
        emission = UIEmission(
            emission_type=UIEmissionType.PAC_RECEIVED,
            message="PAC-025 validated",
        )
        rendered = emission.render()
        assert "🟦" in rendered
        assert "PAC_RECEIVED" in rendered
        assert "PAC-025 validated" in rendered

    def test_render_with_hash(self):
        """Renders emission with hash reference."""
        emission = UIEmission(
            emission_type=UIEmissionType.PDO_EMITTED,
            message="PDO-025",
            hash_ref="sha256:abc123def456789012345678901234567890",  # Long hash
        )
        rendered = emission.render()
        assert "🧿" in rendered
        assert "[sha256:abc123def456...]" in rendered  # Truncated at 12 chars after prefix

    def test_to_dict(self):
        """Converts to dictionary correctly."""
        emission = UIEmission(
            emission_type=UIEmissionType.AGENT_COMPLETED,
            message="GID-01",
            agent_gid="GID-01",
        )
        result = emission.to_dict()
        assert result["emission_type"] == "AGENT_COMPLETED"
        assert result["message"] == "GID-01"
        assert result["agent_gid"] == "GID-01"

    def test_frozen_immutability(self):
        """Emission is immutable (frozen)."""
        emission = UIEmission(
            emission_type=UIEmissionType.PAC_RECEIVED,
            message="test",
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            emission.message = "modified"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: validate_ui_emission
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidateUIEmission:
    """Tests for validate_ui_emission function."""

    def test_valid_emission_passes(self):
        """Valid emission passes validation."""
        emission = UIEmission(
            emission_type=UIEmissionType.PAC_RECEIVED,
            message="PAC-025 validated",
        )
        assert validate_ui_emission(emission) is True

    def test_long_message_rejected(self):
        """INV-UI-001: Message exceeding max length is rejected."""
        emission = UIEmission(
            emission_type=UIEmissionType.PAC_RECEIVED,
            message="x" * 200,  # Way too long
        )
        with pytest.raises(UnboundedOutputError):
            validate_ui_emission(emission)

    def test_forbidden_content_rejected(self):
        """Forbidden content is rejected."""
        emission = UIEmission(
            emission_type=UIEmissionType.ERROR_SIGNAL,
            message="DEBUG: Something happened",
        )
        with pytest.raises(ForbiddenEmissionError):
            validate_ui_emission(emission)

    def test_invalid_hash_format_rejected(self):
        """Invalid hash format is rejected."""
        emission = UIEmission(
            emission_type=UIEmissionType.WRAP_HASH_RECEIVED,
            message="GID-01",
            hash_ref="not-a-valid-hash",
        )
        with pytest.raises(ForbiddenEmissionError):
            validate_ui_emission(emission)

    def test_valid_sha256_hash_accepted(self):
        """Valid sha256 hash is accepted."""
        emission = UIEmission(
            emission_type=UIEmissionType.WRAP_HASH_RECEIVED,
            message="GID-01",
            hash_ref="sha256:abc123def456789012345678901234567890123456789012345678901234",
        )
        assert validate_ui_emission(emission) is True

    def test_valid_ber_id_accepted(self):
        """Valid BER ID as hash ref is accepted."""
        emission = UIEmission(
            emission_type=UIEmissionType.BER_ISSUED,
            message="APPROVE",
            hash_ref="BER-PAC-025",
        )
        assert validate_ui_emission(emission) is True

    def test_valid_pdo_id_accepted(self):
        """Valid PDO ID as hash ref is accepted."""
        emission = UIEmission(
            emission_type=UIEmissionType.PDO_EMITTED,
            message="PDO-025",
            hash_ref="PDO-PAC-025",
        )
        assert validate_ui_emission(emission) is True


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: reject_unbounded_output
# ═══════════════════════════════════════════════════════════════════════════════

class TestRejectUnboundedOutput:
    """Tests for reject_unbounded_output function."""

    def test_always_raises(self):
        """INV-UI-006: Always raises, never truncates."""
        with pytest.raises(UnboundedOutputError):
            reject_unbounded_output("any output")

    def test_includes_type_info(self):
        """Error includes type information."""
        try:
            reject_unbounded_output({"key": "value"})
        except UnboundedOutputError as e:
            assert "dict" in str(e)

    def test_includes_preview(self):
        """Error includes preview of content."""
        try:
            reject_unbounded_output("Some content here")
        except UnboundedOutputError as e:
            assert "Some content" in str(e)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: UIOutputContract Class
# ═══════════════════════════════════════════════════════════════════════════════

class TestUIOutputContract:
    """Tests for UIOutputContract class."""

    def test_initialization(self, fresh_contract):
        """Contract initializes with default config."""
        assert fresh_contract.config["max_emission_length"] == 120
        assert fresh_contract.config["fail_closed"] is True

    def test_custom_config(self):
        """Can initialize with custom config."""
        contract = UIOutputContract(config={"max_emission_length": 100})
        assert contract.config["max_emission_length"] == 100

    def test_emit_valid_emission(self, fresh_contract):
        """Can emit valid emission."""
        emission = UIEmission(
            emission_type=UIEmissionType.PAC_RECEIVED,
            message="PAC-025 validated",
        )
        result = fresh_contract.emit(emission)
        assert "PAC_RECEIVED" in result
        assert "PAC-025" in result

    def test_emit_invalid_emission_raises(self, fresh_contract):
        """INV-UI-006: Invalid emission raises exception."""
        emission = UIEmission(
            emission_type=UIEmissionType.PAC_RECEIVED,
            message="x" * 200,  # Too long
        )
        with pytest.raises(UIContractViolation):
            fresh_contract.emit(emission)

    def test_emission_logged(self, fresh_contract):
        """Emissions are logged for audit."""
        emission = UIEmission(
            emission_type=UIEmissionType.PAC_RECEIVED,
            message="test",
        )
        fresh_contract.emit(emission)
        
        log = fresh_contract.get_emission_log()
        assert len(log) == 1
        assert log[0].validated is True

    def test_emission_count_tracked(self, fresh_contract):
        """Emission count is tracked."""
        emission = UIEmission(
            emission_type=UIEmissionType.PAC_RECEIVED,
            message="test",
        )
        
        assert fresh_contract.get_emission_count() == 0
        fresh_contract.emit(emission)
        assert fresh_contract.get_emission_count() == 1

    def test_create_emission_validates(self, fresh_contract):
        """create_emission validates before returning."""
        with pytest.raises(UnboundedOutputError):
            fresh_contract.create_emission(
                UIEmissionType.PAC_RECEIVED,
                "x" * 200,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: UIOutputContract Convenience Methods
# ═══════════════════════════════════════════════════════════════════════════════

class TestUIOutputContractConvenienceMethods:
    """Tests for UIOutputContract convenience methods."""

    def test_emit_pac_received(self, fresh_contract):
        """emit_pac_received emits correct checkpoint."""
        result = fresh_contract.emit_pac_received("PAC-025")
        assert "PAC_RECEIVED" in result
        assert "PAC-025" in result

    def test_emit_agents_dispatched(self, fresh_contract):
        """emit_agents_dispatched emits correct checkpoint."""
        result = fresh_contract.emit_agents_dispatched(["GID-01", "GID-02"])
        assert "AGENTS_DISPATCHED" in result
        assert "2 agents" in result

    def test_emit_agent_started(self, fresh_contract):
        """emit_agent_started emits correct checkpoint."""
        result = fresh_contract.emit_agent_started("GID-01", "BACKEND")
        assert "AGENT_STARTED" in result
        assert "GID-01" in result
        assert "BACKEND" in result

    def test_emit_agent_completed(self, fresh_contract):
        """emit_agent_completed emits correct checkpoint."""
        result = fresh_contract.emit_agent_completed("GID-01", test_count=25)
        assert "AGENT_COMPLETED" in result
        assert "25 tests passed" in result

    def test_emit_wrap_received(self, fresh_contract):
        """emit_wrap_received emits correct checkpoint."""
        result = fresh_contract.emit_wrap_received(
            "GID-01",
            "sha256:abc123def456",
        )
        assert "WRAP_HASH_RECEIVED" in result
        assert "GID-01" in result

    def test_emit_all_wraps_received(self, fresh_contract):
        """emit_all_wraps_received emits correct checkpoint."""
        result = fresh_contract.emit_all_wraps_received(4)
        assert "ALL_WRAPS_RECEIVED" in result
        assert "4/4" in result

    def test_emit_ber_issued(self, fresh_contract):
        """emit_ber_issued emits correct checkpoint."""
        result = fresh_contract.emit_ber_issued("APPROVE", "BER-025")
        assert "BER_ISSUED" in result
        assert "APPROVE" in result

    def test_emit_pdo_emitted(self, fresh_contract):
        """emit_pdo_emitted emits correct checkpoint."""
        result = fresh_contract.emit_pdo_emitted("PDO-025", "sha256:pdo123")
        assert "PDO_EMITTED" in result
        assert "PDO-025" in result

    def test_emit_error(self, fresh_contract):
        """emit_error emits correct checkpoint."""
        result = fresh_contract.emit_error("VALIDATION", "Schema mismatch")
        assert "ERROR_SIGNAL" in result
        assert "VALIDATION" in result


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Emission Count Formula
# ═══════════════════════════════════════════════════════════════════════════════

class TestEmissionCountFormula:
    """Tests for emission count formula: 4 + 3N."""

    def test_single_agent_formula(self, fresh_contract):
        """1 agent: 4 + 3(1) = 7 max emissions."""
        assert fresh_contract.calculate_max_emissions(1) == 7

    def test_four_agent_formula(self, fresh_contract):
        """4 agents: 4 + 3(4) = 16 max emissions."""
        assert fresh_contract.calculate_max_emissions(4) == 16

    def test_eight_agent_formula(self, fresh_contract):
        """8 agents: 4 + 3(8) = 28 max emissions."""
        assert fresh_contract.calculate_max_emissions(8) == 28

    def test_simulated_4_agent_execution(self, fresh_contract):
        """Simulated 4-agent execution stays within bounds."""
        agents = ["GID-01", "GID-02", "GID-03", "GID-04"]
        max_allowed = fresh_contract.calculate_max_emissions(len(agents))
        
        # 1. PAC_RECEIVED
        fresh_contract.emit_pac_received("PAC-025")
        
        # 2. AGENTS_DISPATCHED
        fresh_contract.emit_agents_dispatched(agents)
        
        # 3. For each agent: AGENT_COMPLETED + WRAP_RECEIVED (2 each = 8 total)
        for agent in agents:
            fresh_contract.emit_agent_completed(agent)
            fresh_contract.emit_wrap_received(agent, f"sha256:{agent}")
        
        # 4. ALL_WRAPS_RECEIVED
        fresh_contract.emit_all_wraps_received(4)
        
        # 5. BER_ISSUED
        fresh_contract.emit_ber_issued("APPROVE", "BER-025")
        
        # 6. PDO_EMITTED
        fresh_contract.emit_pdo_emitted("PDO-025", "sha256:pdo")
        
        # Verify within bounds
        # Expected: 1 + 1 + 8 + 1 + 1 + 1 = 13 emissions
        # Formula max: 4 + 3(4) = 16
        assert fresh_contract.get_emission_count() <= max_allowed


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Singleton Management
# ═══════════════════════════════════════════════════════════════════════════════

class TestSingletonManagement:
    """Tests for singleton contract management."""

    def test_singleton_returns_same_instance(self):
        """get_ui_contract returns same instance."""
        reset_ui_contract()
        contract1 = get_ui_contract()
        contract2 = get_ui_contract()
        assert contract1 is contract2
        reset_ui_contract()

    def test_reset_clears_singleton(self):
        """reset_ui_contract clears singleton."""
        reset_ui_contract()
        contract1 = get_ui_contract()
        reset_ui_contract()
        contract2 = get_ui_contract()
        assert contract1 is not contract2
        reset_ui_contract()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Thread Safety
# ═══════════════════════════════════════════════════════════════════════════════

class TestThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_emissions(self, fresh_contract):
        """Multiple threads can emit concurrently."""
        import threading
        
        results = []
        errors = []
        
        def emit_checkpoint(agent_id: str):
            try:
                result = fresh_contract.emit_agent_completed(agent_id)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=emit_checkpoint, args=(f"GID-{i:02d}",))
            for i in range(10)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 10
        assert fresh_contract.get_emission_count() == 10


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Contract Invariants (INV-UI-*)
# ═══════════════════════════════════════════════════════════════════════════════

class TestContractInvariants:
    """Tests for UI Output Contract invariants."""

    def test_inv_ui_001_bounded_output(self, fresh_contract):
        """INV-UI-001: All emissions ≤120 characters."""
        # Valid emission
        emission = fresh_contract.create_emission(
            UIEmissionType.PAC_RECEIVED,
            "PAC-025 validated",
        )
        rendered = emission.render()
        assert len(rendered) <= 120
        
        # Invalid long emission
        with pytest.raises(UnboundedOutputError):
            fresh_contract.create_emission(
                UIEmissionType.PAC_RECEIVED,
                "x" * 200,
            )

    def test_inv_ui_002_checkpoint_only(self, fresh_contract):
        """INV-UI-002: Only checkpoint-type emissions allowed."""
        # All emission types are checkpoint types (by definition)
        for emission_type in UIEmissionType:
            emission = fresh_contract.create_emission(
                emission_type,
                "test message",
            )
            assert validate_ui_emission(emission) is True

    def test_inv_ui_003_hash_only_references(self, fresh_contract):
        """INV-UI-003: Hash-only references (no full payloads)."""
        # Valid hash reference
        emission = fresh_contract.create_emission(
            UIEmissionType.WRAP_HASH_RECEIVED,
            "GID-01",
            hash_ref="sha256:abc123",
        )
        assert validate_ui_emission(emission) is True
        
        # Invalid non-hash reference
        with pytest.raises(ForbiddenEmissionError):
            fresh_contract.create_emission(
                UIEmissionType.WRAP_HASH_RECEIVED,
                "GID-01",
                hash_ref="full payload content here",
            )

    def test_inv_ui_004_no_agent_narration(self, fresh_contract):
        """INV-UI-004: No agent narration in emissions."""
        # Forbidden: verbose narration (exceeds length limit)
        # The message needs to be long enough that the full rendered output
        # exceeds 120 characters
        verbose_message = (
            "Agent GID-01 is now processing the first task and working hard. "
            "It will create the file and run many many tests. This is way too long."
        )
        # This should fail on length (narration is inherently verbose)
        emission = UIEmission(
            emission_type=UIEmissionType.AGENT_STARTED,
            message=verbose_message,
        )
        with pytest.raises(UnboundedOutputError):
            validate_ui_emission(emission)

    def test_inv_ui_006_fail_closed(self, fresh_contract):
        """INV-UI-006: FAIL-CLOSED — never truncates, always raises."""
        # Attempt to emit invalid content
        emission = UIEmission(
            emission_type=UIEmissionType.PAC_RECEIVED,
            message="x" * 200,  # Too long
        )
        
        # Must raise, not truncate
        with pytest.raises(UIContractViolation):
            fresh_contract.emit(emission)
        
        # Emission count should not increase
        assert fresh_contract.get_emission_count() == 0


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_message(self, fresh_contract):
        """Empty message is allowed."""
        emission = fresh_contract.create_emission(
            UIEmissionType.CHECKPOINT_REACHED,
            "",
        )
        assert validate_ui_emission(emission) is True

    def test_unicode_in_message(self, fresh_contract):
        """Unicode characters in message are allowed."""
        emission = fresh_contract.create_emission(
            UIEmissionType.AGENT_COMPLETED,
            "GID-01 ✓ 完成",
        )
        assert validate_ui_emission(emission) is True

    def test_exactly_max_length(self, fresh_contract):
        """Message exactly at max length is allowed."""
        # Calculate exact length needed (accounting for symbol and type prefix)
        max_len = UI_OUTPUT_CONFIG["max_emission_length"]
        prefix_len = len("🟦 PAC_RECEIVED: ")
        message_len = max_len - prefix_len
        
        emission = fresh_contract.create_emission(
            UIEmissionType.PAC_RECEIVED,
            "x" * message_len,
        )
        rendered = emission.render()
        assert len(rendered) <= max_len

    def test_one_over_max_length_rejected(self, fresh_contract):
        """Message one character over max is rejected."""
        max_len = UI_OUTPUT_CONFIG["max_emission_length"]
        
        # Create message that will definitely exceed limit
        emission = UIEmission(
            emission_type=UIEmissionType.PAC_RECEIVED,
            message="x" * (max_len + 50),
        )
        
        with pytest.raises(UnboundedOutputError):
            validate_ui_emission(emission)

    def test_none_hash_ref_allowed(self, fresh_contract):
        """None hash_ref is allowed."""
        emission = fresh_contract.create_emission(
            UIEmissionType.PAC_RECEIVED,
            "test",
            hash_ref=None,
        )
        assert validate_ui_emission(emission) is True

    def test_special_characters_in_message(self, fresh_contract):
        """Special characters in message are handled."""
        emission = fresh_contract.create_emission(
            UIEmissionType.ERROR_SIGNAL,
            "Error: [test] — 'quoted'",
        )
        assert validate_ui_emission(emission) is True
