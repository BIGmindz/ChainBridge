"""
Unit Tests for ChainBridge Tool-Strip Enforcement
════════════════════════════════════════════════════════════════════════════════

Tests all enforcement paths for tool stripping:
- Gateway-level tool stripping
- Runtime enforcement
- FAIL-CLOSED behavior
- Path restrictions by lane

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-TOOL-STRIP-ENFORCEMENT-014
Effective Date: 2025-12-26

════════════════════════════════════════════════════════════════════════════════
"""

import pytest
from typing import List

# Import enforcement modules
from core.governance.enforcement import (
    EnforcementContext,
    enforce,
    get_enforcer,
)
from core.governance.tool_matrix import (
    ToolCategory,
    evaluate_tools,
    is_tool_permitted,
    is_path_permitted,
    strip_disallowed_tools,
)
from gateway.tool_strip_gateway import (
    ToolStripGateway,
    ToolStripDenialError,
    ToolStripResult,
    filter_tools_before_execution,
    assert_tool_before_execution,
    get_tool_strip_gateway,
    reset_tool_strip_gateway,
)
from core.governance.runtime_tool_enforcement import (
    RuntimeToolEnforcer,
    ToolExecutionDenied,
    PathExecutionDenied,
    get_runtime_enforcer,
    reset_runtime_enforcer,
    enforced_runtime,
    tool_enforcement_session,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset all singletons before each test."""
    reset_tool_strip_gateway()
    reset_runtime_enforcer()
    get_enforcer().clear_context()
    yield
    reset_tool_strip_gateway()
    reset_runtime_enforcer()
    get_enforcer().clear_context()


@pytest.fixture
def all_tools() -> List[str]:
    """Sample list of all tools."""
    return [
        "read_file",
        "write_file",
        "edit_file",
        "delete_file",
        "create_directory",
        "run_in_terminal",
        "semantic_search",
        "grep_search",
        "file_search",
        "list_dir",
        "fetch_webpage",
        "runSubagent",
        "create_pac",
        "get_errors",
    ]


@pytest.fixture
def execution_context() -> EnforcementContext:
    """Create an enforcement context for EXECUTION mode."""
    return enforce(
        gid="GID-01",
        role="Senior Backend Engineer",
        mode="EXECUTION",
        execution_lane="CORE",
    )


@pytest.fixture
def review_context() -> EnforcementContext:
    """Create an enforcement context for REVIEW mode."""
    return enforce(
        gid="GID-01",
        role="Senior Backend Engineer",
        mode="REVIEW",
        execution_lane="CORE",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# GATEWAY-LEVEL TOOL STRIPPING TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestToolStripGateway:
    """Tests for gateway-level tool stripping."""
    
    def test_strip_tools_for_execution_mode(self, all_tools: List[str]):
        """EXECUTION mode keeps read and write tools."""
        gateway = get_tool_strip_gateway()
        result = gateway.strip_tools(all_tools, "EXECUTION", "CORE")
        
        # Should have read and write tools
        assert "read_file" in result.allowed_tools
        assert "write_file" in result.allowed_tools
        assert "edit_file" in result.allowed_tools
        assert "run_in_terminal" in result.allowed_tools
        
        # Should NOT have authority tools
        assert "runSubagent" not in result.allowed_tools
        assert "create_pac" not in result.allowed_tools
    
    def test_strip_tools_for_review_mode(self, all_tools: List[str]):
        """REVIEW mode strips all write tools."""
        gateway = get_tool_strip_gateway()
        result = gateway.strip_tools(all_tools, "REVIEW", "CORE")
        
        # Should have only read tools
        assert "read_file" in result.allowed_tools
        assert "semantic_search" in result.allowed_tools
        assert "grep_search" in result.allowed_tools
        
        # Should NOT have write tools
        assert "write_file" not in result.allowed_tools
        assert "edit_file" not in result.allowed_tools
        assert "run_in_terminal" not in result.allowed_tools
    
    def test_strip_tools_for_orchestration_mode(self, all_tools: List[str]):
        """ORCHESTRATION mode has full access including authority tools."""
        gateway = get_tool_strip_gateway()
        result = gateway.strip_tools(all_tools, "ORCHESTRATION", "ALL")
        
        # Should have all tools
        assert "read_file" in result.allowed_tools
        assert "write_file" in result.allowed_tools
        assert "runSubagent" in result.allowed_tools
    
    def test_strip_result_tracks_stripped_tools(self, all_tools: List[str]):
        """Strip result correctly tracks which tools were stripped."""
        gateway = get_tool_strip_gateway()
        result = gateway.strip_tools(all_tools, "REVIEW", "CORE")
        
        # Verify stripped tools set is accurate
        assert result.is_restricted
        assert result.tools_removed > 0
        assert "write_file" in result.stripped_tools
        assert "edit_file" in result.stripped_tools
        
        # Verify was_stripped method
        assert result.was_stripped("write_file")
        assert not result.was_stripped("read_file")
    
    def test_intercept_tool_call_allows_valid(self):
        """Valid tool calls are allowed."""
        gateway = get_tool_strip_gateway()
        
        # Should not raise
        result = gateway.intercept_tool_call(
            "write_file",
            "EXECUTION",
            "CORE",
            "GID-01",
        )
        assert result is True
    
    def test_intercept_tool_call_denies_invalid(self):
        """Invalid tool calls are denied with exception."""
        gateway = get_tool_strip_gateway()
        
        with pytest.raises(ToolStripDenialError) as exc_info:
            gateway.intercept_tool_call(
                "write_file",  # Write tool
                "REVIEW",      # Read-only mode
                "CORE",
                "GID-01",
            )
        
        assert exc_info.value.tool_name == "write_file"
        assert exc_info.value.mode == "REVIEW"
        assert "HARD FAIL" in str(exc_info.value)
    
    def test_intercept_stats_tracking(self):
        """Gateway tracks interception statistics."""
        gateway = get_tool_strip_gateway()
        
        # Make some allowed calls
        gateway.intercept_tool_call("read_file", "REVIEW", "CORE")
        gateway.intercept_tool_call("read_file", "REVIEW", "CORE")
        
        # Make a denied call
        try:
            gateway.intercept_tool_call("write_file", "REVIEW", "CORE")
        except ToolStripDenialError:
            pass
        
        stats = gateway.intercept_stats
        assert stats["allowed"] == 2
        assert stats["intercepted_and_denied"] == 1
        assert stats["total_checks"] == 3


class TestFilterToolsBeforeExecution:
    """Tests for the canonical pre-execution filter."""
    
    def test_filter_with_valid_gid(self, all_tools: List[str]):
        """Tools are filtered for valid GID."""
        filtered = filter_tools_before_execution(
            all_tools,
            gid="GID-01",
            mode="EXECUTION",
            lane="CORE",
        )
        
        assert "read_file" in filtered
        assert "write_file" in filtered
        assert "runSubagent" not in filtered
    
    def test_filter_with_unknown_gid(self, all_tools: List[str]):
        """Unknown GID results in empty tool list (FAIL-CLOSED)."""
        filtered = filter_tools_before_execution(
            all_tools,
            gid="GID-99",  # Unknown
            mode="EXECUTION",
            lane="CORE",
        )
        
        # FAIL-CLOSED: no tools for unknown GID
        assert len(filtered) == 0
    
    def test_assert_tool_before_execution_allows_valid(self):
        """Valid tool is allowed before execution."""
        # Should not raise
        assert_tool_before_execution(
            "write_file",
            gid="GID-01",
            mode="EXECUTION",
            lane="CORE",
        )
    
    def test_assert_tool_before_execution_denies_invalid(self):
        """Invalid tool raises exception before execution."""
        with pytest.raises(ToolStripDenialError):
            assert_tool_before_execution(
                "write_file",
                gid="GID-01",
                mode="REVIEW",  # Read-only mode
                lane="CORE",
            )


# ═══════════════════════════════════════════════════════════════════════════════
# RUNTIME ENFORCEMENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRuntimeToolEnforcer:
    """Tests for runtime tool enforcement."""
    
    def test_filter_with_bound_context(
        self,
        execution_context: EnforcementContext,
        all_tools: List[str],
    ):
        """Tools are filtered based on bound context."""
        enforcer = get_runtime_enforcer()
        enforcer.bind_context(execution_context)
        
        filtered = enforcer.filter_available_tools(all_tools)
        
        assert "read_file" in filtered
        assert "write_file" in filtered
        assert "runSubagent" not in filtered
        
        enforcer.unbind_context()
    
    def test_assert_tool_allowed_passes(self, execution_context: EnforcementContext):
        """Allowed tools pass assertion."""
        enforcer = get_runtime_enforcer()
        enforcer.bind_context(execution_context)
        
        # Should not raise
        enforcer.assert_tool_allowed("write_file")
        enforcer.assert_tool_allowed("read_file")
        
        enforcer.unbind_context()
    
    def test_assert_tool_denied_raises(self, review_context: EnforcementContext):
        """Denied tools raise exception."""
        enforcer = get_runtime_enforcer()
        enforcer.bind_context(review_context)
        
        with pytest.raises(ToolExecutionDenied) as exc_info:
            enforcer.assert_tool_allowed("write_file")
        
        assert exc_info.value.tool_name == "write_file"
        assert exc_info.value.context is not None
        
        enforcer.unbind_context()
    
    def test_assert_path_allowed_passes(self, execution_context: EnforcementContext):
        """Allowed paths pass assertion."""
        enforcer = get_runtime_enforcer()
        enforcer.bind_context(execution_context)
        
        # CORE lane should allow /core/ paths
        enforcer.assert_path_allowed("/core/governance/test.py")
        
        enforcer.unbind_context()
    
    def test_audit_report_generation(self, execution_context: EnforcementContext):
        """Audit report is generated correctly."""
        enforcer = get_runtime_enforcer()
        enforcer.bind_context(execution_context)
        
        # Make some assertions
        enforcer.assert_tool_allowed("read_file")
        enforcer.assert_tool_allowed("write_file")
        
        try:
            enforcer.assert_tool_allowed("runSubagent")
        except ToolExecutionDenied:
            pass
        
        report = enforcer.get_audit_report()
        
        assert report["context"]["gid"] == "GID-01"
        assert report["context"]["mode"] == "EXECUTION"
        assert report["enforcement"]["total_allows"] == 2
        assert report["enforcement"]["total_denials"] == 1
        
        enforcer.unbind_context()


class TestEnforcedRuntimeContextManager:
    """Tests for context manager-based enforcement."""
    
    def test_enforced_runtime_context(self, execution_context: EnforcementContext):
        """Context manager provides enforced runtime."""
        with enforced_runtime(execution_context) as enforcer:
            assert enforcer is not None
            
            # Should work
            enforcer.assert_tool_allowed("write_file")
    
    def test_tool_enforcement_session(self):
        """Quick session context manager works."""
        with tool_enforcement_session("GID-01", "EXECUTION", "CORE") as enforcer:
            enforcer.assert_tool_allowed("write_file")
            
            # Should fail
            with pytest.raises(ToolExecutionDenied):
                enforcer.assert_tool_allowed("runSubagent")


# ═══════════════════════════════════════════════════════════════════════════════
# FAIL-CLOSED BEHAVIOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFailClosedBehavior:
    """Tests that verify FAIL-CLOSED behavior."""
    
    def test_unknown_mode_restricts_to_readonly(self, all_tools: List[str]):
        """Unknown mode defaults to most restrictive (read-only)."""
        gateway = get_tool_strip_gateway()
        result = gateway.strip_tools(all_tools, "UNKNOWN_MODE", "ALL")
        
        # Should have only read-only tools
        assert "read_file" in result.allowed_tools
        assert "write_file" not in result.allowed_tools
        assert "run_in_terminal" not in result.allowed_tools
    
    def test_unknown_tool_denied(self):
        """Unknown tools are denied (FAIL-CLOSED)."""
        is_allowed = is_tool_permitted("unknown_tool_xyz", "EXECUTION", "CORE")
        assert is_allowed is False
    
    def test_empty_context_denies_all(self, all_tools: List[str]):
        """No context means no tools (FAIL-CLOSED)."""
        enforcer = get_enforcer()
        enforcer.clear_context()
        
        # strip_tools should return empty list when no context
        stripped = enforcer.strip_tools(all_tools)
        assert len(stripped) == 0
    
    def test_gateway_intercept_unknown_tool(self):
        """Gateway intercept denies unknown tools."""
        gateway = get_tool_strip_gateway()
        
        with pytest.raises(ToolStripDenialError):
            gateway.intercept_tool_call(
                "totally_unknown_tool",
                "EXECUTION",
                "CORE",
            )


# ═══════════════════════════════════════════════════════════════════════════════
# PATH RESTRICTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPathRestrictions:
    """Tests for lane-based path restrictions."""
    
    def test_core_lane_allows_core_paths(self):
        """CORE lane allows /core/ paths."""
        assert is_path_permitted("/core/engine.py", "CORE")
        assert is_path_permitted("/src/core/main.py", "CORE")
    
    def test_frontend_lane_allows_frontend_paths(self):
        """FRONTEND lane allows frontend paths."""
        assert is_path_permitted("/chainboard-ui/src/App.tsx", "FRONTEND")
        assert is_path_permitted("/frontend/index.js", "FRONTEND")
    
    def test_all_lane_allows_everything(self):
        """ALL lane has no restrictions."""
        assert is_path_permitted("/anything/anywhere/file.py", "ALL")
        assert is_path_permitted("/core/test.py", "ALL")
        assert is_path_permitted("/frontend/test.tsx", "ALL")
    
    def test_governance_lane_restrictions(self):
        """GOVERNANCE lane allows governance paths."""
        assert is_path_permitted("/core/governance/enforcement.py", "GOVERNANCE")


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL CATEGORY MAPPING TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestToolCategoryMapping:
    """Tests for tool category mapping."""
    
    def test_execution_mode_tool_categories(self):
        """EXECUTION mode has correct tool categories."""
        result = evaluate_tools("EXECUTION", "CORE")
        
        # Check specific categories
        assert ToolCategory.READ_FILE in result.allowed_tools
        assert ToolCategory.WRITE_FILE in result.allowed_tools
        assert ToolCategory.EDIT_FILE in result.allowed_tools
        assert ToolCategory.RUN_TERMINAL in result.allowed_tools
        assert ToolCategory.SEMANTIC_SEARCH in result.allowed_tools
        
        # Authority tools should be denied
        assert ToolCategory.RUN_SUBAGENT in result.denied_tools
    
    def test_review_mode_tool_categories(self):
        """REVIEW mode has only read tools."""
        result = evaluate_tools("REVIEW", "CORE")
        
        # Only read tools
        assert ToolCategory.READ_FILE in result.allowed_tools
        assert ToolCategory.SEMANTIC_SEARCH in result.allowed_tools
        
        # All write tools denied
        assert ToolCategory.WRITE_FILE in result.denied_tools
        assert ToolCategory.EDIT_FILE in result.denied_tools
        assert ToolCategory.RUN_TERMINAL in result.denied_tools
    
    def test_orchestration_mode_tool_categories(self):
        """ORCHESTRATION mode has all tools including authority."""
        result = evaluate_tools("ORCHESTRATION", "ALL")
        
        # Should have everything
        assert ToolCategory.RUN_SUBAGENT in result.allowed_tools
        assert ToolCategory.READ_FILE in result.allowed_tools
        assert ToolCategory.WRITE_FILE in result.allowed_tools


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestToolStripIntegration:
    """Integration tests for full tool stripping flow."""
    
    def test_full_enforcement_flow(self, all_tools: List[str]):
        """Full flow from enforcement context to tool filtering."""
        # 1. Create enforcement context
        ctx = enforce(
            gid="GID-01",
            role="Backend Engineer",
            mode="EXECUTION",
            execution_lane="CORE",
        )
        
        # 2. Filter tools at gateway level
        filtered = filter_tools_before_execution(
            all_tools,
            gid=ctx.gid,
            mode=ctx.mode,
            lane=ctx.execution_lane,
        )
        
        # 3. Verify filtering
        assert "write_file" in filtered
        assert "runSubagent" not in filtered
        
        # 4. Use runtime enforcer
        with enforced_runtime(ctx) as enforcer:
            # Should pass
            enforcer.assert_tool_allowed("write_file")
            
            # Should fail
            with pytest.raises(ToolExecutionDenied):
                enforcer.assert_tool_allowed("runSubagent")
    
    def test_mode_switch_updates_tools(self):
        """Switching modes updates available tools."""
        # First with EXECUTION
        ctx_exec = enforce(
            gid="GID-01",
            role="Backend",
            mode="EXECUTION",
            execution_lane="CORE",
        )
        
        enforcer = get_runtime_enforcer()
        enforcer.bind_context(ctx_exec)
        enforcer.assert_tool_allowed("write_file")  # Should pass
        enforcer.unbind_context()
        
        # Now with REVIEW
        ctx_review = enforce(
            gid="GID-01",
            role="Backend",
            mode="REVIEW",
            execution_lane="CORE",
        )
        
        enforcer.bind_context(ctx_review)
        
        with pytest.raises(ToolExecutionDenied):
            enforcer.assert_tool_allowed("write_file")  # Should fail
        
        enforcer.unbind_context()

