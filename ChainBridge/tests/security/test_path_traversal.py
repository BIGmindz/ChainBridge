"""
PAC-SAM-R2-001: Security tests for path traversal protection.

These tests verify that the path_security module correctly blocks
directory traversal attacks while allowing legitimate paths.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from core.path_security import PathTraversalError, safe_filename, safe_join, validate_path_within_base


class TestPathTraversalProtection:
    """Tests for path traversal blocking."""

    def test_safe_join_blocks_parent_traversal(self, tmp_path: Path) -> None:
        """Traversal via .. should be rejected."""
        with pytest.raises(PathTraversalError, match="traversal"):
            safe_join(tmp_path, "../secrets")

    def test_safe_join_blocks_deep_traversal(self, tmp_path: Path) -> None:
        """Deep traversal attempts should be rejected."""
        with pytest.raises(PathTraversalError, match="traversal"):
            safe_join(tmp_path, "a/b/../../..")

    def test_safe_join_blocks_absolute_paths(self, tmp_path: Path) -> None:
        """Absolute paths should be rejected."""
        with pytest.raises(PathTraversalError, match="Absolute.*not allowed"):
            safe_join(tmp_path, "/etc/passwd")

    def test_safe_join_blocks_null_bytes(self, tmp_path: Path) -> None:
        """Null byte injection should be rejected."""
        with pytest.raises(PathTraversalError, match="[Nn]ull"):
            safe_join(tmp_path, "file\x00.txt")

    def test_safe_join_allows_valid_nested_path(self, tmp_path: Path) -> None:
        """Valid nested paths should be allowed."""
        result = safe_join(tmp_path, "uploads/data/file.csv")
        assert result.is_relative_to(tmp_path)
        assert result.name == "file.csv"

    def test_safe_join_allows_simple_filename(self, tmp_path: Path) -> None:
        """Simple filenames should be allowed."""
        result = safe_join(tmp_path, "report.csv")
        assert result == tmp_path / "report.csv"


class TestSafeFilename:
    """Tests for filename sanitization."""

    def test_safe_filename_strips_path_components(self) -> None:
        """Path separators should be stripped."""
        assert safe_filename("../../../etc/passwd") == "passwd"

    def test_safe_filename_preserves_valid_name(self) -> None:
        """Valid filenames should be preserved."""
        assert safe_filename("data_2024.csv") == "data_2024.csv"

    def test_safe_filename_rejects_null_bytes(self) -> None:
        """Null bytes in filenames should be rejected."""
        with pytest.raises(PathTraversalError):
            safe_filename("file\x00.txt")

    def test_safe_filename_rejects_empty(self) -> None:
        """Empty or dot-only names should be rejected."""
        with pytest.raises(PathTraversalError):
            safe_filename("..")


class TestValidatePathWithinBase:
    """Tests for base directory containment validation."""

    def test_validate_blocks_escape_attempt(self, tmp_path: Path) -> None:
        """Paths escaping the base should be blocked."""
        with pytest.raises(PathTraversalError):
            validate_path_within_base(tmp_path / ".." / "secrets", tmp_path)

    def test_validate_allows_contained_path(self, tmp_path: Path) -> None:
        """Paths within base should be allowed."""
        # Should not raise
        result = validate_path_within_base(tmp_path / "data" / "file.csv", tmp_path)
        assert result.is_relative_to(tmp_path)

    def test_validate_blocks_symlink_escape(self, tmp_path: Path) -> None:
        """Symlinks pointing outside base should be blocked."""
        # Create a symlink pointing outside the base
        external = Path(tempfile.gettempdir()) / "external_target"
        external.touch()
        try:
            symlink = tmp_path / "escape_link"
            symlink.symlink_to(external)

            with pytest.raises(PathTraversalError, match="not within"):
                validate_path_within_base(symlink, tmp_path)
        finally:
            external.unlink(missing_ok=True)


class TestEdgeCases:
    """Edge case tests for robustness."""

    def test_url_encoded_traversal_blocked(self, tmp_path: Path) -> None:
        """URL-encoded traversal attempts should be blocked."""
        # If decoded by caller: %2e%2e = ..
        with pytest.raises(PathTraversalError):
            safe_join(tmp_path, "..%2f..%2f..%2fetc/passwd".replace("%2f", "/").replace("%2e", "."))

    def test_backslash_traversal_blocked(self, tmp_path: Path) -> None:
        """Backslash traversal (Windows-style) should be blocked."""
        with pytest.raises(PathTraversalError):
            safe_join(tmp_path, "..\\..\\secrets")

    def test_mixed_traversal_blocked(self, tmp_path: Path) -> None:
        """Mixed forward/back traversal should be blocked."""
        with pytest.raises(PathTraversalError):
            safe_join(tmp_path, "valid/../../../secrets")

    def test_current_dir_dots_allowed(self, tmp_path: Path) -> None:
        """Single dots (current dir) should be allowed if result is valid."""
        result = safe_join(tmp_path, "./data/./file.csv")
        assert result.is_relative_to(tmp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
