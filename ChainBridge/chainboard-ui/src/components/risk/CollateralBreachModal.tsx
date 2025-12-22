/**
 * CollateralBreachModal
 *
 * "War Room" Modal for critical collateral breach.
 * Triggered when LTV > 90% or liquidation is imminent.
 *
 * Visual Design: RED MODE - Dark red backgrounds, critical alerts
 *
 * Features:
 * - Critical risk display with LTV percentage
 * - Required deposit amount to restore health
 * - Live countdown timer to liquidation
 * - Primary action: "Flash Repay" (Connect Wallet)
 * - Secondary action: "Abandon & Liquidate"
 * - Persistent alert until action is taken
 */

import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, Clock, X, Zap } from "lucide-react";
import { useEffect, useState } from "react";

import type { CollateralBreach } from "../../types/chainbridge";

interface CollateralBreachModalProps {
  breach: CollateralBreach | null;
  isOpen: boolean;
  onClose: () => void;
  onFlashRepay: (positionId: string) => Promise<void>;
  onAbandonLiquidate: (positionId: string) => Promise<void>;
}

/**
 * Countdown Timer Component
 */
function CountdownTimer({ ms }: { ms: number }) {
  const [remaining, setRemaining] = useState(ms);

  useEffect(() => {
    const interval = setInterval(() => {
      setRemaining((prev) => Math.max(0, prev - 1000));
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const seconds = Math.floor((remaining / 1000) % 60);
  const minutes = Math.floor((remaining / (1000 * 60)) % 60);
  const hours = Math.floor((remaining / (1000 * 60 * 60)) % 24);

  return (
    <div className="text-center">
      <div className="text-sm text-slate-400 mb-2">Liquidation in</div>
      <div className="flex items-center justify-center gap-3">
        <Clock className="h-5 w-5 text-red-500 animate-pulse" />
        <div className="text-4xl font-bold font-mono text-red-400">
          {String(hours).padStart(2, "0")}:{String(minutes).padStart(2, "0")}:{String(seconds).padStart(2, "0")}
        </div>
      </div>
    </div>
  );
}

/**
 * LTV Display with Critical Badge
 */
function LTVDisplay({ ltv, required }: { ltv: number; required: number }) {
  return (
    <div className="space-y-4">
      {/* LTV Meter */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-slate-400">Current LTV</span>
          <span className="text-3xl font-bold font-mono text-red-400">{ltv.toFixed(1)}%</span>
        </div>

        {/* Bar showing danger zones */}
        <div className="relative h-6 bg-slate-800 rounded overflow-hidden border border-slate-700">
          {/* 0-80%: Safe (Green) */}
          <div className="absolute top-0 left-0 h-full w-[80%] bg-emerald-900/20" />
          {/* 80-90%: Warning (Amber) */}
          <div className="absolute top-0 left-[80%] h-full w-[10%] bg-amber-900/30" />
          {/* 90-100%: Critical (Red) */}
          <div className="absolute top-0 left-[90%] h-full w-[10%] bg-red-900/40" />

          {/* Current LTV Indicator */}
          <motion.div
            className="absolute top-0 h-full w-1 bg-red-500 shadow-lg shadow-red-500/50"
            style={{ left: `${Math.min(ltv, 100)}%` }}
            animate={{ boxShadow: ["0 0 8px rgba(239, 68, 68, 0.5)", "0 0 16px rgba(239, 68, 68, 0.8)", "0 0 8px rgba(239, 68, 68, 0.5)"] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />

          {/* Labels */}
          <div className="absolute inset-0 flex items-end justify-between px-2 pb-0.5 text-xs font-semibold text-slate-600">
            <span>Safe</span>
            <span>Risk</span>
            <span className="text-red-600">CRITICAL</span>
          </div>
        </div>

        {/* Status Text */}
        <div className="mt-2 text-xs text-red-400">
          ⚠ LTV exceeds safe threshold. Liquidation will occur if not remedied.
        </div>
      </div>

      {/* Required Deposit */}
      <div className="bg-red-900/20 border border-red-700/50 rounded-lg p-3">
        <div className="text-xs text-slate-400 mb-1">Required Deposit to Restore Health</div>
        <div className="text-2xl font-bold text-red-400 font-mono">
          {required.toLocaleString("en-US", {
            style: "currency",
            currency: "USD",
            maximumFractionDigits: 2,
          })}
        </div>
        <div className="text-xs text-slate-600 mt-2">
          Deposit this amount to bring LTV below 80%
        </div>
      </div>
    </div>
  );
}

/**
 * Main Modal Component
 */
export function CollateralBreachModal({
  breach,
  isOpen,
  onClose,
  onFlashRepay,
  onAbandonLiquidate,
}: CollateralBreachModalProps) {
  const [isProcessing, setIsProcessing] = useState(false);
  const [action, setAction] = useState<"none" | "repay" | "abandon">("none");

  const handleFlashRepay = async () => {
    if (!breach) return;
    setAction("repay");
    setIsProcessing(true);
    try {
      await onFlashRepay(breach.positionId);
      onClose();
    } catch (error) {
      console.error("Flash repay failed:", error);
    } finally {
      setIsProcessing(false);
      setAction("none");
    }
  };

  const handleAbandon = async () => {
    if (!breach) return;
    setAction("abandon");
    setIsProcessing(true);
    try {
      await onAbandonLiquidate(breach.positionId);
      onClose();
    } catch (error) {
      console.error("Abandon liquidate failed:", error);
    } finally {
      setIsProcessing(false);
      setAction("none");
    }
  };

  return (
    <AnimatePresence>
      {isOpen && breach && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 bg-black/80 backdrop-blur-sm z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            className="fixed inset-0 flex items-center justify-center z-50 p-4"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ type: "spring", damping: 20 }}
          >
            <div className="w-full max-w-md">
              {/* Modal Container */}
              <motion.div
                className="bg-gradient-to-br from-red-900/40 to-slate-900 border-2 border-red-700/50 rounded-lg overflow-hidden shadow-2xl"
                initial={{ y: 20 }}
                animate={{ y: 0 }}
              >
                {/* Header: RED MODE */}
                <div className="px-6 py-4 bg-gradient-to-r from-red-900 to-red-800 border-b-2 border-red-700 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                    >
                      <AlertTriangle className="h-6 w-6 text-red-300" />
                    </motion.div>
                    <div>
                      <h2 className="text-lg font-bold text-red-100">COLLATERAL BREACH</h2>
                      <p className="text-xs text-red-300">Critical liquidation risk detected</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={onClose}
                    disabled={isProcessing}
                    className="p-1 hover:bg-red-800 rounded transition-colors disabled:opacity-50"
                    title="Close modal"
                  >
                    <X className="h-5 w-5 text-red-200" />
                  </button>
                </div>

                {/* Content */}
                <div className="px-6 py-5 space-y-5">
                  {/* Countdown Timer */}
                  <CountdownTimer ms={breach.liquidationCountdownMs} />

                  {/* Divider */}
                  <div className="h-px bg-gradient-to-r from-transparent via-red-700/50 to-transparent" />

                  {/* LTV Display */}
                  <LTVDisplay ltv={breach.currentLTV} required={breach.requiredDeposit} />

                  {/* Additional Info */}
                  <div className="bg-slate-800/50 border border-slate-700 rounded p-3 text-xs text-slate-300 space-y-1">
                    <div>
                      <span className="text-slate-500">Position ID:</span>{" "}
                      <span className="font-mono text-slate-200">{breach.positionId.slice(0, 12)}...</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Shipment:</span>{" "}
                      <span className="font-mono text-slate-200">{breach.shipmentId.slice(0, 12)}...</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Collateral:</span>{" "}
                      <span className="font-mono text-slate-200">
                        {breach.collateralValue.toLocaleString("en-US", {
                          style: "currency",
                          currency: "USD",
                          maximumFractionDigits: 0,
                        })}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="px-6 py-4 bg-slate-900/50 border-t border-slate-700 grid grid-cols-2 gap-3">
                  {/* Flash Repay (Primary) */}
                  <motion.button
                    type="button"
                    onClick={handleFlashRepay}
                    disabled={isProcessing}
                    className="px-4 py-3 rounded-lg font-semibold text-sm flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-500 hover:to-amber-600 text-white shadow-lg shadow-amber-600/30"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    {isProcessing && action === "repay" ? (
                      <>
                        <motion.div
                          animate={{ rotate: 360 }}
                          transition={{ duration: 1, repeat: Infinity }}
                        >
                          <Zap className="h-4 w-4" />
                        </motion.div>
                        Processing...
                      </>
                    ) : (
                      <>
                        <Zap className="h-4 w-4" />
                        Flash Repay
                      </>
                    )}
                  </motion.button>

                  {/* Abandon & Liquidate (Secondary) */}
                  <motion.button
                    type="button"
                    onClick={handleAbandon}
                    disabled={isProcessing}
                    className="px-4 py-3 rounded-lg font-semibold text-sm flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-600 hover:border-slate-500"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    {isProcessing && action === "abandon" ? (
                      <>
                        <motion.div
                          animate={{ rotate: 360 }}
                          transition={{ duration: 1, repeat: Infinity }}
                        >
                          <Zap className="h-4 w-4" />
                        </motion.div>
                        Processing...
                      </>
                    ) : (
                      "Abandon & Liquidate"
                    )}
                  </motion.button>
                </div>

                {/* Warning Footer */}
                <div className="px-6 py-3 bg-red-950/50 border-t border-red-700/50 text-xs text-red-300/80 italic">
                  ⚠ Liquidation is irreversible. All collateral will be sold at market rates.
                </div>
              </motion.div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
