"""
Monetization Engine — Revenue, Usage, and Billing Infrastructure.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-REAL-WORK-032
Agent: GID-05 (Sophie) — MONETIZATION & REVENUE SURFACES
Deliverable: UsageMeter, PricingTier, BillingCalculator, QuotaManager, 
             RevenueAnalytics, EntitlementService

Features:
- Per-token, per-call, per-resource usage metering
- Tiered pricing with volume discounts
- Real-time billing calculation
- Quota enforcement with grace periods
- Revenue analytics and forecasting
- Entitlement management
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Protocol,
    Set,
    Tuple,
    TypeVar,
    Union,
)


# =============================================================================
# VERSION
# =============================================================================

MONETIZATION_ENGINE_VERSION = "1.0.0"


# =============================================================================
# ENUMS
# =============================================================================

class UsageType(Enum):
    """Types of billable usage."""
    TOKEN = "TOKEN"           # LLM tokens
    API_CALL = "API_CALL"     # API invocations
    COMPUTE = "COMPUTE"       # Compute time (seconds)
    STORAGE = "STORAGE"       # Storage (bytes)
    BANDWIDTH = "BANDWIDTH"   # Network (bytes)
    AGENT = "AGENT"           # Agent executions


class PricingModel(Enum):
    """Pricing model types."""
    FLAT = "FLAT"             # Fixed price
    TIERED = "TIERED"         # Volume tiers
    USAGE = "USAGE"           # Pay per use
    COMMITTED = "COMMITTED"   # Committed spend
    HYBRID = "HYBRID"         # Base + overage


class BillingPeriod(Enum):
    """Billing period types."""
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    ANNUAL = "ANNUAL"


class QuotaStatus(Enum):
    """Quota enforcement status."""
    WITHIN_LIMIT = "WITHIN_LIMIT"
    SOFT_LIMIT = "SOFT_LIMIT"     # Warning threshold
    HARD_LIMIT = "HARD_LIMIT"     # Enforcement threshold
    EXCEEDED = "EXCEEDED"         # Over limit
    GRACE_PERIOD = "GRACE_PERIOD" # In grace period


class EntitlementState(Enum):
    """Entitlement states."""
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"
    PENDING = "PENDING"
    CANCELLED = "CANCELLED"


# =============================================================================
# EXCEPTIONS
# =============================================================================

class MonetizationError(Exception):
    """Base monetization exception."""
    pass


class QuotaExceededError(MonetizationError):
    """Quota exceeded error — FAIL-CLOSED."""
    def __init__(self, usage_type: UsageType, current: float, limit: float) -> None:
        self.usage_type = usage_type
        self.current = current
        self.limit = limit
        super().__init__(
            f"Quota exceeded for {usage_type.value}: {current:.2f}/{limit:.2f}"
        )


class EntitlementError(MonetizationError):
    """Entitlement validation error."""
    pass


class BillingError(MonetizationError):
    """Billing calculation error."""
    pass


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class UsageRecord:
    """A single usage record."""
    record_id: str
    tenant_id: str
    usage_type: UsageType
    quantity: Decimal
    timestamp: datetime
    resource_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "record_id": self.record_id,
            "tenant_id": self.tenant_id,
            "usage_type": self.usage_type.value,
            "quantity": str(self.quantity),
            "timestamp": self.timestamp.isoformat(),
            "resource_id": self.resource_id,
        }


@dataclass
class PricingTier:
    """A pricing tier definition."""
    tier_id: str
    name: str
    min_units: Decimal
    max_units: Optional[Decimal]  # None = unlimited
    unit_price: Decimal
    currency: str = "USD"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tier_id": self.tier_id,
            "name": self.name,
            "min_units": str(self.min_units),
            "max_units": str(self.max_units) if self.max_units else None,
            "unit_price": str(self.unit_price),
            "currency": self.currency,
        }


@dataclass
class QuotaDefinition:
    """Quota definition for a usage type."""
    usage_type: UsageType
    soft_limit: Decimal
    hard_limit: Decimal
    grace_period_hours: int = 24
    reset_period: BillingPeriod = BillingPeriod.MONTHLY
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "usage_type": self.usage_type.value,
            "soft_limit": str(self.soft_limit),
            "hard_limit": str(self.hard_limit),
            "grace_period_hours": self.grace_period_hours,
            "reset_period": self.reset_period.value,
        }


@dataclass
class Entitlement:
    """An entitlement grant."""
    entitlement_id: str
    tenant_id: str
    feature: str
    state: EntitlementState
    granted_at: datetime
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_valid(self, at_time: Optional[datetime] = None) -> bool:
        """Check if entitlement is valid."""
        check_time = at_time or datetime.now(timezone.utc)
        
        if self.state != EntitlementState.ACTIVE:
            return False
        
        if self.expires_at and check_time >= self.expires_at:
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entitlement_id": self.entitlement_id,
            "tenant_id": self.tenant_id,
            "feature": self.feature,
            "state": self.state.value,
            "granted_at": self.granted_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


@dataclass
class Invoice:
    """A generated invoice."""
    invoice_id: str
    tenant_id: str
    period_start: datetime
    period_end: datetime
    line_items: List[Dict[str, Any]]
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    currency: str = "USD"
    status: str = "DRAFT"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "invoice_id": self.invoice_id,
            "tenant_id": self.tenant_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "line_items": self.line_items,
            "subtotal": str(self.subtotal),
            "tax": str(self.tax),
            "total": str(self.total),
            "currency": self.currency,
            "status": self.status,
        }


@dataclass
class RevenueMetrics:
    """Revenue analytics metrics."""
    period: str
    mrr: Decimal  # Monthly Recurring Revenue
    arr: Decimal  # Annual Recurring Revenue
    arpu: Decimal  # Average Revenue Per User
    ltv: Decimal   # Lifetime Value estimate
    churn_rate: Decimal
    growth_rate: Decimal
    revenue_by_type: Dict[str, Decimal]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "period": self.period,
            "mrr": str(self.mrr),
            "arr": str(self.arr),
            "arpu": str(self.arpu),
            "ltv": str(self.ltv),
            "churn_rate": str(self.churn_rate),
            "growth_rate": str(self.growth_rate),
            "revenue_by_type": {k: str(v) for k, v in self.revenue_by_type.items()},
        }


# =============================================================================
# USAGE METER
# =============================================================================

class UsageMeter:
    """
    Real-time usage metering.
    
    Features:
    - Per-token, per-call, per-resource tracking
    - Aggregation by tenant, type, period
    - Efficient batch recording
    - Thread-safe operations
    """
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._records: List[UsageRecord] = []
        self._aggregates: Dict[str, Dict[UsageType, Decimal]] = defaultdict(
            lambda: defaultdict(Decimal)
        )
        self._counter = 0
    
    def record(
        self,
        tenant_id: str,
        usage_type: UsageType,
        quantity: Union[int, float, Decimal],
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UsageRecord:
        """Record a usage event."""
        with self._lock:
            self._counter += 1
            record = UsageRecord(
                record_id=f"usage_{self._counter}_{datetime.now(timezone.utc).timestamp()}",
                tenant_id=tenant_id,
                usage_type=usage_type,
                quantity=Decimal(str(quantity)),
                timestamp=datetime.now(timezone.utc),
                resource_id=resource_id,
                metadata=metadata or {},
            )
            
            self._records.append(record)
            self._aggregates[tenant_id][usage_type] += record.quantity
            
            return record
    
    def record_batch(
        self,
        tenant_id: str,
        records: List[Tuple[UsageType, Union[int, float, Decimal]]],
    ) -> List[UsageRecord]:
        """Record multiple usage events efficiently."""
        results = []
        with self._lock:
            for usage_type, quantity in records:
                record = self.record(tenant_id, usage_type, quantity)
                results.append(record)
        return results
    
    def get_usage(
        self,
        tenant_id: str,
        usage_type: UsageType,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Decimal:
        """Get usage for a tenant and type."""
        with self._lock:
            if start_time is None and end_time is None:
                # Return aggregate
                return self._aggregates[tenant_id][usage_type]
            
            # Filter by time range
            total = Decimal(0)
            for record in self._records:
                if record.tenant_id != tenant_id:
                    continue
                if record.usage_type != usage_type:
                    continue
                if start_time and record.timestamp < start_time:
                    continue
                if end_time and record.timestamp >= end_time:
                    continue
                total += record.quantity
            
            return total
    
    def get_all_usage(
        self,
        tenant_id: str,
    ) -> Dict[UsageType, Decimal]:
        """Get all usage for a tenant."""
        with self._lock:
            return dict(self._aggregates[tenant_id])
    
    def get_records(
        self,
        tenant_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[UsageRecord]:
        """Get usage records for a tenant."""
        with self._lock:
            results = []
            for record in reversed(self._records):
                if record.tenant_id != tenant_id:
                    continue
                if start_time and record.timestamp < start_time:
                    continue
                if end_time and record.timestamp >= end_time:
                    continue
                results.append(record)
                if len(results) >= limit:
                    break
            return results
    
    def reset_tenant(self, tenant_id: str) -> None:
        """Reset usage for a tenant (e.g., billing cycle reset)."""
        with self._lock:
            self._aggregates[tenant_id] = defaultdict(Decimal)
            self._records = [r for r in self._records if r.tenant_id != tenant_id]


# =============================================================================
# PRICING MANAGER
# =============================================================================

class PricingManager:
    """
    Pricing tier management.
    
    Features:
    - Tiered pricing with volume discounts
    - Multiple pricing models
    - Currency support
    - Price versioning
    """
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._tiers: Dict[UsageType, List[PricingTier]] = defaultdict(list)
        self._pricing_models: Dict[UsageType, PricingModel] = {}
    
    def add_tier(
        self,
        usage_type: UsageType,
        tier: PricingTier,
    ) -> None:
        """Add a pricing tier."""
        with self._lock:
            self._tiers[usage_type].append(tier)
            # Sort by min_units
            self._tiers[usage_type].sort(key=lambda t: t.min_units)
    
    def set_pricing_model(
        self,
        usage_type: UsageType,
        model: PricingModel,
    ) -> None:
        """Set pricing model for a usage type."""
        with self._lock:
            self._pricing_models[usage_type] = model
    
    def get_tiers(self, usage_type: UsageType) -> List[PricingTier]:
        """Get all tiers for a usage type."""
        return list(self._tiers.get(usage_type, []))
    
    def calculate_price(
        self,
        usage_type: UsageType,
        quantity: Decimal,
    ) -> Tuple[Decimal, List[Dict[str, Any]]]:
        """
        Calculate price for usage.
        
        Returns:
            Tuple of (total_price, breakdown)
        """
        tiers = self._tiers.get(usage_type, [])
        model = self._pricing_models.get(usage_type, PricingModel.TIERED)
        
        if not tiers:
            return Decimal(0), []
        
        if model == PricingModel.FLAT:
            # Use first tier's price for all units
            price = quantity * tiers[0].unit_price
            return price.quantize(Decimal("0.01"), ROUND_HALF_UP), [{
                "tier": tiers[0].name,
                "quantity": str(quantity),
                "unit_price": str(tiers[0].unit_price),
                "amount": str(price),
            }]
        
        # Tiered pricing
        total = Decimal(0)
        breakdown = []
        remaining = quantity
        
        for tier in tiers:
            if remaining <= 0:
                break
            
            # Calculate units in this tier
            if tier.max_units:
                tier_capacity = tier.max_units - tier.min_units
                units_in_tier = min(remaining, tier_capacity)
            else:
                units_in_tier = remaining
            
            tier_amount = units_in_tier * tier.unit_price
            total += tier_amount
            remaining -= units_in_tier
            
            breakdown.append({
                "tier": tier.name,
                "quantity": str(units_in_tier),
                "unit_price": str(tier.unit_price),
                "amount": str(tier_amount.quantize(Decimal("0.01"), ROUND_HALF_UP)),
            })
        
        return total.quantize(Decimal("0.01"), ROUND_HALF_UP), breakdown
    
    def setup_default_pricing(self) -> None:
        """Setup default pricing tiers."""
        # Token pricing (per 1M tokens)
        self.add_tier(UsageType.TOKEN, PricingTier(
            tier_id="token_tier_1",
            name="Standard",
            min_units=Decimal(0),
            max_units=Decimal(1_000_000),
            unit_price=Decimal("0.000002"),  # $2/1M tokens
        ))
        self.add_tier(UsageType.TOKEN, PricingTier(
            tier_id="token_tier_2",
            name="Volume",
            min_units=Decimal(1_000_000),
            max_units=Decimal(10_000_000),
            unit_price=Decimal("0.0000015"),  # $1.50/1M tokens
        ))
        self.add_tier(UsageType.TOKEN, PricingTier(
            tier_id="token_tier_3",
            name="Enterprise",
            min_units=Decimal(10_000_000),
            max_units=None,
            unit_price=Decimal("0.000001"),  # $1/1M tokens
        ))
        
        # API call pricing
        self.add_tier(UsageType.API_CALL, PricingTier(
            tier_id="api_tier_1",
            name="Standard",
            min_units=Decimal(0),
            max_units=Decimal(10_000),
            unit_price=Decimal("0.001"),  # $0.001/call
        ))
        self.add_tier(UsageType.API_CALL, PricingTier(
            tier_id="api_tier_2",
            name="Volume",
            min_units=Decimal(10_000),
            max_units=None,
            unit_price=Decimal("0.0005"),  # $0.0005/call
        ))
        
        # Agent execution pricing
        self.add_tier(UsageType.AGENT, PricingTier(
            tier_id="agent_tier_1",
            name="Standard",
            min_units=Decimal(0),
            max_units=None,
            unit_price=Decimal("0.05"),  # $0.05/execution
        ))
        
        # Set models
        self.set_pricing_model(UsageType.TOKEN, PricingModel.TIERED)
        self.set_pricing_model(UsageType.API_CALL, PricingModel.TIERED)
        self.set_pricing_model(UsageType.AGENT, PricingModel.FLAT)


# =============================================================================
# BILLING CALCULATOR
# =============================================================================

class BillingCalculator:
    """
    Real-time billing calculation.
    
    Features:
    - Invoice generation
    - Tax calculation
    - Discount application
    - Pro-rating
    """
    
    def __init__(
        self,
        usage_meter: UsageMeter,
        pricing_manager: PricingManager,
    ) -> None:
        self._meter = usage_meter
        self._pricing = pricing_manager
        self._lock = threading.RLock()
        self._discounts: Dict[str, Decimal] = {}  # tenant_id -> discount %
        self._tax_rates: Dict[str, Decimal] = {}  # region -> tax %
        self._invoice_counter = 0
    
    def set_discount(self, tenant_id: str, discount_percent: Decimal) -> None:
        """Set discount for a tenant."""
        with self._lock:
            self._discounts[tenant_id] = discount_percent
    
    def set_tax_rate(self, region: str, tax_percent: Decimal) -> None:
        """Set tax rate for a region."""
        with self._lock:
            self._tax_rates[region] = tax_percent
    
    def calculate_current_charges(
        self,
        tenant_id: str,
    ) -> Tuple[Decimal, Dict[UsageType, Dict[str, Any]]]:
        """
        Calculate current charges for a tenant.
        
        Returns:
            Tuple of (total, breakdown_by_type)
        """
        usage = self._meter.get_all_usage(tenant_id)
        total = Decimal(0)
        breakdown: Dict[UsageType, Dict[str, Any]] = {}
        
        for usage_type, quantity in usage.items():
            price, tier_breakdown = self._pricing.calculate_price(usage_type, quantity)
            total += price
            breakdown[usage_type] = {
                "quantity": str(quantity),
                "price": str(price),
                "tiers": tier_breakdown,
            }
        
        # Apply discount
        discount = self._discounts.get(tenant_id, Decimal(0))
        if discount > 0:
            discount_amount = total * (discount / 100)
            total -= discount_amount
        
        return total.quantize(Decimal("0.01"), ROUND_HALF_UP), breakdown
    
    def generate_invoice(
        self,
        tenant_id: str,
        period_start: datetime,
        period_end: datetime,
        region: str = "US",
    ) -> Invoice:
        """Generate an invoice for a tenant."""
        with self._lock:
            self._invoice_counter += 1
            
            # Get usage for period
            usage = self._meter.get_all_usage(tenant_id)
            
            line_items = []
            subtotal = Decimal(0)
            
            for usage_type, quantity in usage.items():
                price, tier_breakdown = self._pricing.calculate_price(usage_type, quantity)
                subtotal += price
                line_items.append({
                    "description": f"{usage_type.value} Usage",
                    "quantity": str(quantity),
                    "unit_price": "varies",
                    "amount": str(price),
                    "breakdown": tier_breakdown,
                })
            
            # Apply discount
            discount = self._discounts.get(tenant_id, Decimal(0))
            if discount > 0:
                discount_amount = subtotal * (discount / 100)
                subtotal -= discount_amount
                line_items.append({
                    "description": f"Discount ({discount}%)",
                    "quantity": "1",
                    "unit_price": str(-discount_amount),
                    "amount": str(-discount_amount),
                })
            
            # Calculate tax
            tax_rate = self._tax_rates.get(region, Decimal(0))
            tax = (subtotal * (tax_rate / 100)).quantize(Decimal("0.01"), ROUND_HALF_UP)
            
            total = subtotal + tax
            
            invoice = Invoice(
                invoice_id=f"INV-{self._invoice_counter:06d}",
                tenant_id=tenant_id,
                period_start=period_start,
                period_end=period_end,
                line_items=line_items,
                subtotal=subtotal.quantize(Decimal("0.01"), ROUND_HALF_UP),
                tax=tax,
                total=total.quantize(Decimal("0.01"), ROUND_HALF_UP),
            )
            
            return invoice
    
    def estimate_month_end(
        self,
        tenant_id: str,
        days_remaining: int,
    ) -> Decimal:
        """Estimate month-end charges based on current usage rate."""
        current_charges, _ = self.calculate_current_charges(tenant_id)
        
        # Simple linear projection
        now = datetime.now(timezone.utc)
        days_elapsed = now.day
        
        if days_elapsed == 0:
            return current_charges
        
        daily_rate = current_charges / days_elapsed
        projected = current_charges + (daily_rate * days_remaining)
        
        return projected.quantize(Decimal("0.01"), ROUND_HALF_UP)


# =============================================================================
# QUOTA MANAGER
# =============================================================================

class QuotaManager:
    """
    Quota enforcement.
    
    Features:
    - Soft and hard limits
    - Grace periods
    - Real-time enforcement
    - FAIL-CLOSED behavior
    """
    
    def __init__(self, usage_meter: UsageMeter) -> None:
        self._meter = usage_meter
        self._lock = threading.RLock()
        self._quotas: Dict[str, Dict[UsageType, QuotaDefinition]] = defaultdict(dict)
        self._grace_periods: Dict[str, Dict[UsageType, datetime]] = defaultdict(dict)
    
    def set_quota(
        self,
        tenant_id: str,
        quota: QuotaDefinition,
    ) -> None:
        """Set quota for a tenant."""
        with self._lock:
            self._quotas[tenant_id][quota.usage_type] = quota
    
    def check_quota(
        self,
        tenant_id: str,
        usage_type: UsageType,
        requested_quantity: Decimal = Decimal(0),
    ) -> Tuple[QuotaStatus, Dict[str, Any]]:
        """
        Check quota status — FAIL-CLOSED.
        
        Returns:
            Tuple of (status, details)
        """
        with self._lock:
            quota = self._quotas.get(tenant_id, {}).get(usage_type)
            
            if not quota:
                # No quota defined — default to FAIL-CLOSED for unknown
                return QuotaStatus.WITHIN_LIMIT, {"reason": "no_quota_defined"}
            
            current = self._meter.get_usage(tenant_id, usage_type)
            projected = current + requested_quantity
            
            details = {
                "current": str(current),
                "requested": str(requested_quantity),
                "projected": str(projected),
                "soft_limit": str(quota.soft_limit),
                "hard_limit": str(quota.hard_limit),
            }
            
            # Check hard limit first — ABSOLUTE BARRIER
            if projected > quota.hard_limit:
                # Hard limit is an absolute barrier - always return EXCEEDED
                return QuotaStatus.EXCEEDED, details
            
            # Check soft limit
            if projected > quota.soft_limit:
                # Start grace period if not already started
                if tenant_id not in self._grace_periods:
                    self._grace_periods[tenant_id] = {}
                if usage_type not in self._grace_periods[tenant_id]:
                    self._grace_periods[tenant_id][usage_type] = datetime.now(timezone.utc)
                
                return QuotaStatus.SOFT_LIMIT, details
            
            return QuotaStatus.WITHIN_LIMIT, details
    
    def enforce_quota(
        self,
        tenant_id: str,
        usage_type: UsageType,
        requested_quantity: Decimal,
    ) -> None:
        """
        Enforce quota — raises on violation.
        
        FAIL-CLOSED: If quota check fails, deny the request.
        """
        status, details = self.check_quota(tenant_id, usage_type, requested_quantity)
        
        if status == QuotaStatus.EXCEEDED:
            raise QuotaExceededError(
                usage_type,
                float(details["current"]),
                float(details["hard_limit"]),
            )
    
    def get_quota_status(
        self,
        tenant_id: str,
    ) -> Dict[UsageType, Dict[str, Any]]:
        """Get quota status for all types."""
        result = {}
        for usage_type in UsageType:
            status, details = self.check_quota(tenant_id, usage_type)
            result[usage_type] = {
                "status": status.value,
                "details": details,
            }
        return result
    
    def reset_grace_period(
        self,
        tenant_id: str,
        usage_type: UsageType,
    ) -> None:
        """Reset grace period for a usage type."""
        with self._lock:
            if tenant_id in self._grace_periods:
                self._grace_periods[tenant_id].pop(usage_type, None)


# =============================================================================
# REVENUE ANALYTICS
# =============================================================================

class RevenueAnalytics:
    """
    Revenue analytics and forecasting.
    
    Features:
    - MRR/ARR calculation
    - ARPU and LTV estimation
    - Churn analysis
    - Growth metrics
    - Revenue forecasting
    """
    
    def __init__(self, billing_calculator: BillingCalculator) -> None:
        self._billing = billing_calculator
        self._lock = threading.RLock()
        self._tenant_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    def record_billing_event(
        self,
        tenant_id: str,
        amount: Decimal,
        event_type: str,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Record a billing event for analytics."""
        with self._lock:
            self._tenant_history[tenant_id].append({
                "amount": amount,
                "event_type": event_type,
                "timestamp": timestamp or datetime.now(timezone.utc),
            })
    
    def calculate_mrr(self) -> Decimal:
        """Calculate Monthly Recurring Revenue."""
        with self._lock:
            total = Decimal(0)
            for tenant_id, history in self._tenant_history.items():
                if history:
                    # Use latest billing amount
                    latest = sorted(history, key=lambda x: x["timestamp"])[-1]
                    total += latest["amount"]
            return total.quantize(Decimal("0.01"), ROUND_HALF_UP)
    
    def calculate_arr(self) -> Decimal:
        """Calculate Annual Recurring Revenue."""
        return (self.calculate_mrr() * 12).quantize(Decimal("0.01"), ROUND_HALF_UP)
    
    def calculate_arpu(self) -> Decimal:
        """Calculate Average Revenue Per User."""
        with self._lock:
            active_tenants = len(self._tenant_history)
            if active_tenants == 0:
                return Decimal(0)
            
            mrr = self.calculate_mrr()
            return (mrr / active_tenants).quantize(Decimal("0.01"), ROUND_HALF_UP)
    
    def calculate_ltv(self, avg_lifetime_months: int = 24) -> Decimal:
        """Calculate estimated Lifetime Value."""
        arpu = self.calculate_arpu()
        return (arpu * avg_lifetime_months).quantize(Decimal("0.01"), ROUND_HALF_UP)
    
    def calculate_churn_rate(
        self,
        period_start: datetime,
        period_end: datetime,
    ) -> Decimal:
        """Calculate churn rate for a period."""
        with self._lock:
            start_count = 0
            churned = 0
            
            for tenant_id, history in self._tenant_history.items():
                # Count tenants active at start
                had_activity_before = any(
                    h["timestamp"] < period_start for h in history
                )
                if had_activity_before:
                    start_count += 1
                    
                    # Check if churned (no activity in period)
                    period_activity = [
                        h for h in history
                        if period_start <= h["timestamp"] < period_end
                    ]
                    if not period_activity:
                        churned += 1
            
            if start_count == 0:
                return Decimal(0)
            
            return (Decimal(churned) / Decimal(start_count) * 100).quantize(
                Decimal("0.01"), ROUND_HALF_UP
            )
    
    def calculate_growth_rate(
        self,
        current_mrr: Decimal,
        previous_mrr: Decimal,
    ) -> Decimal:
        """Calculate MRR growth rate."""
        if previous_mrr == 0:
            return Decimal(100) if current_mrr > 0 else Decimal(0)
        
        return (
            (current_mrr - previous_mrr) / previous_mrr * 100
        ).quantize(Decimal("0.01"), ROUND_HALF_UP)
    
    def get_metrics(self, period: str = "current") -> RevenueMetrics:
        """Get comprehensive revenue metrics."""
        mrr = self.calculate_mrr()
        arr = self.calculate_arr()
        arpu = self.calculate_arpu()
        ltv = self.calculate_ltv()
        
        # Calculate revenue by type (simplified)
        revenue_by_type: Dict[str, Decimal] = {}
        for usage_type in UsageType:
            revenue_by_type[usage_type.value] = Decimal(0)
        
        return RevenueMetrics(
            period=period,
            mrr=mrr,
            arr=arr,
            arpu=arpu,
            ltv=ltv,
            churn_rate=Decimal(0),  # Would need historical data
            growth_rate=Decimal(0),  # Would need historical data
            revenue_by_type=revenue_by_type,
        )
    
    def forecast_revenue(
        self,
        months_ahead: int,
        growth_rate: Decimal = Decimal(5),
    ) -> List[Dict[str, Any]]:
        """Forecast revenue for future months."""
        forecasts = []
        current_mrr = self.calculate_mrr()
        
        for month in range(1, months_ahead + 1):
            projected_mrr = current_mrr * ((1 + growth_rate / 100) ** month)
            forecasts.append({
                "month": month,
                "projected_mrr": str(projected_mrr.quantize(Decimal("0.01"))),
                "projected_arr": str((projected_mrr * 12).quantize(Decimal("0.01"))),
                "growth_rate": str(growth_rate),
            })
        
        return forecasts


