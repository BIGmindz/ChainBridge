# ═══════════════════════════════════════════════════════════════════════════════
# AML Typology Library — Reference Data & Red Flags
# PAC-BENSON-P28: AML GOVERNED AGENT PROGRAM
# Agent: RESEARCH BENSON (GID-03)
# ═══════════════════════════════════════════════════════════════════════════════

"""
AML Typology Library — Reference Typologies & Indicator Catalog

PURPOSE:
    Provide deterministic reference data for AML analysis including:
    - Known money laundering typologies
    - Red flag indicators by category
    - High-risk jurisdiction lists
    - Sanctions list references

SOURCES:
    - FATF guidance documents
    - FinCEN advisories
    - Wolfsberg principles
    - Regional regulatory guidance

LANE: REFERENCE (READ-ONLY DATA)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set


# ═══════════════════════════════════════════════════════════════════════════════
# TYPOLOGY ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class TypologyCategory(Enum):
    """Category of money laundering typology."""

    # Traditional methods
    TRADE_BASED = "TRADE_BASED"
    CASH_BASED = "CASH_BASED"
    REAL_ESTATE = "REAL_ESTATE"
    SHELL_COMPANIES = "SHELL_COMPANIES"
    CORRESPONDENT_BANKING = "CORRESPONDENT_BANKING"

    # Modern methods
    VIRTUAL_ASSETS = "VIRTUAL_ASSETS"
    DIGITAL_BANKING = "DIGITAL_BANKING"
    CROWDFUNDING = "CROWDFUNDING"
    PAYMENT_PROCESSORS = "PAYMENT_PROCESSORS"

    # Specialized methods
    PROFESSIONAL_SERVICES = "PROFESSIONAL_SERVICES"
    CASINO_GAMING = "CASINO_GAMING"
    PRECIOUS_METALS = "PRECIOUS_METALS"
    ART_AND_ANTIQUITIES = "ART_AND_ANTIQUITIES"

    # Fraud-related
    FRAUD_PROCEEDS = "FRAUD_PROCEEDS"
    TAX_EVASION = "TAX_EVASION"
    SANCTIONS_EVASION = "SANCTIONS_EVASION"


class RedFlagCategory(Enum):
    """Category of red flag indicator."""

    CUSTOMER = "CUSTOMER"
    TRANSACTION = "TRANSACTION"
    GEOGRAPHIC = "GEOGRAPHIC"
    BEHAVIORAL = "BEHAVIORAL"
    DOCUMENTATION = "DOCUMENTATION"
    NETWORK = "NETWORK"


class RiskLevel(Enum):
    """Risk level classification."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    PROHIBITED = "PROHIBITED"


class JurisdictionRiskType(Enum):
    """Type of jurisdiction risk."""

    FATF_BLACKLIST = "FATF_BLACKLIST"  # High-Risk Jurisdictions
    FATF_GREYLIST = "FATF_GREYLIST"  # Increased Monitoring
    SANCTIONS = "SANCTIONS"  # OFAC/EU/UN Sanctions
    TAX_HAVEN = "TAX_HAVEN"
    HIGH_CORRUPTION = "HIGH_CORRUPTION"
    CONFLICT_ZONE = "CONFLICT_ZONE"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class Typology:
    """
    Money laundering typology definition.

    Represents a known method or pattern used to launder funds.
    """

    typology_id: str
    name: str
    category: TypologyCategory
    description: str
    indicators: List[str]
    risk_level: RiskLevel
    source_reference: str
    detection_guidance: str
    examples: List[str] = field(default_factory=list)
    related_typologies: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.typology_id.startswith("TYP-"):
            raise ValueError(f"Typology ID must start with 'TYP-': {self.typology_id}")

    def compute_typology_hash(self) -> str:
        """Compute deterministic hash."""
        data = {
            "typology_id": self.typology_id,
            "name": self.name,
            "category": self.category.value,
            "indicators": sorted(self.indicators),
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "typology_id": self.typology_id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "indicators": self.indicators,
            "risk_level": self.risk_level.value,
            "source_reference": self.source_reference,
            "detection_guidance": self.detection_guidance,
            "examples": self.examples,
            "related_typologies": self.related_typologies,
            "typology_hash": self.compute_typology_hash(),
        }


