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
 * Confidence Display: Neutral numeric display only
 * No colors. No status labels. No icons.
 */
function ConfidenceDisplay({ score }: { score: number }) {
  // Clamp score to 0-100
  const normalizedScore = Math.max(0, Math.min(100, score));

  return (
    <div className="space-y-2">
      {/* Score Display */}
      <div className="flex items-center justify-between">
        <div className="text-xs font-mono text-slate-500 uppercase tracking-wider">
          confidence_score
        </div>
        <div className="text-lg font-mono text-slate-300">
          {normalizedScore.toFixed(1)}%
        </div>
      </div>

      {/* Neutral meter bar */}
      <div className="relative h-3 overflow-hidden bg-slate-800 border border-slate-700">
        <motion.div
          className="h-full bg-slate-500 origin-left"
          initial={{ scaleX: 0 }}
          animate={{ scaleX: normalizedScore / 100 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          style={{ willChange: "transform" }}
        />
      </div>

      {/* Range Labels */}
      <div className="flex justify-between text-xs text-slate-600 font-mono px-1">
        <span>0%</span>
        <span>100%</span>
      </div>
    </div>
  );
}

/**
 * Vector List: Individual impact factors
 * Neutral display only — no severity colors.
 */
function VectorList({ vectors }: { vectors: AuditVector[] }) {
  if (vectors.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      <div className="text-xs font-mono text-slate-500 uppercase tracking-wider">
        decision_vectors
      </div>

      <div className="space-y-1.5 max-h-48 overflow-y-auto">
        {vectors.map((vector, idx) => {
          return (
            <motion.div
              key={idx}
              className="px-3 py-2 border bg-slate-800 border-slate-700 text-xs"
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.05 }}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex-1">
                  <div className="font-mono text-slate-300">
                    {vector.label}
                  </div>
                  <div className="text-slate-500 text-xs mt-0.5 font-mono">
                    value: {vector.value.toFixed(2)} {vector.unit}
                  </div>
                </div>

                <div className="flex items-center gap-1 font-mono text-slate-400">
                  <span>impact: {vector.impact.toFixed(1)}%</span>
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
 * Neutral display — no semantic colors.
 */
function DeductionBreakdown({
  deduction,
  currency = "USD",
}: {
  deduction: number;
  currency: string;
}) {
  return (
    <motion.div
      className="px-3 py-3 border bg-slate-800/50 border-slate-700/50"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 font-mono">deduction_impact</span>
        </div>
        <div className="text-sm font-mono text-slate-300">
          -{deduction.toLocaleString("en-US", { style: "currency", currency })}
        </div>
      </div>
    </motion.div>
  );
}

/**
 * Main Component
 * Neutralized: no semantic colors, no status icons.
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
      className="bg-slate-900 border border-slate-800 p-4 space-y-4"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <p className="text-xs text-slate-500 font-mono uppercase tracking-wide">
          reconciliation_record
        </p>
        <div className="text-xs text-slate-600 font-mono">ChainAudit</div>
      </div>

      {/* Confidence Display */}
      <ConfidenceDisplay score={confidenceScore} />

      {/* Deduction Breakdown */}
      <DeductionBreakdown deduction={deduction} currency={currency} />

      {/* Decision Vectors */}
      <VectorList vectors={vectors} />

      {/* Action Buttons — neutral styling */}
      <div className="grid grid-cols-2 gap-2 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-3 py-2 text-xs font-mono border border-slate-700 text-slate-400 hover:bg-slate-800 transition-colors"
        >
          Review
        </button>

        <motion.button
          type="button"
          onClick={() => onAccept?.(needsAdjustment)}
          className="px-3 py-2 text-xs font-mono border border-slate-600 text-slate-300 hover:bg-slate-700 transition-colors"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          {needsAdjustment ? "Accept (Adjusted)" : "Accept"}
        </motion.button>
      </div>

      {/* Footer: Record note — no interpretation */}
      {needsAdjustment && (
        <motion.div
          className="text-xs text-slate-500 border-l-2 border-slate-700 px-2 py-1 font-mono"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          {reconciliationResult ? (
            <>
              {reconciliationResult.recommendedAction === "APPROVE" && "recommended_action: APPROVE"}
              {reconciliationResult.recommendedAction === "PARTIAL" && "recommended_action: PARTIAL"}
              {reconciliationResult.recommendedAction === "REJECT" && "recommended_action: REJECT"}
              {reconciliationResult.recommendedAction === "MANUAL_REVIEW" && "recommended_action: MANUAL_REVIEW"}
            </>
          ) : (
            "adjustment_pending: true"
          )}
        </motion.div>
      )}
    </motion.div>
  );
}