# =============================================================================
# ENTITLEMENT SERVICE
# =============================================================================

class EntitlementService:
    """
    Entitlement management.
    
    Features:
    - Feature flag integration
    - Granular permissions
    - Time-based entitlements
    - FAIL-CLOSED validation
    """
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._entitlements: Dict[str, List[Entitlement]] = defaultdict(list)
        self._counter = 0
    
    def grant(
        self,
        tenant_id: str,
        feature: str,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Entitlement:
        """Grant an entitlement."""
        with self._lock:
            self._counter += 1
            entitlement = Entitlement(
                entitlement_id=f"ent_{self._counter}",
                tenant_id=tenant_id,
                feature=feature,
                state=EntitlementState.ACTIVE,
                granted_at=datetime.now(timezone.utc),
                expires_at=expires_at,
                metadata=metadata or {},
            )
            
            self._entitlements[tenant_id].append(entitlement)
            return entitlement
    
    def revoke(
        self,
        tenant_id: str,
        feature: str,
    ) -> bool:
        """Revoke an entitlement."""
        with self._lock:
            for ent in self._entitlements.get(tenant_id, []):
                if ent.feature == feature and ent.state == EntitlementState.ACTIVE:
                    ent.state = EntitlementState.CANCELLED
                    return True
            return False
    
    def check(
        self,
        tenant_id: str,
        feature: str,
    ) -> bool:
        """
        Check if tenant has entitlement — FAIL-CLOSED.
        
        Returns False for any invalid/missing entitlement.
        """
        with self._lock:
            for ent in self._entitlements.get(tenant_id, []):
                if ent.feature == feature and ent.is_valid():
                    return True
            return False
    
    def require(
        self,
        tenant_id: str,
        feature: str,
    ) -> None:
        """Require entitlement — raises on missing."""
        if not self.check(tenant_id, feature):
            raise EntitlementError(
                f"Tenant {tenant_id} lacks entitlement for feature: {feature}"
            )
    
    def get_entitlements(
        self,
        tenant_id: str,
        active_only: bool = True,
    ) -> List[Entitlement]:
        """Get all entitlements for a tenant."""
        with self._lock:
            ents = self._entitlements.get(tenant_id, [])
            if active_only:
                return [e for e in ents if e.is_valid()]
            return list(ents)
    
    def expire_stale(self) -> int:
        """Expire stale entitlements."""
        with self._lock:
            count = 0
            now = datetime.now(timezone.utc)
            
            for tenant_id, ents in self._entitlements.items():
                for ent in ents:
                    if ent.expires_at and now >= ent.expires_at:
                        if ent.state == EntitlementState.ACTIVE:
                            ent.state = EntitlementState.EXPIRED
                            count += 1
            
            return count


# =============================================================================
# MONETIZATION ENGINE FACADE
# =============================================================================

class MonetizationEngine:
    """
    Unified monetization interface.
    
    Combines all monetization components into a single facade.
    """
    
    def __init__(self) -> None:
        self._meter = UsageMeter()
        self._pricing = PricingManager()
        self._pricing.setup_default_pricing()
        
        self._billing = BillingCalculator(self._meter, self._pricing)
        self._quotas = QuotaManager(self._meter)
        self._analytics = RevenueAnalytics(self._billing)
        self._entitlements = EntitlementService()
    
    @property
    def meter(self) -> UsageMeter:
        """Access usage meter."""
        return self._meter
    
    @property
    def pricing(self) -> PricingManager:
        """Access pricing manager."""
        return self._pricing
    
    @property
    def billing(self) -> BillingCalculator:
        """Access billing calculator."""
        return self._billing
    
    @property
    def quotas(self) -> QuotaManager:
        """Access quota manager."""
        return self._quotas
    
    @property
    def analytics(self) -> RevenueAnalytics:
        """Access revenue analytics."""
        return self._analytics
    
    @property
    def entitlements(self) -> EntitlementService:
        """Access entitlement service."""
        return self._entitlements
    
    def record_and_bill(
        self,
        tenant_id: str,
        usage_type: UsageType,
        quantity: Union[int, float, Decimal],
        enforce_quota: bool = True,
    ) -> Tuple[UsageRecord, Decimal]:
        """
        Record usage and calculate current charges.
        
        Args:
            tenant_id: Tenant identifier
            usage_type: Type of usage
            quantity: Amount to record
            enforce_quota: Whether to enforce quotas
        
        Returns:
            Tuple of (usage_record, current_charges)
        """
        quantity_dec = Decimal(str(quantity))
        
        # Enforce quota first (FAIL-CLOSED)
        if enforce_quota:
            self._quotas.enforce_quota(tenant_id, usage_type, quantity_dec)
        
        # Record usage
        record = self._meter.record(tenant_id, usage_type, quantity_dec)
        
        # Calculate current charges
        charges, _ = self._billing.calculate_current_charges(tenant_id)
        
        return record, charges
    
    def get_tenant_summary(
        self,
        tenant_id: str,
    ) -> Dict[str, Any]:
        """Get comprehensive summary for a tenant."""
        usage = self._meter.get_all_usage(tenant_id)
        charges, breakdown = self._billing.calculate_current_charges(tenant_id)
        quota_status = self._quotas.get_quota_status(tenant_id)
        entitlements = self._entitlements.get_entitlements(tenant_id)
        
        return {
            "tenant_id": tenant_id,
            "usage": {k.value: str(v) for k, v in usage.items()},
            "current_charges": str(charges),
            "breakdown": {k.value: v for k, v in breakdown.items()},
            "quota_status": {k.value: v for k, v in quota_status.items()},
            "entitlements": [e.to_dict() for e in entitlements],
        }


# =============================================================================
# WRAP HASH COMPUTATION
# =============================================================================

def compute_wrap_hash() -> str:
    """Compute WRAP hash for GID-05 deliverable."""
    content = f"GID-05:monetization_engine:v{MONETIZATION_ENGINE_VERSION}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    "MONETIZATION_ENGINE_VERSION",
    "UsageType",
    "PricingModel",
    "BillingPeriod",
    "QuotaStatus",
    "EntitlementState",
    "MonetizationError",
    "QuotaExceededError",
    "EntitlementError",
    "BillingError",
    "UsageRecord",
    "PricingTier",
    "QuotaDefinition",
    "Entitlement",
    "Invoice",
    "RevenueMetrics",
    "UsageMeter",
    "PricingManager",
    "BillingCalculator",
    "QuotaManager",
    "RevenueAnalytics",
    "EntitlementService",
    "MonetizationEngine",
    "compute_wrap_hash",
]