@dataclass
class RedFlag:
    """
    Red flag indicator definition.

    Represents a specific warning sign that may indicate ML/TF activity.
    """

    flag_id: str
    name: str
    category: RedFlagCategory
    description: str
    risk_weight: float  # 0.0 to 1.0
    applicable_typologies: List[str] = field(default_factory=list)
    detection_rules: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.flag_id.startswith("RF-"):
            raise ValueError(f"Flag ID must start with 'RF-': {self.flag_id}")
        if not 0.0 <= self.risk_weight <= 1.0:
            raise ValueError(f"Risk weight must be between 0.0 and 1.0: {self.risk_weight}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "flag_id": self.flag_id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "risk_weight": self.risk_weight,
            "applicable_typologies": self.applicable_typologies,
            "detection_rules": self.detection_rules,
        }


@dataclass
class JurisdictionRisk:
    """
    Jurisdiction risk classification.

    Represents risk associated with a specific country or territory.
    """

    iso_code: str  # ISO 3166-1 alpha-2
    name: str
    risk_types: List[JurisdictionRiskType]
    risk_level: RiskLevel
    effective_date: str
    notes: str = ""
    sanctions_programs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iso_code": self.iso_code,
            "name": self.name,
            "risk_types": [rt.value for rt in self.risk_types],
            "risk_level": self.risk_level.value,
            "effective_date": self.effective_date,
            "notes": self.notes,
            "sanctions_programs": self.sanctions_programs,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULT TYPOLOGIES
# ═══════════════════════════════════════════════════════════════════════════════


TYP_STRUCTURING = Typology(
    typology_id="TYP-001",
    name="Cash Structuring (Smurfing)",
    category=TypologyCategory.CASH_BASED,
    description="Breaking up large cash transactions into smaller amounts to avoid reporting thresholds",
    indicators=[
        "Multiple deposits just below reporting threshold",
        "Multiple branches same day",
        "Refusing to provide ID for deposits just under threshold",
        "Asking about reporting limits",
    ],
    risk_level=RiskLevel.HIGH,
    source_reference="FATF ML/TF Risk Assessment Guidance",
    detection_guidance="Monitor for transactions between $8,500-$9,999 in patterns",
    examples=[
        "Customer deposits $9,500 at 3 different branches in one day",
        "Multiple $9,000 wire transfers to same beneficiary",
    ],
)

TYP_SHELL_COMPANIES = Typology(
    typology_id="TYP-002",
    name="Shell Company Layering",
    category=TypologyCategory.SHELL_COMPANIES,
    description="Using shell companies to obscure ownership and source of funds",
    indicators=[
        "No apparent business purpose",
        "Complex ownership structures",
        "Nominee directors/shareholders",
        "Inconsistent transaction patterns with stated business",
    ],
    risk_level=RiskLevel.HIGH,
    source_reference="FATF Legal Persons and Arrangements Guidance",
    detection_guidance="Verify beneficial ownership and business purpose",
    examples=[
        "Multiple LLCs receiving/sending large transfers with no inventory",
        "Circular transactions between related entities",
    ],
)

TYP_TRADE_MISINVOICING = Typology(
    typology_id="TYP-003",
    name="Trade-Based ML (Misinvoicing)",
    category=TypologyCategory.TRADE_BASED,
    description="Manipulating trade invoices to move value across borders",
    indicators=[
        "Over/under invoicing goods",
        "Phantom shipments",
        "Multiple invoicing",
        "Misrepresentation of goods",
    ],
    risk_level=RiskLevel.HIGH,
    source_reference="FATF Trade-Based ML Guidance",
    detection_guidance="Compare invoiced values to market rates for goods",
    examples=[
        "Importing goods at 10x market value",
        "Exporting goods with no corresponding customs records",
    ],
)

TYP_VIRTUAL_ASSET_LAYERING = Typology(
    typology_id="TYP-004",
    name="Virtual Asset Layering",
    category=TypologyCategory.VIRTUAL_ASSETS,
    description="Using cryptocurrency and virtual assets to layer illicit funds",
    indicators=[
        "Conversion to privacy coins",
        "Use of mixing/tumbling services",
        "Peel chain transactions",
        "High-risk exchange jurisdictions",
    ],
    risk_level=RiskLevel.HIGH,
    source_reference="FATF Virtual Assets Guidance",
    detection_guidance="Monitor for VASP transfers to high-risk jurisdictions",
    examples=[
        "Converting BTC to XMR across multiple exchanges",
        "Using decentralized exchanges to avoid KYC",
    ],
)

