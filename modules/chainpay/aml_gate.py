#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           CHAINBRIDGE AML GATE MODULE (P65)                                  ║
║                   FINANCIAL SOVEREIGNTY PILLAR                               ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  TYPE: FINANCIAL_COMPLIANCE                                                  ║
║  GOVERNANCE_TIER: REGULATORY                                                 ║
║  MODE: TRANSACTION_SCREENING                                                 ║
║  LANE: MONEY_LANE                                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

AML GATE ARCHITECTURE:
  Watchlist Check:    Screen against OFAC/SDN sanctions lists
  Transaction Limits: Enforce daily/monthly thresholds
  Velocity Analysis:  Detect suspicious transaction patterns
  Risk Scoring:       Assign composite risk score

DECISION MATRIX:
  ┌─────────────┬─────────────┬────────────┐
  │ WATCHLIST   │ LIMITS      │ DECISION   │
  ├─────────────┼─────────────┼────────────┤
  │ ❌ HIT      │ (any)       │ REJECT     │
  │ ✅ CLEAR    │ ❌ EXCEEDED │ REJECT     │
  │ ✅ CLEAR    │ ✅ OK       │ APPROVE    │
  └─────────────┴─────────────┴────────────┘

INVARIANT:
  CLEAN_MONEY: No sanctioned entity may transact on the network.
