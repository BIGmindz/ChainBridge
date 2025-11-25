/**
 * ReconciliationScoreCardCompact
 *
 * Compact inline reconciliation score display for Money View.
 * Shows payout confidence as a small badge with color coding.
 * No action button - intended for read-only display in tables.
 *
 * Features:
 * - Small confidence percentage badge with color coding
 * - Confidence level label as tooltip
 * - Delta display (if present)
 */

import type { PaymentIntentListItem } from "../../types/chainbridge";

interface ReconciliationScoreCardCompactProps {
  paymentIntent: PaymentIntentListItem | null;
}

function getConfidenceColor(score: number): {
  bg: string;
  text: string;
  label: string;
} {
  if (score >= 0.95) {
    return { bg: "bg-emerald-900/40", text: "text-emerald-400", label: "Excellent" };
  }
  if (score >= 0.8) {
    return { bg: "bg-amber-900/40", text: "text-amber-400", label: "Good" };
  }
  return { bg: "bg-rose-900/40", text: "text-rose-400", label: "Needs Review" };
}

export function ReconciliationScoreCardCompact({
  paymentIntent,
}: ReconciliationScoreCardCompactProps) {
  const isReconciled = paymentIntent && paymentIntent.payout_confidence != null;

  if (!isReconciled) {
    return (
      <div className="px-1.5 py-0.5 rounded text-xs border bg-slate-700/50 text-slate-500 border-slate-600">
        Not Reconciled
      </div>
    );
  }

  const colors = getConfidenceColor(paymentIntent.payout_confidence!);

  return (
    <div
      className={`px-2 py-1 rounded text-xs border font-semibold ${colors.bg} ${colors.text} border-current border-opacity-30`}
      title={`${colors.label} confidence - ${(paymentIntent.payout_confidence! * 100).toFixed(1)}%`}
    >
      {(paymentIntent.payout_confidence! * 100).toFixed(0)}%
    </div>
  );
}
