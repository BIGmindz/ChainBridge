/**
 * PriceDriftAlert - Shows price changes with clear UX
 *
 * Displays amber warning when server price differs from client price:
 * - Shows old vs new price comparison
 * - Offers retry button
 * - Auto-updates parent component state
 */

import { motion } from "framer-motion";
import { AlertTriangle, RefreshCw, TrendingDown, TrendingUp } from "lucide-react";

import { classNames } from "../../utils/classNames";

interface PriceDriftAlertProps {
  oldPrice: number;
  newPrice: number;
  onAcceptNewPrice: () => void;
  onCancel: () => void;
  isUpdating?: boolean;
  className?: string;
}

export function PriceDriftAlert({
  oldPrice,
  newPrice,
  onAcceptNewPrice,
  onCancel,
  isUpdating = false,
  className,
}: PriceDriftAlertProps) {
  const priceDifference = newPrice - oldPrice;
  const percentageChange = (priceDifference / oldPrice) * 100;
  const isPriceIncrease = priceDifference > 0;
  const isPriceDecrease = priceDifference < 0;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95, y: -10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95, y: -10 }}
      transition={{ type: "spring", duration: 0.3 }}
      className={classNames("p-4 bg-amber-950/30 rounded-lg border border-amber-500/30", className)}
    >
      {/* Header */}
      <div className="flex items-start gap-3 mb-4">
        <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-amber-400 mb-1">Price Updated</h3>
          <p className="text-xs text-amber-300">
            The official ChainBridge price has changed since your quote. Please review the updated
            price.
          </p>
        </div>
      </div>

      {/* Price Comparison */}
      <div className="space-y-3 mb-4">
        {/* Old Price */}
        <div className="flex items-center justify-between p-3 bg-slate-800/30 rounded border border-slate-700/50">
          <div className="text-sm text-slate-400">Previous Price</div>
          <div className="text-lg font-mono font-bold text-slate-300">
            ${oldPrice.toLocaleString()}
          </div>
        </div>

        {/* Price Change Arrow */}
        <div className="flex justify-center">
          <div
            className={classNames(
              "flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium",
              isPriceIncrease
                ? "bg-red-500/20 border border-red-500/30 text-red-400"
                : isPriceDecrease
                  ? "bg-emerald-500/20 border border-emerald-500/30 text-emerald-400"
                  : "bg-slate-500/20 border border-slate-500/30 text-slate-400"
            )}
          >
            {isPriceIncrease ? (
              <TrendingUp className="w-3 h-3" />
            ) : isPriceDecrease ? (
              <TrendingDown className="w-3 h-3" />
            ) : (
              <RefreshCw className="w-3 h-3" />
            )}
            <span>
              {isPriceIncrease ? "+" : ""}
              {priceDifference.toLocaleString()}({percentageChange > 0 ? "+" : ""}
              {percentageChange.toFixed(1)}%)
            </span>
          </div>
        </div>

        {/* New Price */}
        <div className="flex items-center justify-between p-3 bg-cyan-950/30 rounded border border-cyan-500/30">
          <div className="text-sm text-cyan-400 flex items-center gap-2">
            <span>Updated Price</span>
            <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
          </div>
          <div className="text-lg font-mono font-bold text-cyan-300">
            ${newPrice.toLocaleString()}
          </div>
        </div>
      </div>

      {/* Impact Message */}
      <div className="mb-4 p-3 bg-slate-950/50 rounded border border-slate-700/50">
        <div className="text-xs text-slate-400">
          {isPriceIncrease ? (
            <>
              Price increased by ${Math.abs(priceDifference).toLocaleString()}. You&apos;ll pay the
              higher amount if you proceed.
            </>
          ) : isPriceDecrease ? (
            <>
              Price decreased by ${Math.abs(priceDifference).toLocaleString()}. You&apos;ll benefit
              from the lower price!
            </>
          ) : (
            <>Price has been updated. The new price will be used for settlement.</>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={onCancel}
          disabled={isUpdating}
          className="flex-1 px-4 py-2 text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Cancel
        </button>
        <button
          onClick={onAcceptNewPrice}
          disabled={isUpdating}
          className={classNames(
            "flex-2 px-4 py-2 rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2",
            isPriceDecrease
              ? "bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white"
              : "bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white"
          )}
        >
          {isUpdating && (
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
              className="w-4 h-4 border-2 border-current border-t-transparent rounded-full"
            />
          )}
          Accept New Price
        </button>
      </div>

      {/* Trust Indicator */}
      <div className="mt-3 pt-3 border-t border-amber-500/20">
        <div className="text-xs text-amber-400/70 text-center">
          Official pricing validated by ChainBridge servers
        </div>
      </div>
    </motion.div>
  );
}

/**
 * Compact price drift indicator for inline use
 */
export function PriceDriftBadge({
  oldPrice,
  newPrice,
  className,
}: {
  oldPrice: number;
  newPrice: number;
  className?: string;
}) {
  const priceDifference = newPrice - oldPrice;
  const isPriceIncrease = priceDifference > 0;

  return (
    <div
      className={classNames(
        "inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium",
        isPriceIncrease
          ? "bg-red-500/20 border border-red-500/30 text-red-400"
          : "bg-emerald-500/20 border border-emerald-500/30 text-emerald-400",
        className
      )}
    >
      {isPriceIncrease ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
      <span>
        {isPriceIncrease ? "+" : ""}${Math.abs(priceDifference).toLocaleString()}
      </span>
    </div>
  );
}
