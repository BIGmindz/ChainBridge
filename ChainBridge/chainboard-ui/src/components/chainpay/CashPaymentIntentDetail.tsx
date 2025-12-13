/**
 * CashPaymentIntentDetail
 *
 * Detail panel for selected payment intent in ChainPay Cash View.
 * Shows core intent fields, risk info, proof state, and settlement timeline.
 *
 * Features:
 * - Full payment intent metadata
 * - Status and risk display
 * - Proof attachment indicator
 * - Ready-for-payment explanation
 * - Enterprise settlement timeline with animations
 */

import { useSettlementEvents } from "../../hooks/useSettlementEvents";
import type { PaymentIntentListItem, PaymentIntentStatus } from "../../types/chainbridge";
import { classNames } from "../../utils/classNames";
import { PricingBreakdownCard } from "../settlement/PricingBreakdownCard";
import { ReconciliationScoreCard } from "../settlement/ReconciliationScoreCard";
import { SettlementTimeline } from "../settlement/SettlementTimeline";

interface CashPaymentIntentDetailProps {
  intent: PaymentIntentListItem | null;
}

const STATUS_COLORS: Record<PaymentIntentStatus, string> = {
  READY_FOR_PAYMENT: "bg-emerald-500/20 text-emerald-400 border-emerald-500/50",
  AWAITING_PROOF: "bg-amber-500/20 text-amber-400 border-amber-500/50",
  BLOCKED_BY_RISK: "bg-red-500/20 text-red-400 border-red-500/50",
  PENDING: "bg-slate-500/20 text-slate-400 border-slate-500/50",
  CANCELLED: "bg-slate-600/20 text-slate-500 border-slate-600/50",
};

const STATUS_LABELS: Record<PaymentIntentStatus, string> = {
  READY_FOR_PAYMENT: "Ready for Payment",
  AWAITING_PROOF: "Awaiting Proof",
  BLOCKED_BY_RISK: "Blocked by Risk",
  PENDING: "Pending",
  CANCELLED: "Cancelled",
};

const STATUS_EXPLANATIONS: Record<PaymentIntentStatus, string> = {
  READY_FOR_PAYMENT: "All conditions met. Payment can be initiated.",
  AWAITING_PROOF: "Waiting for proof of delivery or settlement documentation.",
  BLOCKED_BY_RISK: "Risk score too high. Requires manual review before payment.",
  PENDING: "Intent created, pending risk assessment.",
  CANCELLED: "Payment intent has been cancelled.",
};

export function CashPaymentIntentDetail({ intent }: CashPaymentIntentDetailProps) {
  // Fetch settlement events for the selected intent
  const { data: events, isLoading: eventsLoading, isError: eventsError } = useSettlementEvents(intent?.id);

  if (!intent) {
    return (
      <div className="p-8 text-center text-slate-500">
        <div className="text-4xl mb-3">💰</div>
        <p className="text-sm">Select a payment intent to view details</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-700 bg-slate-800/50">
        <h3 className="text-sm font-semibold text-slate-200">Payment Intent Detail</h3>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Shipment Info */}
        <div>
          <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">Shipment</div>
          <div className="font-mono text-sm text-slate-200 font-semibold">{intent.shipmentId}</div>
        </div>

        {/* Corridor & Mode */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">Corridor</div>
            <div className="text-sm text-slate-300">
              {intent.corridor_code || <span className="text-slate-600">—</span>}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">Mode</div>
            <div className="text-sm text-slate-300 uppercase">
              {intent.mode ? intent.mode.replace(/_/g, " ") : <span className="text-slate-600">—</span>}
            </div>
          </div>
        </div>

        {/* Incoterm */}
        {intent.incoterm && (
          <div>
            <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">Incoterm</div>
            <div className="text-sm text-slate-300 uppercase">{intent.incoterm}</div>
          </div>
        )}

        {/* Status */}
        <div>
          <div className="text-xs text-slate-500 uppercase tracking-wide mb-2">Status</div>
          <div className={classNames(
            "inline-flex px-3 py-1.5 rounded text-sm border font-medium",
            STATUS_COLORS[intent.status]
          )}>
            {STATUS_LABELS[intent.status]}
          </div>
          <div className="text-xs text-slate-400 mt-2 leading-relaxed">
            {STATUS_EXPLANATIONS[intent.status]}
          </div>
        </div>

        {/* Pricing Breakdown */}
        {intent.pricing && (
          <div>
            <div className="text-xs text-slate-500 uppercase tracking-wide mb-2">Pricing Breakdown</div>
            <PricingBreakdownCard
              pricing={intent.pricing}
              isLoading={false}
              compact={true}
            />
          </div>
        )}

        {/* Reconciliation Score */}
        <div>
          <div className="text-xs text-slate-500 uppercase tracking-wide mb-2">Reconciliation</div>
          <ReconciliationScoreCard
            paymentIntent={intent}
            originalAmount={intent.pricing?.total_price}
            showAction={true}
          />
        </div>

        {/* Proof State */}
        <div>
          <div className="text-xs text-slate-500 uppercase tracking-wide mb-2">Proof Attached</div>
          <div className="flex items-center gap-2">
            {intent.has_proof ? (
              <>
                <div className="w-2 h-2 bg-emerald-400 rounded-full" />
                <span className="text-sm text-emerald-400 font-medium">Yes</span>
              </>
            ) : (
              <>
                <div className="w-2 h-2 bg-slate-600 rounded-full" />
                <span className="text-sm text-slate-500">No</span>
              </>
            )}
          </div>
        </div>

        {/* Risk Info */}
        {intent.risk_level && intent.riskScore !== null && (
          <div>
            <div className="text-xs text-slate-500 uppercase tracking-wide mb-2">Risk Assessment</div>
            <div className="flex items-center gap-3">
              <span className={classNames(
                "text-sm font-medium",
                intent.risk_level === "HIGH" || intent.risk_level === "CRITICAL"
                  ? "text-red-400"
                  : intent.risk_level === "MEDIUM"
                  ? "text-amber-400"
                  : "text-emerald-400"
              )}>
                {intent.risk_level}
              </span>
              <span className="text-slate-600">·</span>
              <span className="text-sm text-slate-400">Score: {intent.riskScore}/100</span>
            </div>
          </div>
        )}

        {/* Ready for Payment */}
        <div>
          <div className="text-xs text-slate-500 uppercase tracking-wide mb-2">Ready for Payment</div>
          <div className="flex items-center gap-2">
            {intent.ready_for_payment ? (
              <>
                <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                <span className="text-sm text-emerald-400 font-medium">Ready</span>
              </>
            ) : (
              <>
                <div className="w-2 h-2 bg-slate-600 rounded-full" />
                <span className="text-sm text-slate-500">Not Ready</span>
              </>
            )}
          </div>
        </div>

        {/* Timestamps */}
        <div className="border-t border-slate-800 pt-4 space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-slate-500">Created:</span>
            <span className="text-slate-400">
              {new Date(intent.createdAt).toLocaleString()}
            </span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-slate-500">Updated:</span>
            <span className="text-slate-400">
              {new Date(intent.updatedAt).toLocaleString()}
            </span>
          </div>
        </div>

        {/* Settlement Timeline */}
        <div className="border-t border-slate-800 pt-4">
          <div className="text-xs text-slate-500 uppercase tracking-wide mb-3">Settlement Timeline</div>
          <SettlementTimeline
            events={events ?? []}
            isLoading={eventsLoading}
            isError={eventsError}
            compact={false}
            autoExpand={true}
          />
        </div>
      </div>
    </div>
  );
}
