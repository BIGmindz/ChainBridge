"""
Identity Middleware - GID Registry Binding
===========================================

PAC-SEC-P821: AUTHENTICATION MIDDLEWARE HARDENING
Component: GID Registry Integration

INVARIANTS:
  INV-AUTH-002: GID binding MUST be verified against gid_registry.json
  INV-GID-001: Unknown GID → HARD FAIL (per RULE-GID-002)
  INV-GID-002: GID format MUST match pattern GID-XX (per RULE-GID-003)
  INV-GID-003: Execution lane permissions MUST be enforced

ENFORCEMENT RULES (from gid_registry.json):
  RULE-GID-001: All PACs must reference a valid GID from this registry
  RULE-GID-002: Unknown GID → immediate rejection (HARD FAIL)
  RULE-GID-003: GID format must match pattern GID-XX where XX is 00-99
  RULE-GID-004: GIDs are immutable once assigned
  RULE-GID-005: No agent may operate without a registered GID
  RULE-GID-006: System components (system=true) are non-persona, non-conversational
  RULE-GID-007: Only SYSTEM_ORCHESTRATOR may issue BER
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Set

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# Configure logging
logger = logging.getLogger("chainbridge.identity")

# GID format pattern: GID-XX where XX is 00-99
GID_PATTERN = re.compile(r"^GID-\d{2}$")

# Registry file path
GID_REGISTRY_PATH = Path("core/governance/gid_registry.json")


@dataclass
class GIDInfo:
    """Information about a registered GID."""
    gid: str
    name: str
    role: str
    lane: str
    level: str
    permitted_modes: List[str]
    execution_lanes: List[str]
    can_issue_pac: bool
    can_issue_ber: bool
    can_override: bool
    is_system: bool
    system_type: Optional[str] = None
    has_persona: bool = False
    is_conversational: bool = False
    
    def can_execute_in_lane(self, lane: str) -> bool:
        """Check if GID can execute in a specific lane."""
        return lane.upper() in self.execution_lanes or "ALL" in self.execution_lanes
    
    def has_mode(self, mode: str) -> bool:
        """Check if GID has a specific permitted mode."""
        return mode.upper() in self.permitted_modes


class GIDValidator:
    """
    GID Registry validator with HARD FAIL enforcement.
    
    Loads gid_registry.json and validates GID references.
    Unknown GID = HARD FAIL per RULE-GID-002.
    """
    
    def __init__(self, registry_path: Path = GID_REGISTRY_PATH):
        self.registry_path = registry_path
        self._registry: Dict[str, Any] = {}
        self._agents: Dict[str, GIDInfo] = {}
        self._enforcement_rules: Dict[str, str] = {}
        self._load_registry()
    
    def _load_registry(self) -> None:
        """Load GID registry from file."""
        try:
            if self.registry_path.exists():
                with open(self.registry_path) as f:
                    self._registry = json.load(f)
                
                self._enforcement_rules = self._registry.get("enforcement_rules", {})
                
                # Parse agent entries
                agents_data = self._registry.get("agents", {})
                for gid, data in agents_data.items():
                    if not self._validate_gid_format(gid):
                        logger.warning(f"Invalid GID format in registry: {gid}")
                        continue
                    
                    self._agents[gid] = GIDInfo(
                        gid=gid,
                        name=data.get("name", ""),
                        role=data.get("role", ""),
                        lane=data.get("lane", ""),
                        level=data.get("level", ""),
                        permitted_modes=data.get("permitted_modes", []),
                        execution_lanes=data.get("execution_lanes", []),
                        can_issue_pac=data.get("can_issue_pac", False),
                        can_issue_ber=data.get("can_issue_ber", False),
                        can_override=data.get("can_override", False),
                        is_system=data.get("system", False),
                        system_type=data.get("system_type"),
                        has_persona=data.get("has_persona", False),
                        is_conversational=data.get("is_conversational", False),
                    )
                
                logger.info(f"Loaded {len(self._agents)} agents from GID registry")
            else:
                logger.warning(f"GID registry not found: {self.registry_path}")
        
        except Exception as e:
            logger.error(f"Failed to load GID registry: {e}")
    
    def _validate_gid_format(self, gid: str) -> bool:
        """Validate GID format per RULE-GID-003."""
        return bool(GID_PATTERN.match(gid))
    
    def validate_gid(self, gid: str) -> Optional[GIDInfo]:
        """
        Validate a GID against the registry.
        
        Returns GIDInfo if valid, None if invalid (HARD FAIL case).
        Per RULE-GID-002: Unknown GID → immediate rejection.
        """
        if not gid:
            return None
        
        # Validate format
        if not self._validate_gid_format(gid):
            logger.warning(f"RULE-GID-003 violation: Invalid GID format: {gid}")
            return None
        
        # Check registry
        if gid not in self._agents:
            logger.warning(f"RULE-GID-002 violation: Unknown GID: {gid}")
            return None
        
        return self._agents[gid]
    
    def get_agent(self, gid: str) -> Optional[GIDInfo]:
        """Get agent info by GID."""
        return self._agents.get(gid)
    
    def list_agents(self) -> List[GIDInfo]:
        """List all registered agents."""
        return list(self._agents.values())
    
    def get_enforcement_rule(self, rule_id: str) -> Optional[str]:
        """Get an enforcement rule by ID."""
        return self._enforcement_rules.get(rule_id)


@dataclass
class IdentityContext:
    """Identity context for a request."""
    gid: Optional[str] = None
    gid_info: Optional[GIDInfo] = None
    is_validated: bool = False
    is_system: bool = False
    execution_lanes: List[str] = field(default_factory=list)
    error: Optional[str] = None


class IdentityMiddleware(BaseHTTPMiddleware):
    """
    Identity middleware for GID registry binding.
    
    Enforces INV-AUTH-002: GID binding MUST be verified against gid_registry.json.
    
    For requests with a GID claim:
      - Validates GID format (RULE-GID-003)
      - Validates GID exists in registry (RULE-GID-002)
      - Attaches GIDInfo to request state
      - Enforces execution lane permissions
    
    For requests without a GID claim:
      - Allows request if user_id is present (external user)
      - Logs warning for monitoring
    """
    
    def __init__(
        self,
        app,
        exempt_paths: FrozenSet[str] = frozenset(),
        require_gid: bool = False,
        validator: Optional[GIDValidator] = None,
    ):
        super().__init__(app)
        self.exempt_paths = exempt_paths
        self.require_gid = require_gid
        self.validator = validator or GIDValidator()
    
    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from identity validation."""
        if path in self.exempt_paths:
            return True
        path_normalized = path.rstrip("/")
        if path_normalized in self.exempt_paths:
            return True
        for exempt in self.exempt_paths:
            if path.startswith(exempt + "/"):
                return True
        return False
    
    def _extract_lane_from_path(self, path: str) -> Optional[str]:
        """
        Extract execution lane from request path.
        
        Mapping:
          /api/* -> API
          /v1/transactions/* -> CORE
          /v1/governance/* -> GOVERNANCE
          /docs/* -> (exempt)
        """
        path_lower = path.lower()
        
        if path_lower.startswith("/v1/transaction"):
            return "CORE"
        if path_lower.startswith("/v1/governance"):
            return "GOVERNANCE"
        if path_lower.startswith("/v1/module"):
            return "BACKEND"
        if path_lower.startswith("/api"):
            return "API"
        
        return None
    
    async def dispatch(self, request: Request, call_next):
        """Process identity validation for incoming request."""
        path = request.url.path
        
        # Check exemption
        if self._is_exempt(path):
            return await call_next(request)
        
        # Get auth result from upstream middleware
        auth = getattr(request.state, "auth", None)
        if not auth:
            # No auth context - should have been caught by AuthMiddleware
            return await call_next(request)
        
        # Create identity context
        identity = IdentityContext()
        
        # Check for GID claim
        gid = getattr(request.state, "gid", None) or auth.claims.get("gid")
        
        if gid:
            # Validate GID against registry
            gid_info = self.validator.validate_gid(gid)
            
            if gid_info is None:
                # HARD FAIL per RULE-GID-002
                logger.warning(
                    f"GID validation failed: gid={gid} path={path} "
                    f"user_id={auth.user_id}"
                )
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Forbidden",
                        "message": "Invalid agent identity",
                        "code": "INVALID_GID",
                    },
                )
            
            # Check execution lane permission
            lane = self._extract_lane_from_path(path)
            if lane and not gid_info.can_execute_in_lane(lane):
                logger.warning(
                    f"Lane permission denied: gid={gid} lane={lane} "
                    f"allowed_lanes={gid_info.execution_lanes}"
                )
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Forbidden",
                        "message": f"Agent not permitted in lane: {lane}",
                        "code": "LANE_DENIED",
                    },
                )
            
            identity.gid = gid
            identity.gid_info = gid_info
            identity.is_validated = True
            identity.is_system = gid_info.is_system
            identity.execution_lanes = gid_info.execution_lanes
        
        elif self.require_gid:
            # GID required but not present
            logger.warning(f"GID required but not present: path={path}")
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Forbidden",
                    "message": "Agent identity required",
                    "code": "GID_REQUIRED",
                },
            )
        
        else:
            # External user without GID - allow but log
            logger.info(f"Request without GID: user_id={auth.user_id} path={path}")
        
        # Attach identity context to request state
        request.state.identity = identity
        
        return await call_next(request)
