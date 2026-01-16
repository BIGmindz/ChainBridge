#!/usr/bin/env python3
"""
Customer Acquisition Pipeline
==============================

Documents and tracks the Go-To-Market strategy and 
customer acquisition pipeline for ChainBridge.

PAC Reference: PAC-JEFFREY-TARGET-20M-001 (TASK 5)
Constitutional Authority: ALEX (FOUNDER / CEO)
Executor: BENSON [GID-00]

Schema: v4.0.0
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum, auto
from typing import Any, Dict, List, Optional
import json


# =============================================================================
# ENUMS
# =============================================================================

class DealStage(Enum):
    """Sales pipeline stages."""
    PROSPECT = auto()          # Initial identification
    QUALIFIED = auto()         # BANT qualified
    DISCOVERY = auto()         # Needs analysis
    DEMO = auto()              # Product demonstration
    PROPOSAL = auto()          # Proposal/pricing sent
    NEGOTIATION = auto()       # Contract negotiation
    VERBAL_COMMIT = auto()     # Verbal commitment received
    CLOSED_WON = auto()        # Deal signed
    CLOSED_LOST = auto()       # Deal lost


class LeadSource(Enum):
    """Lead source channels."""
    INBOUND_WEB = "inbound_web"
    CONTENT_MARKETING = "content_marketing"
    CONFERENCE = "conference"
    REFERRAL = "referral"
    PARTNER = "partner"
    OUTBOUND_EMAIL = "outbound_email"
    LINKEDIN = "linkedin"
    ANALYST_REFERRAL = "analyst"


class Segment(Enum):
    """Customer segments."""
    SHIPPER_ENTERPRISE = "shipper_enterprise"       # Large shippers ($1B+)
    SHIPPER_MID_MARKET = "shipper_mid_market"       # Mid-size shippers ($100M-$1B)
    THREE_PL = "3pl"                                 # Third-party logistics
    FREIGHT_BROKER = "freight_broker"               # Freight brokers
    CARRIER = "carrier"                              # Asset carriers
    FINTECH = "fintech"                              # Financial technology (Agent University)
    AI_PLATFORM = "ai_platform"                      # AI/ML platforms (Agent University)


class Product(Enum):
    """Product offerings."""
    CHAINFREIGHT = "chainfreight"
    CHAINPAY = "chainpay"
    CHAINSENSE = "chainsense"
    AGENT_UNIVERSITY = "agent_university"
    PLATFORM_BUNDLE = "platform_bundle"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class IdealCustomerProfile:
    """Ideal Customer Profile (ICP) definition."""
    segment: Segment
    min_revenue: Decimal
    max_revenue: Optional[Decimal]
    pain_points: List[str]
    value_proposition: str
    target_persona_titles: List[str]
    deal_size_range: tuple[Decimal, Decimal]
    sales_cycle_days: int
    key_objections: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment": self.segment.value,
            "min_revenue": str(self.min_revenue),
            "max_revenue": str(self.max_revenue) if self.max_revenue else None,
            "pain_points": self.pain_points,
            "value_proposition": self.value_proposition,
            "target_persona_titles": self.target_persona_titles,
            "deal_size_range": [str(d) for d in self.deal_size_range],
            "sales_cycle_days": self.sales_cycle_days,
            "key_objections": self.key_objections,
        }


@dataclass
class Lead:
    """Sales lead."""
    lead_id: str
    company_name: str
    segment: Segment
    source: LeadSource
    contact_name: str
    contact_title: str
    contact_email: str
    estimated_deal_size: Decimal
    created_at: datetime
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "lead_id": self.lead_id,
            "company_name": self.company_name,
            "segment": self.segment.value,
            "source": self.source.value,
            "contact_name": self.contact_name,
            "contact_title": self.contact_title,
            "estimated_deal_size": str(self.estimated_deal_size),
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Opportunity:
    """Sales opportunity (qualified lead)."""
    opportunity_id: str
    lead: Lead
    stage: DealStage
    products: List[Product]
    deal_value: Decimal
    probability: int  # 0-100%
    expected_close_date: datetime
    created_at: datetime
    updated_at: datetime
    champion: Optional[str] = None
    economic_buyer: Optional[str] = None
    decision_criteria: List[str] = field(default_factory=list)
    next_steps: Optional[str] = None
    competitor: Optional[str] = None
    loss_reason: Optional[str] = None
    
    @property
    def weighted_value(self) -> Decimal:
        return self.deal_value * (Decimal(self.probability) / 100)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "company_name": self.lead.company_name,
            "stage": self.stage.name,
            "products": [p.value for p in self.products],
            "deal_value": str(self.deal_value),
            "probability": self.probability,
            "weighted_value": str(self.weighted_value),
            "expected_close_date": self.expected_close_date.isoformat(),
            "champion": self.champion,
            "next_steps": self.next_steps,
        }


@dataclass
class Activity:
    """Sales activity record."""
    activity_id: str
    opportunity_id: str
    activity_type: str  # call, email, meeting, demo, proposal
    description: str
    outcome: Optional[str]
    timestamp: datetime
    next_activity: Optional[str] = None


@dataclass
class Campaign:
    """Marketing campaign."""
    campaign_id: str
    name: str
    channel: LeadSource
    target_segments: List[Segment]
    budget: Decimal
    start_date: datetime
    end_date: Optional[datetime]
    leads_generated: int = 0
    opportunities_created: int = 0
    deals_closed: int = 0
    revenue_attributed: Decimal = Decimal("0")
    
    @property
    def cost_per_lead(self) -> Optional[Decimal]:
        if self.leads_generated > 0:
            return self.budget / self.leads_generated
        return None
    
    @property
    def roi(self) -> Optional[Decimal]:
        if self.budget > 0:
            return ((self.revenue_attributed - self.budget) / self.budget) * 100
        return None


# =============================================================================
# IDEAL CUSTOMER PROFILES
# =============================================================================

class ICPCatalog:
    """Catalog of Ideal Customer Profiles."""
    
    PROFILES: Dict[Segment, IdealCustomerProfile] = {
        Segment.SHIPPER_ENTERPRISE: IdealCustomerProfile(
            segment=Segment.SHIPPER_ENTERPRISE,
            min_revenue=Decimal("1000000000"),  # $1B+
            max_revenue=None,
            pain_points=[
                "Manual freight payment reconciliation",
                "Carrier payment disputes",
                "Lack of real-time settlement visibility",
                "Multiple payment platforms to manage",
                "Compliance and audit burden",
            ],
            value_proposition="Real-time blockchain settlement reduces payment disputes by 90% and cuts reconciliation time by 70%",
            target_persona_titles=[
                "VP Supply Chain",
                "VP Transportation",
                "Chief Procurement Officer",
                "VP Finance - Operations",
            ],
            deal_size_range=(Decimal("200000"), Decimal("1000000")),  # $200K-$1M ACV
            sales_cycle_days=180,
            key_objections=[
                "Already have payment systems in place",
                "Blockchain is unproven in enterprise",
                "Integration complexity concerns",
            ],
        ),
        
        Segment.SHIPPER_MID_MARKET: IdealCustomerProfile(
            segment=Segment.SHIPPER_MID_MARKET,
            min_revenue=Decimal("100000000"),  # $100M
            max_revenue=Decimal("1000000000"),  # $1B
            pain_points=[
                "Manual invoice processing",
                "Late payment penalties",
                "Limited visibility into payment status",
                "Carrier relationship management",
            ],
            value_proposition="Automated settlement workflow eliminates late payments and improves carrier relationships",
            target_persona_titles=[
                "Director of Logistics",
                "Director of Finance",
                "Supply Chain Manager",
            ],
            deal_size_range=(Decimal("50000"), Decimal("200000")),  # $50K-$200K ACV
            sales_cycle_days=90,
            key_objections=[
                "Budget constraints",
                "IT resources for implementation",
                "Change management concerns",
            ],
        ),
        
        Segment.THREE_PL: IdealCustomerProfile(
            segment=Segment.THREE_PL,
            min_revenue=Decimal("50000000"),  # $50M
            max_revenue=None,
            pain_points=[
                "Cash flow management with float",
                "Multiple shipper payment systems",
                "Carrier factoring costs",
                "Audit and compliance burden",
            ],
            value_proposition="Instant settlement eliminates float and reduces factoring costs while providing audit-ready records",
            target_persona_titles=[
                "CFO",
                "VP Operations",
                "Director of Finance",
            ],
            deal_size_range=(Decimal("75000"), Decimal("300000")),  # $75K-$300K ACV
            sales_cycle_days=120,
            key_objections=[
                "Complex multi-shipper requirements",
                "Existing TMS integrations",
                "Carrier adoption concerns",
            ],
        ),
        
        Segment.FINTECH: IdealCustomerProfile(
            segment=Segment.FINTECH,
            min_revenue=Decimal("10000000"),  # $10M
            max_revenue=None,
            pain_points=[
                "Governance for AI agents in production",
                "Audit trail for AI decisions",
                "Risk management for autonomous systems",
                "Regulatory compliance for AI",
            ],
            value_proposition="Constitutional AI governance provides audit-ready control and compliance for AI agent operations",
            target_persona_titles=[
                "Head of AI/ML",
                "VP Engineering",
                "Chief Risk Officer",
                "Head of Compliance",
            ],
            deal_size_range=(Decimal("60000"), Decimal("240000")),  # $60K-$240K ACV (licensing)
            sales_cycle_days=60,
            key_objections=[
                "Build vs buy decision",
                "Integration with existing AI stack",
                "Proof of governance effectiveness",
            ],
        ),
        
        Segment.AI_PLATFORM: IdealCustomerProfile(
            segment=Segment.AI_PLATFORM,
            min_revenue=Decimal("25000000"),  # $25M
            max_revenue=None,
            pain_points=[
                "Multi-agent orchestration at scale",
                "Constitutional AI requirements",
                "Customer trust and safety",
                "Enterprise governance needs",
            ],
            value_proposition="Production-ready governance framework accelerates enterprise AI deployments with constitutional guarantees",
            target_persona_titles=[
                "CTO",
                "VP Product",
                "Head of Trust & Safety",
                "VP Enterprise",
            ],
            deal_size_range=(Decimal("120000"), Decimal("500000")),  # $120K-$500K ACV
            sales_cycle_days=90,
            key_objections=[
                "Competitive differentiation concerns",
                "Open source alternatives",
                "Technical integration complexity",
            ],
        ),
    }
    
    @classmethod
    def get_profile(cls, segment: Segment) -> Optional[IdealCustomerProfile]:
        return cls.PROFILES.get(segment)
    
    @classmethod
    def get_all_profiles(cls) -> List[IdealCustomerProfile]:
        return list(cls.PROFILES.values())


# =============================================================================
# PIPELINE MANAGER
# =============================================================================

class PipelineManager:
    """
    Manages the customer acquisition pipeline.
    
    Tracks:
    - Leads by source and segment
    - Opportunities by stage
    - Pipeline value and velocity
    - Campaign attribution
    
    Constitutional Compliance:
    - INV-NO-NARRATIVE-INFLATION: Real pipeline only
    - INV-PDO-PRIMACY: Tracked metrics, not projections
    """
    
    # Stage probability mappings (industry standard)
    STAGE_PROBABILITY = {
        DealStage.PROSPECT: 5,
        DealStage.QUALIFIED: 10,
        DealStage.DISCOVERY: 20,
        DealStage.DEMO: 35,
        DealStage.PROPOSAL: 50,
        DealStage.NEGOTIATION: 70,
        DealStage.VERBAL_COMMIT: 90,
        DealStage.CLOSED_WON: 100,
        DealStage.CLOSED_LOST: 0,
    }
    
    def __init__(self):
        self._leads: Dict[str, Lead] = {}
        self._opportunities: Dict[str, Opportunity] = {}
        self._activities: List[Activity] = []
        self._campaigns: Dict[str, Campaign] = {}
        self._icp_catalog = ICPCatalog()
    
    def create_lead(
        self,
        company_name: str,
        segment: Segment,
        source: LeadSource,
        contact_name: str,
        contact_title: str,
        contact_email: str,
        estimated_deal_size: Optional[Decimal] = None,
        notes: Optional[str] = None,
    ) -> Lead:
        """Create a new lead."""
        lead_id = f"LEAD-{uuid.uuid4().hex[:8].upper()}"
        
        # Use ICP for deal size estimate if not provided
        if estimated_deal_size is None:
            icp = self._icp_catalog.get_profile(segment)
            if icp:
                # Use midpoint of range
                estimated_deal_size = (icp.deal_size_range[0] + icp.deal_size_range[1]) / 2
            else:
                estimated_deal_size = Decimal("50000")
        
        lead = Lead(
            lead_id=lead_id,
            company_name=company_name,
            segment=segment,
            source=source,
            contact_name=contact_name,
            contact_title=contact_title,
            contact_email=contact_email,
            estimated_deal_size=estimated_deal_size,
            created_at=datetime.now(timezone.utc),
            notes=notes,
        )
        
        self._leads[lead_id] = lead
        return lead
    
    def qualify_lead(
        self,
        lead_id: str,
        products: List[Product],
        deal_value: Decimal,
        expected_close_date: datetime,
        champion: Optional[str] = None,
    ) -> Opportunity:
        """Convert lead to qualified opportunity."""
        lead = self._leads.get(lead_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")
        
        opp_id = f"OPP-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc)
        
        opportunity = Opportunity(
            opportunity_id=opp_id,
            lead=lead,
            stage=DealStage.QUALIFIED,
            products=products,
            deal_value=deal_value,
            probability=self.STAGE_PROBABILITY[DealStage.QUALIFIED],
            expected_close_date=expected_close_date,
            created_at=now,
            updated_at=now,
            champion=champion,
        )
        
        self._opportunities[opp_id] = opportunity
        return opportunity
    
    def advance_stage(
        self,
        opportunity_id: str,
        new_stage: DealStage,
        notes: Optional[str] = None,
    ) -> Opportunity:
        """Advance opportunity to next stage."""
        opp = self._opportunities.get(opportunity_id)
        if not opp:
            raise ValueError(f"Opportunity {opportunity_id} not found")
        
        opp.stage = new_stage
        opp.probability = self.STAGE_PROBABILITY[new_stage]
        opp.updated_at = datetime.now(timezone.utc)
        
        if notes:
            opp.next_steps = notes
        
        return opp
    
    def close_won(
        self,
        opportunity_id: str,
        final_value: Optional[Decimal] = None,
    ) -> Opportunity:
        """Close opportunity as won."""
        opp = self._opportunities.get(opportunity_id)
        if not opp:
            raise ValueError(f"Opportunity {opportunity_id} not found")
        
        opp.stage = DealStage.CLOSED_WON
        opp.probability = 100
        opp.updated_at = datetime.now(timezone.utc)
        
        if final_value:
            opp.deal_value = final_value
        
        return opp
    
    def close_lost(
        self,
        opportunity_id: str,
        loss_reason: str,
        competitor: Optional[str] = None,
    ) -> Opportunity:
        """Close opportunity as lost."""
        opp = self._opportunities.get(opportunity_id)
        if not opp:
            raise ValueError(f"Opportunity {opportunity_id} not found")
        
        opp.stage = DealStage.CLOSED_LOST
        opp.probability = 0
        opp.loss_reason = loss_reason
        opp.competitor = competitor
        opp.updated_at = datetime.now(timezone.utc)
        
        return opp
    
    def record_activity(
        self,
        opportunity_id: str,
        activity_type: str,
        description: str,
        outcome: Optional[str] = None,
        next_activity: Optional[str] = None,
    ) -> Activity:
        """Record sales activity."""
        activity_id = f"ACT-{uuid.uuid4().hex[:8].upper()}"
        
        activity = Activity(
            activity_id=activity_id,
            opportunity_id=opportunity_id,
            activity_type=activity_type,
            description=description,
            outcome=outcome,
            timestamp=datetime.now(timezone.utc),
            next_activity=next_activity,
        )
        
        self._activities.append(activity)
        return activity
    
    def create_campaign(
        self,
        name: str,
        channel: LeadSource,
        target_segments: List[Segment],
        budget: Decimal,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ) -> Campaign:
        """Create a marketing campaign."""
        campaign_id = f"CAMP-{uuid.uuid4().hex[:8].upper()}"
        
        campaign = Campaign(
            campaign_id=campaign_id,
            name=name,
            channel=channel,
            target_segments=target_segments,
            budget=budget,
            start_date=start_date,
            end_date=end_date,
        )
        
        self._campaigns[campaign_id] = campaign
        return campaign
    
    def get_pipeline_metrics(self) -> Dict[str, Any]:
        """Get pipeline metrics."""
        open_opps = [
            o for o in self._opportunities.values()
            if o.stage not in (DealStage.CLOSED_WON, DealStage.CLOSED_LOST)
        ]
        won_opps = [
            o for o in self._opportunities.values()
            if o.stage == DealStage.CLOSED_WON
        ]
        lost_opps = [
            o for o in self._opportunities.values()
            if o.stage == DealStage.CLOSED_LOST
        ]
        
        # Pipeline value
        total_pipeline = sum(o.deal_value for o in open_opps)
        weighted_pipeline = sum(o.weighted_value for o in open_opps)
        
        # Won/lost
        total_won = sum(o.deal_value for o in won_opps)
        total_lost = sum(o.deal_value for o in lost_opps)
        
        # Win rate
        closed_count = len(won_opps) + len(lost_opps)
        win_rate = (len(won_opps) / closed_count * 100) if closed_count > 0 else 0
        
        # By stage
        by_stage = {}
        for stage in DealStage:
            stage_opps = [o for o in open_opps if o.stage == stage]
            by_stage[stage.name] = {
                "count": len(stage_opps),
                "value": str(sum(o.deal_value for o in stage_opps)),
            }
        
        # By product
        by_product = {}
        for product in Product:
            product_opps = [o for o in open_opps if product in o.products]
            by_product[product.value] = {
                "count": len(product_opps),
                "value": str(sum(o.deal_value for o in product_opps)),
            }
        
        return {
            "total_leads": len(self._leads),
            "total_opportunities": len(self._opportunities),
            "open_opportunities": len(open_opps),
            "total_pipeline_value": str(total_pipeline),
            "weighted_pipeline_value": str(weighted_pipeline),
            "total_won_value": str(total_won),
            "total_lost_value": str(total_lost),
            "win_rate_percent": str(win_rate),
            "by_stage": by_stage,
            "by_product": by_product,
            "active_campaigns": len(self._campaigns),
        }
    
    def get_forecast(self, months: int = 3) -> Dict[str, Any]:
        """Get revenue forecast based on pipeline."""
        from datetime import timedelta
        
        now = datetime.now(timezone.utc)
        forecast_end = now + timedelta(days=months * 30)
        
        # Opportunities expected to close in forecast period
        forecast_opps = [
            o for o in self._opportunities.values()
            if o.stage not in (DealStage.CLOSED_WON, DealStage.CLOSED_LOST)
            and o.expected_close_date <= forecast_end
        ]
        
        # Weighted forecast
        weighted_forecast = sum(o.weighted_value for o in forecast_opps)
        
        # Best case (all close)
        best_case = sum(o.deal_value for o in forecast_opps)
        
        # Committed (verbal commit or later)
        committed_opps = [
            o for o in forecast_opps 
            if o.stage in (DealStage.VERBAL_COMMIT, DealStage.NEGOTIATION)
        ]
        committed = sum(o.deal_value for o in committed_opps)
        
        return {
            "forecast_period_months": months,
            "forecast_end_date": forecast_end.isoformat(),
            "opportunities_in_period": len(forecast_opps),
            "weighted_forecast": str(weighted_forecast),
            "best_case_forecast": str(best_case),
            "committed_value": str(committed),
        }
    
    def export_pipeline(self) -> Dict[str, Any]:
        """Export complete pipeline data."""
        return {
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "leads": [l.to_dict() for l in self._leads.values()],
            "opportunities": [o.to_dict() for o in self._opportunities.values()],
            "metrics": self.get_pipeline_metrics(),
            "forecast": self.get_forecast(),
            "icp_profiles": [
                p.to_dict() for p in self._icp_catalog.get_all_profiles()
            ],
        }


# =============================================================================
# GTM STRATEGY DOCUMENT
# =============================================================================

GTM_STRATEGY = """
================================================================================
CHAINBRIDGE GO-TO-MARKET STRATEGY
================================================================================