TYP_REAL_ESTATE = Typology(
    typology_id="TYP-005",
    name="Real Estate ML",
    category=TypologyCategory.REAL_ESTATE,
    description="Using real estate transactions to integrate illicit funds",
    indicators=[
        "Cash purchases of high-value property",
        "Quick buy/sell transactions",
        "Use of legal entities to mask ownership",
        "Unexplained funding sources",
    ],
    risk_level=RiskLevel.HIGH,
    source_reference="FATF Real Estate ML Guidance",
    detection_guidance="Verify source of funds for large property purchases",
    examples=[
        "LLC purchases $5M property in cash, sells 6 months later",
        "Multiple properties purchased through different nominee entities",
    ],
)

TYP_CORRESPONDENT_BANKING = Typology(
    typology_id="TYP-006",
    name="Correspondent Banking Abuse",
    category=TypologyCategory.CORRESPONDENT_BANKING,
    description="Misusing correspondent banking relationships to move illicit funds",
    indicators=[
        "Nested accounts from high-risk jurisdictions",
        "Payable-through accounts",
        "Shell bank relationships",
        "Unusual transaction patterns through respondent",
    ],
    risk_level=RiskLevel.HIGH,
    source_reference="Wolfsberg Correspondent Banking Principles",
    detection_guidance="Enhanced due diligence on respondent relationships",
)


# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULT RED FLAGS
# ═══════════════════════════════════════════════════════════════════════════════


RF_STRUCTURING = RedFlag(
    flag_id="RF-001",
    name="Transaction Structuring",
    category=RedFlagCategory.TRANSACTION,
    description="Multiple transactions just below reporting thresholds",
    risk_weight=0.8,
    applicable_typologies=["TYP-001"],
    detection_rules=["RULE-AML-001"],
)

RF_UNUSUAL_VELOCITY = RedFlag(
    flag_id="RF-002",
    name="Unusual Transaction Velocity",
    category=RedFlagCategory.TRANSACTION,
    description="Sudden increase in transaction frequency or volume",
    risk_weight=0.6,
    applicable_typologies=["TYP-001", "TYP-002"],
    detection_rules=["RULE-AML-002"],
)

RF_RAPID_MOVEMENT = RedFlag(
    flag_id="RF-003",
    name="Rapid Fund Movement",
    category=RedFlagCategory.TRANSACTION,
    description="Funds deposited and withdrawn quickly with no business purpose",
    risk_weight=0.7,
    applicable_typologies=["TYP-002", "TYP-006"],
    detection_rules=["RULE-AML-003"],
)

RF_HIGH_RISK_JURISDICTION = RedFlag(
    flag_id="RF-004",
    name="High-Risk Jurisdiction",
    category=RedFlagCategory.GEOGRAPHIC,
    description="Transactions involving FATF high-risk or sanctioned jurisdictions",
    risk_weight=0.9,
    applicable_typologies=["TYP-002", "TYP-003", "TYP-004"],
)

RF_SHELL_COMPANY_INDICATORS = RedFlag(
    flag_id="RF-005",
    name="Shell Company Indicators",
    category=RedFlagCategory.CUSTOMER,
    description="Entity exhibits characteristics of shell company",
    risk_weight=0.8,
    applicable_typologies=["TYP-002"],
)

RF_INCONSISTENT_PROFILE = RedFlag(
    flag_id="RF-006",
    name="Inconsistent Customer Profile",
    category=RedFlagCategory.BEHAVIORAL,
    description="Transaction activity inconsistent with customer profile",
    risk_weight=0.7,
    applicable_typologies=["TYP-001", "TYP-002", "TYP-003"],
)

RF_ADVERSE_MEDIA = RedFlag(
    flag_id="RF-007",
    name="Adverse Media",
    category=RedFlagCategory.CUSTOMER,
    description="Customer appears in adverse media related to financial crime",
    risk_weight=0.9,
)

RF_PEP_ASSOCIATED = RedFlag(
    flag_id="RF-008",
    name="PEP Association",
    category=RedFlagCategory.CUSTOMER,
    description="Customer is or is associated with a Politically Exposed Person",
    risk_weight=0.7,
)

