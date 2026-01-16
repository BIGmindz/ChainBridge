#!/usr/bin/env python3
"""
Agent University Licensing Module
=================================

Productizes the Agent University governance framework as a 
licensable SaaS offering (Governance-as-a-Service).

PAC Reference: PAC-JEFFREY-TARGET-20M-001 (TASK 3)
Constitutional Authority: ALEX (FOUNDER / CEO)
Executor: BENSON [GID-00]

Schema: v4.0.0
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set
import json


# =============================================================================
# ENUMS
# =============================================================================

class LicenseTier(Enum):
    """Licensing tiers for Agent University."""
    STARTER = "starter"           # Single agent, basic features
    PROFESSIONAL = "professional"  # 5 agents, full governance
    ENTERPRISE = "enterprise"      # Unlimited agents, custom doctrines
    SOVEREIGN = "sovereign"        # Full source, self-hosted


class LicenseStatus(Enum):
    """License lifecycle status."""
    TRIAL = auto()
    ACTIVE = auto()
    SUSPENDED = auto()
    EXPIRED = auto()
    CANCELLED = auto()


class FeatureFlag(Enum):
    """Available features for licensing."""
    AGENT_REGISTRY = "agent_registry"
    GID_MANAGEMENT = "gid_management"
    PAC_FRAMEWORK = "pac_framework"
    BER_REPORTING = "ber_reporting"
    SCRAM_CONTROLLER = "scram_controller"
    DOCTRINE_ENGINE = "doctrine_engine"
    LANE_ORCHESTRATION = "lane_orchestration"
    CERTIFICATION_LEVELS = "certification_levels"
    AUDIT_TRAIL = "audit_trail"
    CONSTITUTIONAL_GATES = "constitutional_gates"
    CUSTOM_DOCTRINES = "custom_doctrines"
    WHITE_LABEL = "white_label"
    API_ACCESS = "api_access"
    SSO_INTEGRATION = "sso_integration"
    PRIORITY_SUPPORT = "priority_support"
    SOURCE_ACCESS = "source_access"


class DeploymentModel(Enum):
    """Deployment models available."""
    SAAS = "saas"              # ChainBridge hosted
    HYBRID = "hybrid"          # Shared hosting with dedicated compute
    DEDICATED = "dedicated"    # Single-tenant cloud
    ON_PREMISE = "on_premise"  # Customer self-hosted


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PricingPlan:
    """Pricing structure for a license tier."""
    tier: LicenseTier
    base_monthly_usd: Decimal
    per_agent_monthly_usd: Decimal
    included_agents: int
    max_agents: Optional[int]  # None = unlimited
    annual_discount_percent: Decimal = Decimal("20")
    setup_fee_usd: Decimal = Decimal("0")
    features: Set[FeatureFlag] = field(default_factory=set)
    
    def calculate_monthly(self, agent_count: int) -> Decimal:
        """Calculate monthly cost for given agent count."""
        base = self.base_monthly_usd
        
        extra_agents = max(0, agent_count - self.included_agents)
        if self.max_agents and agent_count > self.max_agents:
            raise ValueError(f"Agent count {agent_count} exceeds tier maximum {self.max_agents}")
        
        agent_cost = extra_agents * self.per_agent_monthly_usd
        
        return base + agent_cost
    
    def calculate_annual(self, agent_count: int) -> Decimal:
        """Calculate annual cost with discount."""
        monthly = self.calculate_monthly(agent_count)
        annual = monthly * 12
        discount = annual * (self.annual_discount_percent / 100)
        return annual - discount
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier.value,
            "base_monthly_usd": str(self.base_monthly_usd),
            "per_agent_monthly_usd": str(self.per_agent_monthly_usd),
            "included_agents": self.included_agents,
            "max_agents": self.max_agents,
            "annual_discount_percent": str(self.annual_discount_percent),
            "setup_fee_usd": str(self.setup_fee_usd),
            "features": [f.value for f in self.features],
        }


@dataclass
class Customer:
    """Licensed customer."""
    customer_id: str
    company_name: str
    industry: str
    contact_email: str
    contact_name: str
    billing_address: str
    deployment_model: DeploymentModel
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "customer_id": self.customer_id,
            "company_name": self.company_name,
            "industry": self.industry,
            "contact_email": self.contact_email,
            "deployment_model": self.deployment_model.value,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class License:
    """Agent University license."""
    license_id: str
    customer: Customer
    plan: PricingPlan
    status: LicenseStatus
    agent_count: int
    start_date: datetime
    end_date: datetime
    renewal_date: Optional[datetime]
    is_annual: bool
    monthly_cost: Decimal
    license_key: str
    features_enabled: Set[FeatureFlag]
    custom_doctrines: List[str] = field(default_factory=list)
    usage_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "license_id": self.license_id,
            "customer_id": self.customer.customer_id,
            "company_name": self.customer.company_name,
            "tier": self.plan.tier.value,
            "status": self.status.name,
            "agent_count": self.agent_count,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "monthly_cost": str(self.monthly_cost),
            "is_annual": self.is_annual,
            "features_enabled": [f.value for f in self.features_enabled],
        }
    
    @property
    def is_active(self) -> bool:
        return self.status == LicenseStatus.ACTIVE
    
    @property
    def days_until_renewal(self) -> int:
        if not self.renewal_date:
            return -1
        delta = self.renewal_date - datetime.now(timezone.utc)
        return max(0, delta.days)


@dataclass
class UsageRecord:
    """Usage tracking record."""
    record_id: str
    license_id: str
    timestamp: datetime
    metric_type: str  # "agent_invocation", "pac_created", "ber_generated", etc.
    count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Invoice:
    """License invoice."""
    invoice_id: str
    license_id: str
    customer_id: str
    period_start: datetime
    period_end: datetime
    line_items: List[Dict[str, Any]]
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    status: str  # draft, sent, paid, overdue
    due_date: datetime
    paid_date: Optional[datetime] = None


# =============================================================================
# PRICING CATALOG
# =============================================================================

class PricingCatalog:
    """
    Pricing catalog for Agent University licensing.
    
    Tiers designed for different organizational sizes:
    - STARTER: Individuals/small teams exploring AI governance
    - PROFESSIONAL: SMB implementing AI agent operations  
    - ENTERPRISE: Large organizations with complex governance needs
    - SOVEREIGN: Organizations requiring full control/customization
    """
    
    CATALOG: Dict[LicenseTier, PricingPlan] = {
        LicenseTier.STARTER: PricingPlan(
            tier=LicenseTier.STARTER,
            base_monthly_usd=Decimal("299"),
            per_agent_monthly_usd=Decimal("99"),
            included_agents=1,
            max_agents=3,
            annual_discount_percent=Decimal("15"),
            setup_fee_usd=Decimal("0"),
            features={
                FeatureFlag.AGENT_REGISTRY,
                FeatureFlag.GID_MANAGEMENT,
                FeatureFlag.PAC_FRAMEWORK,
                FeatureFlag.BER_REPORTING,
                FeatureFlag.AUDIT_TRAIL,
                FeatureFlag.API_ACCESS,
            },
        ),
        
        LicenseTier.PROFESSIONAL: PricingPlan(
            tier=LicenseTier.PROFESSIONAL,
            base_monthly_usd=Decimal("999"),
            per_agent_monthly_usd=Decimal("79"),
            included_agents=5,
            max_agents=20,
            annual_discount_percent=Decimal("20"),
            setup_fee_usd=Decimal("500"),
            features={
                FeatureFlag.AGENT_REGISTRY,
                FeatureFlag.GID_MANAGEMENT,
                FeatureFlag.PAC_FRAMEWORK,
                FeatureFlag.BER_REPORTING,
                FeatureFlag.SCRAM_CONTROLLER,
                FeatureFlag.DOCTRINE_ENGINE,
                FeatureFlag.LANE_ORCHESTRATION,
                FeatureFlag.CERTIFICATION_LEVELS,
                FeatureFlag.AUDIT_TRAIL,
                FeatureFlag.CONSTITUTIONAL_GATES,
                FeatureFlag.API_ACCESS,
                FeatureFlag.SSO_INTEGRATION,
            },
        ),
        
        LicenseTier.ENTERPRISE: PricingPlan(
            tier=LicenseTier.ENTERPRISE,
            base_monthly_usd=Decimal("4999"),
            per_agent_monthly_usd=Decimal("49"),
            included_agents=25,
            max_agents=None,  # Unlimited
            annual_discount_percent=Decimal("25"),
            setup_fee_usd=Decimal("5000"),
            features={
                FeatureFlag.AGENT_REGISTRY,
                FeatureFlag.GID_MANAGEMENT,
                FeatureFlag.PAC_FRAMEWORK,
                FeatureFlag.BER_REPORTING,
                FeatureFlag.SCRAM_CONTROLLER,
                FeatureFlag.DOCTRINE_ENGINE,
                FeatureFlag.LANE_ORCHESTRATION,
                FeatureFlag.CERTIFICATION_LEVELS,
                FeatureFlag.AUDIT_TRAIL,
                FeatureFlag.CONSTITUTIONAL_GATES,
                FeatureFlag.CUSTOM_DOCTRINES,
                FeatureFlag.API_ACCESS,
                FeatureFlag.SSO_INTEGRATION,
                FeatureFlag.PRIORITY_SUPPORT,
            },
        ),
        
        LicenseTier.SOVEREIGN: PricingPlan(
            tier=LicenseTier.SOVEREIGN,
            base_monthly_usd=Decimal("19999"),
            per_agent_monthly_usd=Decimal("0"),  # Unlimited included
            included_agents=999,
            max_agents=None,
            annual_discount_percent=Decimal("30"),
            setup_fee_usd=Decimal("50000"),
            features={f for f in FeatureFlag},  # All features
        ),
    }
    
    @classmethod
    def get_plan(cls, tier: LicenseTier) -> PricingPlan:
        """Get pricing plan for tier."""
        return cls.CATALOG[tier]
    
    @classmethod
    def get_all_plans(cls) -> List[PricingPlan]:
        """Get all pricing plans."""
        return list(cls.CATALOG.values())
    
    @classmethod
    def recommend_tier(cls, agent_count: int, needs_custom_doctrines: bool) -> LicenseTier:
        """Recommend appropriate tier based on requirements."""
        if needs_custom_doctrines:
            if agent_count > 25:
                return LicenseTier.SOVEREIGN
            return LicenseTier.ENTERPRISE
        
        if agent_count <= 3:
            return LicenseTier.STARTER
        elif agent_count <= 20:
            return LicenseTier.PROFESSIONAL
        elif agent_count <= 50:
            return LicenseTier.ENTERPRISE
        else:
            return LicenseTier.SOVEREIGN


# =============================================================================
# LICENSE MANAGER
# =============================================================================

class LicenseManager:
    """
    Manages Agent University licensing operations.
    
    Responsibilities:
    - License provisioning and activation
    - Usage tracking and metering
    - Billing and invoicing
    - Feature enforcement
    
    Constitutional Compliance:
    - INV-NO-NARRATIVE-INFLATION: Real licensing metrics only
    - INV-FAIL-CLOSED: Strict feature gating
    """
    
    def __init__(self):
        self._customers: Dict[str, Customer] = {}
        self._licenses: Dict[str, License] = {}
        self._usage: List[UsageRecord] = []
        self._invoices: Dict[str, Invoice] = {}
        self._catalog = PricingCatalog()
    
    def _generate_license_key(self, license_id: str, customer_id: str) -> str:
        """Generate unique license key."""
        seed = f"{license_id}:{customer_id}:{datetime.now(timezone.utc).isoformat()}"
        hash_val = hashlib.sha256(seed.encode()).hexdigest()
        # Format: XXXX-XXXX-XXXX-XXXX
        return "-".join([hash_val[i:i+4].upper() for i in range(0, 16, 4)])
    
    def register_customer(
        self,
        company_name: str,
        industry: str,
        contact_email: str,
        contact_name: str,
        billing_address: str,
        deployment_model: DeploymentModel = DeploymentModel.SAAS,
    ) -> Customer:
        """Register a new customer."""
        customer_id = f"CUST-{uuid.uuid4().hex[:8].upper()}"
        
        customer = Customer(
            customer_id=customer_id,
            company_name=company_name,
            industry=industry,
            contact_email=contact_email,
            contact_name=contact_name,
            billing_address=billing_address,
            deployment_model=deployment_model,
            created_at=datetime.now(timezone.utc),
        )
        
        self._customers[customer_id] = customer
        return customer
    
    def create_trial_license(
        self,
        customer_id: str,
        tier: LicenseTier = LicenseTier.PROFESSIONAL,
        trial_days: int = 14,
    ) -> License:
        """Create a trial license."""
        customer = self._customers.get(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        
        plan = self._catalog.get_plan(tier)
        license_id = f"LIC-{uuid.uuid4().hex[:8].upper()}"
        
        now = datetime.now(timezone.utc)
        from datetime import timedelta
        end_date = now + timedelta(days=trial_days)
        
        license_key = self._generate_license_key(license_id, customer_id)
        
        license_obj = License(
            license_id=license_id,
            customer=customer,
            plan=plan,
            status=LicenseStatus.TRIAL,
            agent_count=plan.included_agents,
            start_date=now,
            end_date=end_date,
            renewal_date=None,
            is_annual=False,
            monthly_cost=Decimal("0"),  # Trial is free
            license_key=license_key,
            features_enabled=plan.features,
        )
        
        self._licenses[license_id] = license_obj
        return license_obj
    
    def activate_license(
        self,
        customer_id: str,
        tier: LicenseTier,
        agent_count: int,
        is_annual: bool = True,
    ) -> License:
        """Activate a paid license."""
        customer = self._customers.get(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        
        plan = self._catalog.get_plan(tier)
        
        # Validate agent count
        if plan.max_agents and agent_count > plan.max_agents:
            raise ValueError(
                f"Agent count {agent_count} exceeds tier maximum {plan.max_agents}"
            )
        
        license_id = f"LIC-{uuid.uuid4().hex[:8].upper()}"
        license_key = self._generate_license_key(license_id, customer_id)
        
        now = datetime.now(timezone.utc)
        from datetime import timedelta
        
        if is_annual:
            end_date = now + timedelta(days=365)
            monthly_cost = plan.calculate_annual(agent_count) / 12
        else:
            end_date = now + timedelta(days=30)
            monthly_cost = plan.calculate_monthly(agent_count)
        
        renewal_date = end_date - timedelta(days=30)  # Remind 30 days before
        
        license_obj = License(
            license_id=license_id,
            customer=customer,
            plan=plan,
            status=LicenseStatus.ACTIVE,
            agent_count=agent_count,
            start_date=now,
            end_date=end_date,
            renewal_date=renewal_date,
            is_annual=is_annual,
            monthly_cost=monthly_cost,
            license_key=license_key,
            features_enabled=plan.features,
        )
        
        self._licenses[license_id] = license_obj
        return license_obj
    
    def validate_license(self, license_key: str) -> Optional[License]:
        """Validate a license key and return license if valid."""
        for license_obj in self._licenses.values():
            if license_obj.license_key == license_key:
                # Check expiration
                if datetime.now(timezone.utc) > license_obj.end_date:
                    license_obj.status = LicenseStatus.EXPIRED
                    return None
                
                if license_obj.status == LicenseStatus.ACTIVE:
                    return license_obj
                elif license_obj.status == LicenseStatus.TRIAL:
                    return license_obj
        
        return None
    
    def check_feature(self, license_id: str, feature: FeatureFlag) -> bool:
        """Check if a feature is enabled for a license."""
        license_obj = self._licenses.get(license_id)
        if not license_obj or not license_obj.is_active:
            return False
        return feature in license_obj.features_enabled
    
    def record_usage(
        self,
        license_id: str,
        metric_type: str,
        count: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UsageRecord:
        """Record usage for a license."""
        license_obj = self._licenses.get(license_id)
        if not license_obj:
            raise ValueError(f"License {license_id} not found")
        
        record_id = f"USE-{uuid.uuid4().hex[:8].upper()}"
        
        record = UsageRecord(
            record_id=record_id,
            license_id=license_id,
            timestamp=datetime.now(timezone.utc),
            metric_type=metric_type,
            count=count,
            metadata=metadata or {},
        )
        
        self._usage.append(record)
        
        # Update license usage metrics
        if metric_type not in license_obj.usage_metrics:
            license_obj.usage_metrics[metric_type] = 0
        license_obj.usage_metrics[metric_type] += count
        
        return record
    
    def get_usage_summary(self, license_id: str) -> Dict[str, Any]:
        """Get usage summary for a license."""
        license_obj = self._licenses.get(license_id)
        if not license_obj:
            raise ValueError(f"License {license_id} not found")
        
        usage_records = [u for u in self._usage if u.license_id == license_id]
        
        by_type = {}
        for record in usage_records:
            if record.metric_type not in by_type:
                by_type[record.metric_type] = 0
            by_type[record.metric_type] += record.count
        
        return {
            "license_id": license_id,
            "total_records": len(usage_records),
            "by_type": by_type,
            "current_agent_count": license_obj.agent_count,
            "max_agents": license_obj.plan.max_agents,
        }
    
    def upgrade_license(
        self,
        license_id: str,
        new_tier: LicenseTier,
        new_agent_count: Optional[int] = None,
    ) -> License:
        """Upgrade a license to a higher tier."""
        license_obj = self._licenses.get(license_id)
        if not license_obj:
            raise ValueError(f"License {license_id} not found")
        
        current_tier_value = list(LicenseTier).index(license_obj.plan.tier)
        new_tier_value = list(LicenseTier).index(new_tier)
        
        if new_tier_value <= current_tier_value:
            raise ValueError("Can only upgrade to a higher tier")
        
        new_plan = self._catalog.get_plan(new_tier)
        agent_count = new_agent_count or license_obj.agent_count
        
        license_obj.plan = new_plan
        license_obj.agent_count = agent_count
        license_obj.monthly_cost = new_plan.calculate_monthly(agent_count)
        license_obj.features_enabled = new_plan.features
        
        return license_obj
    
    def suspend_license(self, license_id: str, reason: str) -> License:
        """Suspend a license."""
        license_obj = self._licenses.get(license_id)
        if not license_obj:
            raise ValueError(f"License {license_id} not found")
        
        license_obj.status = LicenseStatus.SUSPENDED
        license_obj.usage_metrics["suspension_reason"] = reason
        
        return license_obj
    
    def get_arr_metrics(self) -> Dict[str, Any]:
        """Get Annual Recurring Revenue metrics."""
        active_licenses = [l for l in self._licenses.values() if l.is_active]
        
        total_mrr = sum(l.monthly_cost for l in active_licenses)
        total_arr = total_mrr * 12
        
        by_tier = {}
        for tier in LicenseTier:
            tier_licenses = [l for l in active_licenses if l.plan.tier == tier]
            tier_mrr = sum(l.monthly_cost for l in tier_licenses)
            by_tier[tier.value] = {
                "count": len(tier_licenses),
                "mrr": str(tier_mrr),
                "arr": str(tier_mrr * 12),
            }
        
        return {
            "total_licenses": len(self._licenses),
            "active_licenses": len(active_licenses),
            "total_mrr": str(total_mrr),
            "total_arr": str(total_arr),
            "by_tier": by_tier,
            "total_customers": len(self._customers),
        }
    
    def get_license(self, license_id: str) -> Optional[License]:
        """Get license by ID."""
        return self._licenses.get(license_id)
    
    def get_customer_licenses(self, customer_id: str) -> List[License]:
        """Get all licenses for a customer."""
        return [l for l in self._licenses.values() if l.customer.customer_id == customer_id]


# =============================================================================
# FEATURE GATE
# =============================================================================

class FeatureGate:
    """
    Feature gating for licensed Agent University instances.
    
    Enforces license-based access control to platform features.
    """
    
    def __init__(self, license_manager: LicenseManager):
        self._license_manager = license_manager
    
    def check_access(
        self,
        license_key: str,
        feature: FeatureFlag,
    ) -> tuple[bool, str]:
        """
        Check if license has access to feature.
        
        Returns:
            Tuple of (allowed, reason)
        """
        license_obj = self._license_manager.validate_license(license_key)
        
        if not license_obj:
            return False, "Invalid or expired license"
        
        if license_obj.status == LicenseStatus.SUSPENDED:
            return False, "License suspended"
        
        if feature in license_obj.features_enabled:
            return True, "Access granted"
        
        return False, f"Feature {feature.value} not included in {license_obj.plan.tier.value} tier"
    
    def enforce_agent_limit(
        self,
        license_key: str,
        requested_agents: int,
    ) -> tuple[bool, str]:
        """
        Enforce agent count limits.
        
        Returns:
            Tuple of (allowed, reason)
        """
        license_obj = self._license_manager.validate_license(license_key)
        
        if not license_obj:
            return False, "Invalid or expired license"
        
        max_agents = license_obj.plan.max_agents
        
        if max_agents is None:
            return True, "Unlimited agents allowed"
        
        if requested_agents <= max_agents:
            return True, f"Within limit ({requested_agents}/{max_agents})"
        
        return False, f"Agent limit exceeded ({requested_agents}/{max_agents})"


# =============================================================================
# SELF-TEST
# =============================================================================

def self_test() -> bool:
    """Self-test for licensing module."""
    print("=" * 60)
    print("AGENT UNIVERSITY LICENSING - SELF TEST")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Create manager
    tests_total += 1
    try:
        manager = LicenseManager()
        print("✅ TEST 1: Manager creation - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 1: Manager creation - FAILED: {e}")
        return False
    
    # Test 2: Pricing catalog
    tests_total += 1
    try:
        starter_plan = PricingCatalog.get_plan(LicenseTier.STARTER)
        assert starter_plan.base_monthly_usd == Decimal("299")
        enterprise_plan = PricingCatalog.get_plan(LicenseTier.ENTERPRISE)
        assert FeatureFlag.CUSTOM_DOCTRINES in enterprise_plan.features
        print("✅ TEST 2: Pricing catalog - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 2: Pricing catalog - FAILED: {e}")
    
    # Test 3: Register customer
    tests_total += 1
    try:
        customer = manager.register_customer(
            company_name="TechCorp AI",
            industry="Technology",
            contact_email="admin@techcorp.ai",
            contact_name="Jane Doe",
            billing_address="123 Tech Street, SF, CA 94102",
        )
        assert customer.customer_id.startswith("CUST-")
        print(f"✅ TEST 3: Customer registration ({customer.customer_id}) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 3: Customer registration - FAILED: {e}")
    
    # Test 4: Create trial license
    tests_total += 1
    try:
        trial = manager.create_trial_license(
            customer_id=customer.customer_id,
            tier=LicenseTier.PROFESSIONAL,
            trial_days=14,
        )
        assert trial.status == LicenseStatus.TRIAL
        assert trial.monthly_cost == Decimal("0")
        print(f"✅ TEST 4: Trial license ({trial.license_id}) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 4: Trial license - FAILED: {e}")
    
    # Test 5: Activate paid license
    tests_total += 1
    try:
        license_obj = manager.activate_license(
            customer_id=customer.customer_id,
            tier=LicenseTier.ENTERPRISE,
            agent_count=30,
            is_annual=True,
        )
        assert license_obj.status == LicenseStatus.ACTIVE
        assert license_obj.is_active
        print(f"✅ TEST 5: Paid license (${license_obj.monthly_cost}/mo) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 5: Paid license - FAILED: {e}")
    
    # Test 6: Validate license key
    tests_total += 1
    try:
        validated = manager.validate_license(license_obj.license_key)
        assert validated is not None
        assert validated.license_id == license_obj.license_id
        print(f"✅ TEST 6: License validation ({license_obj.license_key[:8]}...) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 6: License validation - FAILED: {e}")
    
    # Test 7: Feature check
    tests_total += 1
    try:
        has_scram = manager.check_feature(license_obj.license_id, FeatureFlag.SCRAM_CONTROLLER)
        assert has_scram  # Enterprise includes SCRAM
        has_source = manager.check_feature(license_obj.license_id, FeatureFlag.SOURCE_ACCESS)
        assert not has_source  # Source access is SOVEREIGN only
        print("✅ TEST 7: Feature checking - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 7: Feature checking - FAILED: {e}")
    
    # Test 8: Usage recording
    tests_total += 1
    try:
        usage = manager.record_usage(
            license_obj.license_id,
            "agent_invocation",
            count=100,
        )
        summary = manager.get_usage_summary(license_obj.license_id)
        assert summary["by_type"]["agent_invocation"] == 100
        print(f"✅ TEST 8: Usage recording ({summary['by_type']}) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 8: Usage recording - FAILED: {e}")
    
    # Test 9: Feature gate
    tests_total += 1
    try:
        gate = FeatureGate(manager)
        allowed, reason = gate.check_access(license_obj.license_key, FeatureFlag.DOCTRINE_ENGINE)
        assert allowed
        allowed, reason = gate.check_access(license_obj.license_key, FeatureFlag.SOURCE_ACCESS)
        assert not allowed
        print("✅ TEST 9: Feature gate - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 9: Feature gate - FAILED: {e}")
    
    # Test 10: ARR metrics
    tests_total += 1
    try:
        metrics = manager.get_arr_metrics()
        assert int(metrics["active_licenses"]) >= 1
        assert Decimal(metrics["total_arr"]) > 0
        print(f"✅ TEST 10: ARR metrics (ARR=${metrics['total_arr']}) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 10: ARR metrics - FAILED: {e}")
    
    # Summary
    print("=" * 60)
    print(f"LICENSING TESTS: {tests_passed}/{tests_total} PASSED")
    print("=" * 60)
    
    return tests_passed == tests_total


if __name__ == "__main__":
    success = self_test()
    exit(0 if success else 1)