EXECUTIVE SUMMARY
-----------------
ChainBridge operates a dual-product GTM strategy:
1. ChainFreight/ChainPay: Blockchain-powered freight settlement
2. Agent University: AI governance-as-a-service licensing

TARGET MARKETS
--------------

PRIMARY: ChainFreight/ChainPay
- Enterprise Shippers ($1B+ revenue): 180-day sales cycle, $200K-$1M ACV
- Mid-Market Shippers ($100M-$1B): 90-day sales cycle, $50K-$200K ACV
- Third-Party Logistics: 120-day sales cycle, $75K-$300K ACV

SECONDARY: Agent University  
- FinTech (AI-first companies): 60-day sales cycle, $60K-$240K ACV
- AI Platform Companies: 90-day sales cycle, $120K-$500K ACV

GO-TO-MARKET MOTIONS
--------------------

1. PILOT-LED GROWTH (ChainFreight)
   - Free 30-day Explorer pilots for qualification
   - 60-day Growth pilots with 50% discount
   - 90-day Enterprise pilots for strategic accounts
   - Conversion incentives at pilot completion

2. PRODUCT-LED GROWTH (Agent University)
   - 14-day free trial of Professional tier
   - Self-serve activation for Starter tier
   - Sales-assisted for Enterprise and Sovereign