RF_SANCTIONS_PROXIMITY = RedFlag(
    flag_id="RF-009",
    name="Sanctions Proximity",
    category=RedFlagCategory.CUSTOMER,
    description="Customer or counterparty has proximity to sanctioned entities",
    risk_weight=0.95,
)

RF_ROUND_AMOUNTS = RedFlag(
    flag_id="RF-010",
    name="Round Amount Pattern",
    category=RedFlagCategory.TRANSACTION,
    description="High proportion of transactions in round amounts",
    risk_weight=0.4,
    detection_rules=["RULE-AML-005"],
)

RF_UNUSUAL_TIMING = RedFlag(
    flag_id="RF-011",
    name="Unusual Transaction Timing",
    category=RedFlagCategory.TRANSACTION,
    description="Transactions at unusual times (nights/weekends)",
    risk_weight=0.3,
    detection_rules=["RULE-AML-008"],
)

RF_CIRCULAR_FLOW = RedFlag(
    flag_id="RF-012",
    name="Circular Fund Flow",
    category=RedFlagCategory.NETWORK,
    description="Funds returning to origin through intermediaries",
    risk_weight=0.85,
    applicable_typologies=["TYP-002"],
    detection_rules=["RULE-AML-007"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# JURISDICTION RISK DATA
# ═══════════════════════════════════════════════════════════════════════════════


# FATF High-Risk Jurisdictions (Blacklist) - as of common reference
FATF_BLACKLIST = [
    JurisdictionRisk(
        iso_code="KP",
        name="Democratic People's Republic of Korea",
        risk_types=[JurisdictionRiskType.FATF_BLACKLIST, JurisdictionRiskType.SANCTIONS],
        risk_level=RiskLevel.PROHIBITED,
        effective_date="2011-02-25",
        sanctions_programs=["OFAC", "EU", "UN"],
    ),
    JurisdictionRisk(
        iso_code="IR",
        name="Iran",
        risk_types=[JurisdictionRiskType.FATF_BLACKLIST, JurisdictionRiskType.SANCTIONS],
        risk_level=RiskLevel.PROHIBITED,
        effective_date="2009-02-25",
        sanctions_programs=["OFAC", "EU", "UN"],
    ),
    JurisdictionRisk(
        iso_code="MM",
        name="Myanmar",
        risk_types=[JurisdictionRiskType.FATF_BLACKLIST],
        risk_level=RiskLevel.PROHIBITED,
        effective_date="2022-10-21",
    ),
]

# FATF Greylist (Increased Monitoring) - representative sample
FATF_GREYLIST = [
    JurisdictionRisk(
        iso_code="SY",
        name="Syria",
        risk_types=[JurisdictionRiskType.FATF_GREYLIST, JurisdictionRiskType.SANCTIONS, JurisdictionRiskType.CONFLICT_ZONE],
        risk_level=RiskLevel.HIGH,
        effective_date="2010-02-01",
        sanctions_programs=["OFAC", "EU"],
    ),
    JurisdictionRisk(
        iso_code="YE",
        name="Yemen",
        risk_types=[JurisdictionRiskType.FATF_GREYLIST, JurisdictionRiskType.CONFLICT_ZONE],
        risk_level=RiskLevel.HIGH,
        effective_date="2010-02-01",
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# TYPOLOGY LIBRARY SERVICE
# ═══════════════════════════════════════════════════════════════════════════════


class TypologyLibrary:
    """
    Reference library for AML typologies and indicators.

    Provides:
    - Typology catalog lookup
    - Red flag reference
    - Jurisdiction risk data
    - Pattern matching guidance
    """

    def __init__(self) -> None:
        self._typologies: Dict[str, Typology] = {}
        self._red_flags: Dict[str, RedFlag] = {}
        self._jurisdiction_risks: Dict[str, JurisdictionRisk] = {}

        # Load defaults
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default reference data."""
        # Typologies
        for typology in [
            TYP_STRUCTURING,
            TYP_SHELL_COMPANIES,
            TYP_TRADE_MISINVOICING,
            TYP_VIRTUAL_ASSET_LAYERING,
            TYP_REAL_ESTATE,
            TYP_CORRESPONDENT_BANKING,
        ]:
            self._typologies[typology.typology_id] = typology

        # Red flags
        for flag in [
            RF_STRUCTURING,
            RF_UNUSUAL_VELOCITY,
            RF_RAPID_MOVEMENT,
            RF_HIGH_RISK_JURISDICTION,
            RF_SHELL_COMPANY_INDICATORS,
            RF_INCONSISTENT_PROFILE,
            RF_ADVERSE_MEDIA,
            RF_PEP_ASSOCIATED,
            RF_SANCTIONS_PROXIMITY,
            RF_ROUND_AMOUNTS,
            RF_UNUSUAL_TIMING,
            RF_CIRCULAR_FLOW,
        ]:
            self._red_flags[flag.flag_id] = flag

        # Jurisdiction risks
        for jurisdiction in FATF_BLACKLIST + FATF_GREYLIST:
            self._jurisdiction_risks[jurisdiction.iso_code] = jurisdiction

    # ───────────────────────────────────────────────────────────────────────────
    # TYPOLOGY QUERIES
    # ───────────────────────────────────────────────────────────────────────────

    def get_typology(self, typology_id: str) -> Optional[Typology]:
        """Get typology by ID."""
        return self._typologies.get(typology_id)

    def list_typologies(self) -> List[Typology]:
        """List all typologies."""
        return list(self._typologies.values())

    def get_typologies_by_category(self, category: TypologyCategory) -> List[Typology]:
        """Get typologies by category."""
        return [t for t in self._typologies.values() if t.category == category]

    def search_typologies(self, keyword: str) -> List[Typology]:
        """Search typologies by keyword."""
        keyword_lower = keyword.lower()
        return [
            t for t in self._typologies.values()
            if keyword_lower in t.name.lower() or keyword_lower in t.description.lower()
        ]

    # ───────────────────────────────────────────────────────────────────────────
    # RED FLAG QUERIES
    # ───────────────────────────────────────────────────────────────────────────

    def get_red_flag(self, flag_id: str) -> Optional[RedFlag]:
        """Get red flag by ID."""
        return self._red_flags.get(flag_id)

    def list_red_flags(self) -> List[RedFlag]:
        """List all red flags."""
        return list(self._red_flags.values())

    def get_red_flags_by_category(self, category: RedFlagCategory) -> List[RedFlag]:
        """Get red flags by category."""
        return [f for f in self._red_flags.values() if f.category == category]

    def get_red_flags_for_typology(self, typology_id: str) -> List[RedFlag]:
        """Get red flags applicable to a typology."""
        return [
            f for f in self._red_flags.values()
            if typology_id in f.applicable_typologies
        ]

    def get_high_weight_flags(self, threshold: float = 0.7) -> List[RedFlag]:
        """Get red flags above a risk weight threshold."""
        return [f for f in self._red_flags.values() if f.risk_weight >= threshold]

    # ───────────────────────────────────────────────────────────────────────────
    # JURISDICTION QUERIES
    # ───────────────────────────────────────────────────────────────────────────

    def get_jurisdiction_risk(self, iso_code: str) -> Optional[JurisdictionRisk]:
        """Get jurisdiction risk by ISO code."""
        return self._jurisdiction_risks.get(iso_code.upper())

    def list_jurisdiction_risks(self) -> List[JurisdictionRisk]:
        """List all jurisdiction risks."""
        return list(self._jurisdiction_risks.values())

    def get_prohibited_jurisdictions(self) -> List[JurisdictionRisk]:
        """Get prohibited jurisdictions."""
        return [j for j in self._jurisdiction_risks.values() if j.risk_level == RiskLevel.PROHIBITED]

    def get_high_risk_jurisdictions(self) -> List[JurisdictionRisk]:
        """Get high-risk jurisdictions."""
        return [j for j in self._jurisdiction_risks.values() if j.risk_level in (RiskLevel.HIGH, RiskLevel.PROHIBITED)]

    def get_sanctioned_jurisdictions(self) -> List[JurisdictionRisk]:
        """Get sanctioned jurisdictions."""
        return [
            j for j in self._jurisdiction_risks.values()
            if JurisdictionRiskType.SANCTIONS in j.risk_types
        ]

    def check_jurisdiction(self, iso_code: str) -> Dict[str, Any]:
        """Check risk status of a jurisdiction."""
        risk = self.get_jurisdiction_risk(iso_code.upper())
        if risk is None:
            return {
                "iso_code": iso_code.upper(),
                "found": False,
                "risk_level": "UNKNOWN",
                "is_prohibited": False,
                "is_high_risk": False,
                "is_sanctioned": False,
            }
        return {
            "iso_code": risk.iso_code,
            "found": True,
            "name": risk.name,
            "risk_level": risk.risk_level.value,
            "is_prohibited": risk.risk_level == RiskLevel.PROHIBITED,
            "is_high_risk": risk.risk_level in (RiskLevel.HIGH, RiskLevel.PROHIBITED),
            "is_sanctioned": JurisdictionRiskType.SANCTIONS in risk.risk_types,
            "risk_types": [rt.value for rt in risk.risk_types],
            "sanctions_programs": risk.sanctions_programs,
        }

    # ───────────────────────────────────────────────────────────────────────────
    # RISK ASSESSMENT
    # ───────────────────────────────────────────────────────────────────────────

    def compute_indicator_risk_score(self, flag_ids: List[str]) -> float:
        """
        Compute aggregate risk score from multiple indicators.

        Uses weighted combination of red flag risk weights.
        """
        if not flag_ids:
            return 0.0

        weights: List[float] = []
        for flag_id in flag_ids:
            flag = self.get_red_flag(flag_id)
            if flag:
                weights.append(flag.risk_weight)

        if not weights:
            return 0.0

        # Combine using 1 - product of (1-weight) formula
        # This gives higher weight to multiple indicators
        complement_product = 1.0
        for w in weights:
            complement_product *= (1.0 - w)

        return 1.0 - complement_product

    def match_typology_indicators(
        self,
        observed_flags: Set[str],
    ) -> List[Tuple[Typology, float]]:
        """
        Match observed red flags to typologies.

        Returns list of (typology, match_score) sorted by score.
        """
        matches: List[Tuple[Typology, float]] = []

        for typology in self._typologies.values():
            applicable_flags = self.get_red_flags_for_typology(typology.typology_id)
            applicable_flag_ids = {f.flag_id for f in applicable_flags}

            if not applicable_flag_ids:
                continue

            matched = observed_flags & applicable_flag_ids
            if matched:
                score = len(matched) / len(applicable_flag_ids)
                matches.append((typology, score))

        return sorted(matches, key=lambda x: x[1], reverse=True)

    # ───────────────────────────────────────────────────────────────────────────
    # REPORTING
    # ───────────────────────────────────────────────────────────────────────────

    def generate_report(self) -> Dict[str, Any]:
        """Generate library status report."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_typologies": len(self._typologies),
            "total_red_flags": len(self._red_flags),
            "total_jurisdiction_risks": len(self._jurisdiction_risks),
            "prohibited_jurisdictions": len(self.get_prohibited_jurisdictions()),
            "high_risk_jurisdictions": len(self.get_high_risk_jurisdictions()),
            "typologies_by_category": {
                cat.value: len(self.get_typologies_by_category(cat))
                for cat in TypologyCategory
            },
            "red_flags_by_category": {
                cat.value: len(self.get_red_flags_by_category(cat))
                for cat in RedFlagCategory
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "TypologyCategory",
    "RedFlagCategory",
    "RiskLevel",
    "JurisdictionRiskType",
    # Data Classes
    "Typology",
    "RedFlag",
    "JurisdictionRisk",
    # Service
    "TypologyLibrary",
    # Default Typologies
    "TYP_STRUCTURING",
    "TYP_SHELL_COMPANIES",
    "TYP_TRADE_MISINVOICING",
    "TYP_VIRTUAL_ASSET_LAYERING",
    "TYP_REAL_ESTATE",
    "TYP_CORRESPONDENT_BANKING",
    # Default Red Flags
    "RF_STRUCTURING",
    "RF_UNUSUAL_VELOCITY",
    "RF_RAPID_MOVEMENT",
    "RF_HIGH_RISK_JURISDICTION",
    "RF_SHELL_COMPANY_INDICATORS",
    "RF_INCONSISTENT_PROFILE",
    "RF_ADVERSE_MEDIA",
    "RF_PEP_ASSOCIATED",
    "RF_SANCTIONS_PROXIMITY",
    "RF_ROUND_AMOUNTS",
    "RF_UNUSUAL_TIMING",
    "RF_CIRCULAR_FLOW",
    # Jurisdiction Data
    "FATF_BLACKLIST",
    "FATF_GREYLIST",
]
