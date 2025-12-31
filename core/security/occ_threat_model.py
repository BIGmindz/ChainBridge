# ═══════════════════════════════════════════════════════════════════════════════
# OCC Threat Model — UI Attack Surface Audit
# PAC-BENSON-P25: PARALLEL PLATFORM EXPANSION & OPERATOR-GRADE EXECUTION
# Agent: SAM (GID-06) — Security & Threat
# ═══════════════════════════════════════════════════════════════════════════════

"""
OCC Threat Model — Enterprise Security Analysis

PURPOSE:
    Define and validate threat model for OCC UI and control plane interfaces.
    Enumerate attack vectors, mitigations, and security invariants.

THREAT CATEGORIES:
    1. UI INJECTION — XSS, template injection, DOM manipulation
    2. STATE MANIPULATION — Client-side state tampering
    3. API ABUSE — Rate limiting bypass, authorization bypass
    4. DATA EXFILTRATION — Unauthorized data access, leakage
    5. PRIVILEGE ESCALATION — Role bypass, admin impersonation

SECURITY INVARIANTS:
    INV-SEC-UI-001: All user input must be sanitized before display
    INV-SEC-UI-002: No client-side mutation of control plane state
    INV-SEC-UI-003: All API calls require authentication
    INV-SEC-UI-004: Rate limiting enforced on all endpoints
    INV-SEC-UI-005: Audit logging for all security-relevant actions

EXECUTION MODE: PARALLEL
LANE: SECURITY (GID-06)
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


# ═══════════════════════════════════════════════════════════════════════════════
# THREAT CLASSIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════


class ThreatCategory(Enum):
    """STRIDE-aligned threat categories."""

    SPOOFING = "SPOOFING"  # Identity spoofing
    TAMPERING = "TAMPERING"  # Data/state tampering
    REPUDIATION = "REPUDIATION"  # Deniability attacks
    INFORMATION_DISCLOSURE = "INFORMATION_DISCLOSURE"  # Data leakage
    DENIAL_OF_SERVICE = "DENIAL_OF_SERVICE"  # Availability attacks
    ELEVATION_OF_PRIVILEGE = "ELEVATION_OF_PRIVILEGE"  # Auth bypass


class ThreatSeverity(Enum):
    """CVSS-aligned severity levels."""

    CRITICAL = "CRITICAL"  # CVSS 9.0-10.0
    HIGH = "HIGH"  # CVSS 7.0-8.9
    MEDIUM = "MEDIUM"  # CVSS 4.0-6.9
    LOW = "LOW"  # CVSS 0.1-3.9
    INFORMATIONAL = "INFORMATIONAL"  # CVSS 0.0


class MitigationStatus(Enum):
    """Mitigation implementation status."""

    IMPLEMENTED = "IMPLEMENTED"
    PARTIAL = "PARTIAL"
    PLANNED = "PLANNED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AttackSurface(Enum):
    """Attack surface areas."""

    OCC_UI = "OCC_UI"  # OCC Dashboard UI
    API_GATEWAY = "API_GATEWAY"  # API Gateway endpoints
    CONTROL_PLANE = "CONTROL_PLANE"  # Control plane services
    DATA_STORE = "DATA_STORE"  # Database/storage
    NETWORK = "NETWORK"  # Network layer
    CLIENT = "CLIENT"  # Client-side browser


# ═══════════════════════════════════════════════════════════════════════════════
# THREAT DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ThreatVector:
    """Individual threat vector definition."""

    vector_id: str
    name: str
    description: str
    category: ThreatCategory
    severity: ThreatSeverity
    attack_surface: AttackSurface
    attack_complexity: str  # LOW, MEDIUM, HIGH
    prerequisites: tuple[str, ...]
    impact: str
    likelihood: str  # LOW, MEDIUM, HIGH


@dataclass(frozen=True)
class Mitigation:
    """Mitigation control definition."""

    mitigation_id: str
    name: str
    description: str
    implementation: str
    status: MitigationStatus
    validates_invariant: Optional[str] = None


@dataclass
class ThreatAssessment:
    """Assessment of a threat with mitigations."""

    vector: ThreatVector
    mitigations: List[Mitigation]
    residual_risk: str  # LOW, MEDIUM, HIGH, ACCEPTED
    assessment_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    assessor: str = "SAM (GID-06)"
    notes: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# OCC UI THREAT VECTORS
# ═══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# INJECTION THREATS
# ─────────────────────────────────────────────────────────────────────────────

THREAT_UI_XSS_001 = ThreatVector(
    vector_id="THREAT-UI-XSS-001",
    name="Stored XSS in Decision Cards",
    description=(
        "Attacker injects malicious JavaScript into agent decision summaries "
        "which gets rendered in OCC dashboard without sanitization."
    ),
    category=ThreatCategory.TAMPERING,
    severity=ThreatSeverity.HIGH,
    attack_surface=AttackSurface.OCC_UI,
    attack_complexity="MEDIUM",
    prerequisites=("Ability to submit content to decision stream",),
    impact="Session hijacking, credential theft, UI defacement",
    likelihood="MEDIUM",
)

THREAT_UI_XSS_002 = ThreatVector(
    vector_id="THREAT-UI-XSS-002",
    name="Reflected XSS via URL Parameters",
    description=(
        "Attacker crafts malicious URL with script in query parameters "
        "that executes when operator clicks link."
    ),
    category=ThreatCategory.TAMPERING,
    severity=ThreatSeverity.MEDIUM,
    attack_surface=AttackSurface.OCC_UI,
    attack_complexity="LOW",
    prerequisites=("Social engineering to get operator to click link",),
    impact="Session hijacking, phishing",
    likelihood="LOW",
)

THREAT_UI_TEMPLATE_001 = ThreatVector(
    vector_id="THREAT-UI-TEMPLATE-001",
    name="Template Injection in Error Messages",
    description=(
        "Error messages containing user-controlled content are rendered "
        "through template engine without escaping."
    ),
    category=ThreatCategory.TAMPERING,
    severity=ThreatSeverity.MEDIUM,
    attack_surface=AttackSurface.OCC_UI,
    attack_complexity="MEDIUM",
    prerequisites=("Ability to trigger specific errors",),
    impact="Information disclosure, potential RCE",
    likelihood="LOW",
)

# ─────────────────────────────────────────────────────────────────────────────
# STATE MANIPULATION THREATS
# ─────────────────────────────────────────────────────────────────────────────

THREAT_STATE_001 = ThreatVector(
    vector_id="THREAT-STATE-001",
    name="Client-Side State Tampering",
    description=(
        "Attacker uses browser developer tools to modify React state "
        "to display false information or bypass UI controls."
    ),
    category=ThreatCategory.TAMPERING,
    severity=ThreatSeverity.LOW,
    attack_surface=AttackSurface.CLIENT,
    attack_complexity="LOW",
    prerequisites=("Access to browser developer tools",),
    impact="Misleading UI display (no backend impact)",
    likelihood="MEDIUM",
)

THREAT_STATE_002 = ThreatVector(
    vector_id="THREAT-STATE-002",
    name="LocalStorage Token Theft",
    description=(
        "Attacker extracts authentication tokens from localStorage/sessionStorage "
        "via XSS or physical access."
    ),
    category=ThreatCategory.INFORMATION_DISCLOSURE,
    severity=ThreatSeverity.HIGH,
    attack_surface=AttackSurface.CLIENT,
    attack_complexity="MEDIUM",
    prerequisites=("XSS vulnerability or physical access",),
    impact="Session hijacking, impersonation",
    likelihood="MEDIUM",
)

# ─────────────────────────────────────────────────────────────────────────────
# API ABUSE THREATS
# ─────────────────────────────────────────────────────────────────────────────

THREAT_API_001 = ThreatVector(
    vector_id="THREAT-API-001",
    name="Rate Limit Bypass via Header Spoofing",
    description=(
        "Attacker bypasses rate limiting by spoofing X-Forwarded-For "
        "or other headers to appear as different clients."
    ),
    category=ThreatCategory.DENIAL_OF_SERVICE,
    severity=ThreatSeverity.MEDIUM,
    attack_surface=AttackSurface.API_GATEWAY,
    attack_complexity="LOW",
    prerequisites=("No trusted proxy configuration",),
    impact="API exhaustion, DoS",
    likelihood="MEDIUM",
)

THREAT_API_002 = ThreatVector(
    vector_id="THREAT-API-002",
    name="BOLA/IDOR on OCC Endpoints",
    description=(
        "Attacker accesses other operators' data by manipulating "
        "resource IDs in API requests."
    ),
    category=ThreatCategory.INFORMATION_DISCLOSURE,
    severity=ThreatSeverity.HIGH,
    attack_surface=AttackSurface.API_GATEWAY,
    attack_complexity="LOW",
    prerequisites=("Valid authentication",),
    impact="Unauthorized data access",
    likelihood="MEDIUM",
)

THREAT_API_003 = ThreatVector(
    vector_id="THREAT-API-003",
    name="Mass Assignment on SOP Parameters",
    description=(
        "Attacker includes additional fields in SOP execution requests "
        "that get bound to internal parameters."
    ),
    category=ThreatCategory.ELEVATION_OF_PRIVILEGE,
    severity=ThreatSeverity.HIGH,
    attack_surface=AttackSurface.API_GATEWAY,
    attack_complexity="MEDIUM",
    prerequisites=("Knowledge of internal field names",),
    impact="Privilege escalation, data corruption",
    likelihood="LOW",
)

# ─────────────────────────────────────────────────────────────────────────────
# PRIVILEGE ESCALATION THREATS
# ─────────────────────────────────────────────────────────────────────────────

THREAT_PRIV_001 = ThreatVector(
    vector_id="THREAT-PRIV-001",
    name="Role Confusion via JWT Claims",
    description=(
        "Attacker modifies JWT claims to impersonate higher-privileged "
        "roles without proper signature validation."
    ),
    category=ThreatCategory.SPOOFING,
    severity=ThreatSeverity.CRITICAL,
    attack_surface=AttackSurface.API_GATEWAY,
    attack_complexity="MEDIUM",
    prerequisites=("Weak JWT validation",),
    impact="Full admin access",
    likelihood="LOW",
)

THREAT_PRIV_002 = ThreatVector(
    vector_id="THREAT-PRIV-002",
    name="Horizontal Privilege Escalation",
    description=(
        "Operator A accesses Operator B's organization data "
        "by manipulating organization ID parameters."
    ),
    category=ThreatCategory.ELEVATION_OF_PRIVILEGE,
    severity=ThreatSeverity.HIGH,
    attack_surface=AttackSurface.CONTROL_PLANE,
    attack_complexity="LOW",
    prerequisites=("Multi-tenant deployment",),
    impact="Cross-tenant data access",
    likelihood="MEDIUM",
)

# ═══════════════════════════════════════════════════════════════════════════════
# MITIGATIONS
# ═══════════════════════════════════════════════════════════════════════════════

MIT_XSS_001 = Mitigation(
    mitigation_id="MIT-XSS-001",
    name="React Auto-Escaping",
    description="React's JSX automatically escapes embedded values",
    implementation="Use React JSX for all dynamic content rendering",
    status=MitigationStatus.IMPLEMENTED,
    validates_invariant="INV-SEC-UI-001",
)

MIT_XSS_002 = Mitigation(
    mitigation_id="MIT-XSS-002",
    name="Content Security Policy",
    description="Strict CSP headers prevent inline script execution",
    implementation="CSP: default-src 'self'; script-src 'self'",
    status=MitigationStatus.IMPLEMENTED,
    validates_invariant="INV-SEC-UI-001",
)

MIT_XSS_003 = Mitigation(
    mitigation_id="MIT-XSS-003",
    name="Input Validation on Backend",
    description="All input sanitized before storage",
    implementation="Pydantic models with validators, HTML escaping",
    status=MitigationStatus.IMPLEMENTED,
    validates_invariant="INV-SEC-UI-001",
)

MIT_STATE_001 = Mitigation(
    mitigation_id="MIT-STATE-001",
    name="Read-Only OCC Invariant",
    description="OCC UI cannot trigger mutations, enforced by API",
    implementation="INV-OCC-001 enforced at API layer",
    status=MitigationStatus.IMPLEMENTED,
    validates_invariant="INV-SEC-UI-002",
)

MIT_STATE_002 = Mitigation(
    mitigation_id="MIT-STATE-002",
    name="HttpOnly Cookies for Tokens",
    description="Authentication tokens in HttpOnly cookies",
    implementation="Set-Cookie: HttpOnly; Secure; SameSite=Strict",
    status=MitigationStatus.IMPLEMENTED,
    validates_invariant="INV-SEC-UI-003",
)

MIT_API_001 = Mitigation(
    mitigation_id="MIT-API-001",
    name="Trusted Proxy Configuration",
    description="Rate limiting based on real client IP",
    implementation="Configure X-Real-IP from load balancer only",
    status=MitigationStatus.IMPLEMENTED,
    validates_invariant="INV-SEC-UI-004",
)

MIT_API_002 = Mitigation(
    mitigation_id="MIT-API-002",
    name="Resource-Level Authorization",
    description="Every API call validates resource ownership",
    implementation="Authorization middleware checks org_id claim",
    status=MitigationStatus.IMPLEMENTED,
    validates_invariant="INV-SEC-UI-003",
)

MIT_API_003 = Mitigation(
    mitigation_id="MIT-API-003",
    name="Explicit Field Allow-Lists",
    description="Pydantic models define exact allowed fields",
    implementation="Use Pydantic with extra='forbid'",
    status=MitigationStatus.IMPLEMENTED,
    validates_invariant="INV-SEC-UI-002",
)

MIT_PRIV_001 = Mitigation(
    mitigation_id="MIT-PRIV-001",
    name="JWT Signature Validation",
    description="All JWTs validated against known signing keys",
    implementation="RS256 with key rotation, signature verification",
    status=MitigationStatus.IMPLEMENTED,
    validates_invariant="INV-SEC-UI-003",
)

MIT_PRIV_002 = Mitigation(
    mitigation_id="MIT-PRIV-002",
    name="Tenant Isolation Middleware",
    description="All queries scoped to authenticated tenant",
    implementation="Automatic tenant_id injection in queries",
    status=MitigationStatus.IMPLEMENTED,
    validates_invariant="INV-SEC-UI-003",
)

MIT_AUDIT_001 = Mitigation(
    mitigation_id="MIT-AUDIT-001",
    name="Comprehensive Audit Logging",
    description="All security-relevant actions logged",
    implementation="SecurityAuditLog captures all operations",
    status=MitigationStatus.IMPLEMENTED,
    validates_invariant="INV-SEC-UI-005",
)


# ═══════════════════════════════════════════════════════════════════════════════
# THREAT MODEL REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════


class ThreatModelRegistry:
    """
    Registry for threat vectors and their assessments.

    Provides methods to query threats by category, severity,
    attack surface, and mitigation status.
    """

    _instance: Optional["ThreatModelRegistry"] = None
    _initialized: bool = False

    def __new__(cls) -> "ThreatModelRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if ThreatModelRegistry._initialized:
            return
        ThreatModelRegistry._initialized = True

        self._threats: Dict[str, ThreatVector] = {}
        self._mitigations: Dict[str, Mitigation] = {}
        self._assessments: Dict[str, ThreatAssessment] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register all default threats and mitigations."""
        # Register threats
        threats = [
            THREAT_UI_XSS_001,
            THREAT_UI_XSS_002,
            THREAT_UI_TEMPLATE_001,
            THREAT_STATE_001,
            THREAT_STATE_002,
            THREAT_API_001,
            THREAT_API_002,
            THREAT_API_003,
            THREAT_PRIV_001,
            THREAT_PRIV_002,
        ]
        for threat in threats:
            self._threats[threat.vector_id] = threat

        # Register mitigations
        mitigations = [
            MIT_XSS_001,
            MIT_XSS_002,
            MIT_XSS_003,
            MIT_STATE_001,
            MIT_STATE_002,
            MIT_API_001,
            MIT_API_002,
            MIT_API_003,
            MIT_PRIV_001,
            MIT_PRIV_002,
            MIT_AUDIT_001,
        ]
        for mit in mitigations:
            self._mitigations[mit.mitigation_id] = mit

        # Create assessments
        self._create_default_assessments()

    def _create_default_assessments(self) -> None:
        """Create default threat assessments with mitigations."""
        # XSS-001 Assessment
        self._assessments["THREAT-UI-XSS-001"] = ThreatAssessment(
            vector=THREAT_UI_XSS_001,
            mitigations=[MIT_XSS_001, MIT_XSS_002, MIT_XSS_003],
            residual_risk="LOW",
            notes="React auto-escaping + CSP provides strong defense",
        )

        # XSS-002 Assessment
        self._assessments["THREAT-UI-XSS-002"] = ThreatAssessment(
            vector=THREAT_UI_XSS_002,
            mitigations=[MIT_XSS_002],
            residual_risk="LOW",
            notes="CSP blocks inline scripts from URL params",
        )

        # Template-001 Assessment
        self._assessments["THREAT-UI-TEMPLATE-001"] = ThreatAssessment(
            vector=THREAT_UI_TEMPLATE_001,
            mitigations=[MIT_XSS_001, MIT_XSS_003],
            residual_risk="LOW",
            notes="No server-side templates used; React-only rendering",
        )

        # State-001 Assessment
        self._assessments["THREAT-STATE-001"] = ThreatAssessment(
            vector=THREAT_STATE_001,
            mitigations=[MIT_STATE_001],
            residual_risk="ACCEPTED",
            notes="Client state tampering cannot affect backend; accepted risk",
        )

        # State-002 Assessment
        self._assessments["THREAT-STATE-002"] = ThreatAssessment(
            vector=THREAT_STATE_002,
            mitigations=[MIT_STATE_002],
            residual_risk="LOW",
            notes="HttpOnly cookies prevent JS access to tokens",
        )

        # API-001 Assessment
        self._assessments["THREAT-API-001"] = ThreatAssessment(
            vector=THREAT_API_001,
            mitigations=[MIT_API_001],
            residual_risk="LOW",
            notes="Trusted proxy config ensures real IP used",
        )

        # API-002 Assessment
        self._assessments["THREAT-API-002"] = ThreatAssessment(
            vector=THREAT_API_002,
            mitigations=[MIT_API_002],
            residual_risk="LOW",
            notes="Every endpoint validates resource ownership",
        )

        # API-003 Assessment
        self._assessments["THREAT-API-003"] = ThreatAssessment(
            vector=THREAT_API_003,
            mitigations=[MIT_API_003],
            residual_risk="LOW",
            notes="Pydantic extra='forbid' blocks mass assignment",
        )

        # Priv-001 Assessment
        self._assessments["THREAT-PRIV-001"] = ThreatAssessment(
            vector=THREAT_PRIV_001,
            mitigations=[MIT_PRIV_001],
            residual_risk="LOW",
            notes="RS256 signature validation on all JWTs",
        )

        # Priv-002 Assessment
        self._assessments["THREAT-PRIV-002"] = ThreatAssessment(
            vector=THREAT_PRIV_002,
            mitigations=[MIT_PRIV_002],
            residual_risk="LOW",
            notes="Tenant isolation enforced at query level",
        )

    def get_threat(self, vector_id: str) -> Optional[ThreatVector]:
        """Get threat vector by ID."""
        return self._threats.get(vector_id)

    def get_mitigation(self, mitigation_id: str) -> Optional[Mitigation]:
        """Get mitigation by ID."""
        return self._mitigations.get(mitigation_id)

    def get_assessment(self, vector_id: str) -> Optional[ThreatAssessment]:
        """Get threat assessment by vector ID."""
        return self._assessments.get(vector_id)

    def get_all_threats(self) -> List[ThreatVector]:
        """Get all registered threats."""
        return list(self._threats.values())

    def get_threats_by_category(self, category: ThreatCategory) -> List[ThreatVector]:
        """Get threats by category."""
        return [t for t in self._threats.values() if t.category == category]

    def get_threats_by_severity(self, severity: ThreatSeverity) -> List[ThreatVector]:
        """Get threats by severity."""
        return [t for t in self._threats.values() if t.severity == severity]

    def get_threats_by_surface(self, surface: AttackSurface) -> List[ThreatVector]:
        """Get threats by attack surface."""
        return [t for t in self._threats.values() if t.attack_surface == surface]

    def get_mitigations_by_invariant(self, invariant_id: str) -> List[Mitigation]:
        """Get mitigations validating a specific invariant."""
        return [
            m for m in self._mitigations.values()
            if m.validates_invariant == invariant_id
        ]

    def get_unmitigated_threats(self) -> List[ThreatVector]:
        """Get threats with residual risk above LOW."""
        return [
            self._threats[vid]
            for vid, assessment in self._assessments.items()
            if assessment.residual_risk in ("MEDIUM", "HIGH")
        ]

    def get_critical_threats(self) -> List[ThreatVector]:
        """Get all CRITICAL and HIGH severity threats."""
        return [
            t for t in self._threats.values()
            if t.severity in (ThreatSeverity.CRITICAL, ThreatSeverity.HIGH)
        ]

    def count(self) -> int:
        """Return count of registered threats."""
        return len(self._threats)

    def generate_report(self) -> Dict[str, Any]:
        """Generate threat model summary report."""
        return {
            "total_threats": len(self._threats),
            "total_mitigations": len(self._mitigations),
            "by_severity": {
                s.value: len(self.get_threats_by_severity(s))
                for s in ThreatSeverity
            },
            "by_category": {
                c.value: len(self.get_threats_by_category(c))
                for c in ThreatCategory
            },
            "by_surface": {
                s.value: len(self.get_threats_by_surface(s))
                for s in AttackSurface
            },
            "residual_risk_summary": {
                "LOW": sum(
                    1 for a in self._assessments.values()
                    if a.residual_risk == "LOW"
                ),
                "ACCEPTED": sum(
                    1 for a in self._assessments.values()
                    if a.residual_risk == "ACCEPTED"
                ),
                "MEDIUM": sum(
                    1 for a in self._assessments.values()
                    if a.residual_risk == "MEDIUM"
                ),
                "HIGH": sum(
                    1 for a in self._assessments.values()
                    if a.residual_risk == "HIGH"
                ),
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "assessor": "SAM (GID-06)",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# INPUT SANITIZATION
# ═══════════════════════════════════════════════════════════════════════════════


class InputSanitizer:
    """
    Input sanitization utilities for OCC security.

    INV-SEC-UI-001: All user input must be sanitized before display
    """

    # HTML entities to escape
    HTML_ESCAPE_MAP = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#x27;",
        "/": "&#x2F;",
    }

    # Dangerous patterns to detect
    DANGEROUS_PATTERNS = [
        r"<script",
        r"javascript:",
        r"on\w+\s*=",  # onclick, onerror, etc.
        r"data:\s*text/html",
        r"vbscript:",
        r"expression\s*\(",
    ]

    @classmethod
    def escape_html(cls, text: str) -> str:
        """Escape HTML special characters."""
        for char, entity in cls.HTML_ESCAPE_MAP.items():
            text = text.replace(char, entity)
        return text

    @classmethod
    def detect_xss(cls, text: str) -> bool:
        """Detect potential XSS patterns in text."""
        text_lower = text.lower()
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False

    @classmethod
    def sanitize_for_display(cls, text: str) -> str:
        """
        Sanitize text for safe display.

        INV-SEC-UI-001 enforcement point.
        """
        # Escape HTML
        sanitized = cls.escape_html(text)

        # Log if XSS detected (for audit)
        if cls.detect_xss(text):
            # Would log to security audit in production
            pass

        return sanitized

    @classmethod
    def validate_identifier(cls, identifier: str) -> bool:
        """Validate identifier format (alphanumeric + hyphens/underscores)."""
        return bool(re.match(r"^[a-zA-Z0-9_-]+$", identifier))


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "ThreatCategory",
    "ThreatSeverity",
    "MitigationStatus",
    "AttackSurface",
    # Data classes
    "ThreatVector",
    "Mitigation",
    "ThreatAssessment",
    # Registry
    "ThreatModelRegistry",
    # Sanitization
    "InputSanitizer",
    # Threat instances
    "THREAT_UI_XSS_001",
    "THREAT_UI_XSS_002",
    "THREAT_STATE_001",
    "THREAT_API_001",
    "THREAT_API_002",
    "THREAT_PRIV_001",
    "THREAT_PRIV_002",
    # Mitigation instances
    "MIT_XSS_001",
    "MIT_XSS_002",
    "MIT_STATE_001",
    "MIT_API_001",
    "MIT_PRIV_001",
]
