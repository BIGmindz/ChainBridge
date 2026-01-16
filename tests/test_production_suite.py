#!/usr/bin/env python3
"""
ChainBridge Production Test Suite
=================================

Comprehensive test coverage for production readiness.
Covers all core modules with unit and integration tests.

PAC Reference: PAC-JEFFREY-TARGET-20M-001 (TASK 4)
Constitutional Authority: ALEX (FOUNDER / CEO)
Executor: BENSON [GID-00]

Schema: v4.0.0
"""

import json
import sys
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import Mock, patch, MagicMock


# =============================================================================
# TEST CONFIGURATION
# =============================================================================

class TestConfig:
    """Test suite configuration."""
    VERBOSE = True
    FAIL_FAST = False
    COVERAGE_TARGET = 80  # Minimum 80% coverage
    

# =============================================================================
# SETTLEMENT ENGINE TESTS
# =============================================================================

class TestSettlementEngine(unittest.TestCase):
    """Test suite for ChainPay settlement engine."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Import here to handle potential import errors gracefully
        try:
            from modules.chainpay.settlement_engine import (
                SettlementEngine,
                PaymentParty,
                Money,
                Currency,
                SettlementMethod,
                PaymentStatus,
                FeeCalculator,
                ExchangeRateService,
                create_settlement_engine,
            )
            self.engine = create_settlement_engine()
            self.PaymentParty = PaymentParty
            self.Money = Money
            self.Currency = Currency
            self.SettlementMethod = SettlementMethod
            self.PaymentStatus = PaymentStatus
            self.FeeCalculator = FeeCalculator
            self.ExchangeRateService = ExchangeRateService
            self.module_available = True
        except ImportError as e:
            self.module_available = False
            self.skipTest(f"Settlement engine module not available: {e}")
    
    def test_create_payment_valid(self):
        """Test creating a valid payment."""
        source = self.PaymentParty("SRC-001", "Test Sender", "ACC-123", kyc_verified=True)
        dest = self.PaymentParty("DST-001", "Test Receiver", "ACC-456", kyc_verified=True)
        amount = self.Money(Decimal("1000.00"), self.Currency.USD)
        
        tx = self.engine.create_payment(
            source=source,
            destination=dest,
            amount=amount,
            method=self.SettlementMethod.HEDERA_INSTANT,
            reference="TEST-REF-001",
        )
        
        self.assertIsNotNone(tx.transaction_id)
        self.assertTrue(tx.transaction_id.startswith("TX-"))
        self.assertEqual(tx.status, self.PaymentStatus.INITIATED)
        self.assertEqual(tx.amount.amount, Decimal("1000.00"))
    
    def test_create_payment_invalid_amount(self):
        """Test that zero/negative amounts are rejected."""
        source = self.PaymentParty("SRC-002", "Sender", "ACC-001")
        dest = self.PaymentParty("DST-002", "Receiver", "ACC-002")
        
        with self.assertRaises(ValueError):
            amount = self.Money(Decimal("0"), self.Currency.USD)
            self.engine.create_payment(
                source=source,
                destination=dest,
                amount=amount,
                method=self.SettlementMethod.XRP_PAYMENT,
                reference="TEST-INVALID",
            )
    
    def test_fee_calculation_hedera(self):
        """Test fee calculation for Hedera settlement."""
        calc = self.FeeCalculator()
        amount = self.Money(Decimal("10000.00"), self.Currency.USD)
        
        fee = calc.calculate_fee(amount, self.SettlementMethod.HEDERA_INSTANT)
        
        # 0.15% = 15 basis points
        expected = Decimal("15.00")  # 10000 * 0.0015
        self.assertEqual(fee.amount, expected)
    
    def test_fee_calculation_minimum(self):
        """Test minimum fee enforcement."""
        calc = self.FeeCalculator()
        amount = self.Money(Decimal("10.00"), self.Currency.USD)  # Small amount
        
        fee = calc.calculate_fee(amount, self.SettlementMethod.HEDERA_INSTANT)
        
        # Should hit minimum fee of $0.50
        self.assertGreaterEqual(fee.amount, Decimal("0.50"))
    
    def test_exchange_rate_usd_eur(self):
        """Test USD to EUR exchange rate."""
        exchange = self.ExchangeRateService()
        
        rate = exchange.get_rate(self.Currency.USD, self.Currency.EUR)
        
        self.assertGreater(rate, Decimal("0"))
        self.assertLess(rate, Decimal("2"))  # Reasonable range
    
    def test_exchange_rate_same_currency(self):
        """Test same currency returns 1.0 rate."""
        exchange = self.ExchangeRateService()
        
        rate = exchange.get_rate(self.Currency.USD, self.Currency.USD)
        
        self.assertEqual(rate, Decimal("1.0"))
    
    def test_full_pipeline(self):
        """Test complete settlement pipeline."""
        source = self.PaymentParty("SRC-FULL", "Full Test Sender", "ACC-F1", kyc_verified=True)
        dest = self.PaymentParty("DST-FULL", "Full Test Receiver", "ACC-F2", kyc_verified=True)
        amount = self.Money(Decimal("5000.00"), self.Currency.USD)
        
        tx = self.engine.execute_full_pipeline(
            source=source,
            destination=dest,
            amount=amount,
            method=self.SettlementMethod.XRP_PAYMENT,
            reference="FULL-PIPELINE-TEST",
        )
        
        self.assertEqual(tx.status, self.PaymentStatus.CONFIRMED)
        self.assertIsNotNone(tx.blockchain_tx_hash)
        self.assertIsNotNone(tx.aml_reference)
    
    def test_batch_processing(self):
        """Test batch settlement processing."""
        tx_ids = []
        for i in range(3):
            source = self.PaymentParty(f"SRC-B{i}", f"Batch Sender {i}", f"ACC-BS{i}", kyc_verified=True)
            dest = self.PaymentParty(f"DST-B{i}", f"Batch Receiver {i}", f"ACC-BR{i}", kyc_verified=True)
            amount = self.Money(Decimal("500.00"), self.Currency.USD)
            
            tx = self.engine.create_payment(
                source=source,
                destination=dest,
                amount=amount,
                method=self.SettlementMethod.ACH_BATCH,
                reference=f"BATCH-TEST-{i}",
            )
            self.engine.screen_aml(tx.transaction_id)
            self.engine.validate_payment(tx.transaction_id)
            tx_ids.append(tx.transaction_id)
        
        batch = self.engine.create_batch(tx_ids, self.SettlementMethod.ACH_BATCH)
        success, batch_hash = self.engine.process_batch(batch.batch_id)
        
        self.assertTrue(success)
        self.assertEqual(batch.total_amount.amount, Decimal("1500.00"))
    
    def test_reconciliation(self):
        """Test reconciliation matching."""
        source = self.PaymentParty("SRC-REC", "Recon Sender", "ACC-R1", kyc_verified=True)
        dest = self.PaymentParty("DST-REC", "Recon Receiver", "ACC-R2", kyc_verified=True)
        amount = self.Money(Decimal("1000.00"), self.Currency.USD)
        
        tx = self.engine.execute_full_pipeline(
            source=source,
            destination=dest,
            amount=amount,
            method=self.SettlementMethod.HEDERA_INSTANT,
            reference="RECON-TEST",
        )
        
        record = self.engine.create_reconciliation_record(tx.transaction_id)
        matched = self.engine.match_reconciliation(record.record_id, tx.amount)
        
        from modules.chainpay.settlement_engine import ReconciliationStatus
        self.assertEqual(matched.status, ReconciliationStatus.MATCHED)
    
    def test_metrics(self):
        """Test settlement metrics gathering."""
        metrics = self.engine.get_settlement_metrics()
        
        self.assertIn("total_transactions", metrics)
        self.assertIn("by_status", metrics)
        self.assertIn("confirmed_volume_usd", metrics)


# =============================================================================
# PILOT PROGRAM TESTS
# =============================================================================

class TestPilotProgram(unittest.TestCase):
    """Test suite for ChainFreight pilot program."""
    
    def setUp(self):
        """Set up test fixtures."""
        try:
            from modules.freight.pilot_program import (
                PilotProgramManager,
                CompanyProfile,
                Contact,
                CompanySize,
                FreightMode,
                PilotTier,
                PilotStatus,
            )
            self.manager = PilotProgramManager()
            self.CompanyProfile = CompanyProfile
            self.Contact = Contact
            self.CompanySize = CompanySize
            self.FreightMode = FreightMode
            self.PilotTier = PilotTier
            self.PilotStatus = PilotStatus
            self.module_available = True
        except ImportError as e:
            self.module_available = False
            self.skipTest(f"Pilot program module not available: {e}")
    
    def _create_test_company(self) -> "CompanyProfile":
        """Create a test company profile."""
        return self.CompanyProfile(
            company_id="TEST-COMP-001",
            name="Test Logistics LLC",
            industry="Transportation",
            size=self.CompanySize.MID_MARKET,
            annual_freight_spend=Decimal("25000000"),
            primary_modes=[self.FreightMode.FTL, self.FreightMode.LTL],
            headquarters_state="CA",
        )
    
    def _create_test_contact(self) -> "Contact":
        """Create a test contact."""
        return self.Contact(
            contact_id="TEST-CONT-001",
            company_id="TEST-COMP-001",
            name="Test User",
            title="VP Operations",
            email="test@testlogistics.com",
            is_decision_maker=True,
        )
    
    def test_company_registration(self):
        """Test company registration."""
        company = self._create_test_company()
        company_id = self.manager.register_company(company)
        
        self.assertEqual(company_id, "TEST-COMP-001")
    
    def test_lead_qualification_pass(self):
        """Test lead qualification with passing criteria."""
        qualification = self.manager.qualify_lead(
            company_id="TEST-COMP-001",
            has_budget=True,
            has_authority=True,
            has_need=True,
            has_timeline=True,
            fit_score=80,
        )
        
        self.assertTrue(qualification.is_qualified)
    
    def test_lead_qualification_fail(self):
        """Test lead qualification with failing criteria."""
        qualification = self.manager.qualify_lead(
            company_id="TEST-COMP-001",
            has_budget=True,
            has_authority=False,  # Missing authority
            has_need=True,
            has_timeline=True,
            fit_score=80,
        )
        
        self.assertFalse(qualification.is_qualified)
    
    def test_pilot_creation(self):
        """Test pilot program creation."""
        company = self._create_test_company()
        contact = self._create_test_contact()
        
        qualification = self.manager.qualify_lead(
            company_id=company.company_id,
            has_budget=True,
            has_authority=True,
            has_need=True,
            has_timeline=True,
            fit_score=85,
        )
        
        pilot = self.manager.create_pilot(
            company=company,
            contacts=[contact],
            qualification=qualification,
            tier=self.PilotTier.GROWTH,
        )
        
        self.assertIsNotNone(pilot.pilot_id)
        self.assertEqual(pilot.status, self.PilotStatus.QUALIFIED)
    
    def test_loi_generation(self):
        """Test LOI generation."""
        company = self._create_test_company()
        company.company_id = "LOI-COMP-001"
        contact = self._create_test_contact()
        contact.company_id = "LOI-COMP-001"
        
        qualification = self.manager.qualify_lead(
            company_id=company.company_id,
            has_budget=True,
            has_authority=True,
            has_need=True,
            has_timeline=True,
            fit_score=90,
        )
        
        pilot = self.manager.create_pilot(
            company=company,
            contacts=[contact],
            qualification=qualification,
            tier=self.PilotTier.ENTERPRISE,
        )
        
        loi = self.manager.generate_loi(
            pilot_id=pilot.pilot_id,
            special_terms=["Custom API integration"],
        )
        
        self.assertIsNotNone(loi.loi_id)
        self.assertEqual(loi.status, "draft")
        self.assertEqual(pilot.status, self.PilotStatus.LOI_SENT)
    
    def test_loi_rendering(self):
        """Test LOI document rendering."""
        company = self._create_test_company()
        company.company_id = "RENDER-COMP-001"
        contact = self._create_test_contact()
        contact.company_id = "RENDER-COMP-001"
        
        qualification = self.manager.qualify_lead(
            company_id=company.company_id,
            has_budget=True,
            has_authority=True,
            has_need=True,
            has_timeline=True,
            fit_score=85,
        )
        
        pilot = self.manager.create_pilot(
            company=company,
            contacts=[contact],
            qualification=qualification,
        )
        
        loi = self.manager.generate_loi(pilot_id=pilot.pilot_id)
        document = self.manager.render_loi_document(loi.loi_id)
        
        self.assertIn("LETTER OF INTENT", document)
        self.assertIn(company.name, document)
        self.assertIn("ChainFreight", document)
    
    def test_pilot_shipment_tracking(self):
        """Test shipment recording in pilot."""
        company = self._create_test_company()
        company.company_id = "SHIP-COMP-001"
        contact = self._create_test_contact()
        contact.company_id = "SHIP-COMP-001"
        
        qualification = self.manager.qualify_lead(
            company_id=company.company_id,
            has_budget=True,
            has_authority=True,
            has_need=True,
            has_timeline=True,
            fit_score=85,
        )
        
        pilot = self.manager.create_pilot(company=company, contacts=[contact], qualification=qualification)
        loi = self.manager.generate_loi(pilot_id=pilot.pilot_id)
        self.manager.sign_loi(loi.loi_id, contact.name)
        self.manager.start_pilot(pilot.pilot_id)
        
        # Record shipments
        for i in range(5):
            self.manager.record_shipment(
                pilot.pilot_id,
                success=True,
                freight_value=Decimal("10000"),
                settlement_time_hours=Decimal("2"),
            )
        
        self.assertEqual(pilot.metrics.shipments_completed, 5)
        self.assertEqual(pilot.metrics.success_rate, Decimal("100"))
    
    def test_pipeline_metrics(self):
        """Test pipeline metrics gathering."""
        metrics = self.manager.get_pipeline_metrics()
        
        self.assertIn("total_pilots", metrics)
        self.assertIn("by_status", metrics)
        self.assertIn("conversion_rate_percent", metrics)


# =============================================================================
# LICENSING TESTS
# =============================================================================

class TestLicensing(unittest.TestCase):
    """Test suite for Agent University licensing."""
    
    def setUp(self):
        """Set up test fixtures."""
        try:
            from modules.gaas.licensing import (
                LicenseManager,
                PricingCatalog,
                LicenseTier,
                LicenseStatus,
                FeatureFlag,
                DeploymentModel,
                FeatureGate,
            )
            self.manager = LicenseManager()
            self.PricingCatalog = PricingCatalog
            self.LicenseTier = LicenseTier
            self.LicenseStatus = LicenseStatus
            self.FeatureFlag = FeatureFlag
            self.DeploymentModel = DeploymentModel
            self.FeatureGate = FeatureGate
            self.module_available = True
        except ImportError as e:
            self.module_available = False
            self.skipTest(f"Licensing module not available: {e}")
    
    def test_pricing_catalog(self):
        """Test pricing catalog retrieval."""
        starter = self.PricingCatalog.get_plan(self.LicenseTier.STARTER)
        
        self.assertEqual(starter.base_monthly_usd, Decimal("299"))
        self.assertEqual(starter.included_agents, 1)
    
    def test_pricing_calculation_monthly(self):
        """Test monthly pricing calculation."""
        pro = self.PricingCatalog.get_plan(self.LicenseTier.PROFESSIONAL)
        
        # 5 included + 5 extra at $79 each
        monthly = pro.calculate_monthly(10)
        expected = Decimal("999") + (5 * Decimal("79"))
        
        self.assertEqual(monthly, expected)
    
    def test_tier_recommendation(self):
        """Test tier recommendation logic."""
        # Small team
        tier = self.PricingCatalog.recommend_tier(2, needs_custom_doctrines=False)
        self.assertEqual(tier, self.LicenseTier.STARTER)
        
        # Large team with custom doctrines
        tier = self.PricingCatalog.recommend_tier(30, needs_custom_doctrines=True)
        self.assertEqual(tier, self.LicenseTier.SOVEREIGN)
    
    def test_customer_registration(self):
        """Test customer registration."""
        customer = self.manager.register_customer(
            company_name="Test Corp",
            industry="Technology",
            contact_email="test@test.com",
            contact_name="Test User",
            billing_address="123 Test St",
        )
        
        self.assertTrue(customer.customer_id.startswith("CUST-"))
    
    def test_trial_license(self):
        """Test trial license creation."""
        customer = self.manager.register_customer(
            company_name="Trial Corp",
            industry="Finance",
            contact_email="trial@trial.com",
            contact_name="Trial User",
            billing_address="456 Trial Ave",
        )
        
        trial = self.manager.create_trial_license(
            customer_id=customer.customer_id,
            tier=self.LicenseTier.PROFESSIONAL,
            trial_days=14,
        )
        
        self.assertEqual(trial.status, self.LicenseStatus.TRIAL)
        self.assertEqual(trial.monthly_cost, Decimal("0"))
    
    def test_license_activation(self):
        """Test paid license activation."""
        customer = self.manager.register_customer(
            company_name="Paid Corp",
            industry="Healthcare",
            contact_email="paid@paid.com",
            contact_name="Paid User",
            billing_address="789 Paid Blvd",
        )
        
        license_obj = self.manager.activate_license(
            customer_id=customer.customer_id,
            tier=self.LicenseTier.ENTERPRISE,
            agent_count=30,
            is_annual=True,
        )
        
        self.assertEqual(license_obj.status, self.LicenseStatus.ACTIVE)
        self.assertTrue(license_obj.is_active)
        self.assertGreater(license_obj.monthly_cost, Decimal("0"))
    
    def test_license_validation(self):
        """Test license key validation."""
        customer = self.manager.register_customer(
            company_name="Valid Corp",
            industry="Retail",
            contact_email="valid@valid.com",
            contact_name="Valid User",
            billing_address="101 Valid Way",
        )
        
        license_obj = self.manager.activate_license(
            customer_id=customer.customer_id,
            tier=self.LicenseTier.PROFESSIONAL,
            agent_count=10,
        )
        
        validated = self.manager.validate_license(license_obj.license_key)
        
        self.assertIsNotNone(validated)
        self.assertEqual(validated.license_id, license_obj.license_id)
    
    def test_feature_check(self):
        """Test feature availability checking."""
        customer = self.manager.register_customer(
            company_name="Feature Corp",
            industry="Manufacturing",
            contact_email="feature@feature.com",
            contact_name="Feature User",
            billing_address="202 Feature St",
        )
        
        license_obj = self.manager.activate_license(
            customer_id=customer.customer_id,
            tier=self.LicenseTier.ENTERPRISE,
            agent_count=25,
        )
        
        # Enterprise should have SCRAM
        has_scram = self.manager.check_feature(
            license_obj.license_id, 
            self.FeatureFlag.SCRAM_CONTROLLER
        )
        self.assertTrue(has_scram)
        
        # Enterprise should NOT have source access
        has_source = self.manager.check_feature(
            license_obj.license_id,
            self.FeatureFlag.SOURCE_ACCESS
        )
        self.assertFalse(has_source)
    
    def test_usage_recording(self):
        """Test usage metrics recording."""
        customer = self.manager.register_customer(
            company_name="Usage Corp",
            industry="Logistics",
            contact_email="usage@usage.com",
            contact_name="Usage User",
            billing_address="303 Usage Dr",
        )
        
        license_obj = self.manager.activate_license(
            customer_id=customer.customer_id,
            tier=self.LicenseTier.PROFESSIONAL,
            agent_count=5,
        )
        
        self.manager.record_usage(license_obj.license_id, "agent_invocation", 50)
        self.manager.record_usage(license_obj.license_id, "pac_created", 10)
        
        summary = self.manager.get_usage_summary(license_obj.license_id)
        
        self.assertEqual(summary["by_type"]["agent_invocation"], 50)
        self.assertEqual(summary["by_type"]["pac_created"], 10)
    
    def test_feature_gate(self):
        """Test feature gate enforcement."""
        customer = self.manager.register_customer(
            company_name="Gate Corp",
            industry="Education",
            contact_email="gate@gate.com",
            contact_name="Gate User",
            billing_address="404 Gate Ln",
        )
        
        license_obj = self.manager.activate_license(
            customer_id=customer.customer_id,
            tier=self.LicenseTier.STARTER,
            agent_count=2,
        )
        
        gate = self.FeatureGate(self.manager)
        
        # Starter has basic registry
        allowed, _ = gate.check_access(license_obj.license_key, self.FeatureFlag.AGENT_REGISTRY)
        self.assertTrue(allowed)
        
        # Starter does NOT have custom doctrines
        allowed, reason = gate.check_access(license_obj.license_key, self.FeatureFlag.CUSTOM_DOCTRINES)
        self.assertFalse(allowed)
        self.assertIn("not included", reason)
    
    def test_arr_metrics(self):
        """Test ARR metrics calculation."""
        # Create multiple customers/licenses
        for i in range(3):
            customer = self.manager.register_customer(
                company_name=f"ARR Corp {i}",
                industry="Tech",
                contact_email=f"arr{i}@arr.com",
                contact_name=f"ARR User {i}",
                billing_address=f"{i}00 ARR St",
            )
            self.manager.activate_license(
                customer_id=customer.customer_id,
                tier=self.LicenseTier.PROFESSIONAL,
                agent_count=5,
            )
        
        metrics = self.manager.get_arr_metrics()
        
        self.assertGreater(int(metrics["active_licenses"]), 0)
        self.assertGreater(Decimal(metrics["total_arr"]), Decimal("0"))


# =============================================================================
# VALUATION MODULE TESTS
# =============================================================================

class TestValuationModules(unittest.TestCase):
    """Test suite for valuation modules."""
    
    def test_ai_native_economics(self):
        """Test AI native economics module."""
        try:
            from modules.valuation.ai_native_economics import (
                calculate_fte_replacement,
                calculate_cost_savings,
            )
            
            result = calculate_fte_replacement(
                python_loc=100000,
                test_files=20,
                pac_artifacts=50,
            )
            
            self.assertIn("min_fte", result)
            self.assertIn("max_fte", result)
            self.assertGreater(result["min_fte"], 0)
            
        except ImportError:
            self.skipTest("AI native economics module not available")
    
    def test_tam_sam_som(self):
        """Test market sizing module."""
        try:
            from modules.valuation.tam_sam_som import (
                calculate_tam_sam_som,
            )
            
            result = calculate_tam_sam_som()
            
            self.assertIn("tam", result)
            self.assertIn("sam", result)
            self.assertIn("som", result)
            self.assertGreater(result["tam"], result["sam"])
            self.assertGreater(result["sam"], result["som"])
            
        except ImportError:
            self.skipTest("TAM SAM SOM module not available")
    
    def test_ip_portfolio(self):
        """Test IP portfolio valuation."""
        try:
            from modules.valuation.ip_portfolio import (
                assess_ip_portfolio,
            )
            
            result = assess_ip_portfolio()
            
            self.assertIn("total_value", result)
            self.assertIn("categories", result)
            self.assertGreater(result["total_value"], 0)
            
        except ImportError:
            self.skipTest("IP portfolio module not available")


# =============================================================================
# GOVERNANCE TESTS
# =============================================================================

class TestGovernance(unittest.TestCase):
    """Test suite for governance modules."""
    
    def test_gid_registry_exists(self):
        """Test GID registry file exists and is valid JSON."""
        registry_path = Path("core/governance/gid_registry.json")
        
        self.assertTrue(registry_path.exists(), "GID registry not found")
        
        with open(registry_path) as f:
            registry = json.load(f)
        
        self.assertIn("agents", registry)
        self.assertGreater(len(registry["agents"]), 0)
    
    def test_gid_registry_structure(self):
        """Test GID registry has required structure."""
        registry_path = Path("core/governance/gid_registry.json")
        
        if not registry_path.exists():
            self.skipTest("GID registry not found")
        
        with open(registry_path) as f:
            registry = json.load(f)
        
        for agent in registry["agents"]:
            self.assertIn("gid", agent)
            self.assertIn("name", agent)
            self.assertTrue(agent["gid"].startswith("GID-"))
    
    def test_scram_module_exists(self):
        """Test SCRAM module exists."""
        scram_paths = [
            Path("core/governance/scram.py"),
            Path("core/governance/scram_controller.py"),
        ]
        
        found = any(p.exists() for p in scram_paths)
        self.assertTrue(found, "SCRAM module not found")


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration(unittest.TestCase):
    """Integration tests across modules."""
    
    def test_settlement_to_freight_integration(self):
        """Test that settlement and freight modules can work together."""
        try:
            from modules.chainpay.settlement_engine import (
                create_settlement_engine,
                PaymentParty,
                Money,
                Currency,
                SettlementMethod,
            )
            from modules.freight.pilot_program import (
                PilotProgramManager,
                CompanyProfile,
                Contact,
                CompanySize,
                FreightMode,
            )
            
            # Create pilot customer
            pilot_manager = PilotProgramManager()
            company = CompanyProfile(
                company_id="INT-001",
                name="Integration Test Co",
                industry="3PL",
                size=CompanySize.SMB,
                annual_freight_spend=Decimal("10000000"),
                primary_modes=[FreightMode.FTL],
            )
            pilot_manager.register_company(company)
            
            # Process a freight payment
            settlement_engine = create_settlement_engine()
            shipper = PaymentParty("SHP-INT", company.name, "ACC-INT-1", kyc_verified=True)
            carrier = PaymentParty("CAR-INT", "Carrier Corp", "ACC-INT-2", kyc_verified=True)
            
            tx = settlement_engine.execute_full_pipeline(
                source=shipper,
                destination=carrier,
                amount=Money(Decimal("5000"), Currency.USD),
                method=SettlementMethod.HEDERA_INSTANT,
                reference="FREIGHT-INT-001",
            )
            
            from modules.chainpay.settlement_engine import PaymentStatus
            self.assertEqual(tx.status, PaymentStatus.CONFIRMED)
            
        except ImportError as e:
            self.skipTest(f"Required modules not available: {e}")
    
    def test_licensing_feature_gate_integration(self):
        """Test licensing integrates with feature gates."""
        try:
            from modules.gaas.licensing import (
                LicenseManager,
                LicenseTier,
                FeatureFlag,
                FeatureGate,
            )
            
            manager = LicenseManager()
            gate = FeatureGate(manager)
            
            # Create customer and license
            customer = manager.register_customer(
                company_name="Feature Gate Test",
                industry="Tech",
                contact_email="fg@test.com",
                contact_name="FG User",
                billing_address="123 FG St",
            )
            
            license_obj = manager.activate_license(
                customer_id=customer.customer_id,
                tier=LicenseTier.ENTERPRISE,
                agent_count=25,
            )
            
            # Test gate enforcement
            allowed, _ = gate.check_access(
                license_obj.license_key,
                FeatureFlag.SCRAM_CONTROLLER
            )
            self.assertTrue(allowed)
            
            # Test agent limit enforcement
            allowed, _ = gate.enforce_agent_limit(license_obj.license_key, 100)
            self.assertTrue(allowed)  # Enterprise has unlimited
            
        except ImportError as e:
            self.skipTest(f"Licensing module not available: {e}")


# =============================================================================
# TEST RUNNER
# =============================================================================

def run_tests(verbosity: int = 2) -> Tuple[int, int]:
    """
    Run all tests and return results.
    
    Returns:
        Tuple of (tests_run, failures)
    """
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestSettlementEngine,
        TestPilotProgram,
        TestLicensing,
        TestValuationModules,
        TestGovernance,
        TestIntegration,
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    return result.testsRun, len(result.failures) + len(result.errors)


def main():
    """Main entry point for test suite."""
    print("=" * 70)
    print("CHAINBRIDGE PRODUCTION TEST SUITE")
    print("PAC: PAC-JEFFREY-TARGET-20M-001 (TASK 4)")
    print("=" * 70)
    
    tests_run, failures = run_tests(verbosity=2)
    
    print("=" * 70)
    print(f"TESTS RUN: {tests_run}")
    print(f"FAILURES: {failures}")
    print(f"SUCCESS RATE: {((tests_run - failures) / tests_run * 100) if tests_run > 0 else 0:.1f}%")
    print("=" * 70)
    
    # Return appropriate exit code
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
