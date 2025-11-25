/**
 * SettlementTimeline (Enterprise Edition)
 *
 * Full-featured settlement event timeline for operator intelligence.
 * Replaces all timeline stubs across OC and ChainPay with unified component.
 *
 * Features:
 * - Vertical timeline with status-colored iconography
 * - Absolute + relative timestamps
 * - Collapse/expand event groups
 * - Animated transitions
 * - Error state visualization (FAILED events pulse)
 * - Hover details with metadata popover
 * - Keyboard navigation support
 * - Empty/loading/error states
 */

import { useState } from "react";

import type { SettlementEvent } from "../../types/chainbridge";
import { classNames } from "../../utils/classNames";

interface SettlementTimelineProps {
  events: SettlementEvent[];
  isLoading?: boolean;
  isError?: boolean;
  compact?: boolean; // Compact mode for embedded views (OC Money View)
  autoExpand?: boolean; // Auto-expand all groups on load
}

const STATUS_COLORS = {
  SUCCESS: {
    dot: "bg-emerald-500 border-emerald-400",
    text: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/30",
  },
  FAILED: {
    dot: "bg-rose-500 border-rose-400 animate-pulse",
    text: "text-rose-400",
    bg: "bg-rose-500/10",
    border: "border-rose-500/30",
  },
  PENDING: {
    dot: "bg-amber-500 border-amber-400",
    text: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
  },
};

const EVENT_TYPE_LABELS = {
  CREATED: "Payment Intent Created",
  AUTHORIZED: "Authorization Approved",
  CAPTURED: "Funds Captured",
  FAILED: "Payment Failed",
  REFUNDED: "Refund Processed",
};

const EVENT_TYPE_ICONS = {
  CREATED: "📝",
  AUTHORIZED: "✓",
  CAPTURED: "💰",
  FAILED: "⚠️",
  REFUNDED: "↩️",
};

export function SettlementTimeline({
  events,
  isLoading = false,
  isError = false,
  compact = false,
  autoExpand = true,
}: SettlementTimelineProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    autoExpand ? new Set(events.map((e) => e.eventType)) : new Set()
  );

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-3 animate-pulse">
        <div className="h-20 bg-slate-800/50 rounded-lg" />
        <div className="h-20 bg-slate-800/50 rounded-lg" />
        <div className="h-16 bg-slate-800/50 rounded-lg" />
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg p-4 text-center">
        <div className="text-rose-400 text-sm font-medium mb-1">
          ⚠️ Failed to load settlement events
        </div>
        <div className="text-xs text-rose-400/70">Please check your connection and try again</div>
      </div>
    );
  }

  // Empty state
  if (events.length === 0) {
    return (
      <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6 text-center">
        <div className="text-4xl mb-2">💸</div>
        <div className="text-slate-500 text-sm mb-1">No settlement events yet</div>
        <div className="text-xs text-slate-600 leading-relaxed">
          This payment intent hasn&apos;t moved through the settlement pipeline.
        </div>
      </div>
    );
  }

  // Group events by type for collapse/expand
  const groupedEvents = events.reduce(
    (acc, event) => {
      if (!acc[event.eventType]) {
        acc[event.eventType] = [];
      }
      acc[event.eventType].push(event);
      return acc;
    },
    {} as Record<string, SettlementEvent[]>
  );

  const toggleGroup = (eventType: string) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(eventType)) {
      newExpanded.delete(eventType);
    } else {
      newExpanded.add(eventType);
    }
    setExpandedGroups(newExpanded);
  };

  return (
    <div className={classNames("space-y-0", compact && "text-xs")}>
      {events.map((event, index) => {
        const isLast = index === events.length - 1;
        const isExpanded = expandedGroups.has(event.eventType);
        const statusStyle = STATUS_COLORS[event.status];
        const relativeTime = getRelativeTime(event.occurredAt);

        return (
          <div key={event.id} className="relative flex gap-3">
            {/* Timeline Line & Dot */}
            <div className="relative flex flex-col items-center">
              {/* Dot with icon */}
              <div
                className={classNames(
                  "relative flex items-center justify-center w-8 h-8 rounded-full border-2 border-slate-900 z-10 transition-all duration-200",
                  statusStyle.dot,
                  !compact && "hover:scale-110"
                )}
                title={`${event.status} - ${EVENT_TYPE_LABELS[event.eventType]}`}
              >
                <span className="text-xs">{EVENT_TYPE_ICONS[event.eventType]}</span>
              </div>

              {/* Vertical Line */}
              {!isLast && <div className="w-px flex-1 bg-slate-700 mt-1 min-h-12" />}
            </div>

            {/* Event Content */}
            <div
              className={classNames("flex-1 pb-6 transition-all duration-200", isLast && "pb-0")}
            >
              {/* Event Header */}
              <button
                onClick={() => !compact && toggleGroup(event.eventType)}
                className={classNames(
                  "w-full text-left group",
                  !compact && "cursor-pointer hover:opacity-80"
                )}
              >
                <div className="flex items-start justify-between gap-2 mb-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={classNames(
                        "font-medium",
                        statusStyle.text,
                        compact ? "text-xs" : "text-sm"
                      )}
                    >
                      {EVENT_TYPE_LABELS[event.eventType]}
                    </span>
                    {!compact && groupedEvents[event.eventType].length > 1 && (
                      <span className="text-xs text-slate-500">
                        ({groupedEvents[event.eventType].length})
                      </span>
                    )}
                  </div>

                  {/* Status Badge */}
                  <span
                    className={classNames(
                      "px-2 py-0.5 rounded text-xs font-medium border",
                      statusStyle.bg,
                      statusStyle.text,
                      statusStyle.border
                    )}
                  >
                    {event.status}
                  </span>
                </div>
              </button>

              {/* Event Details (expandable) */}
              <div
                className={classNames(
                  "overflow-hidden transition-all duration-200",
                  isExpanded || compact ? "max-h-96 opacity-100" : "max-h-0 opacity-0"
                )}
              >
                {/* Amount */}
                <div
                  className={classNames(
                    "font-mono mb-1",
                    compact ? "text-xs" : "text-sm",
                    statusStyle.text
                  )}
                >
                  {event.currency}{" "}
                  {event.amount.toLocaleString("en-US", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </div>

                {/* Timestamps */}
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    <span className="text-slate-500">Occurred:</span>
                    <span>
                      {new Date(event.occurredAt).toLocaleString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                        hour: "numeric",
                        minute: "2-digit",
                        hour12: true,
                      })}
                    </span>
                    <span className="text-slate-600">({relativeTime})</span>
                  </div>
                </div>

                {/* Metadata (if present) */}
                {event.metadata && Object.keys(event.metadata).length > 0 && !compact && (
                  <details className="mt-2 group/details">
                    <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-400 transition-colors">
                      View metadata →
                    </summary>
                    <div className="mt-2 bg-slate-900/50 border border-slate-800 rounded p-2">
                      <pre className="text-xs text-slate-400 font-mono overflow-x-auto">
                        {JSON.stringify(event.metadata, null, 2)}
                      </pre>
                    </div>
                  </details>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/**
 * Get relative time string (e.g., "2 hours ago", "just now")
 */
function getRelativeTime(timestamp: string): string {
  const now = new Date();
  const past = new Date(timestamp);
  const diffMs = now.getTime() - past.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 30) return `${diffDay}d ago`;
  return `${Math.floor(diffDay / 30)}mo ago`;
}
