/**
 * TrustIndicators - Visual trust cues for Web3 transactions
 *
 * Provides clear indicators that help users understand:
 * - Official ChainBridge pricing validation
 * - Server-authoritative vs client-side calculations
 * - Security and trust signals
 */

import { motion } from "framer-motion";
import { AlertTriangle, Check, Clock, Info, Shield } from "lucide-react";

import { classNames } from "../../utils/classNames";

interface OfficialPriceBadgeProps {
  isValidated?: boolean;
  quotedAt?: string;
  className?: string;
}

/**
 * Badge indicating official ChainBridge pricing
 */
export function OfficialPriceBadge({
  isValidated = false,
  quotedAt,
  className
}: OfficialPriceBadgeProps) {
  return (
    <div className={classNames(
      "inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium border",
      isValidated
        ? "bg-emerald-500/20 border-emerald-500/30 text-emerald-400"
        : "bg-slate-500/20 border-slate-500/30 text-slate-400",
      className
    )}>
      {isValidated ? (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", duration: 0.5 }}
        >
          <Check className="w-3 h-3" />
        </motion.div>
      ) : (
        <Clock className="w-3 h-3" />
      )}
      <span>Official ChainBridge Price</span>
      {quotedAt && (
        <span className="text-xs opacity-70">
          {new Date(quotedAt).toLocaleTimeString()}
        </span>
      )}
    </div>
  );
}

interface PriceValidationTooltipProps {
  children: React.ReactNode;
  isDemo?: boolean;
}

/**
 * Tooltip explaining authoritative pricing
 */
export function PriceValidationTooltip({ children, isDemo = false }: PriceValidationTooltipProps) {
  return (
    <div className="group relative inline-block">
      {children}
      <div className="invisible group-hover:visible absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-64 z-50">
        <div className="bg-slate-900 border border-slate-700 rounded-lg shadow-xl p-3">
          <div className="text-xs text-slate-300 space-y-2">
            <div className="flex items-start gap-2">
              <Shield className="w-3 h-3 text-cyan-400 mt-0.5 flex-shrink-0" />
              <div>
                <div className="font-medium text-white mb-1">Server-Authoritative Pricing</div>
                <div>
                  ChainBridge validates all prices server-side to prevent manipulation and ensure fair market pricing.
                </div>
              </div>
            </div>
            {isDemo && (
              <div className="flex items-start gap-2 pt-2 border-t border-slate-700">
                <Info className="w-3 h-3 text-blue-400 mt-0.5 flex-shrink-0" />
                <div className="text-blue-300">
                  Demo mode uses simulated pricing for testing purposes.
                </div>
              </div>
            )}
          </div>
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-slate-700"></div>
        </div>
      </div>
    </div>
  );
}

interface SecurityBadgeProps {
  walletConnected: boolean;
  isDemoWallet?: boolean;
  className?: string;
}

/**
 * Security status indicator
 */
export function SecurityBadge({
  walletConnected,
  isDemoWallet = false,
  className
}: SecurityBadgeProps) {
  if (!walletConnected) {
    return (
      <div className={classNames(
        "inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium border",
        "bg-slate-500/20 border-slate-500/30 text-slate-400",
        className
      )}>
        <AlertTriangle className="w-3 h-3" />
        <span>Wallet Required</span>
      </div>
    );
  }

  return (
    <div className={classNames(
      "inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium border",
      isDemoWallet
        ? "bg-blue-500/20 border-blue-500/30 text-blue-400"
        : "bg-emerald-500/20 border-emerald-500/30 text-emerald-400",
      className
    )}>
      <Shield className="w-3 h-3" />
      <span>
        {isDemoWallet ? 'Demo Wallet Connected' : 'Wallet Connected'}
      </span>
    </div>
  );
}

interface TrustFooterProps {
  isDemoMode?: boolean;
  className?: string;
}

/**
 * Footer trust message for modals/forms
 */
export function TrustFooter({ isDemoMode = false, className }: TrustFooterProps) {
  return (
    <div className={classNames(
      "text-xs text-slate-500 text-center flex items-center justify-center gap-1",
      className
    )}>
      <Shield className="w-3 h-3" />
      <span>
        {isDemoMode
          ? 'Demo transaction • No real funds involved'
          : 'Signed with your wallet, validated by ChainBridge'
        }
      </span>
    </div>
  );
}

interface AuthoritativePriceIndicatorProps {
  clientPrice: number;
  serverPrice: number;
  isValidated: boolean;
  className?: string;
}

/**
 * Indicates which price is authoritative
 */
export function AuthoritativePriceIndicator({
  clientPrice,
  serverPrice,
  isValidated,
  className
}: AuthoritativePriceIndicatorProps) {
  const hasDifference = Math.abs(clientPrice - serverPrice) > 0;

  return (
    <div className={classNames(
      "p-3 rounded-lg border",
      isValidated
        ? "bg-emerald-950/30 border-emerald-500/30"
        : "bg-slate-950/30 border-slate-700/50",
      className
    )}>
      <div className="flex items-center gap-2 mb-2">
        {isValidated ? (
          <Check className="w-4 h-4 text-emerald-400" />
        ) : (
          <Clock className="w-4 h-4 text-slate-400" />
        )}
        <span className={classNames(
          "text-sm font-medium",
          isValidated ? "text-emerald-400" : "text-slate-400"
        )}>
          {isValidated ? 'Price Validated' : 'Validating Price...'}
        </span>
      </div>

      {hasDifference && isValidated && (
        <div className="text-xs text-slate-400 space-y-1">
          <div>Client estimate: ${clientPrice.toLocaleString()}</div>
          <div className="text-emerald-400">
            Official price: ${serverPrice.toLocaleString()}
          </div>
          <div className="text-xs text-slate-500 mt-2">
            Server price will be used for settlement
          </div>
        </div>
      )}

      {!hasDifference && isValidated && (
        <div className="text-xs text-emerald-400">
          Client and server prices match
        </div>
      )}
    </div>
  );
}
