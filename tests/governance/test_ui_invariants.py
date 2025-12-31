# ═══════════════════════════════════════════════════════════════════════════════
# UI Invariants Tests — PAC-BENSON-P23-C
#
# Tests for UI governance invariants.
# Validates INV-UI-001 through INV-UI-006.
#
# Authors:
# - ALEX (GID-08) — Governance Enforcer
# - DAN (GID-07) — CI/Testing Lead
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from pathlib import Path
import tempfile
import os

from core.governance.ui_invariants import (
    UIInvariantSeverity,
    UIInvariant,
    UI_INVARIANTS,
    InvariantViolation,
    UIInvariantChecker,
)


# ═══════════════════════════════════════════════════════════════════════════════
# UI INVARIANT REGISTRY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestUIInvariantRegistry:
    """Tests for UI invariant definitions."""

    def test_all_invariants_have_ids(self):
        """All invariants have unique IDs."""
        ids = [inv.invariant_id for inv in UI_INVARIANTS]
        assert len(ids) == len(set(ids))

    def test_inv_ui_001_exists(self):
        """INV-UI-001 (No Optimistic State) exists."""
        inv = next((i for i in UI_INVARIANTS if i.invariant_id == "INV-UI-001"), None)
        assert inv is not None
        assert "optimistic" in inv.name.lower()

    def test_inv_ui_002_exists(self):
        """INV-UI-002 (Read-Only Display) exists."""
        inv = next((i for i in UI_INVARIANTS if i.invariant_id == "INV-UI-002"), None)
        assert inv is not None
        assert "read-only" in inv.name.lower()

    def test_inv_ui_003_exists(self):
        """INV-UI-003 (Input Sanitization) exists."""
        inv = next((i for i in UI_INVARIANTS if i.invariant_id == "INV-UI-003"), None)
        assert inv is not None
        assert "sanitization" in inv.name.lower()

    def test_inv_ui_004_exists(self):
        """INV-UI-004 (Accessibility) exists."""
        inv = next((i for i in UI_INVARIANTS if i.invariant_id == "INV-UI-004"), None)
        assert inv is not None
        assert "accessibility" in inv.name.lower()

    def test_critical_invariants_block_pr(self):
        """Critical invariants have BLOCK_PR enforcement."""
        critical = [inv for inv in UI_INVARIANTS if inv.severity == UIInvariantSeverity.CRITICAL]
        assert len(critical) >= 2
        for inv in critical:
            assert inv.enforcement == "BLOCK_PR"


# ═══════════════════════════════════════════════════════════════════════════════
# UI INVARIANT CHECKER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestUIInvariantChecker:
    """Tests for UIInvariantChecker."""

    @pytest.fixture
    def checker(self):
        return UIInvariantChecker()

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_detect_optimistic_update(self, checker, temp_dir):
        """Detects optimistic update patterns (INV-UI-001)."""
        test_file = temp_dir / "test.tsx"
        test_file.write_text("""
            const Component = () => {
                setOptimisticState(newValue);
                optimisticUpdate(data);
                return <div>Test</div>;
            };
        """)
        
        violations = checker.check_file(test_file)
        assert len(violations) >= 1
        assert any(v.invariant_id == "INV-UI-001" for v in violations)

    def test_detect_use_optimistic(self, checker, temp_dir):
        """Detects useOptimistic hook (INV-UI-001)."""
        test_file = temp_dir / "test.tsx"
        test_file.write_text("""
            import { useOptimistic } from 'react';
            const Component = () => useOptimistic(data);
        """)
        
        violations = checker.check_file(test_file)
        assert any(v.invariant_id == "INV-UI-001" for v in violations)

    def test_detect_dangerous_inner_html(self, checker, temp_dir):
        """Detects dangerouslySetInnerHTML (INV-UI-003)."""
        test_file = temp_dir / "test.tsx"
        test_file.write_text("""
            const Component = () => (
                <div dangerouslySetInnerHTML={{__html: content}} />
            );
        """)
        
        violations = checker.check_file(test_file)
        assert any(v.invariant_id == "INV-UI-003" for v in violations)

    def test_detect_eval(self, checker, temp_dir):
        """Detects eval() usage (INV-UI-003)."""
        test_file = temp_dir / "test.ts"
        test_file.write_text("""
            const result = eval(userInput);
        """)
        
        violations = checker.check_file(test_file)
        assert any(v.invariant_id == "INV-UI-003" for v in violations)

    def test_safe_code_no_violations(self, checker, temp_dir):
        """Safe code has no violations."""
        test_file = temp_dir / "safe.tsx"
        test_file.write_text("""
            import React from 'react';
            
            const SafeComponent: React.FC = () => {
                const [data, setData] = useState(null);
                
                useEffect(() => {
                    fetch('/api/data')
                        .then(res => res.json())
                        .then(setData);
                }, []);
                
                return (
                    <div aria-label="Safe content">
                        {data && <span>{data.value}</span>}
                    </div>
                );
            };
        """)
        
        violations = checker.check_file(test_file)
        # Safe code should have no critical violations
        critical_violations = [v for v in violations if v.severity == UIInvariantSeverity.CRITICAL]
        assert len(critical_violations) == 0

    def test_check_directory(self, checker, temp_dir):
        """Can check entire directory."""
        # Create multiple files
        (temp_dir / "file1.tsx").write_text("const x = 1;")
        (temp_dir / "file2.tsx").write_text("const y = 2;")
        (temp_dir / "sub").mkdir()
        (temp_dir / "sub" / "file3.tsx").write_text("const z = 3;")
        
        violations = checker.check_directory(temp_dir)
        # Should process all files without error
        assert isinstance(violations, list)

    def test_summary_generation(self, checker, temp_dir):
        """Can generate violation summary."""
        test_file = temp_dir / "test.tsx"
        test_file.write_text("const x = eval('test');")
        
        violations = checker.check_file(test_file)
        summary = checker.get_summary(violations)
        
        assert "total" in summary
        assert "by_severity" in summary
        assert "by_invariant" in summary
        assert "blocking" in summary

    def test_ignores_non_js_files(self, checker, temp_dir):
        """Ignores non-JavaScript/TypeScript files."""
        test_file = temp_dir / "test.py"
        test_file.write_text("result = eval('test')")
        
        violations = checker.check_file(test_file)
        assert len(violations) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT VIOLATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvariantViolation:
    """Tests for InvariantViolation dataclass."""

    def test_violation_has_timestamp(self):
        """Violations have timestamps."""
        violation = InvariantViolation(
            invariant_id="INV-UI-001",
            file_path="/test/file.tsx",
            line_number=10,
            matched_pattern="setOptimistic",
            context="const [x, setOptimisticX] = useState()",
            severity=UIInvariantSeverity.CRITICAL,
        )
        
        assert violation.timestamp is not None

    def test_violation_severity_types(self):
        """Violation severity is proper enum."""
        violation = InvariantViolation(
            invariant_id="INV-UI-001",
            file_path="/test/file.tsx",
            line_number=10,
            matched_pattern="test",
            context="test",
            severity=UIInvariantSeverity.HIGH,
        )
        
        assert isinstance(violation.severity, UIInvariantSeverity)
