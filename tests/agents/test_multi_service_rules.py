"""
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
ALEX — GID-08 — GOVERNANCE ENGINE
PAC-ALEX-NEXT-023: Multi-Service Compliance Alignment
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪

Multi-Service Compliance Rules Tests
Governs PAC compliance across:
- ChainPay
- ChainIQ
- chainboard-ui
- /scripts
- Root-level AGENTS
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest

# =============================================================================
# SERVICE OWNERSHIP REGISTRY
# =============================================================================

SERVICE_OWNERSHIP: Dict[str, Dict] = {
    "chainpay-service": {
        "primary_owner": "PAX",
        "gid": "GID-10",
        "allowed_agents": ["PAX", "CODY", "SAM", "ALEX"],
        "pac_prefix": "PAC-PAX",
        "description": "CB-USDx tokenization, settlement, payment rails",
    },
    "chainiq-service": {
        "primary_owner": "MAGGIE",
        "gid": "GID-02",
        "allowed_agents": ["MAGGIE", "CODY", "SAM", "ALEX"],
        "pac_prefix": "PAC-MAGGIE",
        "description": "ML risk scoring, feature forensics, glass-box models",
    },
    "chainboard-ui": {
        "primary_owner": "SONNY",
        "gid": "GID-03",
        "allowed_agents": ["SONNY", "LIRA", "ALEX"],
        "pac_prefix": "PAC-SONNY",
        "description": "React/TypeScript dashboard, UI components",
    },
    "scripts": {
        "primary_owner": "DAN",
        "gid": "GID-04",
        "allowed_agents": ["DAN", "SAM", "ALEX", "CODY"],
        "pac_prefix": "PAC-DAN",
        "description": "DevOps scripts, CI/CD utilities, automation",
    },
    "modules": {
        "primary_owner": "CODY",
        "gid": "GID-01",
        "allowed_agents": ["CODY", "MAGGIE", "ALEX"],
        "pac_prefix": "PAC-CODY",
        "description": "Trading modules, signal aggregation",
    },
    "docs/governance": {
        "primary_owner": "ALEX",
        "gid": "GID-08",
        "allowed_agents": ["ALEX"],
        "pac_prefix": "PAC-ALEX",
        "description": "Governance documentation, rules, policies",
    },
    "docs/product": {
        "primary_owner": "ATLAS",
        "gid": "GID-05",
        "allowed_agents": ["ATLAS", "ALEX"],
        "pac_prefix": "PAC-ATLAS",
        "description": "Product documentation, agent registry",
    },
    ".github": {
        "primary_owner": "ALEX",
        "gid": "GID-08",
        "allowed_agents": ["ALEX", "DAN"],
        "pac_prefix": "PAC-ALEX",
        "description": "CI/CD workflows, governance rules",
    },
}

# Root-level agents with global access
ROOT_LEVEL_AGENTS = ["ALEX", "SAM", "DAN"]


# =============================================================================
# MULTI-SERVICE VALIDATION FUNCTIONS
# =============================================================================


def get_service_for_path(filepath: str) -> Tuple[str, Dict]:
    """
    Determine which service owns a given filepath.
    Returns (service_name, service_config) or (None, {}).
    """
    filepath = filepath.replace("\\", "/")

    # Check specific service paths
    for service, config in SERVICE_OWNERSHIP.items():
        if filepath.startswith(service) or f"/{service}/" in filepath:
            return service, config

    return None, {}


def validate_agent_authorization(filepath: str, agent_name: str) -> List[str]:
    """
    Validates if an agent is authorized to modify a service path.
    Returns list of violations.
    """
    violations = []

    service, config = get_service_for_path(filepath)

    if not service:
        return []  # No specific ownership rules

    agent_upper = agent_name.upper()

    # Root-level agents have global access
    if agent_upper in ROOT_LEVEL_AGENTS:
        return []

    if agent_upper not in config.get("allowed_agents", []):
        violations.append(f"Agent {agent_upper} is not authorized to modify {service}. " f"Allowed: {config['allowed_agents']}")

    return violations


def validate_pac_prefix_for_service(filepath: str, pac_id: str) -> List[str]:
    """
    Validates PAC ID prefix matches service ownership.
    Returns list of violations.
    """
    violations = []

    service, config = get_service_for_path(filepath)

    if not service or not config:
        return []

    expected_prefix = config.get("pac_prefix")

    if expected_prefix and not pac_id.upper().startswith(expected_prefix):
        # Allow ALEX governance PACs anywhere
        if pac_id.upper().startswith("PAC-ALEX"):
            return []
        violations.append(f"PAC {pac_id} in {service} should use prefix {expected_prefix}")

    return violations


def get_all_service_files(base_path: str = ".") -> Dict[str, List[str]]:
    """
    Scans workspace and groups files by service.
    """
    base = Path(base_path)
    service_files: Dict[str, List[str]] = {svc: [] for svc in SERVICE_OWNERSHIP.keys()}
    service_files["unassigned"] = []

    for filepath in base.rglob("*"):
        if filepath.is_file():
            rel_path = str(filepath.relative_to(base))
            service, _ = get_service_for_path(rel_path)

            if service:
                service_files[service].append(rel_path)
            else:
                service_files["unassigned"].append(rel_path)

    return service_files


# =============================================================================
# PYTEST TEST CASES
# =============================================================================


class TestServiceOwnership:
    """Test service path ownership detection."""

    def test_chainpay_path_detection(self):
        service, config = get_service_for_path("chainpay-service/app/main.py")
        assert service == "chainpay-service"
        assert config["primary_owner"] == "PAX"

    def test_chainiq_path_detection(self):
        service, config = get_service_for_path("chainiq-service/app/ml/feature_forensics.py")
        assert service == "chainiq-service"
        assert config["primary_owner"] == "MAGGIE"

    def test_chainboard_path_detection(self):
        service, config = get_service_for_path("chainboard-ui/src/components/Dashboard.tsx")
        assert service == "chainboard-ui"
        assert config["primary_owner"] == "SONNY"

    def test_scripts_path_detection(self):
        service, config = get_service_for_path("scripts/dev/run_api_gateway.sh")
        assert service == "scripts"
        assert config["primary_owner"] == "DAN"

    def test_governance_docs_path_detection(self):
        service, config = get_service_for_path("docs/governance/ALEX_RULES.md")
        assert service == "docs/governance"
        assert config["primary_owner"] == "ALEX"

    def test_github_path_detection(self):
        service, config = get_service_for_path(".github/workflows/ci.yml")
        assert service == ".github"
        assert config["primary_owner"] == "ALEX"


class TestAgentAuthorization:
    """Test agent authorization for service modifications."""

    # ChainPay authorization tests
    def test_pax_authorized_for_chainpay(self):
        violations = validate_agent_authorization("chainpay-service/app/main.py", "PAX")
        assert len(violations) == 0

    def test_cody_authorized_for_chainpay(self):
        violations = validate_agent_authorization("chainpay-service/app/main.py", "CODY")
        assert len(violations) == 0

    def test_sonny_unauthorized_for_chainpay(self):
        violations = validate_agent_authorization("chainpay-service/app/main.py", "SONNY")
        assert len(violations) > 0
        assert "not authorized" in violations[0]

    # ChainIQ authorization tests
    def test_maggie_authorized_for_chainiq(self):
        violations = validate_agent_authorization("chainiq-service/app/ml/model.py", "MAGGIE")
        assert len(violations) == 0

    def test_lira_unauthorized_for_chainiq(self):
        violations = validate_agent_authorization("chainiq-service/app/ml/model.py", "LIRA")
        assert len(violations) > 0

    # ChainBoard authorization tests
    def test_sonny_authorized_for_chainboard(self):
        violations = validate_agent_authorization("chainboard-ui/src/App.tsx", "SONNY")
        assert len(violations) == 0

    def test_lira_authorized_for_chainboard(self):
        violations = validate_agent_authorization("chainboard-ui/src/App.tsx", "LIRA")
        assert len(violations) == 0

    def test_maggie_unauthorized_for_chainboard(self):
        violations = validate_agent_authorization("chainboard-ui/src/App.tsx", "MAGGIE")
        assert len(violations) > 0

    # Root-level agent tests
    def test_alex_has_global_access(self):
        for service in SERVICE_OWNERSHIP.keys():
            violations = validate_agent_authorization(f"{service}/file.py", "ALEX")
            assert len(violations) == 0, f"ALEX should have access to {service}"

    def test_sam_has_global_access(self):
        for service in SERVICE_OWNERSHIP.keys():
            violations = validate_agent_authorization(f"{service}/file.py", "SAM")
            assert len(violations) == 0, f"SAM should have access to {service}"

    def test_dan_has_global_access(self):
        for service in SERVICE_OWNERSHIP.keys():
            violations = validate_agent_authorization(f"{service}/file.py", "DAN")
            assert len(violations) == 0, f"DAN should have access to {service}"


class TestPACPrefixValidation:
    """Test PAC ID prefix matches service."""

    def test_pax_pac_in_chainpay(self):
        violations = validate_pac_prefix_for_service("chainpay-service/app/main.py", "PAC-PAX-001")
        assert len(violations) == 0

    def test_maggie_pac_in_chainiq(self):
        violations = validate_pac_prefix_for_service("chainiq-service/app/model.py", "PAC-MAGGIE-A")
        assert len(violations) == 0

    def test_wrong_pac_prefix_in_service(self):
        violations = validate_pac_prefix_for_service("chainpay-service/app/main.py", "PAC-SONNY-001")
        assert len(violations) > 0
        assert "should use prefix PAC-PAX" in violations[0]

    def test_alex_pac_allowed_everywhere(self):
        # ALEX governance PACs should be allowed in any service
        for service in SERVICE_OWNERSHIP.keys():
            violations = validate_pac_prefix_for_service(f"{service}/file.py", "PAC-ALEX-GOV-001")
            assert len(violations) == 0, f"ALEX PAC should be allowed in {service}"


class TestServiceOwnershipRegistry:
    """Test service ownership registry integrity."""

    def test_all_services_have_primary_owner(self):
        for service, config in SERVICE_OWNERSHIP.items():
            assert "primary_owner" in config, f"{service} missing primary_owner"

    def test_all_services_have_gid(self):
        for service, config in SERVICE_OWNERSHIP.items():
            assert "gid" in config, f"{service} missing GID"
            assert config["gid"].startswith("GID-"), f"{service} has invalid GID format"

    def test_all_services_have_allowed_agents(self):
        for service, config in SERVICE_OWNERSHIP.items():
            assert "allowed_agents" in config, f"{service} missing allowed_agents"
            assert len(config["allowed_agents"]) > 0, f"{service} has empty allowed_agents"

    def test_primary_owner_in_allowed_agents(self):
        for service, config in SERVICE_OWNERSHIP.items():
            owner = config["primary_owner"]
            allowed = config["allowed_agents"]
            assert owner in allowed, f"{service}: primary_owner {owner} not in allowed_agents"


class TestCrossServiceCompliance:
    """Test cross-service compliance scenarios."""

    def test_shared_components_authorization(self):
        """Components in modules/ should be accessible to CODY and MAGGIE."""
        violations_cody = validate_agent_authorization("modules/risk_engine.py", "CODY")
        violations_maggie = validate_agent_authorization("modules/risk_engine.py", "MAGGIE")

        assert len(violations_cody) == 0
        assert len(violations_maggie) == 0

    def test_security_agent_has_full_access(self):
        """SAM (Security) must have access to all services."""
        critical_paths = [
            "chainpay-service/app/settlement.py",
            "chainiq-service/app/ml/model.py",
            ".github/workflows/ci.yml",
        ]

        for path in critical_paths:
            violations = validate_agent_authorization(path, "SAM")
            assert len(violations) == 0, f"SAM must have access to {path}"

    def test_governance_agent_has_full_access(self):
        """ALEX (Governance) must have access to all services."""
        critical_paths = [
            "chainpay-service/app/settlement.py",
            "chainiq-service/app/ml/model.py",
            "chainboard-ui/src/App.tsx",
            "scripts/deploy.sh",
        ]

        for path in critical_paths:
            violations = validate_agent_authorization(path, "ALEX")
            assert len(violations) == 0, f"ALEX must have access to {path}"


# =============================================================================
# FOOTER
# ⚪ ALEX — GID-08 — GOVERNANCE ENGINE
# Ensuring absolute alignment.
# ⚪⚪⚪ END OF PAC ⚪⚪⚪
# =============================================================================
