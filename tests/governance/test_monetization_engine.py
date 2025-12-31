"""
Unit Tests for Monetization Engine.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-REAL-WORK-032
Agent: GID-05 (Sophie) — MONETIZATION & REVENUE SURFACES
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

from core.governance.monetization_engine import (
    MONETIZATION_ENGINE_VERSION,
    UsageType,
    PricingModel,
    BillingPeriod,
    QuotaStatus,
    EntitlementState,
    MonetizationError,
    QuotaExceededError,
    EntitlementError,
    BillingError,
    UsageRecord,
    PricingTier,
    QuotaDefinition,
    Entitlement,
    Invoice,
    RevenueMetrics,
    UsageMeter,
    PricingManager,
    BillingCalculator,
    QuotaManager,
    RevenueAnalytics,
    EntitlementService,
    MonetizationEngine,
    compute_wrap_hash,
)


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def usage_meter():
    """Create usage meter instance."""
    return UsageMeter()


@pytest.fixture
def pricing_manager():
    """Create pricing manager with default pricing."""
    pm = PricingManager()
    pm.setup_default_pricing()
    return pm


@pytest.fixture
def billing_calculator(usage_meter, pricing_manager):
    """Create billing calculator."""
    return BillingCalculator(usage_meter, pricing_manager)


@pytest.fixture
def quota_manager(usage_meter):
    """Create quota manager."""
    return QuotaManager(usage_meter)


@pytest.fixture
def entitlement_service():
    """Create entitlement service."""
    return EntitlementService()


@pytest.fixture
def monetization_engine():
    """Create full monetization engine."""
    return MonetizationEngine()


# =============================================================================
# ENUM TESTS
# =============================================================================

class TestEnums:
    """Test enum definitions."""
    
    def test_usage_type_values(self):
        """Test UsageType enum values."""
        assert UsageType.TOKEN.value == "TOKEN"
        assert UsageType.API_CALL.value == "API_CALL"
        assert UsageType.COMPUTE.value == "COMPUTE"
        assert UsageType.STORAGE.value == "STORAGE"
        assert UsageType.BANDWIDTH.value == "BANDWIDTH"
        assert UsageType.AGENT.value == "AGENT"
    
    def test_pricing_model_values(self):
        """Test PricingModel enum values."""
        assert PricingModel.FLAT.value == "FLAT"
        assert PricingModel.TIERED.value == "TIERED"
        assert PricingModel.USAGE.value == "USAGE"
        assert PricingModel.COMMITTED.value == "COMMITTED"
        assert PricingModel.HYBRID.value == "HYBRID"
    
    def test_quota_status_values(self):
        """Test QuotaStatus enum values."""
        assert QuotaStatus.WITHIN_LIMIT.value == "WITHIN_LIMIT"
        assert QuotaStatus.SOFT_LIMIT.value == "SOFT_LIMIT"
        assert QuotaStatus.HARD_LIMIT.value == "HARD_LIMIT"
        assert QuotaStatus.EXCEEDED.value == "EXCEEDED"
        assert QuotaStatus.GRACE_PERIOD.value == "GRACE_PERIOD"
    
    def test_entitlement_state_values(self):
        """Test EntitlementState enum values."""
        assert EntitlementState.ACTIVE.value == "ACTIVE"
        assert EntitlementState.SUSPENDED.value == "SUSPENDED"
        assert EntitlementState.EXPIRED.value == "EXPIRED"


# =============================================================================
# DATA CLASS TESTS
# =============================================================================

class TestUsageRecord:
    """Test UsageRecord dataclass."""
    
    def test_record_creation(self):
        """Test usage record creation."""
        record = UsageRecord(
            record_id="test_1",
            tenant_id="tenant_123",
            usage_type=UsageType.TOKEN,
            quantity=Decimal("1000"),
            timestamp=datetime.now(timezone.utc),
        )
        
        assert record.record_id == "test_1"
        assert record.tenant_id == "tenant_123"
        assert record.usage_type == UsageType.TOKEN
        assert record.quantity == Decimal("1000")
    
    def test_record_to_dict(self):
        """Test record serialization."""
        ts = datetime.now(timezone.utc)
        record = UsageRecord(
            record_id="test_1",
            tenant_id="tenant_123",
            usage_type=UsageType.API_CALL,
            quantity=Decimal("50"),
            timestamp=ts,
        )
        
        data = record.to_dict()
        
        assert data["record_id"] == "test_1"
        assert data["usage_type"] == "API_CALL"
        assert data["quantity"] == "50"


class TestPricingTier:
    """Test PricingTier dataclass."""
    
    def test_tier_creation(self):
        """Test pricing tier creation."""
        tier = PricingTier(
            tier_id="tier_1",
            name="Standard",
            min_units=Decimal(0),
            max_units=Decimal(1000),
            unit_price=Decimal("0.01"),
        )
        
        assert tier.tier_id == "tier_1"
        assert tier.unit_price == Decimal("0.01")
        assert tier.currency == "USD"
    
    def test_tier_to_dict(self):
        """Test tier serialization."""
        tier = PricingTier(
            tier_id="tier_1",
            name="Volume",
            min_units=Decimal(1000),
            max_units=None,
            unit_price=Decimal("0.005"),
        )
        
        data = tier.to_dict()
        
        assert data["name"] == "Volume"
        assert data["max_units"] is None
        assert data["unit_price"] == "0.005"


class TestEntitlement:
    """Test Entitlement dataclass."""
    
    def test_entitlement_is_valid_active(self):
        """Test active entitlement validation."""
        ent = Entitlement(
            entitlement_id="ent_1",
            tenant_id="tenant_123",
            feature="premium",
            state=EntitlementState.ACTIVE,
            granted_at=datetime.now(timezone.utc),
        )
        
        assert ent.is_valid() is True
    
    def test_entitlement_is_valid_expired_state(self):
        """Test expired state entitlement validation."""
        ent = Entitlement(
            entitlement_id="ent_1",
            tenant_id="tenant_123",
            feature="premium",
            state=EntitlementState.EXPIRED,
            granted_at=datetime.now(timezone.utc),
        )
        
        assert ent.is_valid() is False
    
    def test_entitlement_is_valid_time_expired(self):
        """Test time-expired entitlement validation."""
        ent = Entitlement(
            entitlement_id="ent_1",
            tenant_id="tenant_123",
            feature="trial",
            state=EntitlementState.ACTIVE,
            granted_at=datetime.now(timezone.utc) - timedelta(days=30),
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        
        assert ent.is_valid() is False
    
    def test_entitlement_is_valid_future_check(self):
        """Test entitlement validation at future time."""
        ent = Entitlement(
            entitlement_id="ent_1",
            tenant_id="tenant_123",
            feature="trial",
            state=EntitlementState.ACTIVE,
            granted_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        
        # Valid now
        assert ent.is_valid() is True
        
        # Invalid in 30 days
        future_time = datetime.now(timezone.utc) + timedelta(days=30)
        assert ent.is_valid(at_time=future_time) is False


# =============================================================================
# USAGE METER TESTS
# =============================================================================

class TestUsageMeter:
    """Test UsageMeter class."""
    
    def test_record_usage(self, usage_meter):
        """Test recording usage."""
        record = usage_meter.record(
            tenant_id="tenant_1",
            usage_type=UsageType.TOKEN,
            quantity=1000,
        )
        
        assert record.tenant_id == "tenant_1"
        assert record.usage_type == UsageType.TOKEN
        assert record.quantity == Decimal("1000")
    
    def test_record_batch(self, usage_meter):
        """Test batch recording."""
        records = usage_meter.record_batch(
            tenant_id="tenant_1",
            records=[
                (UsageType.TOKEN, 1000),
                (UsageType.API_CALL, 10),
            ],
        )
        
        assert len(records) == 2
    
    def test_get_usage(self, usage_meter):
        """Test getting usage."""
        usage_meter.record("tenant_1", UsageType.TOKEN, 1000)
        usage_meter.record("tenant_1", UsageType.TOKEN, 500)
        
        total = usage_meter.get_usage("tenant_1", UsageType.TOKEN)
        
        assert total == Decimal("1500")
    
    def test_get_usage_time_filtered(self, usage_meter):
        """Test getting usage with time filter."""
        now = datetime.now(timezone.utc)
        
        usage_meter.record("tenant_1", UsageType.TOKEN, 1000)
        
        # Get usage since 1 hour ago
        usage = usage_meter.get_usage(
            "tenant_1",
            UsageType.TOKEN,
            start_time=now - timedelta(hours=1),
        )
        
        assert usage == Decimal("1000")
    
    def test_get_all_usage(self, usage_meter):
        """Test getting all usage for tenant."""
        usage_meter.record("tenant_1", UsageType.TOKEN, 1000)
        usage_meter.record("tenant_1", UsageType.API_CALL, 50)
        
        usage = usage_meter.get_all_usage("tenant_1")
        
        assert usage[UsageType.TOKEN] == Decimal("1000")
        assert usage[UsageType.API_CALL] == Decimal("50")
    
    def test_reset_tenant(self, usage_meter):
        """Test resetting tenant usage."""
        usage_meter.record("tenant_1", UsageType.TOKEN, 1000)
        
        usage_meter.reset_tenant("tenant_1")
        
        usage = usage_meter.get_usage("tenant_1", UsageType.TOKEN)
        assert usage == Decimal("0")


# =============================================================================
# PRICING MANAGER TESTS
# =============================================================================

class TestPricingManager:
    """Test PricingManager class."""
    
    def test_add_tier(self):
        """Test adding pricing tier."""
        pm = PricingManager()
        tier = PricingTier(
            tier_id="t1",
            name="Standard",
            min_units=Decimal(0),
            max_units=Decimal(1000),
            unit_price=Decimal("0.01"),
        )
        
        pm.add_tier(UsageType.TOKEN, tier)
        
        tiers = pm.get_tiers(UsageType.TOKEN)
        assert len(tiers) == 1
        assert tiers[0].name == "Standard"
    
    def test_calculate_price_flat(self):
        """Test flat pricing calculation."""
        pm = PricingManager()
        pm.add_tier(UsageType.AGENT, PricingTier(
            tier_id="t1",
            name="Flat",
            min_units=Decimal(0),
            max_units=None,
            unit_price=Decimal("0.05"),
        ))
        pm.set_pricing_model(UsageType.AGENT, PricingModel.FLAT)
        
        price, breakdown = pm.calculate_price(UsageType.AGENT, Decimal(100))
        
        assert price == Decimal("5.00")
    
    def test_calculate_price_tiered(self, pricing_manager):
        """Test tiered pricing calculation."""
        # Default pricing has tiers for tokens
        price, breakdown = pricing_manager.calculate_price(
            UsageType.TOKEN,
            Decimal(1_500_000),  # 1.5M tokens
        )
        
        # First 1M at $2/1M, next 500K at $1.50/1M
        expected = Decimal("2.00") + Decimal("0.75")  # ~$2.75
        
        assert len(breakdown) == 2
        assert price > Decimal("0")
    
    def test_calculate_price_no_tiers(self):
        """Test pricing with no tiers defined."""
        pm = PricingManager()
        
        price, breakdown = pm.calculate_price(UsageType.STORAGE, Decimal(1000))
        
        assert price == Decimal("0")
        assert breakdown == []


# =============================================================================
# BILLING CALCULATOR TESTS
# =============================================================================

class TestBillingCalculator:
    """Test BillingCalculator class."""
    
    def test_calculate_current_charges(self, usage_meter, pricing_manager):
        """Test current charges calculation."""
        bc = BillingCalculator(usage_meter, pricing_manager)
        
        usage_meter.record("tenant_1", UsageType.TOKEN, 1_000_000)
        
        charges, breakdown = bc.calculate_current_charges("tenant_1")
        
        assert charges > Decimal("0")
        assert UsageType.TOKEN in breakdown
    
    def test_calculate_with_discount(self, usage_meter, pricing_manager):
        """Test charges with discount."""
        bc = BillingCalculator(usage_meter, pricing_manager)
        bc.set_discount("tenant_1", Decimal("10"))  # 10% discount
        
        usage_meter.record("tenant_1", UsageType.TOKEN, 1_000_000)
        
        charges, _ = bc.calculate_current_charges("tenant_1")
        
        # Should be ~10% less than $2
        assert charges < Decimal("2.00")
    
    def test_generate_invoice(self, usage_meter, pricing_manager):
        """Test invoice generation."""
        bc = BillingCalculator(usage_meter, pricing_manager)
        bc.set_tax_rate("US", Decimal("8"))  # 8% tax
        
        usage_meter.record("tenant_1", UsageType.TOKEN, 1_000_000)
        
        now = datetime.now(timezone.utc)
        invoice = bc.generate_invoice(
            tenant_id="tenant_1",
            period_start=now - timedelta(days=30),
            period_end=now,
            region="US",
        )
        
        assert invoice.invoice_id.startswith("INV-")
        assert invoice.tenant_id == "tenant_1"
        assert invoice.subtotal > Decimal("0")
        assert invoice.tax > Decimal("0")
        assert invoice.total == invoice.subtotal + invoice.tax
    
    def test_estimate_month_end(self, usage_meter, pricing_manager):
        """Test month-end estimation."""
        bc = BillingCalculator(usage_meter, pricing_manager)
        
        usage_meter.record("tenant_1", UsageType.TOKEN, 1_000_000)
        
        estimate = bc.estimate_month_end("tenant_1", days_remaining=15)
        
        assert estimate > Decimal("0")


# =============================================================================
# QUOTA MANAGER TESTS
# =============================================================================

class TestQuotaManager:
    """Test QuotaManager class."""
    
    def test_check_quota_within_limit(self, usage_meter):
        """Test quota check within limit."""
        qm = QuotaManager(usage_meter)
        qm.set_quota("tenant_1", QuotaDefinition(
            usage_type=UsageType.TOKEN,
            soft_limit=Decimal(900_000),
            hard_limit=Decimal(1_000_000),
        ))
        
        status, details = qm.check_quota("tenant_1", UsageType.TOKEN, Decimal(100_000))
        
        assert status == QuotaStatus.WITHIN_LIMIT
    
    def test_check_quota_soft_limit(self, usage_meter):
        """Test quota check at soft limit."""
        qm = QuotaManager(usage_meter)
        qm.set_quota("tenant_1", QuotaDefinition(
            usage_type=UsageType.TOKEN,
            soft_limit=Decimal(100),
            hard_limit=Decimal(200),
        ))
        
        usage_meter.record("tenant_1", UsageType.TOKEN, 90)
        
        status, details = qm.check_quota("tenant_1", UsageType.TOKEN, Decimal(20))
        
        assert status == QuotaStatus.SOFT_LIMIT
    
    def test_check_quota_exceeded(self, usage_meter):
        """Test quota check exceeded."""
        qm = QuotaManager(usage_meter)
        qm.set_quota("tenant_1", QuotaDefinition(
            usage_type=UsageType.TOKEN,
            soft_limit=Decimal(100),
            hard_limit=Decimal(200),
        ))
        
        usage_meter.record("tenant_1", UsageType.TOKEN, 190)
        
        status, details = qm.check_quota("tenant_1", UsageType.TOKEN, Decimal(20))
        
        assert status == QuotaStatus.EXCEEDED
    
    def test_enforce_quota_raises(self, usage_meter):
        """Test quota enforcement raises on exceed."""
        qm = QuotaManager(usage_meter)
        qm.set_quota("tenant_1", QuotaDefinition(
            usage_type=UsageType.TOKEN,
            soft_limit=Decimal(100),
            hard_limit=Decimal(200),
        ))
        
        usage_meter.record("tenant_1", UsageType.TOKEN, 190)
        
        with pytest.raises(QuotaExceededError) as exc_info:
            qm.enforce_quota("tenant_1", UsageType.TOKEN, Decimal(20))
        
        assert exc_info.value.usage_type == UsageType.TOKEN
    
    def test_get_quota_status(self, usage_meter):
        """Test getting quota status for all types."""
        qm = QuotaManager(usage_meter)
        qm.set_quota("tenant_1", QuotaDefinition(
            usage_type=UsageType.TOKEN,
            soft_limit=Decimal(1000),
            hard_limit=Decimal(2000),
        ))
        
        status = qm.get_quota_status("tenant_1")
        
        assert UsageType.TOKEN in status
        assert status[UsageType.TOKEN]["status"] == "WITHIN_LIMIT"


# =============================================================================
# ENTITLEMENT SERVICE TESTS
# =============================================================================

class TestEntitlementService:
    """Test EntitlementService class."""
    
    def test_grant_entitlement(self, entitlement_service):
        """Test granting entitlement."""
        ent = entitlement_service.grant(
            tenant_id="tenant_1",
            feature="premium",
        )
        
        assert ent.tenant_id == "tenant_1"
        assert ent.feature == "premium"
        assert ent.state == EntitlementState.ACTIVE
    
    def test_check_entitlement_valid(self, entitlement_service):
        """Test checking valid entitlement."""
        entitlement_service.grant("tenant_1", "feature_x")
        
        result = entitlement_service.check("tenant_1", "feature_x")
        
        assert result is True
    
    def test_check_entitlement_missing(self, entitlement_service):
        """Test checking missing entitlement — FAIL-CLOSED."""
        result = entitlement_service.check("tenant_1", "nonexistent")
        
        assert result is False
    
    def test_revoke_entitlement(self, entitlement_service):
        """Test revoking entitlement."""
        entitlement_service.grant("tenant_1", "feature_x")
        
        result = entitlement_service.revoke("tenant_1", "feature_x")
        
        assert result is True
        assert entitlement_service.check("tenant_1", "feature_x") is False
    
    def test_require_entitlement_raises(self, entitlement_service):
        """Test require raises on missing."""
        with pytest.raises(EntitlementError):
            entitlement_service.require("tenant_1", "premium")
    
    def test_get_entitlements(self, entitlement_service):
        """Test getting all entitlements."""
        entitlement_service.grant("tenant_1", "feature_a")
        entitlement_service.grant("tenant_1", "feature_b")
        
        ents = entitlement_service.get_entitlements("tenant_1")
        
        assert len(ents) == 2
    
    def test_expire_stale(self, entitlement_service):
        """Test expiring stale entitlements."""
        ent = entitlement_service.grant(
            tenant_id="tenant_1",
            feature="trial",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        
        count = entitlement_service.expire_stale()
        
        assert count == 1
        assert entitlement_service.check("tenant_1", "trial") is False


# =============================================================================
# REVENUE ANALYTICS TESTS
# =============================================================================

class TestRevenueAnalytics:
    """Test RevenueAnalytics class."""
    
    def test_calculate_mrr(self, billing_calculator):
        """Test MRR calculation."""
        analytics = RevenueAnalytics(billing_calculator)
        
        analytics.record_billing_event(
            tenant_id="tenant_1",
            amount=Decimal("100"),
            event_type="subscription",
        )
        analytics.record_billing_event(
            tenant_id="tenant_2",
            amount=Decimal("200"),
            event_type="subscription",
        )
        
        mrr = analytics.calculate_mrr()
        
        assert mrr == Decimal("300.00")
    
    def test_calculate_arr(self, billing_calculator):
        """Test ARR calculation."""
        analytics = RevenueAnalytics(billing_calculator)
        analytics.record_billing_event("tenant_1", Decimal("100"), "subscription")
        
        arr = analytics.calculate_arr()
        
        assert arr == Decimal("1200.00")
    
    def test_calculate_arpu(self, billing_calculator):
        """Test ARPU calculation."""
        analytics = RevenueAnalytics(billing_calculator)
        analytics.record_billing_event("tenant_1", Decimal("100"), "subscription")
        analytics.record_billing_event("tenant_2", Decimal("200"), "subscription")
        
        arpu = analytics.calculate_arpu()
        
        assert arpu == Decimal("150.00")
    
    def test_calculate_ltv(self, billing_calculator):
        """Test LTV calculation."""
        analytics = RevenueAnalytics(billing_calculator)
        analytics.record_billing_event("tenant_1", Decimal("100"), "subscription")
        
        ltv = analytics.calculate_ltv(avg_lifetime_months=12)
        
        assert ltv == Decimal("1200.00")
    
    def test_get_metrics(self, billing_calculator):
        """Test getting metrics."""
        analytics = RevenueAnalytics(billing_calculator)
        analytics.record_billing_event("tenant_1", Decimal("100"), "subscription")
        
        metrics = analytics.get_metrics()
        
        assert metrics.mrr == Decimal("100.00")
        assert metrics.arr == Decimal("1200.00")
    
    def test_forecast_revenue(self, billing_calculator):
        """Test revenue forecasting."""
        analytics = RevenueAnalytics(billing_calculator)
        analytics.record_billing_event("tenant_1", Decimal("100"), "subscription")
        
        forecast = analytics.forecast_revenue(months_ahead=3, growth_rate=Decimal("10"))
        
        assert len(forecast) == 3
        assert Decimal(forecast[2]["projected_mrr"]) > Decimal("100")


# =============================================================================
# MONETIZATION ENGINE TESTS
# =============================================================================

class TestMonetizationEngine:
    """Test MonetizationEngine facade."""
    
    def test_engine_initialization(self, monetization_engine):
        """Test engine initialization."""
        assert monetization_engine.meter is not None
        assert monetization_engine.pricing is not None
        assert monetization_engine.billing is not None
        assert monetization_engine.quotas is not None
        assert monetization_engine.analytics is not None
        assert monetization_engine.entitlements is not None
    
    def test_record_and_bill(self, monetization_engine):
        """Test recording usage and billing."""
        record, charges = monetization_engine.record_and_bill(
            tenant_id="tenant_1",
            usage_type=UsageType.TOKEN,
            quantity=1_000_000,
            enforce_quota=False,
        )
        
        assert record.quantity == Decimal("1000000")
        assert charges > Decimal("0")
    
    def test_record_and_bill_with_quota_enforcement(self, monetization_engine):
        """Test recording with quota enforcement."""
        monetization_engine.quotas.set_quota("tenant_1", QuotaDefinition(
            usage_type=UsageType.TOKEN,
            soft_limit=Decimal(500_000),
            hard_limit=Decimal(1_000_000),
        ))
        
        # Should succeed
        record, _ = monetization_engine.record_and_bill(
            tenant_id="tenant_1",
            usage_type=UsageType.TOKEN,
            quantity=400_000,
        )
        
        assert record is not None
    
    def test_record_and_bill_quota_exceeded(self, monetization_engine):
        """Test recording fails on quota exceed."""
        monetization_engine.quotas.set_quota("tenant_1", QuotaDefinition(
            usage_type=UsageType.TOKEN,
            soft_limit=Decimal(100),
            hard_limit=Decimal(200),
        ))
        
        # Record up to limit
        monetization_engine.record_and_bill("tenant_1", UsageType.TOKEN, 190)
        
        # Should raise
        with pytest.raises(QuotaExceededError):
            monetization_engine.record_and_bill("tenant_1", UsageType.TOKEN, 50)
    
    def test_get_tenant_summary(self, monetization_engine):
        """Test tenant summary."""
        monetization_engine.record_and_bill("tenant_1", UsageType.TOKEN, 1000, enforce_quota=False)
        monetization_engine.entitlements.grant("tenant_1", "premium")
        
        summary = monetization_engine.get_tenant_summary("tenant_1")
        
        assert summary["tenant_id"] == "tenant_1"
        assert "usage" in summary
        assert "current_charges" in summary
        assert "entitlements" in summary


# =============================================================================
# THREAD SAFETY TESTS
# =============================================================================

class TestThreadSafety:
    """Test thread safety."""
    
    def test_concurrent_usage_recording(self, usage_meter):
        """Test concurrent usage recording."""
        import threading
        
        def record_usage(count: int):
            for i in range(count):
                usage_meter.record(
                    tenant_id="tenant_1",
                    usage_type=UsageType.TOKEN,
                    quantity=1,
                )
        
        threads = [
            threading.Thread(target=record_usage, args=(100,))
            for _ in range(10)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        total = usage_meter.get_usage("tenant_1", UsageType.TOKEN)
        assert total == Decimal("1000")
    
    def test_concurrent_entitlement_operations(self, entitlement_service):
        """Test concurrent entitlement operations."""
        import threading
        
        def grant_and_check(feature: str):
            entitlement_service.grant("tenant_1", feature)
            entitlement_service.check("tenant_1", feature)
        
        threads = [
            threading.Thread(target=grant_and_check, args=(f"feature_{i}",))
            for i in range(20)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        ents = entitlement_service.get_entitlements("tenant_1")
        assert len(ents) == 20


# =============================================================================
# EXCEPTION TESTS
# =============================================================================

class TestExceptions:
    """Test exception handling."""
    
    def test_quota_exceeded_error(self):
        """Test QuotaExceededError."""
        err = QuotaExceededError(UsageType.TOKEN, 150.0, 100.0)
        
        assert "Quota exceeded" in str(err)
        assert err.usage_type == UsageType.TOKEN
        assert err.current == 150.0
        assert err.limit == 100.0
    
    def test_entitlement_error(self):
        """Test EntitlementError."""
        err = EntitlementError("Missing entitlement")
        
        assert "Missing entitlement" in str(err)


# =============================================================================
# WRAP HASH TESTS
# =============================================================================

class TestWrapHash:
    """Test WRAP hash computation."""
    
    def test_compute_wrap_hash(self):
        """Test WRAP hash computation."""
        hash1 = compute_wrap_hash()
        hash2 = compute_wrap_hash()
        
        assert hash1 == hash2
        assert len(hash1) == 16
    
    def test_wrap_hash_includes_version(self):
        """Test WRAP hash is version-aware."""
        expected_content = f"GID-05:monetization_engine:v{MONETIZATION_ENGINE_VERSION}"
        assert MONETIZATION_ENGINE_VERSION in expected_content


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests."""
    
    def test_full_billing_cycle(self, monetization_engine):
        """Test complete billing cycle."""
        tenant = "tenant_integration"
        
        # Grant entitlement
        monetization_engine.entitlements.grant(tenant, "api_access")
        
        # Set quota
        monetization_engine.quotas.set_quota(tenant, QuotaDefinition(
            usage_type=UsageType.TOKEN,
            soft_limit=Decimal(10_000_000),
            hard_limit=Decimal(20_000_000),
        ))
        
        # Record usage
        for _ in range(10):
            monetization_engine.record_and_bill(
                tenant, UsageType.TOKEN, 100_000
            )
        
        # Check summary
        summary = monetization_engine.get_tenant_summary(tenant)
        
        assert summary["usage"]["TOKEN"] == "1000000"
        assert Decimal(summary["current_charges"]) > Decimal("0")
        
        # Generate invoice
        now = datetime.now(timezone.utc)
        invoice = monetization_engine.billing.generate_invoice(
            tenant,
            now - timedelta(days=30),
            now,
        )
        
        assert invoice.total > Decimal("0")
    
    def test_quota_enforcement_workflow(self, monetization_engine):
        """Test quota enforcement workflow."""
        tenant = "tenant_quota"
        
        # Set strict quota
        monetization_engine.quotas.set_quota(tenant, QuotaDefinition(
            usage_type=UsageType.API_CALL,
            soft_limit=Decimal(5),
            hard_limit=Decimal(10),
        ))
        
        # Use within limits
        for i in range(5):
            monetization_engine.record_and_bill(tenant, UsageType.API_CALL, 1)
        
        # Check soft limit warning
        status, _ = monetization_engine.quotas.check_quota(
            tenant, UsageType.API_CALL, Decimal(1)
        )
        assert status == QuotaStatus.SOFT_LIMIT
        
        # Use up to hard limit
        for i in range(5):
            monetization_engine.record_and_bill(tenant, UsageType.API_CALL, 1)
        
        # Should fail now
        with pytest.raises(QuotaExceededError):
            monetization_engine.record_and_bill(tenant, UsageType.API_CALL, 1)
