/**
 * CashPaymentIntentsTable
 *
 * Table displaying payment intents for ChainPay Cash View.
 * Emphasizes ready-for-payment items with visual hierarchy.
 *
 * Features:
 * - Color-coded status badges
 * - Proof indicators
 * - Risk level display
 * - Row selection support
 * - Ready-for-payment highlighting
 */

import { AlertTriangle } from "lucide-react";

import type { PaymentIntentListItem, PaymentIntentStatus } from "../../types/chainbridge";
import { classNames } from "../../utils/classNames";
import { Skeleton } from "../ui/Skeleton";

interface CashPaymentIntentsTableProps {
  items: PaymentIntentListItem[];
  selectedId?: string;
  selectedIndex?: number;
  isLoading: boolean;
  error?: Error | null;
  onSelect: (id: string) => void;
}

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

export function CashPaymentIntentsTable({
  items,
  selectedId,
  selectedIndex,
  isLoading,
  error,
  onSelect,
}: CashPaymentIntentsTableProps) {
  if (error) {
    return (
      <div className="p-8 text-center text-red-400">
        <AlertTriangle className="h-12 w-12 mx-auto mb-3" />
        <p className="font-medium mb-1">Failed to load payment intents</p>
        <p className="text-xs text-slate-400">{error.message}</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-4 space-y-3">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-20" />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="p-12 text-center text-slate-400">
        <div className="text-4xl mb-3">💰</div>
        <p className="font-medium mb-1">No payment intents found</p>
        <p className="text-xs text-slate-500">Try adjusting filters or check back later</p>
      </div>
    );
  }

  return (
    <div className="overflow-y-auto">
      {/* Table Header */}
      <div className="sticky top-0 bg-slate-800/95 backdrop-blur-sm border-b border-slate-700 px-4 py-2 grid grid-cols-[2fr_1fr_1fr_1.5fr_1fr_1fr] gap-4 text-xs font-medium text-slate-400">
        <div>Shipment</div>
        <div>Corridor</div>
        <div>Mode</div>
        <div>Status</div>
        <div>Proof</div>
        <div>Risk</div>
      </div>

      {/* Table Body */}
      <div className="divide-y divide-slate-800" role="list">
        {items.map((intent, index) => {
          const isSelected = selectedId === intent.id;
          const isKeyboardFocused = selectedIndex === index;
          const isReady = intent.ready_for_payment;

          return (
            <div
              key={intent.id}
              data-id={intent.id}
              onClick={() => onSelect(intent.id)}
              className={classNames(
                "px-4 py-3 grid grid-cols-[2fr_1fr_1fr_1.5fr_1fr_1fr] gap-4 cursor-pointer transition-all border-l-4",
                isSelected && isKeyboardFocused
                  ? "bg-slate-700 border-emerald-400 ring-2 ring-emerald-500/50"
                  : isSelected
                  ? "bg-slate-700 border-blue-500"
                  : isReady
                  ? "bg-slate-800/70 border-emerald-600/30 hover:bg-slate-700/70 hover:border-emerald-500/50"
                  : "bg-slate-900/50 border-slate-700 hover:bg-slate-800/50"
              )}
              role="listitem"
              aria-current={isSelected ? "true" : undefined}
            >
              {/* Shipment ID */}
              <div className="flex flex-col justify-center">
                <div className="font-mono text-xs font-semibold text-slate-200 truncate">
                  {intent.shipmentId}
                </div>
                {isReady && (
                  <div className="text-[10px] text-emerald-400 mt-0.5">
                    ✓ Ready for payment
                  </div>
                )}
              </div>

              {/* Corridor */}
              <div className="flex items-center">
                {intent.corridor_code ? (
                  <span className="text-xs px-2 py-0.5 bg-slate-800 rounded text-slate-300">
                    {intent.corridor_code}
                  </span>
                ) : (
                  <span className="text-xs text-slate-600">—</span>
                )}
              </div>

              {/* Mode */}
              <div className="flex items-center">
                {intent.mode ? (
                  <span className="text-xs text-slate-300 uppercase">
                    {intent.mode.replace(/_/g, " ")}
                  </span>
                ) : (
                  <span className="text-xs text-slate-600">—</span>
                )}
              </div>

              {/* Status */}
              <div className="flex items-center">
                <div
                  className={classNames(
                    "px-2 py-1 rounded text-xs border font-medium",
                    STATUS_COLORS[intent.status]
                  )}
                >
                  {STATUS_LABELS[intent.status]}
                </div>
              </div>

              {/* Proof */}
              <div className="flex items-center">
                {intent.has_proof ? (
                  <div className="text-xs text-emerald-400 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                    Yes
                  </div>
                ) : (
                  <div className="text-xs text-slate-500 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 bg-slate-600 rounded-full" />
                    No
                  </div>
                )}
              </div>

              {/* Risk */}
              <div className="flex items-center">
                {intent.risk_level && intent.riskScore !== null ? (
                  <div className="text-xs flex items-center gap-1.5">
                    <span
                      className={classNames(
                        "font-medium",
                        intent.risk_level === "HIGH" || intent.risk_level === "CRITICAL"
                          ? "text-red-400"
                          : intent.risk_level === "MEDIUM"
                          ? "text-amber-400"
                          : "text-emerald-400"
                      )}
                    >
                      {intent.risk_level}
                    </span>
                    <span className="text-slate-500">·</span>
                    <span className="text-slate-400">{intent.riskScore}</span>
                  </div>
                ) : (
                  <span className="text-xs text-slate-600">—</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