"""

import json
import logging
from enum import Enum
from typing import Dict, Any, Tuple, List
from datetime import datetime, timezone
from decimal import Decimal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [AML_GATE] - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AMLGate")


class AMLDecision(Enum):
    """AML Gate Decision States"""
    APPROVE = "APPROVE"   # Transaction cleared
    REJECT = "REJECT"     # Transaction blocked
    REVIEW = "REVIEW"     # Manual review required


class WatchlistChecker:
    """
    Sanctions and Watchlist Screening
    Managed by: Atlas (GID-11)
    """
    
    def __init__(self):
        self.agent_id = "GID-11"
        self.agent_name = "Atlas"
        # Simulated sanctions list (in production: OFAC/SDN API)
        self.sanctioned_entities = {
            "SANCTIONED-ENTITY-001",
            "BLOCKED-CORP-999",
            "TERROR-ORG-666",
            "NARCO-CARTEL-X",
        }
        self.sanctioned_countries = {"NK", "IR", "SY", "CU"}  # ISO codes
        
    def screen(self, entity_id: str, country_code: str) -> Tuple[bool, str]:
        """
        Screen entity against watchlists.
        
        Returns:
            Tuple[bool, str]: (is_clear, reason)
        """
        logger.info(f"[ATLAS] Screening entity {entity_id} from {country_code}")
        
        # Check entity sanctions
        if entity_id.upper() in self.sanctioned_entities:
            logger.warning(f"[ATLAS] ❌ SANCTIONED ENTITY: {entity_id}")
            return False, f"SANCTIONED_ENTITY: {entity_id}"
        
        # Check country sanctions
        if country_code.upper() in self.sanctioned_countries:
            logger.warning(f"[ATLAS] ❌ SANCTIONED COUNTRY: {country_code}")
            return False, f"SANCTIONED_COUNTRY: {country_code}"
        
        logger.info(f"[ATLAS] ✅ Entity {entity_id} CLEARED")
        return True, "WATCHLIST_CLEAR"


class TransactionLimiter:
    """
    Transaction Threshold Enforcement
    Managed by: Eve (GID-01)
    """
    
    def __init__(self):
        self.agent_id = "GID-01"
        self.agent_name = "Eve"
        self.single_tx_limit = Decimal("1000000.00")      # $1M single transaction
        self.daily_limit = Decimal("5000000.00")          # $5M daily
        self.reporting_threshold = Decimal("10000.00")    # CTR threshold
        
    def check_limits(self, amount: Decimal, daily_total: Decimal = Decimal("0")) -> Tuple[bool, str]:
        """
        Check transaction against limits.
        
        Returns:
            Tuple[bool, str]: (within_limits, reason)
        """
        logger.info(f"[EVE] Checking limits for ${amount:,.2f}")
        
        # Single transaction limit
        if amount > self.single_tx_limit:
            logger.warning(f"[EVE] ❌ SINGLE TX LIMIT EXCEEDED: ${amount:,.2f} > ${self.single_tx_limit:,.2f}")
            return False, f"SINGLE_TX_LIMIT_EXCEEDED (${amount:,.2f})"
        
        # Daily aggregate limit
        new_daily = daily_total + amount
        if new_daily > self.daily_limit:
            logger.warning(f"[EVE] ❌ DAILY LIMIT EXCEEDED: ${new_daily:,.2f} > ${self.daily_limit:,.2f}")
            return False, f"DAILY_LIMIT_EXCEEDED (${new_daily:,.2f})"
        
        # Log if CTR threshold reached (informational)
        if amount >= self.reporting_threshold:
            logger.info(f"[EVE] CTR REPORTABLE: ${amount:,.2f} >= ${self.reporting_threshold:,.2f}")
        
        logger.info(f"[EVE] ✅ Transaction ${amount:,.2f} within limits")
        return True, "WITHIN_LIMITS"


class RiskScorer:
    """
    Composite Risk Assessment
    Managed by: Sam (GID-12)
    """
    
    def __init__(self):
        self.agent_id = "GID-12"
        self.agent_name = "Sam"
        self.risk_threshold = 70  # Scores >= 70 require review
        
    def calculate_risk(self, factors: Dict[str, Any]) -> Tuple[int, str]:
        """
        Calculate composite risk score.
        
        Returns:
            Tuple[int, str]: (risk_score, assessment)
        """
        score = 0
        
        # High-risk country (+30)
        high_risk_countries = {"RU", "CN", "VE", "BY"}
        if factors.get("country_code", "").upper() in high_risk_countries:
            score += 30
        
        # Large amount (+20 if > $100K)
        amount = factors.get("amount", Decimal("0"))
        if amount > Decimal("100000"):
            score += 20
        
        # New customer (+15)
        if factors.get("is_new_customer", False):
            score += 15
        
        # Round numbers (+10 - structuring indicator)
        if amount > 0 and amount % 1000 == 0:
            score += 10
        
        # Unusual timing (+10 if outside business hours)
        if factors.get("off_hours", False):
            score += 10
        
        assessment = "LOW_RISK" if score < 40 else "MEDIUM_RISK" if score < 70 else "HIGH_RISK"
        logger.info(f"[SAM] Risk Score: {score} ({assessment})")
        
        return score, assessment


class AMLGate:
    """
    Master AML Gate - Financial Pillar of Trinity
    Managed by: Benson (GID-00)
    
    Orchestrates watchlist, limits, and risk scoring for
    comprehensive AML compliance.
    """
    
    def __init__(self):
        self.agent_id = "GID-00"
        self.agent_name = "Benson"
        self.watchlist = WatchlistChecker()
        self.limiter = TransactionLimiter()
        self.scorer = RiskScorer()
        self.decisions_made = 0
        
    def process(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process payment through AML Gate.
        
        Args:
            payment_data: Dict containing:
                - payer_id: Entity ID of payer
                - payee_id: Entity ID of payee
                - payer_country: ISO country code
                - payee_country: ISO country code
                - amount: Transaction amount (Decimal or float)
                - daily_total: Running daily total for payer
                
        Returns:
            Dict containing decision and full reasoning
        """
        tx_id = payment_data.get("transaction_id", f"TX-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}")
        logger.info(f"[BENSON] ═══════════════════════════════════════════════")
        logger.info(f"[BENSON] Processing AML Check: {tx_id}")
        logger.info(f"[BENSON] ═══════════════════════════════════════════════")
        
        amount = Decimal(str(payment_data.get("amount", 0)))
        
        # Layer 1: Watchlist Screening (both parties)
        payer_clear, payer_reason = self.watchlist.screen(
            payment_data.get("payer_id", "UNKNOWN"),
            payment_data.get("payer_country", "US")
        )
        payee_clear, payee_reason = self.watchlist.screen(
            payment_data.get("payee_id", "UNKNOWN"),
            payment_data.get("payee_country", "US")
        )
        
        watchlist_pass = payer_clear and payee_clear
        watchlist_detail = "BOTH_PARTIES_CLEAR" if watchlist_pass else f"PAYER: {payer_reason}, PAYEE: {payee_reason}"
        
        # Layer 2: Transaction Limits
        daily_total = Decimal(str(payment_data.get("daily_total", 0)))
        limits_ok, limits_reason = self.limiter.check_limits(amount, daily_total)
        
        # Layer 3: Risk Scoring
        risk_score, risk_assessment = self.scorer.calculate_risk({
            "country_code": payment_data.get("payer_country", "US"),
            "amount": amount,
            "is_new_customer": payment_data.get("is_new_customer", False),
            "off_hours": payment_data.get("off_hours", False)
        })
        
        # Decision Logic
        decision = AMLDecision.REJECT
        final_reason = ""
        
        if not watchlist_pass:
            decision = AMLDecision.REJECT
            final_reason = f"WATCHLIST_HIT: {watchlist_detail}"
            logger.error(f"[BENSON] ❌ REJECT - {final_reason}")
            
        elif not limits_ok:
            decision = AMLDecision.REJECT
            final_reason = f"LIMIT_EXCEEDED: {limits_reason}"
            logger.error(f"[BENSON] ❌ REJECT - {final_reason}")
            
        elif risk_score >= self.scorer.risk_threshold:
            decision = AMLDecision.REVIEW
            final_reason = f"HIGH_RISK_SCORE: {risk_score}"
            logger.warning(f"[BENSON] ⚠️  REVIEW - {final_reason}")
            
        else:
            decision = AMLDecision.APPROVE
            final_reason = "ALL_CHECKS_PASSED"
            logger.info(f"[BENSON] ✅ APPROVE - {final_reason}")
        
        self.decisions_made += 1
        
        return {
            "transaction_id": tx_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision": decision.value,
            "reason": final_reason,
            "requires_review": decision == AMLDecision.REVIEW,
            "amount": str(amount),
            "layers": {
                "watchlist": {
                    "agent": f"{self.watchlist.agent_name} ({self.watchlist.agent_id})",
                    "status": "PASS" if watchlist_pass else "FAIL",
                    "detail": watchlist_detail
                },
                "limits": {
                    "agent": f"{self.limiter.agent_name} ({self.limiter.agent_id})",
                    "status": "PASS" if limits_ok else "FAIL",
                    "detail": limits_reason
                },
                "risk": {
                    "agent": f"{self.scorer.agent_name} ({self.scorer.agent_id})",
                    "score": risk_score,
                    "assessment": risk_assessment
                }
            },
            "gate_agent": f"{self.agent_name} ({self.agent_id})",
            "decision_number": self.decisions_made
        }


if __name__ == "__main__":
    # Quick validation
    gate = AMLGate()
    
    # Clean transaction
    result = gate.process({
        "transaction_id": "TX-CLEAN-001",
        "payer_id": "ACME-CORP",
        "payee_id": "GLOBEX-INC",
        "payer_country": "US",
        "payee_country": "DE",
        "amount": 50000.00,
        "daily_total": 0
    })
    print(f"Clean TX: {result['decision']}")
    assert result["decision"] == "APPROVE"
    
    # Sanctioned entity
    result = gate.process({
        "transaction_id": "TX-SANCTION-001",
        "payer_id": "SANCTIONED-ENTITY-001",
        "payee_id": "GLOBEX-INC",
        "payer_country": "US",
        "payee_country": "US",
        "amount": 1000.00
    })
    print(f"Sanctioned TX: {result['decision']}")
    assert result["decision"] == "REJECT"
    
    print("✅ AML Gate P65 Validated")
