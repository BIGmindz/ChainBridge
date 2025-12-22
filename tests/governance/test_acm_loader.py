"""Tests for ACM Loader — Task 1 of PAC-ACM-02."""

from pathlib import Path

import pytest

from core.governance.acm_loader import ACM, ACMCapabilities, ACMLoader, ACMLoadError, ACMValidationError


class TestACMLoaderBasics:
    """Test basic ACM loading functionality."""

    def test_load_all_from_real_manifests(self, manifests_dir):
        """Test loading real ACM manifests from the repository."""
        loader = ACMLoader(manifests_dir)
        acms = loader.load_all()

        # Should load all 6 agents (including Diggy as correction authority)
        assert len(acms) == 6
        assert "GID-00" in acms  # Diggy (correction authority)
        assert "GID-01" in acms  # Cody
        assert "GID-02" in acms  # Sonny
        assert "GID-06" in acms  # Sam
        assert "GID-07" in acms  # Dan
        assert "GID-08" in acms  # ALEX

    def test_acm_immutability(self, manifests_dir):
        """Test that loaded ACMs are immutable."""
        loader = ACMLoader(manifests_dir)
        acms = loader.load_all()

        acm = acms["GID-01"]

        # ACM should be frozen dataclass
        with pytest.raises(Exception):  # FrozenInstanceError
            acm.agent_id = "Modified"  # type: ignore

    def test_version_validation(self, manifests_dir):
        """Test that all ACMs have valid semantic versions."""
        loader = ACMLoader(manifests_dir)
        acms = loader.load_all()

        for gid, acm in acms.items():
            parts = acm.version.split(".")
            assert len(parts) == 3, f"{gid} has invalid version: {acm.version}"
            assert all(p.isdigit() for p in parts)

    def test_governance_lock_present(self, manifests_dir):
        """Test that all manifests have governance lock marker."""
        loader = ACMLoader(manifests_dir)
        acms = loader.load_all()

        # If we got here, all manifests have the lock marker
        assert len(acms) > 0


class TestACMLoaderFailClosed:
    """Test fail-closed behavior of ACM loader."""

    def test_missing_directory_fails(self, tmp_path):
        """Test that missing manifests directory causes hard failure."""
        loader = ACMLoader(tmp_path / "nonexistent")

        with pytest.raises(ACMLoadError) as exc_info:
            loader.load_all()

        assert "not found" in str(exc_info.value).lower()

    def test_empty_directory_fails(self, tmp_path):
        """Test that empty manifests directory causes hard failure."""
        empty_dir = tmp_path / "empty_manifests"
        empty_dir.mkdir()
        loader = ACMLoader(empty_dir)

        with pytest.raises(ACMLoadError) as exc_info:
            loader.load_all()

        assert "No ACM manifests found" in str(exc_info.value)

    def test_missing_governance_lock_fails(self, temp_manifests_dir):
        """Test that manifest without governance lock fails validation."""
        content = """
agent_id: "Test"
gid: "GID-99"
role: "Test Agent"
color: "Test"
version: "1.0.0"

capabilities:
  read: []
  propose: []
  execute: []
  block: []
  escalate: []
"""
        (temp_manifests_dir / "GID-99_Test.yaml").write_text(content)
        loader = ACMLoader(temp_manifests_dir)

        with pytest.raises(ACMValidationError) as exc_info:
            loader.load_all()

        assert "governance lock" in str(exc_info.value).lower()

    def test_missing_required_fields_fails(self, temp_manifests_dir):
        """Test that manifest missing required fields fails validation."""
        content = """
agent_id: "Test"
gid: "GID-99"
# Missing: role, color, version, capabilities

# END OF ACM — GOVERNANCE LOCKED
"""
        (temp_manifests_dir / "GID-99_Test.yaml").write_text(content)
        loader = ACMLoader(temp_manifests_dir)

        with pytest.raises(ACMValidationError) as exc_info:
            loader.load_all()

        assert "Missing required fields" in str(exc_info.value)

    def test_invalid_version_format_fails(self, temp_manifests_dir):
        """Test that invalid version format fails validation."""
        content = """
agent_id: "Test"
gid: "GID-99"
role: "Test Agent"
color: "Test"
version: "invalid"

capabilities:
  read: []
  propose: []
  execute: []
  block: []
  escalate: []

# END OF ACM — GOVERNANCE LOCKED
"""
        (temp_manifests_dir / "GID-99_Test.yaml").write_text(content)
        loader = ACMLoader(temp_manifests_dir)

        with pytest.raises(ACMValidationError) as exc_info:
            loader.load_all()

        assert "version" in str(exc_info.value).lower()


