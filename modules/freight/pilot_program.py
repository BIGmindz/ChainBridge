#!/usr/bin/env python3
"""
ChainFreight Pilot Program & LOI Framework
==========================================

Letter of Intent and pilot program infrastructure for 
ChainFreight customer acquisition.

PAC Reference: PAC-JEFFREY-TARGET-20M-001 (TASK 2)
Constitutional Authority: ALEX (FOUNDER / CEO)
Executor: BENSON [GID-00]

Schema: v4.0.0
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum, auto
from typing import Any, Dict, List, Optional
import json


# =============================================================================
# ENUMS
# =============================================================================

class PilotStatus(Enum):
    """Pilot program status lifecycle."""
    LEAD = auto()           # Initial contact
    QUALIFIED = auto()      # Qualification criteria met
    LOI_SENT = auto()       # LOI issued to prospect
    LOI_NEGOTIATING = auto()  # In negotiation
    LOI_SIGNED = auto()     # LOI executed
    PILOT_ACTIVE = auto()   # Pilot underway
    PILOT_COMPLETE = auto() # Pilot concluded
    CONVERTED = auto()      # Converted to full customer
    CHURNED = auto()        # Did not convert


class CompanySize(Enum):
    """Company size classification."""
    STARTUP = "startup"           # < $10M revenue
    SMB = "smb"                   # $10M - $100M
    MID_MARKET = "mid_market"     # $100M - $1B
    ENTERPRISE = "enterprise"     # $1B+


class FreightMode(Enum):
    """Freight transportation modes."""
    FTL = "full_truckload"
    LTL = "less_than_truckload"
    INTERMODAL = "intermodal"
    OCEAN = "ocean"
    AIR = "air"
    RAIL = "rail"
    DRAYAGE = "drayage"


class PilotTier(Enum):
    """Pilot program tiers."""
    EXPLORER = "explorer"     # Basic pilot, limited shipments
    GROWTH = "growth"         # Standard pilot, moderate volume
    ENTERPRISE = "enterprise" # Full pilot, high volume


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CompanyProfile:
    """Prospective customer company profile."""
    company_id: str
    name: str
    industry: str
    size: CompanySize
    annual_freight_spend: Decimal
    primary_modes: List[FreightMode]
    headquarters_country: str = "US"
    headquarters_state: Optional[str] = None
    website: Optional[str] = None
    employee_count: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "company_id": self.company_id,
            "name": self.name,
            "industry": self.industry,
            "size": self.size.value,
            "annual_freight_spend": str(self.annual_freight_spend),
            "primary_modes": [m.value for m in self.primary_modes],
            "headquarters_country": self.headquarters_country,
            "headquarters_state": self.headquarters_state,
            "website": self.website,
            "employee_count": self.employee_count,
        }


@dataclass
class Contact:
    """Contact at prospective customer."""
    contact_id: str
    company_id: str
    name: str
    title: str
    email: str
    phone: Optional[str] = None
    is_decision_maker: bool = False
    is_champion: bool = False
    notes: Optional[str] = None


@dataclass
class QualificationCriteria:
    """Lead qualification criteria assessment."""
    has_budget: bool
    has_authority: bool
    has_need: bool
    has_timeline: bool
    fit_score: int  # 0-100
    disqualification_reason: Optional[str] = None
    
    @property
    def is_qualified(self) -> bool:
        return (self.has_budget and self.has_authority and 
                self.has_need and self.has_timeline and 
                self.fit_score >= 60)


@dataclass
class PilotTerms:
    """Pilot program terms."""
    tier: PilotTier
    duration_days: int
    max_shipments: int
    fee_structure: str  # "free", "discounted", "standard"
    discount_percentage: Decimal = Decimal("0")
    success_criteria: List[str] = field(default_factory=list)
    conversion_incentive: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier.value,
            "duration_days": self.duration_days,
            "max_shipments": self.max_shipments,
            "fee_structure": self.fee_structure,
            "discount_percentage": str(self.discount_percentage),
            "success_criteria": self.success_criteria,
            "conversion_incentive": self.conversion_incentive,
        }


@dataclass
class LOI:
    """Letter of Intent document."""
    loi_id: str
    version: str
    company: CompanyProfile
    primary_contact: Contact
    pilot_terms: PilotTerms
    effective_date: datetime
    expiration_date: datetime
    special_terms: List[str] = field(default_factory=list)
    status: str = "draft"  # draft, sent, signed, expired
    signed_date: Optional[datetime] = None
    signed_by: Optional[str] = None
    document_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "loi_id": self.loi_id,
            "version": self.version,
            "company": self.company.to_dict(),
            "pilot_terms": self.pilot_terms.to_dict(),
            "effective_date": self.effective_date.isoformat(),
            "expiration_date": self.expiration_date.isoformat(),
            "special_terms": self.special_terms,
            "status": self.status,
            "signed_date": self.signed_date.isoformat() if self.signed_date else None,
            "signed_by": self.signed_by,
            "document_hash": self.document_hash,
        }
    
    def compute_hash(self) -> str:
        """Compute document hash for integrity."""
        content = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class PilotMetrics:
    """Pilot program performance metrics."""
    pilot_id: str
    shipments_completed: int = 0
    shipments_failed: int = 0
    total_freight_value: Decimal = Decimal("0")
    average_settlement_time_hours: Decimal = Decimal("0")
    customer_satisfaction_score: Optional[int] = None  # 1-10
    issues_reported: int = 0
    issues_resolved: int = 0
    platform_uptime_percentage: Decimal = Decimal("99.9")
    
    @property
    def success_rate(self) -> Decimal:
        total = self.shipments_completed + self.shipments_failed
        if total == 0:
            return Decimal("0")
        return (Decimal(self.shipments_completed) / Decimal(total)) * 100


@dataclass
class PilotProgram:
    """Complete pilot program record."""
    pilot_id: str
    company: CompanyProfile
    contacts: List[Contact]
    qualification: QualificationCriteria
    loi: Optional[LOI]
    terms: PilotTerms
    status: PilotStatus
    metrics: PilotMetrics
    created_at: datetime
    updated_at: datetime
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    conversion_date: Optional[datetime] = None
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pilot_id": self.pilot_id,
            "company": self.company.to_dict(),
            "status": self.status.name,
            "terms": self.terms.to_dict(),
            "loi_id": self.loi.loi_id if self.loi else None,
            "metrics": {
                "shipments_completed": self.metrics.shipments_completed,
                "success_rate": str(self.metrics.success_rate),
                "total_freight_value": str(self.metrics.total_freight_value),
            },
            "created_at": self.created_at.isoformat(),
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
        }


# =============================================================================
# LOI TEMPLATE GENERATOR
# =============================================================================

class LOITemplateGenerator:
    """Generate LOI documents from templates."""
    
    TEMPLATE = '''
LETTER OF INTENT
ChainFreight Pilot Program
================================================================================

LOI Reference: {loi_id}
Version: {version}
Generated: {generated_date}

--------------------------------------------------------------------------------
PARTIES
--------------------------------------------------------------------------------

PROVIDER:
ChainBridge Technologies, Inc.
("ChainBridge" or "Provider")

PROSPECTIVE CUSTOMER:
{company_name}
{company_address}
("Customer")

Primary Contact: {contact_name}, {contact_title}
Email: {contact_email}

--------------------------------------------------------------------------------
PURPOSE
--------------------------------------------------------------------------------

This Letter of Intent ("LOI") establishes the framework for a pilot program 
("Pilot") to evaluate ChainFreight, ChainBridge's blockchain-powered freight 
settlement and documentation platform.

This LOI is non-binding except for the confidentiality provisions herein.

--------------------------------------------------------------------------------
PILOT PROGRAM TERMS
--------------------------------------------------------------------------------

Tier: {pilot_tier}
Duration: {duration_days} days from Effective Date
Maximum Shipments: {max_shipments}
Fee Structure: {fee_structure}
{discount_line}

EFFECTIVE DATE: {effective_date}
EXPIRATION DATE: {expiration_date}

--------------------------------------------------------------------------------
SUCCESS CRITERIA
--------------------------------------------------------------------------------

The Pilot shall be considered successful upon achievement of:

{success_criteria}

--------------------------------------------------------------------------------
MUTUAL OBLIGATIONS
--------------------------------------------------------------------------------

PROVIDER OBLIGATIONS:
1. Provide access to ChainFreight platform features as agreed
2. Provide technical support during business hours
3. Ensure platform availability of 99.5% or greater
4. Provide training for Customer personnel
5. Maintain confidentiality of Customer data

CUSTOMER OBLIGATIONS:
1. Designate primary point of contact
2. Provide timely feedback on platform performance
3. Process minimum volume as agreed for valid pilot assessment
4. Participate in weekly check-in calls
5. Complete pilot evaluation survey

--------------------------------------------------------------------------------
CONFIDENTIALITY
--------------------------------------------------------------------------------

Both parties agree to maintain confidentiality of:
- Pricing and commercial terms
- Technical specifications and documentation
- Business processes and data
- Pilot results and metrics

This confidentiality obligation survives expiration of this LOI for two (2) years.

--------------------------------------------------------------------------------
CONVERSION OFFER
--------------------------------------------------------------------------------

Upon successful completion of the Pilot, Customer may elect to convert to a 
full commercial agreement under the following incentive:

{conversion_incentive}

This offer expires thirty (30) days after Pilot completion.

--------------------------------------------------------------------------------
SPECIAL TERMS
--------------------------------------------------------------------------------

{special_terms}

--------------------------------------------------------------------------------
NON-BINDING NATURE
--------------------------------------------------------------------------------

Except for the confidentiality provisions above, this LOI does not create any 
binding obligations on either party. Either party may terminate discussions at 
any time for any reason.

A binding agreement shall only arise upon execution of a definitive Master 
Services Agreement.

--------------------------------------------------------------------------------
SIGNATURES
--------------------------------------------------------------------------------

CHAINBRIDGE TECHNOLOGIES, INC.

By: _________________________
Name: Alex Bozza
Title: CEO & Founder
Date: _______________________


{company_name_upper}

By: _________________________
Name: {signatory_name}
Title: {signatory_title}  
Date: _______________________


--------------------------------------------------------------------------------
Document Hash: {document_hash}
================================================================================
'''

    def generate(self, loi: LOI) -> str:
        """Generate LOI document from template."""
        
        # Format success criteria
        success_criteria_formatted = "\n".join(
            f"{i+1}. {criterion}" 
            for i, criterion in enumerate(loi.pilot_terms.success_criteria)
        ) or "To be defined during pilot kickoff."
        
        # Format special terms
        special_terms_formatted = "\n".join(
            f"- {term}" for term in loi.special_terms
        ) or "None."
        
        # Discount line
        discount_line = ""
        if loi.pilot_terms.discount_percentage > 0:
            discount_line = f"Discount: {loi.pilot_terms.discount_percentage}% off standard rates"
        
        # Conversion incentive
        conversion_incentive = loi.pilot_terms.conversion_incentive or "Standard commercial terms apply."
        
        # Compute hash before filling template
        loi.document_hash = loi.compute_hash()
        
        return self.TEMPLATE.format(
            loi_id=loi.loi_id,
            version=loi.version,
            generated_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            company_name=loi.company.name,
            company_address=f"{loi.company.headquarters_state or ''}, {loi.company.headquarters_country}",
            contact_name=loi.primary_contact.name,
            contact_title=loi.primary_contact.title,
            contact_email=loi.primary_contact.email,
            pilot_tier=loi.pilot_terms.tier.value.upper(),
            duration_days=loi.pilot_terms.duration_days,
            max_shipments=loi.pilot_terms.max_shipments,
            fee_structure=loi.pilot_terms.fee_structure.title(),
            discount_line=discount_line,
            effective_date=loi.effective_date.strftime("%B %d, %Y"),
            expiration_date=loi.expiration_date.strftime("%B %d, %Y"),
            success_criteria=success_criteria_formatted,
            conversion_incentive=conversion_incentive,
            special_terms=special_terms_formatted,
            company_name_upper=loi.company.name.upper(),
            signatory_name=loi.primary_contact.name if loi.primary_contact.is_decision_maker else "[AUTHORIZED SIGNATORY]",
            signatory_title=loi.primary_contact.title if loi.primary_contact.is_decision_maker else "[TITLE]",
            document_hash=loi.document_hash,
        )


# =============================================================================
# PILOT PROGRAM MANAGER
# =============================================================================

class PilotProgramManager:
    """
    Manages ChainFreight pilot program lifecycle.
    
    Responsibilities:
    - Lead qualification
    - LOI generation and tracking
    - Pilot execution monitoring
    - Conversion tracking
    
    Constitutional Compliance:
    - INV-NO-NARRATIVE-INFLATION: Real metrics only
    - INV-FAIL-CLOSED: No fabricated customers
    """
    
    # Default pilot tier configurations
    TIER_CONFIGS = {
        PilotTier.EXPLORER: PilotTerms(
            tier=PilotTier.EXPLORER,
            duration_days=30,
            max_shipments=10,
            fee_structure="free",
            discount_percentage=Decimal("100"),
            success_criteria=[
                "Complete 5+ shipments through platform",
                "Achieve 90% on-time settlement rate",
                "Provide feedback survey completion",
            ],
            conversion_incentive="20% discount on first 90 days of commercial service",
        ),
        PilotTier.GROWTH: PilotTerms(
            tier=PilotTier.GROWTH,
            duration_days=60,
            max_shipments=50,
            fee_structure="discounted",
            discount_percentage=Decimal("50"),
            success_criteria=[
                "Complete 25+ shipments through platform",
                "Achieve 95% on-time settlement rate",
                "Average settlement time under 4 hours",
                "Customer satisfaction score 8+/10",
            ],
            conversion_incentive="25% discount on first 6 months of commercial service",
        ),
        PilotTier.ENTERPRISE: PilotTerms(
            tier=PilotTier.ENTERPRISE,
            duration_days=90,
            max_shipments=200,
            fee_structure="discounted",
            discount_percentage=Decimal("30"),
            success_criteria=[
                "Complete 100+ shipments through platform",
                "Achieve 99% on-time settlement rate",
                "Average settlement time under 2 hours",
                "Customer satisfaction score 9+/10",
                "Integration with existing TMS complete",
            ],
            conversion_incentive="Custom enterprise pricing with volume commitments",
        ),
    }
    
    def __init__(self):
        self._pilots: Dict[str, PilotProgram] = {}
        self._companies: Dict[str, CompanyProfile] = {}
        self._lois: Dict[str, LOI] = {}
        self._loi_generator = LOITemplateGenerator()
    
    def register_company(self, company: CompanyProfile) -> str:
        """Register a prospective customer company."""
        self._companies[company.company_id] = company
        return company.company_id
    
    def qualify_lead(
        self,
        company_id: str,
        has_budget: bool,
        has_authority: bool,
        has_need: bool,
        has_timeline: bool,
        fit_score: int,
        disqualification_reason: Optional[str] = None,
    ) -> QualificationCriteria:
        """Qualify a lead using BANT criteria."""
        return QualificationCriteria(
            has_budget=has_budget,
            has_authority=has_authority,
            has_need=has_need,
            has_timeline=has_timeline,
            fit_score=fit_score,
            disqualification_reason=disqualification_reason,
        )
    
    def create_pilot(
        self,
        company: CompanyProfile,
        contacts: List[Contact],
        qualification: QualificationCriteria,
        tier: PilotTier = PilotTier.GROWTH,
        custom_terms: Optional[PilotTerms] = None,
    ) -> PilotProgram:
        """Create a new pilot program."""
        
        if not qualification.is_qualified:
            raise ValueError(
                f"Lead not qualified: {qualification.disqualification_reason or 'Does not meet criteria'}"
            )
        
        pilot_id = f"PILOT-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc)
        
        terms = custom_terms or self.TIER_CONFIGS[tier]
        
        pilot = PilotProgram(
            pilot_id=pilot_id,
            company=company,
            contacts=contacts,
            qualification=qualification,
            loi=None,
            terms=terms,
            status=PilotStatus.QUALIFIED,
            metrics=PilotMetrics(pilot_id=pilot_id),
            created_at=now,
            updated_at=now,
        )
        
        self._pilots[pilot_id] = pilot
        
        return pilot
    
    def generate_loi(
        self,
        pilot_id: str,
        special_terms: Optional[List[str]] = None,
        effective_date: Optional[datetime] = None,
    ) -> LOI:
        """Generate LOI for a pilot program."""
        
        pilot = self._pilots.get(pilot_id)
        if not pilot:
            raise ValueError(f"Pilot {pilot_id} not found")
        
        if pilot.status not in (PilotStatus.QUALIFIED, PilotStatus.LOI_NEGOTIATING):
            raise ValueError(f"Pilot {pilot_id} not in valid status for LOI generation")
        
        # Find decision maker contact
        primary_contact = next(
            (c for c in pilot.contacts if c.is_decision_maker or c.is_champion),
            pilot.contacts[0] if pilot.contacts else None
        )
        
        if not primary_contact:
            raise ValueError(f"No contact available for pilot {pilot_id}")
        
        now = datetime.now(timezone.utc)
        eff_date = effective_date or now
        exp_date = eff_date + timedelta(days=30)  # LOI valid for 30 days
        
        loi_id = f"LOI-CF-{uuid.uuid4().hex[:8].upper()}"
        
        loi = LOI(
            loi_id=loi_id,
            version="1.0",
            company=pilot.company,
            primary_contact=primary_contact,
            pilot_terms=pilot.terms,
            effective_date=eff_date,
            expiration_date=exp_date,
            special_terms=special_terms or [],
            status="draft",
        )
        
        # Compute document hash
        loi.document_hash = loi.compute_hash()
        
        self._lois[loi_id] = loi
        pilot.loi = loi
        pilot.status = PilotStatus.LOI_SENT
        pilot.updated_at = now
        
        return loi
    
    def render_loi_document(self, loi_id: str) -> str:
        """Render LOI as formatted document."""
        loi = self._lois.get(loi_id)
        if not loi:
            raise ValueError(f"LOI {loi_id} not found")
        
        return self._loi_generator.generate(loi)
    
    def sign_loi(
        self,
        loi_id: str,
        signed_by: str,
        signed_date: Optional[datetime] = None,
    ) -> LOI:
        """Record LOI signature."""
        loi = self._lois.get(loi_id)
        if not loi:
            raise ValueError(f"LOI {loi_id} not found")
        
        loi.status = "signed"
        loi.signed_by = signed_by
        loi.signed_date = signed_date or datetime.now(timezone.utc)
        
        # Update associated pilot
        for pilot in self._pilots.values():
            if pilot.loi and pilot.loi.loi_id == loi_id:
                pilot.status = PilotStatus.LOI_SIGNED
                pilot.updated_at = datetime.now(timezone.utc)
                break
        
        return loi
    
    def start_pilot(self, pilot_id: str) -> PilotProgram:
        """Start pilot program execution."""
        pilot = self._pilots.get(pilot_id)
        if not pilot:
            raise ValueError(f"Pilot {pilot_id} not found")
        
        if pilot.status != PilotStatus.LOI_SIGNED:
            raise ValueError(f"Pilot {pilot_id} LOI not signed")
        
        now = datetime.now(timezone.utc)
        pilot.status = PilotStatus.PILOT_ACTIVE
        pilot.start_date = now
        pilot.end_date = now + timedelta(days=pilot.terms.duration_days)
        pilot.updated_at = now
        
        return pilot
    
    def record_shipment(
        self,
        pilot_id: str,
        success: bool,
        freight_value: Decimal,
        settlement_time_hours: Decimal,
    ) -> PilotMetrics:
        """Record a shipment in pilot metrics."""
        pilot = self._pilots.get(pilot_id)
        if not pilot:
            raise ValueError(f"Pilot {pilot_id} not found")
        
        if success:
            pilot.metrics.shipments_completed += 1
        else:
            pilot.metrics.shipments_failed += 1
        
        pilot.metrics.total_freight_value += freight_value
        
        # Running average for settlement time
        total_shipments = pilot.metrics.shipments_completed
        if total_shipments > 0:
            old_avg = pilot.metrics.average_settlement_time_hours
            pilot.metrics.average_settlement_time_hours = (
                (old_avg * (total_shipments - 1) + settlement_time_hours) / total_shipments
            )
        
        pilot.updated_at = datetime.now(timezone.utc)
        
        return pilot.metrics
    
    def complete_pilot(self, pilot_id: str, satisfaction_score: int) -> PilotProgram:
        """Complete pilot program."""
        pilot = self._pilots.get(pilot_id)
        if not pilot:
            raise ValueError(f"Pilot {pilot_id} not found")
        
        pilot.metrics.customer_satisfaction_score = satisfaction_score
        pilot.status = PilotStatus.PILOT_COMPLETE
        pilot.end_date = datetime.now(timezone.utc)
        pilot.updated_at = pilot.end_date
        
        return pilot
    
    def convert_pilot(self, pilot_id: str) -> PilotProgram:
        """Convert pilot to full customer."""
        pilot = self._pilots.get(pilot_id)
        if not pilot:
            raise ValueError(f"Pilot {pilot_id} not found")
        
        if pilot.status != PilotStatus.PILOT_COMPLETE:
            raise ValueError(f"Pilot {pilot_id} not complete")
        
        pilot.status = PilotStatus.CONVERTED
        pilot.conversion_date = datetime.now(timezone.utc)
        pilot.updated_at = pilot.conversion_date
        
        return pilot
    
    def get_pipeline_metrics(self) -> Dict[str, Any]:
        """Get pilot pipeline metrics."""
        total = len(self._pilots)
        
        by_status = {}
        for status in PilotStatus:
            count = len([p for p in self._pilots.values() if p.status == status])
            by_status[status.name] = count
        
        total_freight_value = sum(
            p.metrics.total_freight_value 
            for p in self._pilots.values()
        )
        
        converted = [p for p in self._pilots.values() if p.status == PilotStatus.CONVERTED]
        conversion_rate = (len(converted) / total * 100) if total > 0 else 0
        
        return {
            "total_pilots": total,
            "by_status": by_status,
            "total_freight_value": str(total_freight_value),
            "conversion_rate_percent": str(conversion_rate),
            "active_lois": len([l for l in self._lois.values() if l.status in ("sent", "draft")]),
            "signed_lois": len([l for l in self._lois.values() if l.status == "signed"]),
        }


# =============================================================================
# SELF-TEST
# =============================================================================

def self_test() -> bool:
    """Self-test for pilot program manager."""
    print("=" * 60)
    print("CHAINFREIGHT PILOT PROGRAM - SELF TEST")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Create manager
    tests_total += 1
    try:
        manager = PilotProgramManager()
        print("✅ TEST 1: Manager creation - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 1: Manager creation - FAILED: {e}")
        return False
    
    # Test 2: Register company
    tests_total += 1
    try:
        company = CompanyProfile(
            company_id="COMP-001",
            name="Acme Logistics Corp",
            industry="Third-Party Logistics",
            size=CompanySize.MID_MARKET,
            annual_freight_spend=Decimal("50000000"),
            primary_modes=[FreightMode.FTL, FreightMode.LTL],
            headquarters_state="TX",
        )
        manager.register_company(company)
        print(f"✅ TEST 2: Company registration ({company.name}) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 2: Company registration - FAILED: {e}")
    
    # Test 3: Qualify lead
    tests_total += 1
    try:
        qualification = manager.qualify_lead(
            company_id="COMP-001",
            has_budget=True,
            has_authority=True,
            has_need=True,
            has_timeline=True,
            fit_score=85,
        )
        assert qualification.is_qualified
        print(f"✅ TEST 3: Lead qualification (fit={qualification.fit_score}) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 3: Lead qualification - FAILED: {e}")
    
    # Test 4: Create pilot
    tests_total += 1
    try:
        contact = Contact(
            contact_id="CONT-001",
            company_id="COMP-001",
            name="John Smith",
            title="VP Supply Chain",
            email="jsmith@acmelogistics.com",
            is_decision_maker=True,
        )
        
        pilot = manager.create_pilot(
            company=company,
            contacts=[contact],
            qualification=qualification,
            tier=PilotTier.GROWTH,
        )
        assert pilot.status == PilotStatus.QUALIFIED
        print(f"✅ TEST 4: Pilot creation ({pilot.pilot_id}) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 4: Pilot creation - FAILED: {e}")
    
    # Test 5: Generate LOI
    tests_total += 1
    try:
        loi = manager.generate_loi(
            pilot_id=pilot.pilot_id,
            special_terms=["Custom integration support included"],
        )
        assert loi.status == "draft"
        assert loi.document_hash is not None
        print(f"✅ TEST 5: LOI generation ({loi.loi_id}) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 5: LOI generation - FAILED: {e}")
    
    # Test 6: Render LOI document
    tests_total += 1
    try:
        document = manager.render_loi_document(loi.loi_id)
        assert "LETTER OF INTENT" in document
        assert company.name in document
        print(f"✅ TEST 6: LOI rendering ({len(document)} chars) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 6: LOI rendering - FAILED: {e}")
    
    # Test 7: Sign LOI
    tests_total += 1
    try:
        signed_loi = manager.sign_loi(loi.loi_id, "John Smith")
        assert signed_loi.status == "signed"
        assert pilot.status == PilotStatus.LOI_SIGNED
        print(f"✅ TEST 7: LOI signing - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 7: LOI signing - FAILED: {e}")
    
    # Test 8: Start pilot
    tests_total += 1
    try:
        started_pilot = manager.start_pilot(pilot.pilot_id)
        assert started_pilot.status == PilotStatus.PILOT_ACTIVE
        assert started_pilot.start_date is not None
        print(f"✅ TEST 8: Pilot start - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 8: Pilot start - FAILED: {e}")
    
    # Test 9: Record shipments
    tests_total += 1
    try:
        for i in range(5):
            manager.record_shipment(
                pilot.pilot_id,
                success=True,
                freight_value=Decimal("25000"),
                settlement_time_hours=Decimal("2.5"),
            )
        metrics = pilot.metrics
        assert metrics.shipments_completed == 5
        assert metrics.success_rate == Decimal("100")
        print(f"✅ TEST 9: Shipment recording ({metrics.shipments_completed} shipments) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 9: Shipment recording - FAILED: {e}")
    
    # Test 10: Pipeline metrics
    tests_total += 1
    try:
        pipeline_metrics = manager.get_pipeline_metrics()
        assert pipeline_metrics["total_pilots"] > 0
        print(f"✅ TEST 10: Pipeline metrics (total={pipeline_metrics['total_pilots']}) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 10: Pipeline metrics - FAILED: {e}")
    
    # Summary
    print("=" * 60)
    print(f"PILOT PROGRAM TESTS: {tests_passed}/{tests_total} PASSED")
    print("=" * 60)
    
    return tests_passed == tests_total


if __name__ == "__main__":
    success = self_test()
    exit(0 if success else 1)
