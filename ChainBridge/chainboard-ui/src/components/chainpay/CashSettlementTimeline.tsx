/**
 * CashSettlementTimeline
 *
 * Vertical timeline component for displaying settlement events.
 * Used in ChainPay Cash View to show payment intent lifecycle progression.
 *
 * Features:
 * - Vertical timeline with status-colored dots
 * - Event type labels with status chips
 * - Amount and currency display
 * - Formatted timestamps
 * - Empty state for intents with no events
 */

import type { SettlementEvent } from "../../types/chainbridge";
import { classNames } from "../../utils/classNames";

interface CashSettlementTimelineProps {
  events: SettlementEvent[];
}

const STATUS_COLORS = {
  SUCCESS: "bg-emerald-500",
  FAILED: "bg-rose-500",
  PENDING: "bg-amber-500",
};

const EVENT_TYPE_LABELS = {
  CREATED: "Created",
  AUTHORIZED: "Authorized",
  CAPTURED: "Captured",
  FAILED: "Failed",
  REFUNDED: "Refunded",
};

export function CashSettlementTimeline({ events }: CashSettlementTimelineProps) {
  if (events.length === 0) {
    return (
      <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6 text-center">
        <div className="text-slate-500 text-sm mb-1">No settlement events yet</div>
        <div className="text-xs text-slate-600 leading-relaxed">
          This PaymentIntent has not moved through the cash pipeline.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-0">
      {events.map((event, index) => {
        const isLast = index === events.length - 1;

        return (
          <div key={event.id} className="relative flex gap-4">
            {/* Timeline Line & Dot */}
            <div className="relative flex flex-col items-center">
              {/* Dot */}
              <div className={classNames(
                "w-3 h-3 rounded-full border-2 border-slate-900 z-10",
                STATUS_COLORS[event.status]
              )} />

              {/* Vertical Line */}
              {!isLast && (
                <div className="w-px flex-1 bg-slate-700 mt-1 min-h-12" />
              )}
            </div>

            {/* Event Content */}
            <div className={classNames(
              "flex-1",
              isLast ? "pb-0" : "pb-6"
            )}>
              {/* Event Type & Status */}
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-medium text-slate-200">
                  {EVENT_TYPE_LABELS[event.eventType]}
                </span>
                <span className={classNames(
                  "px-2 py-0.5 rounded text-xs font-medium",
                  event.status === "SUCCESS"
                    ? "bg-emerald-500/20 text-emerald-400"
                    : event.status === "FAILED"
                    ? "bg-rose-500/20 text-rose-400"
                    : "bg-amber-500/20 text-amber-400"
                )}>
                  {event.status}
                </span>
              </div>

              {/* Amount */}
              <div className="text-sm text-slate-400 mb-1">
                {event.currency} {event.amount.toLocaleString("en-US", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </div>

              {/* Timestamp */}
              <div className="text-xs text-slate-500">
                {new Date(event.occurredAt).toLocaleString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                  hour: "numeric",
                  minute: "2-digit",
                  hour12: true,
                })}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
