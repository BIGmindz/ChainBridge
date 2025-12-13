/**
 * ShadowEventTimeline - Vertical timeline of shadow mode events
 *
 * Cinematic UI with subtle animations.
 * ADHD-friendly: visual chunking, clear temporal flow.
 */

import { Activity, Clock, TrendingDown, TrendingUp } from "lucide-react";

import type { ShadowEvent } from "../../api/shadowMode";
import { classNames } from "../../utils/classNames";
import { Skeleton } from "../ui/Skeleton";

interface ShadowEventTimelineProps {
  events: ShadowEvent[];
  isLoading?: boolean;
  maxItems?: number;
  className?: string;
}

/**
 * Format delta as percentage with color coding.
 */
function formatDelta(delta: number): { text: string; className: string } {
  const pct = (delta * 100).toFixed(1);
  if (delta < 0.1) {
    return { text: `${pct}%`, className: "text-emerald-400" };
  }
  if (delta < 0.2) {
    return { text: `${pct}%`, className: "text-amber-400" };
  }
  return { text: `${pct}%`, className: "text-red-400" };
}

/**
 * Format timestamp as relative time.
 */
function formatRelativeTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

/**
 * Loading skeleton for timeline.
 */
function TimelineSkeleton({ count = 5 }: { count?: number }): JSX.Element {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-start gap-3">
          <Skeleton className="h-8 w-8 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-3 w-32" />
          </div>
          <Skeleton className="h-5 w-12" />
        </div>
      ))}
    </div>
  );
}

export function ShadowEventTimeline({
  events,
  isLoading,
  maxItems = 10,
  className,
}: ShadowEventTimelineProps): JSX.Element {
  if (isLoading) {
    return (
      <div className={classNames("rounded-xl border border-slate-800/70 bg-slate-900/50 p-4", className)}>
        <div className="mb-4 flex items-center gap-2">
          <Activity className="h-4 w-4 text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-200">Event Timeline</h3>
        </div>
        <TimelineSkeleton count={5} />
      </div>
    );
  }

  const displayEvents = events.slice(0, maxItems);

  return (
    <div className={classNames("rounded-xl border border-slate-800/70 bg-slate-900/50 p-4", className)}>
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-200">Event Timeline</h3>
        </div>
        <span className="text-xs text-slate-500">{events.length} total</span>
      </div>

      {/* Timeline */}
      {displayEvents.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Activity className="mb-2 h-8 w-8 text-slate-600" />
          <p className="text-sm text-slate-400">No events yet</p>
          <p className="text-xs text-slate-500">Events will appear as shadow mode executes</p>
        </div>
      ) : (
        <div className="relative space-y-0">
          {/* Vertical line */}
          <div className="absolute left-4 top-0 h-full w-px bg-slate-800" aria-hidden="true" />

          {displayEvents.map((event, idx) => {
            const delta = formatDelta(event.delta);
            const isHighDelta = event.delta > 0.2;

            return (
              <div
                key={event.id}
                className={classNames(
                  "relative flex items-start gap-3 py-2 pl-1",
                  idx === 0 && "animate-fade-in"
                )}
              >
                {/* Timeline dot */}
                <div
                  className={classNames(
                    "relative z-10 flex h-8 w-8 items-center justify-center rounded-full border",
                    isHighDelta
                      ? "border-red-500/50 bg-red-500/10"
                      : "border-slate-700 bg-slate-800"
                  )}
                >
                  {event.delta > event.real_score - event.dummy_score ? (
                    <TrendingUp className={classNames("h-4 w-4", delta.className)} />
                  ) : (
                    <TrendingDown className={classNames("h-4 w-4", delta.className)} />
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-slate-200 truncate">
                      {event.shipment_id}
                    </span>
                    {event.corridor && (
                      <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">
                        {event.corridor}
                      </span>
                    )}
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-[11px] text-slate-500">
                    <Clock className="h-3 w-3" />
                    <span>{formatRelativeTime(event.created_at)}</span>
                    <span className="text-slate-700">•</span>
                    <span>v{event.model_version}</span>
                  </div>
                </div>

                {/* Delta badge */}
                <div className="flex flex-col items-end">
                  <span className={classNames("text-sm font-bold tabular-nums", delta.className)}>
                    Δ {delta.text}
                  </span>
                  <div className="mt-0.5 flex gap-1 text-[10px] text-slate-500">
                    <span>{(event.dummy_score * 100).toFixed(0)}</span>
                    <span>→</span>
                    <span>{(event.real_score * 100).toFixed(0)}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Show more indicator */}
      {events.length > maxItems && (
        <div className="mt-3 border-t border-slate-800/50 pt-3 text-center">
          <span className="text-xs text-slate-500">
            +{events.length - maxItems} more events
          </span>
        </div>
      )}
    </div>
  );
}
