/**
 * MoneyViewPanel
 *
 * Money View component for Operator Console - displays payment intent status.
 * Shows operators what can be paid vs what's blocked by missing proof or risk.
 *
 * Features:
 * - KPI strip with ready/awaiting/blocked counts
 * - Compact table with shipment → payment mapping
 * - Color-coded status badges
 * - Proof attachment indicators
 * - Auto-polling sync with operator queue
 * - Link to ChainPay Cash View for deep-dive analysis
 */

import { Link } from "react-router-dom";

import { buildDeepLink } from "../../hooks/useDeepLink";
import { usePaymentIntentSummary, usePaymentIntents } from "../../hooks/usePaymentIntents";
import type { PaymentIntentListItem, PaymentIntentStatus } from "../../types/chainbridge";
import { ReconciliationScoreCardCompact } from "../settlement/ReconciliationScoreCardCompact";

// Status badge color mapping
const STATUS_COLORS: Record<PaymentIntentStatus, string> = {
  READY_FOR_PAYMENT: "bg-emerald-500/20 text-emerald-400 border-emerald-500/50",
  AWAITING_PROOF: "bg-amber-500/20 text-amber-400 border-amber-500/50",
  BLOCKED_BY_RISK: "bg-red-500/20 text-red-400 border-red-500/50",
  PENDING: "bg-slate-500/20 text-slate-400 border-slate-500/50",
  CANCELLED: "bg-slate-600/20 text-slate-500 border-slate-600/50",
};

const STATUS_LABELS: Record<PaymentIntentStatus, string> = {
  READY_FOR_PAYMENT: "Ready",
  AWAITING_PROOF: "Needs Proof",
  BLOCKED_BY_RISK: "Blocked",
  PENDING: "Pending",
  CANCELLED: "Cancelled",
};

interface MoneyViewPanelProps {
  className?: string;
}

export function MoneyViewPanel({ className = "" }: MoneyViewPanelProps) {
  // Fetch summary KPIs
  const { data: summary, isLoading: summaryLoading } = usePaymentIntentSummary();

  // Fetch payment intents - default to showing ready_for_payment items
  const {
    data: intents = [],
    isLoading: intentsLoading,
    error: intentsError,
  } = usePaymentIntents({ ready_for_payment: true });

  const isLoading = summaryLoading || intentsLoading;

  return (
    <div className={`flex flex-col ${className}`}>
      {/* Header + KPI Strip */}
      <div className="px-4 py-3 border-b border-slate-700 bg-slate-800/50">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-slate-200">
            💰 Money View – Payment Intents
          </h3>

          {/* ChainPay Deep-Dive Link */}
          <Link
            to="/chainpay"
            className="text-xs text-emerald-400 hover:text-emerald-300 transition-colors flex items-center gap-1"
          >
            Open Cash View →
          </Link>
        </div>

        {isLoading ? (
          <div className="text-xs text-slate-400">Loading payment data...</div>
        ) : summary ? (
          <div className="flex gap-4 text-xs">
            <div className="flex items-center gap-1.5">
              <span className="text-emerald-400 font-medium">{summary.ready_for_payment}</span>
              <span className="text-slate-400">Ready</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-amber-400 font-medium">{summary.awaiting_proof}</span>
              <span className="text-slate-400">Awaiting Proof</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-red-400 font-medium">{summary.blocked_by_risk}</span>
              <span className="text-slate-400">Blocked</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-slate-300 font-medium">{summary.total}</span>
              <span className="text-slate-400">Total</span>
            </div>
          </div>
        ) : null}
      </div>

      {/* Payment Intents Table */}
      <div className="flex-1 overflow-y-auto">
        {intentsError ? (
          <div className="p-4 text-center text-red-400 text-sm">
            Failed to load payment intents
          </div>
        ) : intentsLoading ? (
          <div className="p-4 text-center text-slate-400 text-sm">
            Loading payment intents...
          </div>
        ) : intents.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-sm">
            <div className="mb-2">No payment intents ready</div>
            <div className="text-xs">All shipments either paid or awaiting proof</div>
          </div>
        ) : (
          <div className="divide-y divide-slate-800">
            {intents.map((intent) => (
              <PaymentIntentRow key={intent.id} intent={intent} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface PaymentIntentRowProps {
  intent: PaymentIntentListItem;
}

function PaymentIntentRow({ intent }: PaymentIntentRowProps) {
  const statusColor = STATUS_COLORS[intent.status];
  const statusLabel = STATUS_LABELS[intent.status];

  // Build deep link to ChainPay with this specific intent selected
  const deepLinkUrl = buildDeepLink("/chainpay", {
    intent: intent.id,
    highlight: intent.ready_for_payment ? "ready" : undefined,
  });

  return (
    <Link to={deepLinkUrl} className="block p-3 hover:bg-slate-800/50 transition-colors">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <div className="font-mono text-xs text-slate-300 mb-1 truncate">
            {intent.shipmentId}
          </div>
          <div className="text-xs text-slate-500 flex items-center gap-2">
            {intent.corridor_code && (
              <span className="px-1.5 py-0.5 bg-slate-800 rounded text-slate-400">
                {intent.corridor_code}
              </span>
            )}
            {intent.mode && (
              <span className="text-slate-600">·</span>
            )}
            {intent.mode && (
              <span className="uppercase">{intent.mode}</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Reconciliation Score (if present) */}
          {intent.payout_confidence !== undefined && intent.payout_confidence !== null && (
            <ReconciliationScoreCardCompact paymentIntent={intent} />
          )}

          {/* Proof Badge */}
          {intent.has_proof ? (
            <div
              className="px-2 py-1 rounded text-xs border bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
              title="Proof attached"
            >
              ✓ Proof
            </div>
          ) : (
            <div
              className="px-2 py-1 rounded text-xs border bg-slate-700/50 text-slate-500 border-slate-600"
              title="No proof attached"
            >
              No Proof
            </div>
          )}

          {/* Status Badge */}
          <div
            className={`px-2 py-1 rounded text-xs border ${statusColor}`}
          >
            {statusLabel}
          </div>
        </div>
      </div>

      {/* Risk Info (if present) */}
      {intent.risk_level && intent.riskScore !== null && (
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-500">Risk:</span>
          <span
            className={`font-medium ${
              intent.risk_level === "HIGH" || intent.risk_level === "CRITICAL"
                ? "text-red-400"
                : intent.risk_level === "MEDIUM"
                ? "text-amber-400"
                : "text-emerald-400"
            }`}
          >
            {intent.risk_level}
          </span>
          <span className="text-slate-600">·</span>
          <span className="text-slate-400">{intent.riskScore}/100</span>
        </div>
      )}
    </Link>
  );
}
