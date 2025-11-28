/**
 * LiquidityDashboard (ChainStake)
 *
 * Corporate Treasury Interface for staking positions.
 * Shows working capital, yield accrual, and collateral health.
 *
 * Visual Design: Bloomberg Terminal dark mode with real-time data feeds
 *
 * Features:
 * - HUD with Total Staked vs Liquid Capital
 * - Animated Odometer for yield generation (ticks every second)
 * - Active Positions table with health factors
 * - Color-coded risk (Green/Amber/Red) based on LTV
 * - Margin call warnings for LTV > 90%
 */

import { motion } from "framer-motion";
import { AlertTriangle, TrendingUp, Zap } from "lucide-react";
import { memo, useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { StakingPosition } from "../../types/chainbridge";

interface LiquidityDashboardProps {
  positions: StakingPosition[];
  totalYieldAccrued?: number;
  yieldPerSecond?: number; // How much yield is generated per second
  currency?: string;
}

/**
 * Animated Number Ticker (Odometer Effect)
 */
function AnimatedOdometer({
  value,
  duration = 0.6,
  decimals = 2,
}: {
  value: number;
  duration?: number;
  decimals?: number;
}) {
  const [displayValue, setDisplayValue] = useState(value);

  useEffect(() => {
    let start: number | null = null;
    let animationId: number;

    const animate = (timestamp: number) => {
      if (start === null) start = timestamp;
      const progress = Math.min((timestamp - start) / (duration * 1000), 1);
      setDisplayValue(value * progress);
      if (progress < 1) {
        animationId = requestAnimationFrame(animate);
      }
    };

    animationId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationId);
  }, [value, duration]);

  return <span>{displayValue.toFixed(decimals)}</span>;
}

/**
 * HUD Component: KPI Strip
 */
function LiquidityHUD({
  totalStaked,
  liquidCapital,
  yieldAccrued,
  yieldPerSecond = 0.025,
  currency = "USD",
}: {
  totalStaked: number;
  liquidCapital: number;
  yieldAccrued: number;
  yieldPerSecond?: number;
  currency: string;
}) {
  const [tickingYield, setTickingYield] = useState(yieldAccrued);

  useEffect(() => {
    const interval = setInterval(() => {
      setTickingYield((prev) => prev + yieldPerSecond);
    }, 1000);
    return () => clearInterval(interval);
  }, [yieldPerSecond]);

  const utilizationRate = totalStaked > 0 ? (liquidCapital / totalStaked) * 100 : 0;

  return (
    <motion.div
      className="grid grid-cols-3 gap-4 mb-6"
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      {/* Total Value Staked */}
      <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-4">
        <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Total Staked</div>
        <div className="flex items-baseline gap-2">
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {totalStaked.toLocaleString("en-US", {
              style: "currency",
              currency,
              maximumFractionDigits: 0,
            })}
          </div>
        </div>
        <div className="text-xs text-slate-600 mt-2">Collateral locked</div>
      </div>

      {/* Liquid Capital Available */}
      <div className="bg-gradient-to-br from-emerald-900/30 to-slate-900 border border-emerald-700/50 rounded-lg p-4">
        <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Liquid Capital</div>
        <div className="flex items-baseline gap-2">
          <div className="text-2xl font-bold text-emerald-400 font-mono">
            {liquidCapital.toLocaleString("en-US", {
              style: "currency",
              currency,
              maximumFractionDigits: 0,
            })}
          </div>
          <div className="text-xs text-emerald-600">({utilizationRate.toFixed(0)}%)</div>
        </div>
        <div className="text-xs text-slate-600 mt-2">Available for withdrawal</div>
      </div>

      {/* Yield Generated (Ticking Odometer) */}
      <div className="bg-gradient-to-br from-amber-900/30 to-slate-900 border border-amber-700/50 rounded-lg p-4">
        <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Yield Generated</div>
        <div className="flex items-baseline gap-2">
          <div className="text-2xl font-bold text-amber-400 font-mono">
            <AnimatedOdometer value={tickingYield} decimals={2} />
          </div>
          <div className="text-xs text-amber-600">{currency}</div>
        </div>
        <div className="flex items-center gap-1 text-xs text-slate-600 mt-2">
          <Zap className="h-3 w-3 text-amber-600" />
          <span>+{(yieldPerSecond * 86400).toFixed(2)} {currency}/day</span>
        </div>
      </div>
    </motion.div>
  );
}