3. PARTNER CHANNEL
   - TMS integration partnerships (Blue Yonder, Oracle TMS, etc.)
   - System integrator partnerships for enterprise deployment
   - Consulting firm alliances for digital transformation projects

SALES PROCESS
-------------

Stage 1: PROSPECT (5%)
- Initial outreach or inbound lead
- Basic firmographic qualification

Stage 2: QUALIFIED (10%)
- BANT criteria validated
- Budget, Authority, Need, Timeline confirmed

Stage 3: DISCOVERY (20%)
- Deep-dive on pain points and requirements
- Stakeholder mapping complete

Stage 4: DEMO (35%)
- Product demonstration delivered
- Technical fit confirmed

Stage 5: PROPOSAL (50%)
- Pricing proposal sent
- ROI analysis shared

Stage 6: NEGOTIATION (70%)
- Contract redlines in progress
- Legal/procurement engaged

Stage 7: VERBAL COMMIT (90%)
- Verbal commitment received
- Final paperwork pending

Stage 8: CLOSED WON (100%)
- Contract signed
- Revenue recognized

METRICS & TARGETS
-----------------

Year 1 Pipeline Targets:
- Total Pipeline Value: $5M
- Weighted Pipeline: $2M
- Closed Won: $500K-$1M

Conversion Targets:
- Lead to Opportunity: 25%
- Opportunity to Close: 20%
- Pilot to Customer: 50%

