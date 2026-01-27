"""
PAC-ECO-P90: Autopoietic Capital Loop
======================================
"The Snake eats its tail. The Loop is closed."

Purpose: Convert Excess Capital → New Life (Agents).
         The self-replicating growth engine for ChainBridge.

Created: PAC-ECO-P90 (Autopoietic Capital Loop)
Updated: 2026-01-25

Invariants:
- GROWTH-01: Expansion Cost <= 50% Hot Wallet Balance
- GROWTH-02: Legion Ratio (3:2:1) MUST be preserved (Valuation:Governance:Security)

Philosophy:
- "Growth MUST come from Profit, never from Debt."
- "The System is Self-Replicating."
- "Capital is Fuel. Fuel is Life."

Workflow:
1. Monitor hot wallet balance (10% of total treasury)
2. If balance > growth threshold, calculate expansion capacity
3. Use 50% of hot wallet for agent spawning (50% buffer maintained)
4. Spawn agents in 3:2:1 ratio (Valuation/Governance/Security)
5. Debit treasury for operational costs
6. New agents generate value → revenue → treasury → loop closes

This is the heartbeat of the organism. This is autopoiesis.
"""

import logging
from decimal import Decimal
from typing import Dict, List, Any, Optional
from datetime import datetime

from core.finance.treasury import get_global_treasury, SovereignTreasury
from core.swarm.agent_university import AgentUniversity, AgentClone