/**
 * Health Factor Badge
 */
function HealthFactorBadge({
  ltv,
  health,
}: {
  ltv: number; // Loan-to-value ratio
  health: number; // 0-100 health factor
}) {
  let bgColor = "bg-emerald-900/40 border-emerald-700/50";
  let barColor = "bg-emerald-500";
  let statusText = "Healthy";
  let textColor = "text-emerald-400";

  if (ltv > 90) {
    bgColor = "bg-red-900/40 border-red-700/50";
    barColor = "bg-red-500";
    statusText = "⚠ Margin Call";
    textColor = "text-red-400";
  } else if (ltv > 80) {
    bgColor = "bg-amber-900/40 border-amber-700/50";
    barColor = "bg-amber-500";
    statusText = "At Risk";
    textColor = "text-amber-400";
  }

  return (
    <div className={`px-3 py-2 rounded border flex items-center gap-2 ${bgColor}`}>
      <div className="flex-1">
        <div className={`text-xs font-semibold ${textColor} mb-1`}>{statusText}</div>
        <div className="w-16 h-1.5 bg-slate-800 rounded overflow-hidden">
          <motion.div
            className={`h-full ${barColor}`}
            initial={{ width: 0 }}
            animate={{ width: `${health}%` }}
            transition={{ duration: 0.6 }}
          />
        </div>
      </div>
      <div className={`text-xs font-bold font-mono ${textColor}`}>{health.toFixed(0)}%</div>
    </div>
  );
}

/**
 * Active Positions Table
 */
