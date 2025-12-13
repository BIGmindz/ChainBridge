/**
 * SettlementStatusBar - Real-time settlement status indicator
 *
 * Shows live settlement progress with trust indicators:
 * - pending: spinning badge ("Processing settlement…")
 * - settling: amber badge ("Submitting transaction…")
 * - settled: green badge ("Purchase complete ✓")
 * - failed: red badge ("Settlement failed")
 */

import { motion } from "framer-motion";
import { AlertTriangle, Check, Clock, ExternalLink, X } from "lucide-react";

import type { RealtimeSettlementEvent } from "../../hooks/useSettlementEvents";
import { classNames } from "../../utils/classNames";

interface SettlementStatusBarProps {
  status: RealtimeSettlementEvent['data']['status'];
  txHash?: string | null;
  error?: string | null;
  finalPrice?: number | null;
  intentId?: string | null;
  isDemoMode?: boolean;
  className?: string;
}

export function SettlementStatusBar({
  status,
  txHash,
  error,
  finalPrice,
  intentId,
  isDemoMode = false,
  className,
}: SettlementStatusBarProps) {

  const getStatusConfig = () => {
    switch (status) {
      case 'pending':
        return {
          icon: <Clock className="w-4 h-4" />,
          text: 'Processing settlement...',
          bgColor: 'bg-slate-500/20',
          borderColor: 'border-slate-500/30',
          textColor: 'text-slate-400',
          iconColor: 'text-slate-400',
          animated: true,
        };

      case 'settling':
        return {
          icon: <Clock className="w-4 h-4" />,
          text: 'Submitting transaction...',
          bgColor: 'bg-amber-500/20',
          borderColor: 'border-amber-500/30',
          textColor: 'text-amber-400',
          iconColor: 'text-amber-400',
          animated: true,
        };

      case 'settled':
        return {
          icon: <Check className="w-4 h-4" />,
          text: 'Purchase complete ✓',
          bgColor: 'bg-emerald-500/20',
          borderColor: 'border-emerald-500/30',
          textColor: 'text-emerald-400',
          iconColor: 'text-emerald-400',
          animated: false,
        };

      case 'failed':
      default:
        return {
          icon: <X className="w-4 h-4" />,
          text: 'Settlement failed',
          bgColor: 'bg-red-500/20',
          borderColor: 'border-red-500/30',
          textColor: 'text-red-400',
          iconColor: 'text-red-400',
          animated: false,
        };
    }
  };

  const config = getStatusConfig();

  return (
    <div className={classNames(
      "flex items-center gap-3 p-4 rounded-lg border",
      config.bgColor,
      config.borderColor,
      className
    )}>
      {/* Status Icon */}
      <div className={classNames(
        "flex-shrink-0",
        config.iconColor
      )}>
        {config.animated ? (
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          >
            {config.icon}
          </motion.div>
        ) : (
          config.icon
        )}
      </div>

      {/* Status Content */}
      <div className="flex-1 min-w-0">
        <div className={classNames(
          "text-sm font-medium",
          config.textColor
        )}>
          {config.text}
          {isDemoMode && (
            <span className="ml-2 px-2 py-0.5 text-xs bg-blue-500/20 text-blue-400 rounded border border-blue-500/30">
              DEMO
            </span>
          )}
        </div>

        {/* Additional Info */}
        <div className="mt-1 space-y-1">
          {finalPrice && (
            <div className="text-xs text-slate-400">
              Final price: ${finalPrice.toLocaleString()}
            </div>
          )}

          {error && (
            <div className="flex items-start gap-1 text-xs text-red-400">
              <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {intentId && (
            <div className="text-xs text-slate-500 font-mono">
              Intent: {intentId.slice(0, 8)}...{intentId.slice(-4)}
            </div>
          )}
        </div>
      </div>

      {/* Transaction Link */}
      {txHash && !isDemoMode && (
        <div className="flex-shrink-0">
          <button
            onClick={() => {
              // TODO: Replace with actual blockchain explorer URL
              const explorerUrl = `https://etherscan.io/tx/${txHash}`;
              window.open(explorerUrl, '_blank', 'noopener,noreferrer');
            }}
            className="p-2 text-slate-400 hover:text-slate-300 transition-colors rounded"
            aria-label="View transaction on blockchain explorer"
          >
            <ExternalLink className="w-4 h-4" />
          </button>
        </div>
      )}

      {txHash && isDemoMode && (
        <div className="flex-shrink-0">
          <div className="p-2 text-slate-500 rounded" title="Demo transaction hash">
            <ExternalLink className="w-4 h-4" />
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Compact version for inline use
 */
export function SettlementStatusBadge({
  status,
  isDemoMode = false,
  className,
}: Pick<SettlementStatusBarProps, 'status' | 'isDemoMode' | 'className'>) {

  const getStatusConfig = () => {
    switch (status) {
      case 'pending':
        return {
          icon: <Clock className="w-3 h-3" />,
          text: 'Processing',
          bgColor: 'bg-slate-500/20',
          borderColor: 'border-slate-500/30',
          textColor: 'text-slate-400',
          animated: true,
        };

      case 'settling':
        return {
          icon: <Clock className="w-3 h-3" />,
          text: 'Settling',
          bgColor: 'bg-amber-500/20',
          borderColor: 'border-amber-500/30',
          textColor: 'text-amber-400',
          animated: true,
        };

      case 'settled':
        return {
          icon: <Check className="w-3 h-3" />,
          text: 'Complete',
          bgColor: 'bg-emerald-500/20',
          borderColor: 'border-emerald-500/30',
          textColor: 'text-emerald-400',
          animated: false,
        };

      case 'failed':
      default:
        return {
          icon: <X className="w-3 h-3" />,
          text: 'Failed',
          bgColor: 'bg-red-500/20',
          borderColor: 'border-red-500/30',
          textColor: 'text-red-400',
          animated: false,
        };
    }
  };

  const config = getStatusConfig();

  return (
    <div className={classNames(
      "inline-flex items-center gap-1.5 px-2 py-1 rounded border text-xs font-medium",
      config.bgColor,
      config.borderColor,
      config.textColor,
      className
    )}>
      {config.animated ? (
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
        >
          {config.icon}
        </motion.div>
      ) : (
        config.icon
      )}
      <span>{config.text}</span>
      {isDemoMode && (
        <span className="ml-1 px-1 py-0.5 text-xs bg-blue-500/30 text-blue-300 rounded">
          DEMO
        </span>
      )}
    </div>
  );
}
