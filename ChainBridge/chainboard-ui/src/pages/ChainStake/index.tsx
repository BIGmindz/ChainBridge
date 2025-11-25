/**
 * ChainStakePage
 *
 * Money View Layout for Corporate Treasury.
 * Displays staking positions, liquidity, and yield generation.
 *
 * Layout:
 * 1. Top: LiquidityDashboard HUD (TVS, Liquid Capital, Yield)
 * 2. Middle: Active Positions table with collateral/LTV tracking
 * 3. Bottom: Yield chart + critical alerts
 *
 * Integrations:
 * - Connects to /api/staking/positions
 * - Connects to /api/staking/treasury-summary
 * - Monitors /api/staking/critical-positions for breaches
 */

import { motion } from "framer-motion";
import { AlertTriangle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import {
    flashRepay,
    getCriticalPositions,
    getStakingPositions,
    getTreasurySummary,
    liquidatePosition,
} from "../../api/chainpay";
import { CollateralBreachModal } from "../../components/risk/CollateralBreachModal";
import { Skeleton } from "../../components/ui/Skeleton";
import type { CollateralBreach, StakingPosition, TreasurySummary } from "../../types/chainbridge";

import { LiquidityDashboard } from "./LiquidityDashboard";

/**
 * ChainStakePage: Full Bloomberg Terminal money view
 */
export function ChainStakePage() {
  // Data state
  const [positions, setPositions] = useState<StakingPosition[]>([]);
  const [summary, setSummary] = useState<TreasurySummary | null>(null);
  const [criticalPositions, setCriticalPositions] = useState<CollateralBreach[]>([]);
  const [selectedBreach, setSelectedBreach] = useState<CollateralBreach | null>(null);
  const [isBreachModalOpen, setIsBreachModalOpen] = useState(false);

  // UI state
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshAt, setLastRefreshAt] = useState<string | null>(null);

  // Action states
  const [isProcessing, setIsProcessing] = useState(false);

  /**
   * Fetch all data from backend
   */
  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const [positionsData, summaryData, criticalData] = await Promise.all([
        getStakingPositions(),
        getTreasurySummary(),
        getCriticalPositions(),
      ]);

      setPositions(positionsData);
      setSummary(summaryData);
      setCriticalPositions(criticalData);
      setLastRefreshAt(new Date().toLocaleTimeString());

      // If there are critical positions, show the first one
      if (criticalData.length > 0 && !selectedBreach) {
        setSelectedBreach(criticalData[0]);
        setIsBreachModalOpen(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch staking data");
    } finally {
      setIsLoading(false);
    }
  }, [selectedBreach]);

  /**
   * Initial data load + polling setup
   */
  useEffect(() => {
    fetchData();

    // Poll for updates every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  /**
   * Handle flash repay action
   */
  const handleFlashRepay = useCallback(
    async (positionId: string) => {
      try {
        setIsProcessing(true);
        const success = await flashRepay(positionId);

        if (success) {
          // Refresh data after successful repay
          await fetchData();
          setIsBreachModalOpen(false);
        } else {
          setError("Flash repay failed. Please try again.");
        }
      } finally {
        setIsProcessing(false);
      }
    },
    [fetchData]
  );

  /**
   * Handle liquidation action
   */
  const handleLiquidate = useCallback(
    async (positionId: string) => {
      try {
        setIsProcessing(true);
        const success = await liquidatePosition(
          positionId,
          "Operator initiated liquidation via Bloomberg UI"
        );

        if (success) {
          // Refresh data after liquidation
          await fetchData();
          setIsBreachModalOpen(false);
        } else {
          setError("Liquidation failed. Please try again.");
        }
      } finally {
        setIsProcessing(false);
      }
    },
    [fetchData]
  );

  // Loading state with skeleton loaders
  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 p-6 space-y-6">
        {/* Header skeleton */}
        <div className="border-b border-slate-800 pb-4">
          <Skeleton className="h-8 w-64 mb-2" />
          <Skeleton className="h-4 w-96" />
        </div>

        {/* HUD skeleton (3 cards) */}
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>

        {/* Table skeleton */}
        <div className="space-y-2">
          <Skeleton className="h-10 w-full" />
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>

        {/* Chart skeleton */}
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  // Calculate yield per second from summary
  const yieldPerSecond = summary?.yieldPerSecond || 0;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 space-y-6 p-6">
      {/* Header */}
      <motion.div
        className="border-b border-slate-800 pb-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <h1 className="text-3xl font-bold">ChainStake Treasury</h1>
        <p className="text-slate-500 text-sm mt-1">
          Corporate Staking Dashboard • {lastRefreshAt && `Last Updated: ${lastRefreshAt}`}
        </p>
      </motion.div>

      {/* Error Alert */}
      {error && (
        <motion.div
          className="bg-red-900/20 border border-red-700/50 rounded-lg p-4 flex items-center gap-3"
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <AlertTriangle className="h-5 w-5 text-red-400" />
          <div className="flex-1">
            <p className="text-sm text-red-300">{error}</p>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-red-400 hover:text-red-300 text-sm font-medium"
          >
            Dismiss
          </button>
        </motion.div>
      )}

      {/* Critical Alert Bar */}
      {criticalPositions.length > 0 && (
        <motion.div
          className="bg-red-900/20 border border-red-700 rounded-lg p-3 flex items-center gap-3"
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0 animate-pulse" />
          <div className="flex-1">
            <p className="text-sm text-red-300 font-semibold">
              {criticalPositions.length} position{criticalPositions.length !== 1 ? "s" : ""} at critical risk
            </p>
            <p className="text-xs text-red-400 mt-0.5">
              Liquidation imminent. Immediate action required.
            </p>
          </div>
          <button
            onClick={() => {
              setSelectedBreach(criticalPositions[0]);
              setIsBreachModalOpen(true);
            }}
            className="px-3 py-1.5 rounded bg-red-600 text-white text-sm font-medium hover:bg-red-700 transition-colors"
          >
            View Risk
          </button>
        </motion.div>
      )}

      {/* Main Dashboard */}
      {summary && (
        <LiquidityDashboard
          positions={positions}
          totalYieldAccrued={summary.totalYieldAccrued}
          yieldPerSecond={yieldPerSecond}
          currency="USD"
        />
      )}

      {/* Footer: Quick Actions */}
      <motion.div
        className="border-t border-slate-800 pt-4 flex items-center justify-between text-xs text-slate-500"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <div className="flex gap-4">
          <div>
            <span className="text-slate-400">Total Positions:</span> {positions.length}
          </div>
          <div>
            <span className="text-slate-400">At Risk:</span> {criticalPositions.length}
          </div>
          {summary && (
            <>
              <div>
                <span className="text-slate-400">Portfolio Health:</span>{" "}
                <span className={summary.healthFactor > 80 ? "text-emerald-400" : summary.healthFactor > 50 ? "text-amber-400" : "text-red-400"}>
                  {summary.healthFactor.toFixed(0)}%
                </span>
              </div>
            </>
          )}
        </div>
        <button
          onClick={() => fetchData()}
          className="text-slate-400 hover:text-slate-300 transition-colors font-medium"
        >
          Refresh Now
        </button>
      </motion.div>

      {/* Collateral Breach Modal */}
      <CollateralBreachModal
        breach={selectedBreach}
        isOpen={isBreachModalOpen}
        onClose={() => setIsBreachModalOpen(false)}
        onFlashRepay={handleFlashRepay}
        onAbandonLiquidate={handleLiquidate}
      />

      {/* Processing Overlay */}
      {isProcessing && (
        <motion.div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <div className="bg-slate-900 border border-slate-700 rounded-lg p-6 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border border-slate-700 border-t-emerald-500 mx-auto mb-3" />
            <p className="text-slate-300 text-sm">Processing transaction...</p>
            <p className="text-slate-500 text-xs mt-2">Do not close this window</p>
          </div>
        </motion.div>
      )}
    </div>
  );
}

export default ChainStakePage;
