# ═══════════════════════════════════════════════════════════════════════════════
# AML Shadow Typology Extensions — FATF/FinCEN Extended Mappings
# PAC-BENSON-P29: AML SHADOW PILOT EXECUTION
# Agent: RESEARCH BENSON (GID-03)
# ═══════════════════════════════════════════════════════════════════════════════

"""
AML Shadow Typology Extensions — Extended FATF/FinCEN Reference Data

PURPOSE:
    Extend core typology library with additional mappings for shadow pilot:
    - FinCEN Advisory typologies
    - FATF emerging risks
    - Sector-specific indicators
    - Shadow pilot scenario mappings

SOURCES:
    - FinCEN Advisories (FIN-2019-A001 through FIN-2024)
    - FATF 40 Recommendations
    - FATF Mutual Evaluation Reports
    - Regional guidance (EU AMLD6, etc.)

LANE: REFERENCE (READ-ONLY DATA)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from core.aml.typology_library import (
    JurisdictionRisk,
    JurisdictionRiskType,
    RedFlag,
    RedFlagCategory,
    RiskLevel,
    Typology,
    TypologyCategory,
)


# ═══════════════════════════════════════════════════════════════════════════════
# EXTENDED ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class FinCENAdvisory(Enum):
    """FinCEN Advisory references."""

    HUMAN_TRAFFICKING = "FIN-2020-A008"  # Human Trafficking
    ELDER_FRAUD = "FIN-2022-A001"  # Elder Financial Exploitation
    RANSOMWARE = "FIN-2021-A004"  # Ransomware Payments
    FENTANYL = "FIN-2019-A006"  # Fentanyl Trafficking
    CORRUPTION = "FIN-2018-A003"  # Foreign Corruption
    KLEPTOCRACY = "FIN-2022-RUSSIA"  # Russian Kleptocracy
    WILDLIFE = "FIN-2021-A002"  # Wildlife Trafficking
    HEZBOLLAH = "FIN-2020-A001"  # Hezbollah Financing


class FATFHighRisk(Enum):
    """FATF High-Risk and Other Monitored Jurisdictions (as of Feb 2024)."""

    # Call for Action (Black List)
    DPRK = "KP"  # North Korea
    IRAN = "IR"  # Iran
    MYANMAR = "MM"  # Myanmar

    # Increased Monitoring (Grey List)
    BULGARIA = "BG"
    BURKINA_FASO = "BF"
    CAMEROON = "CM"
    CROATIA = "HR"
    DEMOCRATIC_REPUBLIC_CONGO = "CD"
    HAITI = "HT"
    KENYA = "KE"
    MALI = "ML"
    MONACO = "MC"
    MOZAMBIQUE = "MZ"
    NAMIBIA = "NA"
    NIGERIA = "NG"
    PHILIPPINES = "PH"
    SENEGAL = "SN"
    SOUTH_AFRICA = "ZA"
    SOUTH_SUDAN = "SS"
    SYRIA = "SY"
    TANZANIA = "TZ"
    VIETNAM = "VN"
    YEMEN = "YE"


class SectorRisk(Enum):
    """Sector-specific risk classifications."""

    MSBS = "MONEY_SERVICE_BUSINESSES"
    CASINOS = "CASINOS_GAMING"
    PRECIOUS_METALS = "PRECIOUS_METALS_DEALERS"
    REAL_ESTATE = "REAL_ESTATE_AGENTS"
    LEGAL = "LAWYERS_ACCOUNTANTS"
    VIRTUAL_ASSETS = "VIRTUAL_ASSET_PROVIDERS"
    PRIVATE_BANKING = "PRIVATE_BANKING"
    CORRESPONDENT = "CORRESPONDENT_BANKING"
    TRADE_FINANCE = "TRADE_FINANCE"
    HIGH_VALUE_GOODS = "HIGH_VALUE_GOODS"


# ═══════════════════════════════════════════════════════════════════════════════
# EXTENDED DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class FinCENTypology:
    """
    FinCEN Advisory-based typology.

    Represents ML/TF typologies from FinCEN advisories.
    """

    advisory_id: str
    name: str
    predicate_offense: str
    description: str
    indicators: List[str]
    sar_filing_triggers: List[str]
    risk_level: RiskLevel
    effective_date: str
    related_fatf_recs: List[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.advisory_id.startswith("FIN-"):
            raise ValueError(f"Advisory ID must start with 'FIN-': {self.advisory_id}")

    def compute_hash(self) -> str:
        """Compute deterministic hash."""
        data = {
            "advisory_id": self.advisory_id,
            "name": self.name,
            "indicators": sorted(self.indicators),
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "advisory_id": self.advisory_id,
            "name": self.name,
            "predicate_offense": self.predicate_offense,
            "description": self.description,
            "indicators": self.indicators,
            "sar_filing_triggers": self.sar_filing_triggers,
            "risk_level": self.risk_level.value,
            "effective_date": self.effective_date,
            "related_fatf_recs": self.related_fatf_recs,
            "hash": self.compute_hash(),
        }


@dataclass
class SectorIndicator:
    """
    Sector-specific indicator.

    Represents red flags specific to a business sector.
    """

    indicator_id: str
    sector: SectorRisk
    name: str
    description: str
    risk_weight: float
    detection_guidance: str
    applicable_typologies: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.indicator_id.startswith("SECT-"):
            raise ValueError(f"Indicator ID must start with 'SECT-': {self.indicator_id}")
        if not 0.0 <= self.risk_weight <= 1.0:
            raise ValueError(f"Risk weight must be between 0.0 and 1.0: {self.risk_weight}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "indicator_id": self.indicator_id,
            "sector": self.sector.value,
            "name": self.name,
            "description": self.description,
            "risk_weight": self.risk_weight,
            "detection_guidance": self.detection_guidance,
            "applicable_typologies": self.applicable_typologies,
        }


@dataclass
class FATFRecommendation:
    """
    FATF Recommendation reference.

    Represents a FATF 40 Recommendation mapping.
    """

    rec_number: int
    title: str
    category: str
    description: str
    compliance_requirements: List[str]
    deficiency_indicators: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rec_number": self.rec_number,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "compliance_requirements": self.compliance_requirements,
            "deficiency_indicators": self.deficiency_indicators,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# FINCEN TYPOLOGIES
# ═══════════════════════════════════════════════════════════════════════════════


FINCEN_HUMAN_TRAFFICKING = FinCENTypology(
    advisory_id="FIN-2020-A008",
    name="Human Trafficking Financial Indicators",
    predicate_offense="Human Trafficking (18 U.S.C. § 1591)",
    description="Financial indicators associated with human trafficking and forced labor",
    indicators=[
        "Third-party payments for living expenses of multiple individuals",
        "Large cash withdrawals followed by deposits to foreign accounts",
        "Multiple individuals with same address receiving government benefits",
        "Hotel payments for multiple rooms simultaneously",
        "Frequent international wire transfers to high-risk countries",
        "Payments to known front businesses (massage, labor contractors)",
    ],
    sar_filing_triggers=[
        "Suspected trafficking victim as account holder",
        "Transactions involving known trafficking networks",
        "Pattern matching known trafficking financial flows",
    ],
    risk_level=RiskLevel.HIGH,
    effective_date="2020-10-15",
    related_fatf_recs=[10, 11, 20],
)

FINCEN_ELDER_FRAUD = FinCENTypology(
    advisory_id="FIN-2022-A001",
    name="Elder Financial Exploitation",
    predicate_offense="Elder Abuse (Various state laws)",
    description="Financial indicators of elder financial exploitation",
    indicators=[
        "Sudden change in banking patterns for elderly customer",
        "New authorized signers added to accounts",
        "Large withdrawals inconsistent with prior activity",
        "Wire transfers to unknown recipients",
        "Power of attorney recently granted with immediate transactions",
        "Account changes coinciding with caregiver changes",
    ],
    sar_filing_triggers=[
        "Suspected financial exploitation of elderly customer",
        "Uncharacteristic large transfers",
        "Third-party controlling finances",
    ],
    risk_level=RiskLevel.MEDIUM,
    effective_date="2022-06-15",
    related_fatf_recs=[10, 20],
)

FINCEN_RANSOMWARE = FinCENTypology(
    advisory_id="FIN-2021-A004",
    name="Ransomware and Virtual Currency",
    predicate_offense="Computer Fraud (18 U.S.C. § 1030)",
    description="Financial indicators related to ransomware payments",
    indicators=[
        "Urgent virtual currency purchases without prior history",
        "Transfers to known ransomware-associated wallets",
        "CVC transfers followed by immediate conversion",
        "Use of mixing/tumbling services after payment",
        "Payments to sanctioned virtual currency addresses",
    ],
    sar_filing_triggers=[
        "Known ransomware wallet addresses",
        "Customer reports ransomware incident",
        "Urgency in obtaining virtual currency",
    ],
    risk_level=RiskLevel.HIGH,
    effective_date="2021-11-08",
    related_fatf_recs=[15, 16],
)

FINCEN_CORRUPTION = FinCENTypology(
    advisory_id="FIN-2018-A003",
    name="Foreign Corruption",
    predicate_offense="Foreign Corrupt Practices Act (15 U.S.C. § 78dd-1)",
    description="Financial indicators of foreign public corruption",
    indicators=[
        "PEP receiving funds from corporate entities without clear purpose",
        "Transfers to shell companies in offshore jurisdictions",
        "Real estate purchases through layers of entities",
        "Third-party payments for luxury goods",
        "Consulting fees to PEP-related entities",
        "Complex ownership structures obscuring beneficial ownership",
    ],
    sar_filing_triggers=[
        "Transactions involving foreign PEPs",
        "Payments without clear business purpose to government officials",
        "Layered transactions through high-risk jurisdictions",
    ],
    risk_level=RiskLevel.HIGH,
    effective_date="2018-04-02",
    related_fatf_recs=[12, 22, 24],
)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTOR INDICATORS
# ═══════════════════════════════════════════════════════════════════════════════


SECT_MSB_STRUCTURING = SectorIndicator(
    indicator_id="SECT-MSB-001",
    sector=SectorRisk.MSBS,
    name="MSB Structuring Pattern",
    description="Structuring through money service businesses",
    risk_weight=0.85,
    detection_guidance="Monitor for multiple transactions at different MSB locations",
    applicable_typologies=["TYP-001"],
)

SECT_CASINO_CHIP_CASHING = SectorIndicator(
    indicator_id="SECT-CAS-001",
    sector=SectorRisk.CASINOS,
    name="Minimal Play Chip Cashing",
    description="Converting cash to chips with minimal gaming activity",
    risk_weight=0.80,
    detection_guidance="Monitor chip-to-cash ratio vs gaming activity",
    applicable_typologies=["TYP-001"],
)

SECT_RE_CASH_PURCHASE = SectorIndicator(
    indicator_id="SECT-RE-001",
    sector=SectorRisk.REAL_ESTATE,
    name="All-Cash Real Estate Purchase",
    description="High-value property purchased entirely with cash",
    risk_weight=0.75,
    detection_guidance="Verify source of funds for cash purchases over $300K",
    applicable_typologies=["TYP-005"],
)

SECT_VASP_MIXING = SectorIndicator(
    indicator_id="SECT-VASP-001",
    sector=SectorRisk.VIRTUAL_ASSETS,
    name="Virtual Asset Mixing Services",
    description="Use of mixing/tumbling services",
    risk_weight=0.90,
    detection_guidance="Monitor for transfers to known mixing service addresses",
    applicable_typologies=["TYP-004"],
)

SECT_LEGAL_TRUST = SectorIndicator(
    indicator_id="SECT-LEG-001",
    sector=SectorRisk.LEGAL,
    name="IOLTA Account Misuse",
    description="Misuse of attorney trust accounts",
    risk_weight=0.80,
    detection_guidance="Monitor IOLTA accounts for pass-through activity",
    applicable_typologies=["TYP-002"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# FATF RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════════════════════════


FATF_REC_10 = FATFRecommendation(
    rec_number=10,
    title="Customer Due Diligence",
    category="Preventive Measures",
    description="Financial institutions should conduct CDD when establishing business relationships",
    compliance_requirements=[
        "Identify customer and verify identity",
        "Identify beneficial owner",
        "Understand purpose and nature of business relationship",
        "Ongoing due diligence",
    ],
    deficiency_indicators=[
        "No beneficial ownership information",
        "Outdated customer information",
        "No risk rating",
    ],
)

FATF_REC_15 = FATFRecommendation(
    rec_number=15,
    title="New Technologies",
    category="Preventive Measures",
    description="Countries should identify and assess ML/TF risks from new technologies including virtual assets",
    compliance_requirements=[
        "Risk assessment for new technologies",
        "VASP licensing/registration",
        "VASP supervision",
        "Travel rule compliance",
    ],
    deficiency_indicators=[
        "No virtual asset regulation",
        "Unlicensed VASPs operating",
        "No travel rule implementation",
    ],
)

FATF_REC_20 = FATFRecommendation(
    rec_number=20,
    title="Suspicious Transaction Reporting",
    category="Preventive Measures",
    description="Financial institutions should report suspicious transactions",
    compliance_requirements=[
        "Report suspicious transactions to FIU",
        "Report regardless of amount",
        "Report attempted transactions",
        "Tipping-off prohibition",
    ],
    deficiency_indicators=[
        "Low SAR filing rates",
        "Delayed reporting",
        "Poor quality SARs",
    ],
)


# ═══════════════════════════════════════════════════════════════════════════════
# EXTENDED JURISDICTION RISKS
# ═══════════════════════════════════════════════════════════════════════════════


JURISDICTION_DPRK = JurisdictionRisk(
    iso_code="KP",
    name="North Korea (DPRK)",
    risk_types=[JurisdictionRiskType.FATF_BLACKLIST, JurisdictionRiskType.SANCTIONS],
    risk_level=RiskLevel.PROHIBITED,
    effective_date="2011-02-25",
    notes="FATF Call for Action - apply countermeasures",
    sanctions_programs=["OFAC DPRK", "UN SC 1718"],
)

JURISDICTION_IRAN = JurisdictionRisk(
    iso_code="IR",
    name="Iran",
    risk_types=[JurisdictionRiskType.FATF_BLACKLIST, JurisdictionRiskType.SANCTIONS],
    risk_level=RiskLevel.PROHIBITED,
    effective_date="2008-10-11",
    notes="FATF Call for Action - apply countermeasures",
    sanctions_programs=["OFAC Iran", "UN SC 1737"],
)

JURISDICTION_MYANMAR = JurisdictionRisk(
    iso_code="MM",
    name="Myanmar",
    risk_types=[JurisdictionRiskType.FATF_BLACKLIST, JurisdictionRiskType.SANCTIONS],
    risk_level=RiskLevel.PROHIBITED,
    effective_date="2022-10-21",
    notes="FATF Call for Action - apply countermeasures",
    sanctions_programs=["OFAC Burma"],
)

JURISDICTION_RUSSIA = JurisdictionRisk(
    iso_code="RU",
    name="Russia",
    risk_types=[JurisdictionRiskType.SANCTIONS],
    risk_level=RiskLevel.PROHIBITED,
    effective_date="2022-02-24",
    notes="Comprehensive sanctions following Ukraine invasion",
    sanctions_programs=["OFAC Russia", "EU Russia", "UK Russia"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# TYPOLOGY LIBRARY EXTENSION
# ═══════════════════════════════════════════════════════════════════════════════


class ExtendedTypologyLibrary:
    """
    Extended typology library with FinCEN/FATF mappings.

    Provides comprehensive typology and indicator lookups
    for shadow pilot testing.
    """

    def __init__(self) -> None:
        """Initialize extended library."""
        self._fincen_typologies: Dict[str, FinCENTypology] = {}
        self._sector_indicators: Dict[str, SectorIndicator] = {}
        self._fatf_recs: Dict[int, FATFRecommendation] = {}
        self._jurisdiction_risks: Dict[str, JurisdictionRisk] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default typologies and indicators."""
        # FinCEN typologies
        for typ in [
            FINCEN_HUMAN_TRAFFICKING,
            FINCEN_ELDER_FRAUD,
            FINCEN_RANSOMWARE,
            FINCEN_CORRUPTION,
        ]:
            self._fincen_typologies[typ.advisory_id] = typ

        # Sector indicators
        for ind in [
            SECT_MSB_STRUCTURING,
            SECT_CASINO_CHIP_CASHING,
            SECT_RE_CASH_PURCHASE,
            SECT_VASP_MIXING,
            SECT_LEGAL_TRUST,
        ]:
            self._sector_indicators[ind.indicator_id] = ind

        # FATF recommendations
        for rec in [FATF_REC_10, FATF_REC_15, FATF_REC_20]:
            self._fatf_recs[rec.rec_number] = rec

        # Jurisdiction risks
        for jur in [
            JURISDICTION_DPRK,
            JURISDICTION_IRAN,
            JURISDICTION_MYANMAR,
            JURISDICTION_RUSSIA,
        ]:
            self._jurisdiction_risks[jur.iso_code] = jur

    def get_fincen_typology(self, advisory_id: str) -> Optional[FinCENTypology]:
        """Get FinCEN typology by advisory ID."""
        return self._fincen_typologies.get(advisory_id)

    def get_sector_indicator(self, indicator_id: str) -> Optional[SectorIndicator]:
        """Get sector indicator by ID."""
        return self._sector_indicators.get(indicator_id)

    def get_fatf_recommendation(self, rec_number: int) -> Optional[FATFRecommendation]:
        """Get FATF recommendation by number."""
        return self._fatf_recs.get(rec_number)

    def get_jurisdiction_risk(self, iso_code: str) -> Optional[JurisdictionRisk]:
        """Get jurisdiction risk by ISO code."""
        return self._jurisdiction_risks.get(iso_code.upper())

    def is_prohibited_jurisdiction(self, iso_code: str) -> bool:
        """Check if jurisdiction is prohibited."""
        jur = self._jurisdiction_risks.get(iso_code.upper())
        return jur is not None and jur.risk_level == RiskLevel.PROHIBITED

    def get_indicators_by_sector(self, sector: SectorRisk) -> List[SectorIndicator]:
        """Get all indicators for a sector."""
        return [ind for ind in self._sector_indicators.values() if ind.sector == sector]

    def get_all_fincen_typologies(self) -> List[FinCENTypology]:
        """Get all FinCEN typologies."""
        return list(self._fincen_typologies.values())

    def get_all_prohibited_jurisdictions(self) -> List[JurisdictionRisk]:
        """Get all prohibited jurisdictions."""
        return [j for j in self._jurisdiction_risks.values() if j.risk_level == RiskLevel.PROHIBITED]

    def search_typologies_by_indicator(self, indicator_text: str) -> List[FinCENTypology]:
        """Search typologies containing indicator text."""
        indicator_lower = indicator_text.lower()
        return [
            typ
            for typ in self._fincen_typologies.values()
            if any(indicator_lower in ind.lower() for ind in typ.indicators)
        ]

    def get_library_stats(self) -> Dict[str, int]:
        """Get library statistics."""
        return {
            "fincen_typologies": len(self._fincen_typologies),
            "sector_indicators": len(self._sector_indicators),
            "fatf_recommendations": len(self._fatf_recs),
            "jurisdiction_risks": len(self._jurisdiction_risks),
            "prohibited_jurisdictions": len(self.get_all_prohibited_jurisdictions()),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Export library to dictionary."""
        return {
            "fincen_typologies": [t.to_dict() for t in self._fincen_typologies.values()],
            "sector_indicators": [i.to_dict() for i in self._sector_indicators.values()],
            "fatf_recommendations": [r.to_dict() for r in self._fatf_recs.values()],
            "jurisdiction_risks": [j.to_dict() for j in self._jurisdiction_risks.values()],
            "stats": self.get_library_stats(),
        }
