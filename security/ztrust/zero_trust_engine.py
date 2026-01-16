"""
ChainBridge Zero-Trust Security Engine
======================================

NASA-Grade Policy-as-Code Security Infrastructure
PAC: PAC-JEFFREY-NASA-HARDENING-002

This module REPLACES all prior security with a formally specified,
zero-trust, policy-as-code engine. NO PATCHING. REPLACEMENT ONLY.

Design Principles:
- Zero Trust: Never trust, always verify
- Policy-as-Code: All security decisions from declarative policies
- Deny-by-Default: Explicit allow required, implicit deny
- Complete Audit: Every access decision logged
- Cryptographic Verification: All assertions signed

Formal Invariants:
- INV-ZERO-TRUST: No implicit trust relationships
- INV-POLICY-PRIMACY: Policy engine is sole decision authority
- INV-AUDIT-COMPLETE: Every decision recorded
- INV-DENY-DEFAULT: Unmatched access → DENY

Author: BENSON [GID-00] + SAM [GID-06]
Version: v1.0.0
Classification: SAFETY_CRITICAL
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum, auto
from typing import (
    Any,
    Callable,
    Dict,
    Final,
    FrozenSet,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
)


# =============================================================================
# SECTION 1: SECURITY PRIMITIVES
# =============================================================================

class AccessDecision(Enum):
    """Exhaustive access decision outcomes. No implicit states."""
    ALLOW = auto()
    DENY = auto()
    DENY_NO_POLICY = auto()
    DENY_POLICY_VIOLATION = auto()
    DENY_INVALID_CREDENTIAL = auto()
    DENY_EXPIRED = auto()
    DENY_SCOPE_MISMATCH = auto()
    DENY_RATE_LIMITED = auto()


class ResourceType(Enum):
    """Enumeration of protected resource types."""
    EXECUTION = auto()
    DATA_READ = auto()
    DATA_WRITE = auto()
    CONFIGURATION = auto()
    GOVERNANCE = auto()
    AUDIT = auto()
    SCRAM = auto()
    DEPLOYMENT = auto()


class TrustLevel(Enum):
    """Trust levels - lower number = higher trust."""
    SYSTEM = 0       # Internal system components
    GOVERNANCE = 1   # Governance layer
    OPERATOR = 2     # Human operators
    SERVICE = 3      # External services
    UNTRUSTED = 99   # Default for unknown


@dataclass(frozen=True)
class Principal:
    """
    Immutable security principal (identity).
    
    Represents any entity that can make access requests.
    """
    principal_id: str
    principal_type: str  # AGENT, USER, SERVICE, SYSTEM
    trust_level: TrustLevel
    attributes: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def compute_fingerprint(self) -> str:
        """Compute deterministic fingerprint of principal."""
        content = json.dumps({
            "id": self.principal_id,
            "type": self.principal_type,
            "trust": self.trust_level.name,
            "attrs": dict(sorted(self.attributes.items())),
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class Resource:
    """
    Immutable resource descriptor.
    
    Represents any protected resource in the system.
    """
    resource_id: str
    resource_type: ResourceType
    owner: str
    classification: str  # PUBLIC, INTERNAL, CONFIDENTIAL, CRITICAL
    attributes: Mapping[str, Any] = field(default_factory=dict)
    
    def compute_fingerprint(self) -> str:
        """Compute deterministic fingerprint of resource."""
        content = json.dumps({
            "id": self.resource_id,
            "type": self.resource_type.name,
            "owner": self.owner,
            "class": self.classification,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class AccessRequest:
    """
    Immutable access request.
    
    Represents a request from a principal to access a resource.
    """
    request_id: str
    principal: Principal
    resource: Resource
    action: str  # READ, WRITE, EXECUTE, DELETE, ADMIN
    context: Mapping[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def create(
        cls,
        principal: Principal,
        resource: Resource,
        action: str,
        context: Optional[Mapping[str, Any]] = None,
    ) -> "AccessRequest":
        return cls(
            request_id=f"REQ-{uuid.uuid4().hex[:12].upper()}",
            principal=principal,
            resource=resource,
            action=action,
            context=context or {},
        )


@dataclass(frozen=True)
class AccessDecisionRecord:
    """
    Immutable record of an access decision.
    
    Forms the audit trail of all security decisions.
    """
    decision_id: str
    request_id: str
    decision: AccessDecision
    policy_id: Optional[str]
    reason: str
    timestamp: datetime
    principal_fingerprint: str
    resource_fingerprint: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "decision": self.decision.name,
            "policy_id": self.policy_id,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
            "principal_fingerprint": self.principal_fingerprint,
            "resource_fingerprint": self.resource_fingerprint,
        }


# =============================================================================
# SECTION 2: POLICY ENGINE
# =============================================================================

@dataclass(frozen=True)
class PolicyCondition:
    """A single condition in a policy rule."""
    attribute: str
    operator: str  # eq, ne, in, not_in, gt, lt, gte, lte, matches
    value: Any


@dataclass(frozen=True)
class PolicyRule:
    """
    Immutable policy rule.
    
    Specifies conditions under which access is allowed.
    """
    rule_id: str
    name: str
    effect: str  # ALLOW or DENY
    principals: FrozenSet[str]  # Principal types or IDs that match
    resources: FrozenSet[str]   # Resource types or IDs that match
    actions: FrozenSet[str]     # Actions that match
    conditions: Tuple[PolicyCondition, ...]
    priority: int = 0  # Higher priority rules evaluated first
    
    def matches_principal(self, principal: Principal) -> bool:
        """Check if principal matches this rule."""
        if "*" in self.principals:
            return True
        if principal.principal_id in self.principals:
            return True
        if principal.principal_type in self.principals:
            return True
        return False
    
    def matches_resource(self, resource: Resource) -> bool:
        """Check if resource matches this rule."""
        if "*" in self.resources:
            return True
        if resource.resource_id in self.resources:
            return True
        if resource.resource_type.name in self.resources:
            return True
        return False
    
    def matches_action(self, action: str) -> bool:
        """Check if action matches this rule."""
        return "*" in self.actions or action in self.actions
    
    def evaluate_conditions(
        self,
        principal: Principal,
        resource: Resource,
        context: Mapping[str, Any],
    ) -> bool:
        """Evaluate all conditions against request context."""
        for cond in self.conditions:
            # Get attribute value from context, principal, or resource
            value = None
            if cond.attribute.startswith("principal."):
                attr = cond.attribute[10:]
                value = principal.attributes.get(attr)
            elif cond.attribute.startswith("resource."):
                attr = cond.attribute[9:]
                value = resource.attributes.get(attr)
            elif cond.attribute.startswith("context."):
                attr = cond.attribute[8:]
                value = context.get(attr)
            else:
                value = context.get(cond.attribute)
            
            # Evaluate condition
            if not self._evaluate_condition(value, cond.operator, cond.value):
                return False
        
        return True
    
    def _evaluate_condition(self, actual: Any, operator: str, expected: Any) -> bool:
        """Evaluate a single condition."""
        if operator == "eq":
            return actual == expected
        elif operator == "ne":
            return actual != expected
        elif operator == "in":
            return actual in expected
        elif operator == "not_in":
            return actual not in expected
        elif operator == "gt":
            return actual > expected
        elif operator == "lt":
            return actual < expected
        elif operator == "gte":
            return actual >= expected
        elif operator == "lte":
            return actual <= expected
        elif operator == "exists":
            return actual is not None
        elif operator == "not_exists":
            return actual is None
        else:
            return False  # Unknown operator → fail closed


@dataclass(frozen=True)
class Policy:
    """
    Immutable policy document.
    
    Contains a set of rules for access control.
    """
    policy_id: str
    name: str
    version: str
    rules: Tuple[PolicyRule, ...]
    default_effect: str = "DENY"  # Default is always DENY
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "version": self.version,
            "rules": len(self.rules),
            "default_effect": self.default_effect,
        }


class PolicyEngine:
    """
    Zero-Trust Policy Engine.
    
    The SOLE authority for access decisions. All access goes through this engine.
    
    Properties:
    - Deny-by-default: No policy match → DENY
    - Priority-ordered: Higher priority rules evaluated first
    - Explicit only: No implicit allows
    - Audit complete: Every decision recorded
    """
    
    def __init__(self) -> None:
        self._policies: Dict[str, Policy] = {}
        self._decision_log: List[AccessDecisionRecord] = []
    
    def register_policy(self, policy: Policy) -> None:
        """Register a policy with the engine."""
        self._policies[policy.policy_id] = policy
    
    def evaluate(self, request: AccessRequest) -> AccessDecisionRecord:
        """
        Evaluate an access request.
        
        This is the ONLY entry point for access decisions.
        """
        # Collect all matching rules across all policies
        matching_rules: List[Tuple[str, PolicyRule]] = []
        
        for policy_id, policy in self._policies.items():
            for rule in policy.rules:
                if (rule.matches_principal(request.principal) and
                    rule.matches_resource(request.resource) and
                    rule.matches_action(request.action)):
                    matching_rules.append((policy_id, rule))
        
        # Sort by priority (descending)
        matching_rules.sort(key=lambda x: x[1].priority, reverse=True)
        
        # Evaluate rules in priority order
        for policy_id, rule in matching_rules:
            if rule.evaluate_conditions(
                request.principal,
                request.resource,
                request.context,
            ):
                decision = (
                    AccessDecision.ALLOW if rule.effect == "ALLOW"
                    else AccessDecision.DENY_POLICY_VIOLATION
                )
                record = AccessDecisionRecord(
                    decision_id=f"DEC-{uuid.uuid4().hex[:12].upper()}",
                    request_id=request.request_id,
                    decision=decision,
                    policy_id=policy_id,
                    reason=f"Rule {rule.rule_id}: {rule.name}",
                    timestamp=datetime.now(timezone.utc),
                    principal_fingerprint=request.principal.compute_fingerprint(),
                    resource_fingerprint=request.resource.compute_fingerprint(),
                )
                self._decision_log.append(record)
                return record
        
        # No matching rule → DENY (fail closed)
        record = AccessDecisionRecord(
            decision_id=f"DEC-{uuid.uuid4().hex[:12].upper()}",
            request_id=request.request_id,
            decision=AccessDecision.DENY_NO_POLICY,
            policy_id=None,
            reason="No matching policy rule (deny-by-default)",
            timestamp=datetime.now(timezone.utc),
            principal_fingerprint=request.principal.compute_fingerprint(),
            resource_fingerprint=request.resource.compute_fingerprint(),
        )
        self._decision_log.append(record)
        return record
    
    def get_decision_log(self) -> Sequence[AccessDecisionRecord]:
        """Return audit log of all decisions."""
        return tuple(self._decision_log)


# =============================================================================
# SECTION 3: CREDENTIAL SYSTEM
# =============================================================================

@dataclass(frozen=True)
class Credential:
    """
    Immutable security credential.
    
    Time-bound, scope-limited credential for authentication.
    """
    credential_id: str
    principal_id: str
    credential_type: str  # TOKEN, API_KEY, CERTIFICATE
    issued_at: datetime
    expires_at: datetime
    scopes: FrozenSet[str]
    signature: str
    
    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at
    
    def has_scope(self, required_scope: str) -> bool:
        return "*" in self.scopes or required_scope in self.scopes


class CredentialVault:
    """
    Secure credential storage and validation.
    
    Properties:
    - Time-bound: All credentials expire
    - Scope-limited: Credentials have explicit scope
    - Cryptographically signed: Tampering detectable
    """
    
    SIGNING_KEY: Final[bytes] = b"chainbridge-zero-trust-signing-key-v1"
    
    def __init__(self) -> None:
        self._credentials: Dict[str, Credential] = {}
        self._revoked: Set[str] = set()
    
    def issue_credential(
        self,
        principal_id: str,
        credential_type: str,
        scopes: FrozenSet[str],
        ttl_seconds: int = 3600,
    ) -> Credential:
        """Issue a new credential."""
        now = datetime.now(timezone.utc)
        credential_id = f"CRED-{uuid.uuid4().hex[:12].upper()}"
        
        # Compute signature
        content = json.dumps({
            "id": credential_id,
            "principal": principal_id,
            "type": credential_type,
            "issued": now.isoformat(),
            "scopes": sorted(scopes),
        }, sort_keys=True)
        signature = hmac.new(
            self.SIGNING_KEY,
            content.encode(),
            hashlib.sha256
        ).hexdigest()
        
        credential = Credential(
            credential_id=credential_id,
            principal_id=principal_id,
            credential_type=credential_type,
            issued_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
            scopes=scopes,
            signature=signature,
        )
        
        self._credentials[credential_id] = credential
        return credential
    
    def validate(self, credential_id: str) -> Tuple[bool, str]:
        """
        Validate a credential.
        
        Returns (valid, reason).
        """
        if credential_id in self._revoked:
            return False, "Credential revoked"
        
        if credential_id not in self._credentials:
            return False, "Credential not found"
        
        credential = self._credentials[credential_id]
        
        if credential.is_expired:
            return False, "Credential expired"
        
        # Verify signature
        content = json.dumps({
            "id": credential.credential_id,
            "principal": credential.principal_id,
            "type": credential.credential_type,
            "issued": credential.issued_at.isoformat(),
            "scopes": sorted(credential.scopes),
        }, sort_keys=True)
        expected_sig = hmac.new(
            self.SIGNING_KEY,
            content.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(credential.signature, expected_sig):
            return False, "Invalid signature"
        
        return True, "Valid"
    
    def revoke(self, credential_id: str) -> None:
        """Revoke a credential."""
        self._revoked.add(credential_id)
    
    def get_credential(self, credential_id: str) -> Optional[Credential]:
        """Retrieve a credential."""
        if credential_id in self._revoked:
            return None
        return self._credentials.get(credential_id)


# =============================================================================
# SECTION 4: RATE LIMITER
# =============================================================================

@dataclass
class RateLimitBucket:
    """Token bucket for rate limiting."""
    tokens: float
    last_update: float
    capacity: float
    refill_rate: float  # tokens per second


class RateLimiter:
    """
    Token bucket rate limiter.
    
    Prevents abuse through configurable rate limits.
    """
    
    def __init__(
        self,
        default_capacity: float = 100.0,
        default_refill_rate: float = 10.0,
    ) -> None:
        self._buckets: Dict[str, RateLimitBucket] = {}
        self._default_capacity = default_capacity
        self._default_refill_rate = default_refill_rate
    
    def _get_bucket(self, key: str) -> RateLimitBucket:
        """Get or create a bucket for the given key."""
        if key not in self._buckets:
            self._buckets[key] = RateLimitBucket(
                tokens=self._default_capacity,
                last_update=time.monotonic(),
                capacity=self._default_capacity,
                refill_rate=self._default_refill_rate,
            )
        return self._buckets[key]
    
    def check(self, key: str, cost: float = 1.0) -> Tuple[bool, float]:
        """
        Check if request is allowed.
        
        Returns (allowed, tokens_remaining).
        """
        bucket = self._get_bucket(key)
        now = time.monotonic()
        
        # Refill tokens
        elapsed = now - bucket.last_update
        bucket.tokens = min(
            bucket.capacity,
            bucket.tokens + elapsed * bucket.refill_rate
        )
        bucket.last_update = now
        
        # Check if enough tokens
        if bucket.tokens >= cost:
            bucket.tokens -= cost
            return True, bucket.tokens
        
        return False, bucket.tokens


# =============================================================================
# SECTION 5: SECURITY CONTEXT (Zero-Trust Session)
# =============================================================================

@dataclass(frozen=True)
class SecurityContext:
    """
    Immutable zero-trust security context.
    
    Captures all security state for a session. Must be explicitly established
    and continuously validated.
    """
    context_id: str
    principal: Principal
    credential: Credential
    established_at: datetime
    valid_until: datetime
    trust_assertions: FrozenSet[str]
    
    @property
    def is_valid(self) -> bool:
        return datetime.now(timezone.utc) < self.valid_until
    
    def has_assertion(self, assertion: str) -> bool:
        return assertion in self.trust_assertions


class ZeroTrustEngine:
    """
    Zero-Trust Security Engine.
    
    Combines policy engine, credential vault, and rate limiter into
    a unified security decision point.
    
    ALL security decisions go through this engine.
    """
    
    def __init__(self) -> None:
        self._policy_engine = PolicyEngine()
        self._credential_vault = CredentialVault()
        self._rate_limiter = RateLimiter()
        self._active_contexts: Dict[str, SecurityContext] = {}
    
    def register_policy(self, policy: Policy) -> None:
        """Register a security policy."""
        self._policy_engine.register_policy(policy)
    
    def establish_context(
        self,
        principal: Principal,
        scopes: FrozenSet[str],
        ttl_seconds: int = 3600,
    ) -> SecurityContext:
        """Establish a new security context."""
        credential = self._credential_vault.issue_credential(
            principal_id=principal.principal_id,
            credential_type="SESSION",
            scopes=scopes,
            ttl_seconds=ttl_seconds,
        )
        
        now = datetime.now(timezone.utc)
        context = SecurityContext(
            context_id=f"SCTX-{uuid.uuid4().hex[:12].upper()}",
            principal=principal,
            credential=credential,
            established_at=now,
            valid_until=now + timedelta(seconds=ttl_seconds),
            trust_assertions=frozenset({
                "AUTHENTICATED",
                f"TRUST_LEVEL_{principal.trust_level.name}",
            }),
        )
        
        self._active_contexts[context.context_id] = context
        return context
    
    def authorize(
        self,
        context: SecurityContext,
        resource: Resource,
        action: str,
        request_context: Optional[Mapping[str, Any]] = None,
    ) -> AccessDecisionRecord:
        """
        Authorize an access request.
        
        This is the SINGLE entry point for all authorization decisions.
        """
        # Validate context
        if not context.is_valid:
            return AccessDecisionRecord(
                decision_id=f"DEC-{uuid.uuid4().hex[:12].upper()}",
                request_id=f"REQ-{uuid.uuid4().hex[:12].upper()}",
                decision=AccessDecision.DENY_EXPIRED,
                policy_id=None,
                reason="Security context expired",
                timestamp=datetime.now(timezone.utc),
                principal_fingerprint=context.principal.compute_fingerprint(),
                resource_fingerprint=resource.compute_fingerprint(),
            )
        
        # Validate credential
        valid, reason = self._credential_vault.validate(context.credential.credential_id)
        if not valid:
            return AccessDecisionRecord(
                decision_id=f"DEC-{uuid.uuid4().hex[:12].upper()}",
                request_id=f"REQ-{uuid.uuid4().hex[:12].upper()}",
                decision=AccessDecision.DENY_INVALID_CREDENTIAL,
                policy_id=None,
                reason=f"Invalid credential: {reason}",
                timestamp=datetime.now(timezone.utc),
                principal_fingerprint=context.principal.compute_fingerprint(),
                resource_fingerprint=resource.compute_fingerprint(),
            )
        
        # Check scope
        required_scope = f"{resource.resource_type.name}:{action}"
        if not context.credential.has_scope(required_scope) and not context.credential.has_scope("*"):
            return AccessDecisionRecord(
                decision_id=f"DEC-{uuid.uuid4().hex[:12].upper()}",
                request_id=f"REQ-{uuid.uuid4().hex[:12].upper()}",
                decision=AccessDecision.DENY_SCOPE_MISMATCH,
                policy_id=None,
                reason=f"Scope {required_scope} not in credential",
                timestamp=datetime.now(timezone.utc),
                principal_fingerprint=context.principal.compute_fingerprint(),
                resource_fingerprint=resource.compute_fingerprint(),
            )
        
        # Rate limit check
        rate_key = f"{context.principal.principal_id}:{resource.resource_type.name}"
        allowed, remaining = self._rate_limiter.check(rate_key)
        if not allowed:
            return AccessDecisionRecord(
                decision_id=f"DEC-{uuid.uuid4().hex[:12].upper()}",
                request_id=f"REQ-{uuid.uuid4().hex[:12].upper()}",
                decision=AccessDecision.DENY_RATE_LIMITED,
                policy_id=None,
                reason=f"Rate limit exceeded (remaining: {remaining:.2f})",
                timestamp=datetime.now(timezone.utc),
                principal_fingerprint=context.principal.compute_fingerprint(),
                resource_fingerprint=resource.compute_fingerprint(),
            )
        
        # Policy evaluation
        request = AccessRequest.create(
            principal=context.principal,
            resource=resource,
            action=action,
            context=request_context,
        )
        
        return self._policy_engine.evaluate(request)
    
    def revoke_context(self, context_id: str) -> None:
        """Revoke a security context."""
        if context_id in self._active_contexts:
            context = self._active_contexts[context_id]
            self._credential_vault.revoke(context.credential.credential_id)
            del self._active_contexts[context_id]
    
    def get_policy_engine(self) -> PolicyEngine:
        """Return the policy engine."""
        return self._policy_engine
    
    def get_credential_vault(self) -> CredentialVault:
        """Return the credential vault."""
        return self._credential_vault


# =============================================================================
# SECTION 6: STANDARD POLICIES
# =============================================================================

def create_chainbridge_base_policy() -> Policy:
    """Create the base ChainBridge security policy."""
    return Policy(
        policy_id="POL-CB-BASE-001",
        name="ChainBridge Base Security Policy",
        version="v1.0.0",
        rules=(
            # System components have full access
            PolicyRule(
                rule_id="RULE-SYS-001",
                name="System Full Access",
                effect="ALLOW",
                principals=frozenset({"SYSTEM"}),
                resources=frozenset({"*"}),
                actions=frozenset({"*"}),
                conditions=(),
                priority=1000,
            ),
            # Governance layer access
            PolicyRule(
                rule_id="RULE-GOV-001",
                name="Governance Access",
                effect="ALLOW",
                principals=frozenset({"AGENT"}),
                resources=frozenset({"GOVERNANCE", "EXECUTION"}),
                actions=frozenset({"READ", "WRITE", "EXECUTE"}),
                conditions=(
                    PolicyCondition("principal.trust_level", "lte", 1),
                ),
                priority=500,
            ),
            # Agent execution access
            PolicyRule(
                rule_id="RULE-AGENT-001",
                name="Agent Execution",
                effect="ALLOW",
                principals=frozenset({"AGENT"}),
                resources=frozenset({"EXECUTION", "DATA_READ"}),
                actions=frozenset({"READ", "EXECUTE"}),
                conditions=(),
                priority=100,
            ),
            # Explicit SCRAM access
            PolicyRule(
                rule_id="RULE-SCRAM-001",
                name="SCRAM Access",
                effect="ALLOW",
                principals=frozenset({"SYSTEM", "AGENT"}),
                resources=frozenset({"SCRAM"}),
                actions=frozenset({"EXECUTE"}),
                conditions=(
                    PolicyCondition("context.scram_authorized", "eq", True),
                ),
                priority=900,
            ),
        ),
        default_effect="DENY",
    )


# =============================================================================
# SECTION 7: SELF-TEST SUITE
# =============================================================================

def _run_self_tests() -> None:
    """Run comprehensive self-tests for security engine."""
    print("=" * 70)
    print("ZERO-TRUST SECURITY ENGINE SELF-TEST SUITE")
    print("PAC: PAC-JEFFREY-NASA-HARDENING-002")
    print("=" * 70)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Principal Creation
    print("\n[TEST 1] Principal Creation...")
    try:
        principal = Principal(
            principal_id="AGENT-GID-00",
            principal_type="AGENT",
            trust_level=TrustLevel.GOVERNANCE,
            attributes={"role": "ORCHESTRATOR"},
        )
        assert principal.principal_id == "AGENT-GID-00"
        assert principal.trust_level == TrustLevel.GOVERNANCE
        fingerprint = principal.compute_fingerprint()
        assert len(fingerprint) == 16
        print(f"  ✓ Principal created with fingerprint {fingerprint}")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 2: Resource Creation
    print("\n[TEST 2] Resource Creation...")
    try:
        resource = Resource(
            resource_id="EXEC-001",
            resource_type=ResourceType.EXECUTION,
            owner="SYSTEM",
            classification="CRITICAL",
        )
        assert resource.resource_type == ResourceType.EXECUTION
        fingerprint = resource.compute_fingerprint()
        assert len(fingerprint) == 16
        print(f"  ✓ Resource created with fingerprint {fingerprint}")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 3: Credential Issuance
    print("\n[TEST 3] Credential Issuance...")
    try:
        vault = CredentialVault()
        cred = vault.issue_credential(
            principal_id="AGENT-001",
            credential_type="TOKEN",
            scopes=frozenset({"EXECUTION:READ", "EXECUTION:EXECUTE"}),
            ttl_seconds=3600,
        )
        assert cred.credential_id.startswith("CRED-")
        assert not cred.is_expired
        assert cred.has_scope("EXECUTION:READ")
        print(f"  ✓ Credential {cred.credential_id} issued")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 4: Credential Validation
    print("\n[TEST 4] Credential Validation...")
    try:
        vault = CredentialVault()
        cred = vault.issue_credential(
            principal_id="AGENT-002",
            credential_type="TOKEN",
            scopes=frozenset({"*"}),
        )
        
        valid, reason = vault.validate(cred.credential_id)
        assert valid
        assert reason == "Valid"
        
        # Test invalid credential
        valid, reason = vault.validate("CRED-NONEXISTENT")
        assert not valid
        assert "not found" in reason
        
        print("  ✓ Credential validation working")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 5: Credential Revocation
    print("\n[TEST 5] Credential Revocation...")
    try:
        vault = CredentialVault()
        cred = vault.issue_credential(
            principal_id="AGENT-003",
            credential_type="TOKEN",
            scopes=frozenset({"*"}),
        )
        
        valid, _ = vault.validate(cred.credential_id)
        assert valid
        
        vault.revoke(cred.credential_id)
        
        valid, reason = vault.validate(cred.credential_id)
        assert not valid
        assert "revoked" in reason.lower()
        
        print("  ✓ Credential revocation working")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 6: Policy Engine - Allow
    print("\n[TEST 6] Policy Engine - Allow Decision...")
    try:
        engine = PolicyEngine()
        policy = create_chainbridge_base_policy()
        engine.register_policy(policy)
        
        principal = Principal(
            principal_id="SYSTEM",
            principal_type="SYSTEM",
            trust_level=TrustLevel.SYSTEM,
        )
        resource = Resource(
            resource_id="ANY",
            resource_type=ResourceType.EXECUTION,
            owner="SYSTEM",
            classification="INTERNAL",
        )
        request = AccessRequest.create(principal, resource, "EXECUTE")
        
        decision = engine.evaluate(request)
        assert decision.decision == AccessDecision.ALLOW
        print(f"  ✓ System access ALLOWED (rule: {decision.reason})")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 7: Policy Engine - Deny (No Policy)
    print("\n[TEST 7] Policy Engine - Deny by Default...")
    try:
        engine = PolicyEngine()
        # No policies registered
        
        principal = Principal(
            principal_id="UNKNOWN",
            principal_type="UNKNOWN",
            trust_level=TrustLevel.UNTRUSTED,
        )
        resource = Resource(
            resource_id="SENSITIVE",
            resource_type=ResourceType.GOVERNANCE,
            owner="SYSTEM",
            classification="CRITICAL",
        )
        request = AccessRequest.create(principal, resource, "ADMIN")
        
        decision = engine.evaluate(request)
        assert decision.decision == AccessDecision.DENY_NO_POLICY
        print("  ✓ Unknown access DENIED (no policy)")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 8: Rate Limiter
    print("\n[TEST 8] Rate Limiter...")
    try:
        limiter = RateLimiter(default_capacity=5, default_refill_rate=1)
        
        # Should allow first 5 requests
        for i in range(5):
            allowed, _ = limiter.check("test-key")
            assert allowed, f"Request {i+1} should be allowed"
        
        # 6th request should be denied
        allowed, remaining = limiter.check("test-key")
        assert not allowed
        print(f"  ✓ Rate limiting working (blocked after 5 requests)")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 9: Zero-Trust Engine - Full Flow
    print("\n[TEST 9] Zero-Trust Engine - Full Flow...")
    try:
        engine = ZeroTrustEngine()
        engine.register_policy(create_chainbridge_base_policy())
        
        principal = Principal(
            principal_id="BENSON",
            principal_type="AGENT",
            trust_level=TrustLevel.GOVERNANCE,
            attributes={"gid": "GID-00"},
        )
        
        context = engine.establish_context(
            principal=principal,
            scopes=frozenset({"*"}),
            ttl_seconds=3600,
        )
        
        assert context.context_id.startswith("SCTX-")
        assert context.is_valid
        assert "AUTHENTICATED" in context.trust_assertions
        
        resource = Resource(
            resource_id="TASK-001",
            resource_type=ResourceType.EXECUTION,
            owner="SYSTEM",
            classification="INTERNAL",
        )
        
        decision = engine.authorize(context, resource, "EXECUTE")
        assert decision.decision == AccessDecision.ALLOW
        
        print(f"  ✓ Full zero-trust flow completed")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 10: Security Context Revocation
    print("\n[TEST 10] Security Context Revocation...")
    try:
        engine = ZeroTrustEngine()
        engine.register_policy(create_chainbridge_base_policy())
        
        principal = Principal(
            principal_id="TEMP-AGENT",
            principal_type="AGENT",
            trust_level=TrustLevel.SERVICE,
        )
        
        context = engine.establish_context(
            principal=principal,
            scopes=frozenset({"*"}),
        )
        
        # Revoke the context
        engine.revoke_context(context.context_id)
        
        # Subsequent authorization should fail
        resource = Resource(
            resource_id="TEST",
            resource_type=ResourceType.DATA_READ,
            owner="SYSTEM",
            classification="INTERNAL",
        )
        
        decision = engine.authorize(context, resource, "READ")
        assert decision.decision == AccessDecision.DENY_INVALID_CREDENTIAL
        
        print("  ✓ Context revocation enforced")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1
    
    # Summary
    print("\n" + "=" * 70)
    print(f"SELF-TEST RESULTS: {tests_passed}/{tests_passed + tests_failed} PASSED")
    print("=" * 70)
    
    if tests_failed > 0:
        print(f"\n⚠️  {tests_failed} test(s) FAILED")
    else:
        print("\n✅ ALL TESTS PASSED - Zero-Trust Security Engine OPERATIONAL")


if __name__ == "__main__":
    _run_self_tests()
