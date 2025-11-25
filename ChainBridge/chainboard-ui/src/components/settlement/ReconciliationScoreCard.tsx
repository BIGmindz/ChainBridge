/**
 * ReconciliationScoreCard
 *
 * Displays payout confidence, final payout amount, and adjustment reason.
 * Color-coded confidence indicator with fallback for non-reconciled intents.
 *
 * Features:
 * - Large payout confidence percentage with color coding
 * - Final payout amount vs. original amount delta display
 * - Adjustment reason display
 * - Loading and error states
 * - "Reconcile Now" action button (optional)
 */

import { Loader2, TrendingDown, TrendingUp } from "lucide-react";
import { useMemo } from "react";

import { useReconcilePaymentIntent } from "../../hooks/useReconciliation";
import type { PaymentIntentListItem } from "../../types/chainbridge";
import { classNames } from "../../utils/classNames";

interface ReconciliationScoreCardProps {
  paymentIntent: PaymentIntentListItem | null;
  originalAmount?: number | null;
  onReconcileSuccess?: () => void;
  showAction?: boolean; // Show "Reconcile Now" button
}

interface ConfidenceLevel {
  color: string;
  bgColor: string;
  label: string;
}

function getConfidenceLevel(score: number): ConfidenceLevel {
  if (score >= 0.95) {
    return {
      color: "text-emerald-300",
      bgColor: "bg-emerald-900/40 border-emerald-700/50",
      label: "Excellent",
    };
  }
  if (score >= 0.8) {
    return {
      color: "text-amber-300",
      bgColor: "bg-amber-900/40 border-amber-700/50",
      label: "Good",
    };
  }
  return {
    color: "text-rose-300",
    bgColor: "bg-rose-900/40 border-rose-700/50",
    label: "Needs Review",
  };
}

export function ReconciliationScoreCard({
  paymentIntent,
  originalAmount,
  onReconcileSuccess,
  showAction = true,
}: ReconciliationScoreCardProps) {
  const {
    mutate: reconcileNow,
    isPending: reconciling,
    isError: reconcileError,
  } = useReconcilePaymentIntent();

  const isReconciled = paymentIntent && paymentIntent.payout_confidence != null;

  const confidenceLevel = useMemo(() => {
    if (!isReconciled || !paymentIntent?.payout_confidence) {
      return getConfidenceLevel(0);
    }
    return getConfidenceLevel(paymentIntent.payout_confidence);
  }, [isReconciled, paymentIntent?.payout_confidence]);

  const amountDelta = useMemo(() => {
    if (!isReconciled || !paymentIntent?.final_payout_amount || !originalAmount || originalAmount === 0) {
      return null;
    }
    const delta = paymentIntent.final_payout_amount - originalAmount;
    const deltaPercent = (delta / originalAmount) * 100;
    return {
      delta,
      deltaPercent,
      isPositive: delta >= 0,
    };
  }, [isReconciled, paymentIntent?.final_payout_amount, originalAmount]);

  const handleReconcile = () => {
    if (!paymentIntent?.id) return;
    reconcileNow(
      {
        paymentIntentId: paymentIntent.id,
        payload: { issues: [], blocked: false },
      },
      {
        onSuccess: () => {
          if (onReconcileSuccess) {
            onReconcileSuccess();
          }
        },
      }
    );
  };

  // No reconciliation yet
  if (!isReconciled) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
        <div className="text-center text-slate-400 text-sm">
          <div className="mb-3">💭</div>
          <p>Not reconciled yet</p>
          {showAction && (
            <button
              type="button"
              onClick={handleReconcile}
              disabled={reconciling}
              className="mt-3 inline-flex items-center justify-center gap-2 rounded-md bg-emerald-600 px-3 py-2 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              {reconciling ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
              Reconcile
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
      {/* Header */}
      <div className={classNames(
        "px-4 py-3 border-b border-slate-800 flex items-center justify-between",
        "bg-slate-800/30"
      )}>
        <h3 className="text-sm font-semibold text-slate-200">Reconciliation Score</h3>
        {reconcileError && (
          <div className="text-xs text-rose-400">Error reconciling</div>
        )}
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Confidence Score */}
        <div>
          <div className="text-xs text-slate-500 uppercase tracking-wide mb-2">Payout Confidence</div>
          <div className={classNames(
            "inline-flex items-center gap-3 rounded-lg border px-4 py-3",
            confidenceLevel.bgColor
          )}>
            <div className={classNames("text-3xl font-bold", confidenceLevel.color)}>
              {(paymentIntent.payout_confidence! * 100).toFixed(1)}%
            </div>
            <div className="flex flex-col justify-center">
              <div className={classNames("text-sm font-semibold", confidenceLevel.color)}>
                {confidenceLevel.label}
              </div>
              <div className="text-xs text-slate-400">
                Final payout amount
              </div>
            </div>
          </div>
        </div>

        {/* Amount Adjustment */}
        {amountDelta && (
          <div>
            <div className="text-xs text-slate-500 uppercase tracking-wide mb-2">Amount Adjustment</div>
            <div className="flex items-center gap-3 rounded-lg bg-slate-800/50 border border-slate-700 px-3 py-2">
              {amountDelta.isPositive ? (
                <TrendingUp className="h-5 w-5 text-emerald-400 flex-shrink-0" />
              ) : (
                <TrendingDown className="h-5 w-5 text-amber-400 flex-shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <div className={classNames(
                  "text-sm font-mono font-semibold",
                  amountDelta.isPositive ? "text-emerald-400" : "text-amber-400"
                )}>
                  {amountDelta.isPositive ? "+" : ""}{amountDelta.delta.toFixed(2)} ({amountDelta.deltaPercent.toFixed(1)}%)
                </div>
                <div className="text-xs text-slate-500">
                  vs. original amount
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Adjustment Reason */}
        {paymentIntent.adjustment_reason && (
          <div>
            <div className="text-xs text-slate-500 uppercase tracking-wide mb-2">
              Adjustment Reason
            </div>
            <div className="rounded-lg border border-slate-700 bg-slate-950/40 p-3">
              <p className="text-sm text-slate-300 leading-relaxed">
                {paymentIntent.adjustment_reason}
              </p>
            </div>
          </div>
        )}

        {/* Reconcile Now Action */}
        {showAction && !reconciling && (
          <button
            type="button"
            onClick={handleReconcile}
            className="w-full rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 transition-colors"
          >
            Re-reconcile
          </button>
        )}

        {reconciling && (
          <div className="flex items-center justify-center py-3 gap-2 text-slate-400">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm">Reconciling...</span>
          </div>
        )}
      </div>
    </div>
  );
}
