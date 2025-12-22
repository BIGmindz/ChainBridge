"""
Tests for proofpacks_api path security (CodeQL py/path-injection mitigation).

ATLAS (GID-11) — PR #18 security hardening.
"""

import pytest

from src.api.proofpacks_api import _RUNTIME_BASE, _safe_pack_path


class TestSafePackPath:
    """Test _safe_pack_path prevents path traversal attacks."""

    def test_valid_uuid_returns_path(self):
        """Valid UUID format should return a resolved path under RUNTIME_BASE."""
        pack_id = "12345678-1234-5678-1234-567812345678"
        result = _safe_pack_path(pack_id)
        assert result.name == f"{pack_id}.json"
        # Verify it's under the base
        result.relative_to(_RUNTIME_BASE)

    def test_rejects_traversal_dots(self):
        """Reject path traversal via ../ sequences."""
        with pytest.raises(ValueError, match="Invalid pack_id format"):
            _safe_pack_path("../../../etc/passwd")

    def test_rejects_absolute_path(self):
        """Reject absolute paths disguised as pack_id."""
        with pytest.raises(ValueError, match="Invalid pack_id format"):
            _safe_pack_path("/etc/passwd")

    def test_rejects_non_uuid_format(self):
        """Reject pack_id that doesn't match UUID pattern."""
        with pytest.raises(ValueError, match="Invalid pack_id format"):
            _safe_pack_path("not-a-valid-uuid")

    def test_rejects_empty_string(self):
        """Reject empty string."""
        with pytest.raises(ValueError, match="Invalid pack_id format"):
            _safe_pack_path("")

    def test_rejects_uuid_with_traversal_suffix(self):
        """Reject UUID with traversal appended."""
        with pytest.raises(ValueError, match="Invalid pack_id format"):
            _safe_pack_path("12345678-1234-5678-1234-567812345678/../foo")

    def test_accepts_uppercase_uuid(self):
        """Accept uppercase UUID (case insensitive)."""
        pack_id = "ABCDEF12-1234-5678-1234-567812345678"
        result = _safe_pack_path(pack_id)
        assert result.name == f"{pack_id}.json"