function ActivePositionsTable({
  positions,
  currency = "USD",
}: {
  positions: StakingPosition[];
  currency: string;
}) {
  return (
    <motion.div
      className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.2 }}
    >
      {/* Table Header */}
      <div className="px-4 py-3 bg-slate-800/50 border-b border-slate-800 grid grid-cols-7 gap-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
        <div>Asset ID</div>
        <div>Collateral</div>
        <div>Loan Amount</div>
        <div>LTV %</div>
        <div>APY</div>
        <div>Health</div>
        <div>Status</div>
      </div>

      {/* Table Rows */}
      <div className="divide-y divide-slate-800">
        {positions.map((position) => {
          const ltv = (position.loanAmount / position.collateralValue) * 100;
          const rowHighlight =
            ltv > 90
              ? "bg-red-900/10 hover:bg-red-900/20"
              : ltv > 80
                ? "bg-amber-900/10 hover:bg-amber-900/20"
                : "hover:bg-slate-800/30";

          return (
            <motion.div
              key={position.tokenId}
              className={`px-4 py-3 grid grid-cols-7 gap-4 items-center text-sm transition-colors ${rowHighlight}`}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
            >
              {/* Asset ID */}
              <div className="font-mono text-slate-300 truncate text-xs">
                {position.tokenId.slice(0, 8)}...
              </div>

              {/* Collateral Value */}
              <div className="text-slate-200 font-semibold">
                {position.collateralValue.toLocaleString("en-US", {
                  style: "currency",
                  currency,
                  maximumFractionDigits: 0,
                })}
              </div>

              {/* Loan Amount */}
              <div className="text-slate-200">
                {position.loanAmount.toLocaleString("en-US", {
                  style: "currency",
                  currency,
                  maximumFractionDigits: 0,
                })}
              </div>

              {/* LTV % */}
              <div className={`font-mono font-bold ${ltv > 90 ? "text-red-400" : ltv > 80 ? "text-amber-400" : "text-slate-300"}`}>
                {ltv.toFixed(1)}%
              </div>

              {/* APY */}
              <div className="text-emerald-400 font-semibold">
                {position.apy.toFixed(2)}%
              </div>

              {/* Health Factor */}
              <div>
                <HealthFactorBadge ltv={ltv} health={position.liquidationHealth} />
              </div>

              {/* Status */}
              <div>
                {position.status === "HEALTHY" && (
                  <span className="text-xs font-semibold text-emerald-400">✓ Active</span>
                )}
                {position.status === "AT_RISK" && (
                  <span className="text-xs font-semibold text-amber-400 flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3" /> Monitor
                  </span>
                )}
                {position.status === "LIQUIDATED" && (
                  <span className="text-xs font-semibold text-red-400">✗ Liquidated</span>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Empty State */}
      {positions.length === 0 && (
        <div className="px-4 py-8 text-center text-slate-500 text-sm">
          No active staking positions
        </div>
      )}
    </motion.div>
  );
}

/**
 * Yield Accrual Chart (Mini sparkline)
 */
function YieldChart({ data }: { data: Array<{ time: string; yield: number }> }) {
  if (!data || data.length === 0) {
    return null;
  }

  return (
    <motion.div
      className="bg-slate-900 border border-slate-800 rounded-lg p-4 mt-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.3 }}
    >
      <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
        Yield Accrual (24h)
      </div>
      <ResponsiveContainer width="100%" height={120}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="time" stroke="#64748b" style={{ fontSize: "10px" }} />
          <YAxis stroke="#64748b" style={{ fontSize: "10px" }} />
          <Tooltip
            contentStyle={{
              backgroundColor: "#0f172a",
              border: "1px solid #334155",
              borderRadius: "4px",
            }}
            labelStyle={{ color: "#cbd5e1" }}
          />
          <Line
            type="monotone"
            dataKey="yield"
            stroke="#fbbf24"
            dot={false}
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </motion.div>
  );
}

/**
 * Main LiquidityDashboard Component
 * Wrapped in React.memo to prevent full re-renders on yield ticker updates
 */
function LiquidityDashboardComponent({
  positions,
  totalYieldAccrued = 0,
  yieldPerSecond = 0.025,
  currency = "USD",
}: LiquidityDashboardProps) {
  const totalStaked = positions.reduce((sum, pos) => sum + pos.collateralValue, 0);
  const totalLoan = positions.reduce((sum, pos) => sum + pos.loanAmount, 0);
  const liquidCapital = totalStaked - totalLoan;

  // Generate mock yield chart data
  const yieldChartData = Array.from({ length: 24 }, (_, i) => ({
    time: `${i}h`,
    yield: totalYieldAccrued + i * yieldPerSecond * 3600,
  }));

  return (
    <div className="bg-slate-950 min-h-screen p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <TrendingUp className="h-6 w-6 text-emerald-500" />
            Liquidity Dashboard
          </h1>
          <p className="text-xs text-slate-500 mt-1">ChainStake Corporate Treasury Interface</p>
        </div>
      </div>

      {/* HUD: KPI Strip */}
      <LiquidityHUD
        totalStaked={totalStaked}
        liquidCapital={liquidCapital}
        yieldAccrued={totalYieldAccrued}
        yieldPerSecond={yieldPerSecond}
        currency={currency}
      />

      {/* Active Positions Table */}
      <ActivePositionsTable positions={positions} currency={currency} />

      {/* Yield Chart */}
      <YieldChart data={yieldChartData} />
    </div>
  );
}

/**
 * Export wrapped in React.memo
 * This prevents the entire dashboard from re-rendering when parent updates
 * Only re-renders if positions, totalYieldAccrued, yieldPerSecond, or currency change
 */
export const LiquidityDashboard = memo(LiquidityDashboardComponent);