Activity Targets (per AE):
- 50 calls/week
- 20 meetings/month
- 4 demos/month
- 2 proposals/month

================================================================================
"""


# =============================================================================
# SELF-TEST
# =============================================================================

def self_test() -> bool:
    """Self-test for pipeline module."""
    print("=" * 60)
    print("CUSTOMER ACQUISITION PIPELINE - SELF TEST")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Create manager
    tests_total += 1
    try:
        manager = PipelineManager()
        print("✅ TEST 1: Manager creation - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 1: Manager creation - FAILED: {e}")
        return False
    
    # Test 2: ICP Catalog
    tests_total += 1
    try:
        icp = ICPCatalog.get_profile(Segment.SHIPPER_ENTERPRISE)
        assert icp is not None
        assert icp.min_revenue >= Decimal("1000000000")
        print(f"✅ TEST 2: ICP Catalog ({icp.segment.value}) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 2: ICP Catalog - FAILED: {e}")
    
    # Test 3: Create lead
    tests_total += 1
    try:
        lead = manager.create_lead(
            company_name="Acme Shipping Co",
            segment=Segment.SHIPPER_MID_MARKET,
            source=LeadSource.INBOUND_WEB,
            contact_name="John Doe",
            contact_title="VP Logistics",
            contact_email="jdoe@acme.com",
        )
        assert lead.lead_id.startswith("LEAD-")
        print(f"✅ TEST 3: Lead creation ({lead.lead_id}) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 3: Lead creation - FAILED: {e}")
    
    # Test 4: Qualify lead
    tests_total += 1
    try:
        from datetime import timedelta
        opp = manager.qualify_lead(
            lead_id=lead.lead_id,
            products=[Product.CHAINFREIGHT, Product.CHAINPAY],
            deal_value=Decimal("100000"),
            expected_close_date=datetime.now(timezone.utc) + timedelta(days=90),
            champion="John Doe",
        )
        assert opp.stage == DealStage.QUALIFIED
        assert opp.probability == 10
        print(f"✅ TEST 4: Lead qualification ({opp.opportunity_id}) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 4: Lead qualification - FAILED: {e}")
    
    # Test 5: Advance stages
    tests_total += 1
    try:
        manager.advance_stage(opp.opportunity_id, DealStage.DISCOVERY)
        manager.advance_stage(opp.opportunity_id, DealStage.DEMO)
        manager.advance_stage(opp.opportunity_id, DealStage.PROPOSAL)
        assert opp.stage == DealStage.PROPOSAL
        assert opp.probability == 50
        print(f"✅ TEST 5: Stage advancement ({opp.stage.name}) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 5: Stage advancement - FAILED: {e}")
    
    # Test 6: Record activity
    tests_total += 1
    try:
        activity = manager.record_activity(
            opportunity_id=opp.opportunity_id,
            activity_type="demo",
            description="Platform demo with stakeholders",
            outcome="Positive reception, requested proposal",
            next_activity="Send pricing proposal",
        )
        assert activity.activity_id.startswith("ACT-")
        print(f"✅ TEST 6: Activity recording - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 6: Activity recording - FAILED: {e}")
    
    # Test 7: Create campaign
    tests_total += 1
    try:
        campaign = manager.create_campaign(
            name="Q1 Enterprise Outreach",
            channel=LeadSource.OUTBOUND_EMAIL,
            target_segments=[Segment.SHIPPER_ENTERPRISE],
            budget=Decimal("50000"),
            start_date=datetime.now(timezone.utc),
        )
        assert campaign.campaign_id.startswith("CAMP-")
        print(f"✅ TEST 7: Campaign creation ({campaign.campaign_id}) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 7: Campaign creation - FAILED: {e}")
    
    # Test 8: Pipeline metrics
    tests_total += 1
    try:
        metrics = manager.get_pipeline_metrics()
        assert "total_pipeline_value" in metrics
        assert "weighted_pipeline_value" in metrics
        print(f"✅ TEST 8: Pipeline metrics (pipeline=${metrics['total_pipeline_value']}) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 8: Pipeline metrics - FAILED: {e}")
    
    # Test 9: Forecast
    tests_total += 1
    try:
        forecast = manager.get_forecast(months=3)
        assert "weighted_forecast" in forecast
        print(f"✅ TEST 9: Forecast (weighted=${forecast['weighted_forecast']}) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 9: Forecast - FAILED: {e}")
    
    # Test 10: Export pipeline
    tests_total += 1
    try:
        export = manager.export_pipeline()
        assert "leads" in export
        assert "opportunities" in export
        assert "icp_profiles" in export
        print(f"✅ TEST 10: Pipeline export - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 10: Pipeline export - FAILED: {e}")
    
    # Summary
    print("=" * 60)
    print(f"PIPELINE TESTS: {tests_passed}/{tests_total} PASSED")
    print("=" * 60)
    
    return tests_passed == tests_total


if __name__ == "__main__":
    success = self_test()
    exit(0 if success else 1)