class TestACMCapabilityMatching:
    """Test ACM capability matching logic."""

    def test_exact_match(self):
        """Test exact capability matching."""
        caps = ACMCapabilities(read=frozenset(["backend source code"]))
        acm = ACM(
            agent_id="Test",
            gid="GID-99",
            role="Test",
            color="Test",
            version="1.0.0",
            constraints=frozenset(),
            capabilities=caps,
            escalation_triggers=frozenset(),
            invariants=frozenset(),
        )

        assert acm.has_capability("READ", "backend source code")
        assert not acm.has_capability("READ", "frontend source code")

    def test_all_keyword_match(self):
        """Test 'all' keyword grants universal access."""
        caps = ACMCapabilities(read=frozenset(["all source code (security audit)"]))
        acm = ACM(
            agent_id="Test",
            gid="GID-99",
            role="Test",
            color="Test",
            version="1.0.0",
            constraints=frozenset(),
            capabilities=caps,
            escalation_triggers=frozenset(),
            invariants=frozenset(),
        )

        # "all" at the start should match anything
        assert acm.has_capability("READ", "any target")
        assert acm.has_capability("READ", "backend.tests")

    def test_partial_word_match(self):
        """Test partial word matching in scope."""
        caps = ACMCapabilities(execute=frozenset(["local test runs"]))
        acm = ACM(
            agent_id="Test",
            gid="GID-99",
            role="Test",
            color="Test",
            version="1.0.0",
            constraints=frozenset(),
            capabilities=caps,
            escalation_triggers=frozenset(),
            invariants=frozenset(),
        )

        # "test" word should match targets containing "test"
        assert acm.has_capability("EXECUTE", "test")
        assert acm.has_capability("EXECUTE", "pytest")

    def test_empty_capability_denies_all(self):
        """Test that empty capability set denies all targets."""
        caps = ACMCapabilities(execute=frozenset())
        acm = ACM(
            agent_id="Test",
            gid="GID-99",
            role="Test",
            color="Test",
            version="1.0.0",
            constraints=frozenset(),
            capabilities=caps,
            escalation_triggers=frozenset(),
            invariants=frozenset(),
        )

        assert not acm.has_capability("EXECUTE", "anything")
        assert not acm.has_capability("EXECUTE", "local test runs")

    def test_can_block_authority(self, manifests_dir):
        """Test can_block() returns True only for Sam and ALEX."""
        loader = ACMLoader(manifests_dir)
        acms = loader.load_all()

        # Sam (GID-06) has BLOCK authority
        assert acms["GID-06"].can_block()

        # ALEX (GID-08) has BLOCK authority
        assert acms["GID-08"].can_block()

        # Cody (GID-01) does NOT have BLOCK authority
        assert not acms["GID-01"].can_block()

        # Sonny (GID-02) does NOT have BLOCK authority
        assert not acms["GID-02"].can_block()

        # Dan (GID-07) does NOT have BLOCK authority
        assert not acms["GID-07"].can_block()


class TestACMLoaderCaching:
    """Test ACM loader caching behavior."""

    def test_get_returns_cached_acm(self, manifests_dir):
        """Test that get() returns cached ACM after load_all()."""
        loader = ACMLoader(manifests_dir)

        # First call triggers load
        acm1 = loader.get("GID-01")
        assert acm1 is not None

        # Second call returns cached
        acm2 = loader.get("GID-01")
        assert acm1 is acm2  # Same object

    def test_get_unknown_returns_none(self, manifests_dir):
        """Test that get() returns None for unknown GID."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()

        assert loader.get("GID-99") is None

    def test_is_loaded_flag(self, manifests_dir):
        """Test is_loaded() returns correct state."""
        loader = ACMLoader(manifests_dir)

        assert not loader.is_loaded()

        loader.load_all()

        assert loader.is_loaded()
