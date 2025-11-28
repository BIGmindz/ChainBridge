/**
 * SmartReconcileCard
 *
 * Glass Box UI for ChainAudit fuzzy logic visualization.
 * Shows reconciliation confidence, deduction impact, and decision vectors.
 *
 * Features:
 * - Tolerance Meter: Gradient bar (Green -> Amber -> Red)
 * - Decision vectors with impact visualization
 * - Deduction breakdown with currency formatting
 * - Conditional "Accept & Pay" vs "Accept & Pay (Adjusted)" button
 *
 * Visual Design: Bloomberg Terminal dark mode aesthetic
 */

import { motion } from "framer-motion";
import { AlertCircle, CheckCircle, TrendingDown, Zap } from "lucide-react";

import type { AuditVector, ReconciliationResult } from "../../types/chainbridge";

interface SmartReconcileCardProps {
  confidenceScore: number; // 0-100
  deduction: number; // Currency amount
  vectors: AuditVector[];
  currency?: string;
  reconciliationResult?: ReconciliationResult; // Optional: Full reconciliation object
  onAccept?: (adjusted: boolean) => void;
  onCancel?: () => void;
}

/**
 * Tolerance Meter: Visual gradient bar with color zones
 */
function ToleranceMeter({ score }: { score: number }) {
  // Clamp score to 0-100
  const normalizedScore = Math.max(0, Math.min(100, score));

  // Determine color zones and labels
  const bgGradient = "bg-gradient-to-r from-red-900 via-amber-900 to-emerald-900";
  let barColor = "bg-red-600";
  let statusLabel = "At Risk";
  let statusColor = "text-red-400";

  if (normalizedScore >= 95) {
    barColor = "bg-emerald-500";
    statusLabel = "Safe";
    statusColor = "text-emerald-400";
  } else if (normalizedScore >= 80) {
    barColor = "bg-amber-500";
    statusLabel = "Caution";
    statusColor = "text-amber-400";
  }

  return (
    <div className="space-y-2">
      {/* Score Display */}
      <div className="flex items-center justify-between">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Confidence Score
        </div>
        <div className={`text-lg font-bold ${statusColor}`}>
          {normalizedScore.toFixed(1)}%
        </div>
      </div>

      {/* Tolerance Meter Bar */}
      <div className={`relative h-3 rounded-full overflow-hidden ${bgGradient} border border-slate-700`}>
        <motion.div
          className={`h-full rounded-full ${barColor} shadow-lg shadow-current/50 origin-left`}
          initial={{ scaleX: 0 }}
          animate={{ scaleX: normalizedScore / 100 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          style={{ willChange: "transform" }}
        />
      </div>

      {/* Safe Zone Labels */}
      <div className="flex justify-between text-xs text-slate-500 px-1">
        <span>0%</span>
        <span>95% (Safe)</span>
        <span>100%</span>
      </div>

      {/* Status Badge */}
      <div className="flex items-center gap-2 mt-3">
        {normalizedScore >= 95 ? (
          <>
            <CheckCircle className="h-4 w-4 text-emerald-500" />
            <span className="text-xs text-emerald-400">{statusLabel}</span>
          </>
        ) : normalizedScore >= 80 ? (
          <>
            <AlertCircle className="h-4 w-4 text-amber-500" />
            <span className="text-xs text-amber-400">{statusLabel}</span>
          </>
        ) : (
          <>
            <AlertCircle className="h-4 w-4 text-red-500" />
            <span className="text-xs text-red-400">{statusLabel}</span>
          </>
        )}
      </div>
    </div>
  );
}

/**
 * Vector List: Individual impact factors
 */
function VectorList({ vectors }: { vectors: AuditVector[] }) {
  if (vectors.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
        Decision Vectors
      </div>

      <div className="space-y-1.5 max-h-48 overflow-y-auto">
        {vectors.map((vector, idx) => {
          // Determine severity color
          let severityColor = "bg-slate-800 border-slate-700";
          let impactColor = "text-slate-400";

          if (vector.severity === "HIGH") {
            severityColor = "bg-red-900/30 border-red-700/50";
            impactColor = "text-red-400";
          } else if (vector.severity === "MEDIUM") {
            severityColor = "bg-amber-900/30 border-amber-700/50";
            impactColor = "text-amber-400";
          } else if (vector.severity === "LOW") {
            severityColor = "bg-slate-800 border-slate-700";
            impactColor = "text-slate-400";
          }

          return (
            <motion.div
              key={idx}
              className={`px-3 py-2 rounded border text-xs ${severityColor}`}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.05 }}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex-1">
                  <div className="font-mono text-slate-300">
                    {vector.label}
                  </div>
                  <div className="text-slate-500 text-xs mt-0.5">
                    Value: {vector.value.toFixed(2)} {vector.unit}
                  </div>
                </div>

                <div className={`flex items-center gap-1 font-bold ${impactColor}`}>
                  <TrendingDown className="h-3 w-3" />
                  <span>{vector.impact.toFixed(1)}%</span>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

/**
 * Deduction Breakdown: Shows the financial impact
 */
function DeductionBreakdown({
  deduction,
  currency = "USD",
}: {
  deduction: number;
  currency: string;
}) {
  const isSignificant = deduction > 100; // Flag if deduction is material

  return (
    <motion.div
      className={`px-3 py-3 rounded border ${
        isSignificant
          ? "bg-red-900/20 border-red-700/50"
          : "bg-slate-800/50 border-slate-700/50"
      }`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className={`h-4 w-4 ${isSignificant ? "text-red-400" : "text-amber-400"}`} />
          <span className="text-xs text-slate-400">Deduction Impact</span>
        </div>
        <div className={`text-sm font-bold font-mono ${isSignificant ? "text-red-400" : "text-slate-200"}`}>
          -{deduction.toLocaleString("en-US", { style: "currency", currency })}
        </div>
      </div>
    </motion.div>
  );
}

/**
 * Main Component
 */
export function SmartReconcileCard({
  confidenceScore,
  deduction,
  vectors,
  currency = "USD",
  reconciliationResult,
  onAccept,
  onCancel,
}: SmartReconcileCardProps) {
  const needsAdjustment = confidenceScore < 95;

  return (
    <motion.div
      className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-4 shadow-lg"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide">
          Smart Reconciliation
        </h3>
        <div className="text-xs text-slate-500">ChainAudit Analysis</div>
      </div>

      {/* Tolerance Meter */}
      <ToleranceMeter score={confidenceScore} />

      {/* Deduction Breakdown */}
      <DeductionBreakdown deduction={deduction} currency={currency} />

      {/* Decision Vectors */}
      <VectorList vectors={vectors} />

      {/* Action Buttons */}
      <div className="grid grid-cols-2 gap-2 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-3 py-2 rounded text-xs font-medium border border-slate-700 text-slate-300 hover:bg-slate-800 transition-colors"
        >
          Review
        </button>

        <motion.button
          type="button"
          onClick={() => onAccept?.(needsAdjustment)}
          className={`px-3 py-2 rounded text-xs font-medium font-semibold transition-colors ${
            needsAdjustment
              ? "bg-amber-600 text-white hover:bg-amber-700"
              : "bg-emerald-600 text-white hover:bg-emerald-700"
          }`}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          {needsAdjustment ? "Accept & Pay (Adjusted)" : "Accept & Pay"}
        </motion.button>
      </div>

      {/* Footer: Explanation */}
      {needsAdjustment && (
        <motion.div
          className="text-xs text-amber-400/80 border-l-2 border-amber-700 px-2 py-1"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          {reconciliationResult ? (
            <>
              {reconciliationResult.recommendedAction === "APPROVE" && "Engine recommends APPROVAL. Review fuzzy vectors above for details."}
              {reconciliationResult.recommendedAction === "PARTIAL" && "This payment will be adjusted based on fuzzy logic. Review vectors above for details."}
              {reconciliationResult.recommendedAction === "REJECT" && "Engine flagged concerns. Manual review recommended."}
              {reconciliationResult.recommendedAction === "MANUAL_REVIEW" && "Operator review required before proceeding."}
            </>
          ) : (
            "This payment will be adjusted based on fuzzy logic reconciliation. Review vectors above for details."
          )}
        </motion.div>
      )}
    </motion.div>
  );
}