class GrowthCycleResult:
    """
    Result of a single growth cycle execution.
    
    Captures state transition: Capital → Agents.
    """
    
    def __init__(
        self,
        status: str,
        hot_balance: Decimal,
        investable_capital: Decimal = Decimal("0"),
        new_agent_count: int = 0,
        agent_breakdown: Optional[Dict[str, int]] = None,
        total_cost: Decimal = Decimal("0"),
        remaining_liquidity: Decimal = Decimal("0"),
        reason: Optional[str] = None,
        timestamp: Optional[str] = None
    ):
        self.status = status  # EXPANSION, DORMANT, STASIS
        self.hot_balance = hot_balance
        self.investable_capital = investable_capital
        self.new_agent_count = new_agent_count
        self.agent_breakdown = agent_breakdown or {}
        self.total_cost = total_cost
        self.remaining_liquidity = remaining_liquidity
        self.reason = reason
        self.timestamp = timestamp or datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Export as dictionary."""
        return {
            "status": self.status,
            "timestamp": self.timestamp,
            "hot_balance_usd": float(self.hot_balance),
            "investable_capital_usd": float(self.investable_capital),
            "new_agent_count": self.new_agent_count,
            "agent_breakdown": self.agent_breakdown,
            "total_cost_usd": float(self.total_cost),
            "remaining_liquidity_usd": float(self.remaining_liquidity),
            "reason": self.reason
        }


class AutopoieticEngine:
    """
    PAC-ECO-P90: The Life Force.
    
    Converts Excess Capital → New Life (Agents).
    
    The autopoietic engine monitors treasury liquidity and automatically
    spawns new agents when capital exceeds operational thresholds. This
    creates a self-reinforcing loop: Agents → Revenue → Capital → Agents.
    
    Economic Parameters:
    - COST_PER_AGENT_USD: Operational reserve per agent ($100)
    - GROWTH_THRESHOLD_USD: Minimum batch size for spawning ($1,000)
    - REINVESTMENT_RATE: Percentage of hot wallet used for growth (50%)
    
    Agent Ratios (3:2:1):
    - 50% Valuation (GID-14, Sage) - Revenue generation
    - 33% Governance (GID-08, Athena) - Decision quality
    - 17% Security (GID-06, Sam) - Risk mitigation
    
    Invariants:
    - GROWTH-01: Never exceed 50% of hot wallet (maintain buffer)
    - GROWTH-02: Maintain 3:2:1 agent ratio (balanced legion)
    
    Usage:
        engine = AutopoieticEngine()
        result = engine.execute_growth_cycle()
        # → {"status": "EXPANSION", "new_agents": 10, "cost": 1000.00}
    """
    
    # Economic Constants
    COST_PER_AGENT_USD = Decimal("100.00")  # Operational Reserve
    GROWTH_THRESHOLD_USD = Decimal("1000.00")  # Minimum batch size
    REINVESTMENT_RATE = Decimal("0.50")  # 50% of hot wallet
    
    # Agent Composition Ratios (3:2:1)
    RATIO_VALUATION = Decimal("0.50")  # 50% - Revenue generation
    RATIO_GOVERNANCE = Decimal("0.33")  # 33% - Decision quality
    RATIO_SECURITY = Decimal("0.17")  # 17% - Risk mitigation
    
    # GID Mappings
    GID_VALUATION = "GID-14"  # Sage (CFO)
    GID_GOVERNANCE = "GID-08"  # Athena (Governance)
    GID_SECURITY = "GID-06"  # Sam (Security)
    
    def __init__(
        self,
        treasury: Optional[SovereignTreasury] = None,
        university: Optional[AgentUniversity] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Autopoietic Engine.
        
        Args:
            treasury: Treasury instance (defaults to global)
            university: Agent factory (defaults to new instance)
            logger: Logging instance
        """
        self.treasury = treasury or get_global_treasury()
        self.university = university or AgentUniversity()
        self.logger = logger or logging.getLogger("Autopoiesis")
        
        self.growth_history: List[GrowthCycleResult] = []
        
        self.logger.info(
            f"🌱 AUTOPOIETIC ENGINE INITIALIZED | "
            f"Agent Cost: ${self.COST_PER_AGENT_USD} | "
            f"Growth Threshold: ${self.GROWTH_THRESHOLD_USD}"
        )
    
    def execute_growth_cycle(self) -> GrowthCycleResult:
        """
        The Heartbeat of the Organism.
        
        Executes a single growth cycle:
        1. Check hot wallet liquidity
        2. Calculate expansion capacity
        3. Spawn agents in 3:2:1 ratio
        4. Debit treasury for costs
        
        Returns:
            GrowthCycleResult with status and metrics
        
        Status Types:
        - EXPANSION: Agents spawned successfully
        - DORMANT: Insufficient capital (< threshold)
        - STASIS: Capital too low for minimum unit
        """
        # Step 1: Check Liquid Capital
        hot_balance = self.treasury.get_hot_balance()
        
        self.logger.info(
            f"🌱 CHECKING GROWTH POTENTIAL | Liquidity: ${hot_balance:,.2f}"
        )
        
        # Step 2: Validate Growth Threshold
        if hot_balance < self.GROWTH_THRESHOLD_USD:
            result = GrowthCycleResult(
                status="DORMANT",
                hot_balance=hot_balance,
                reason=f"INSUFFICIENT_FUEL (${hot_balance} < ${self.GROWTH_THRESHOLD_USD})"
            )
            self.growth_history.append(result)
            self.logger.warning(f"⏸️  DORMANT: {result.reason}")
            return result
        
        # Step 3: Calculate Expansion Capacity
        # GROWTH-01: Only spend 50% of Hot Wallet (maintain buffer)
        investable_capital = hot_balance * self.REINVESTMENT_RATE
        new_agent_count = int(investable_capital // self.COST_PER_AGENT_USD)
        
        if new_agent_count == 0:
            result = GrowthCycleResult(
                status="STASIS",
                hot_balance=hot_balance,
                investable_capital=investable_capital,
                reason="CAPITAL_TOO_LOW_FOR_UNIT"
            )
            self.growth_history.append(result)
            self.logger.warning(f"⏸️  STASIS: {result.reason}")
            return result
        
        # Step 4: Spawn New Life (GROWTH-02: Maintain 3:2:1 Ratio)
        agent_breakdown, spawned_agents = self._spawn_balanced_legion(new_agent_count)
        
        # Step 5: Debit Treasury (The Cost of Birth)
        total_cost = new_agent_count * self.COST_PER_AGENT_USD
        self.treasury.debit_hot_wallet(
            amount=float(total_cost),
            reason=f"AUTOPOIESIS: Spawned {new_agent_count} agents",
            batch_id=f"GROWTH-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        
        remaining_liquidity = hot_balance - total_cost
        
        # Step 6: Record Genesis Event
        result = GrowthCycleResult(
            status="EXPANSION",
            hot_balance=hot_balance,
            investable_capital=investable_capital,
            new_agent_count=new_agent_count,
            agent_breakdown=agent_breakdown,
            total_cost=total_cost,
            remaining_liquidity=remaining_liquidity
        )
        self.growth_history.append(result)
        
        self.logger.critical(
            f"🧬 GENESIS EVENT: +{new_agent_count} AGENTS SPAWNED | "
            f"Cost: ${total_cost:,.2f} | Remaining: ${remaining_liquidity:,.2f}"
        )
        self.logger.info(f"   Breakdown: {agent_breakdown}")
        
        return result
    
    def _spawn_balanced_legion(self, total_count: int) -> tuple[Dict[str, int], List[AgentClone]]:
        """
        Spawn agents in balanced 3:2:1 ratio.
        
        GROWTH-02 ENFORCEMENT:
        - 50% Valuation (Sage/GID-14)
        - 33% Governance (Athena/GID-08)
        - 17% Security (Sam/GID-06)
        
        Args:
            total_count: Total agents to spawn
        
        Returns:
            Tuple of (breakdown_dict, spawned_agents_list)
        """
        # Calculate counts per category
        val_count = int(total_count * self.RATIO_VALUATION)
        gov_count = int(total_count * self.RATIO_GOVERNANCE)
        # Security gets remainder to ensure exact count
        sec_count = total_count - val_count - gov_count
        
        breakdown = {
            "valuation": val_count,
            "governance": gov_count,
            "security": sec_count
        }
        
        spawned_agents: List[AgentClone] = []
        
        # Spawn squads
        if val_count > 0:
            val_squad = self.university.spawn_squad(self.GID_VALUATION, val_count)
            spawned_agents.extend(val_squad)
            self.logger.info(f"   🎓 Valuation Squad: {val_count} agents (Sage/GID-14)")
        
        if gov_count > 0:
            gov_squad = self.university.spawn_squad(self.GID_GOVERNANCE, gov_count)
            spawned_agents.extend(gov_squad)
            self.logger.info(f"   🎓 Governance Squad: {gov_count} agents (Athena/GID-08)")
        
        if sec_count > 0:
            sec_squad = self.university.spawn_squad(self.GID_SECURITY, sec_count)
            spawned_agents.extend(sec_squad)
            self.logger.info(f"   🎓 Security Squad: {sec_count} agents (Sam/GID-06)")
        
        return breakdown, spawned_agents
    
    def get_growth_stats(self) -> Dict[str, Any]:
        """
        Get autopoietic growth statistics.
        
        Returns:
            Dictionary with growth metrics
        """
        if not self.growth_history:
            return {
                "total_cycles": 0,
                "total_agents_spawned": 0,
                "total_capital_invested_usd": 0.0,
                "expansion_cycles": 0,
                "dormant_cycles": 0
            }
        
        total_agents = sum(r.new_agent_count for r in self.growth_history)
        total_cost = sum(r.total_cost for r in self.growth_history)
        expansion_count = sum(1 for r in self.growth_history if r.status == "EXPANSION")
        dormant_count = sum(1 for r in self.growth_history if r.status == "DORMANT")
        
        return {
            "total_cycles": len(self.growth_history),
            "total_agents_spawned": total_agents,
            "total_capital_invested_usd": float(total_cost),
            "expansion_cycles": expansion_count,
            "dormant_cycles": dormant_count,
            "average_agents_per_cycle": total_agents / len(self.growth_history) if self.growth_history else 0
        }
    
    def verify_invariants(self) -> Dict[str, bool]:
        """
        Verify GROWTH-01 and GROWTH-02 invariants.
        
        Returns:
            Dictionary with invariant check results
        """
        results = {}
        
        # GROWTH-01: Verify 50% cap on most recent cycle
        if self.growth_history:
            latest = self.growth_history[-1]
            if latest.status == "EXPANSION":
                actual_pct = latest.investable_capital / latest.hot_balance if latest.hot_balance > 0 else Decimal("0")
                results["GROWTH-01"] = actual_pct <= self.REINVESTMENT_RATE
            else:
                results["GROWTH-01"] = True  # N/A for non-expansion
        else:
            results["GROWTH-01"] = True  # No cycles yet
        
        # GROWTH-02: Verify 3:2:1 ratio adherence
        if self.growth_history:
            latest = self.growth_history[-1]
            if latest.status == "EXPANSION" and latest.new_agent_count > 0:
                breakdown = latest.agent_breakdown
                val_ratio = breakdown.get("valuation", 0) / latest.new_agent_count
                gov_ratio = breakdown.get("governance", 0) / latest.new_agent_count
                sec_ratio = breakdown.get("security", 0) / latest.new_agent_count
                
                # Allow 5% tolerance for rounding
                tolerance = 0.05
                results["GROWTH-02"] = (
                    abs(val_ratio - float(self.RATIO_VALUATION)) <= tolerance and
                    abs(gov_ratio - float(self.RATIO_GOVERNANCE)) <= tolerance and
                    abs(sec_ratio - float(self.RATIO_SECURITY)) <= tolerance
                )
            else:
                results["GROWTH-02"] = True  # N/A
        else:
            results["GROWTH-02"] = True  # No cycles yet
        
        return results


# Singleton instance for application-wide use
_global_engine: Optional[AutopoieticEngine] = None


def get_global_engine() -> AutopoieticEngine:
    """
    Get or create the global AutopoieticEngine instance.
    
    Returns:
        AutopoieticEngine instance
    """
    global _global_engine
    if _global_engine is None:
        _global_engine = AutopoieticEngine()
    return _global_engine
