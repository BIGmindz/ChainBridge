/**
 * ShadowIntelligencePanel - Main Shadow Mode Intelligence Component
 *
 * Wires to Cody's /iq/shadow/* endpoints.
 * Cinematic UI with WCAG AA compliance and ADHD-friendly flow.
 *
 * p95 < 70ms UI render after hydration via React Query caching.
 */

import { AlertTriangle, RefreshCw, Zap } from "lucide-react";
import { useState } from "react";

import { classNames } from "../../utils/classNames";
import { useShadowIntelligence, useShadowEvents } from "../../hooks/useShadowMode";
import { Skeleton } from "../ui/Skeleton";

import { CorridorSelector } from "./CorridorSelector";
import { DriftSignalBadge } from "./DriftSignalBadge";
import { ShadowEventTimeline } from "./ShadowEventTimeline";
import { ShadowKPICards } from "./ShadowKPICards";

interface ShadowIntelligencePanelProps {
  className?: string;
  compact?: boolean;
}

/**
 * Panel-level loading skeleton.
 */
function PanelSkeleton(): JSX.Element {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Skeleton className="h-6 w-6 rounded" />
          <Skeleton className="h-6 w-40" />
        </div>
        <Skeleton className="h-8 w-24 rounded-full" />
      </div>
      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Skeleton className="h-32 rounded-xl" />
        <Skeleton className="h-32 rounded-xl" />
        <Skeleton className="h-32 rounded-xl" />
      </div>
      {/* Corridor + Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Skeleton className="h-48 rounded-xl" />
        <Skeleton className="h-48 rounded-xl" />
      </div>
    </div>
  );
}

export function ShadowIntelligencePanel({
  className,
  compact = false,
}: ShadowIntelligencePanelProps): JSX.Element {
  const [selectedCorridor, setSelectedCorridor] = useState<string | null>(null);
  const [timeWindow] = useState(24); // hours

  // Fetch intelligence data
  const { stats, drift, corridors, isLoading, isError, error } = useShadowIntelligence(timeWindow);

  // Fetch events with corridor filter
  const eventsQuery = useShadowEvents(50, selectedCorridor ?? undefined, timeWindow);

  // Handle refresh
  const handleRefresh = () => {
    stats.refetch();
    drift.refetch();
    corridors.refetch();
    eventsQuery.refetch();
  };

  // Error state
  if (isError) {
    return (
      <div className={classNames("rounded-2xl border border-red-500/30 bg-red-500/5 p-6", className)}>
        <div className="flex items-start gap-4">
          <AlertTriangle className="h-6 w-6 text-red-400 flex-shrink-0" />
          <div className="flex-1">
            <h3 className="text-base font-semibold text-red-400">Shadow Intelligence Unavailable</h3>
            <p className="mt-1 text-sm text-slate-400">
              {error?.message || "Failed to connect to ChainIQ shadow endpoints."}
            </p>
            <button
              onClick={handleRefresh}
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-slate-800 px-3 py-1.5 text-sm text-slate-200 hover:bg-slate-700 transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className={classNames("rounded-2xl border border-slate-800/70 bg-slate-900/50 p-6", className)}>
        <PanelSkeleton />
      </div>
    );
  }

  // Prepare corridor options for selector
  const corridorOptions = corridors.data?.corridors.map((c) => ({
    corridor: c.corridor,
    eventCount: c.event_count,
    driftFlag: c.drift_flag,
    p95Delta: c.p95_delta,
  })) ?? [];

  return (
    <div className={classNames("rounded-2xl border border-slate-800/70 bg-slate-900/50", className)}>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800/50 px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/10">
            <Zap className="h-5 w-5 text-indigo-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-100">Shadow Intelligence</h2>
            <p className="text-xs text-slate-500">Model comparison & drift detection</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {drift.data && (
            <DriftSignalBadge
              driftDetected={drift.data.drift_detected}
              p95Delta={drift.data.p95_delta}
              size="md"
            />
          )}
          <button
            onClick={handleRefresh}
            disabled={stats.isFetching}
            className={classNames(
              "rounded-lg border border-slate-700/50 bg-slate-800/50 p-2 text-slate-400 transition-all",
              "hover:bg-slate-700/70 hover:text-slate-200",
              stats.isFetching && "animate-spin"
            )}
            aria-label="Refresh data"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Body */}
      <div className={classNames("space-y-6 p-6", compact && "space-y-4 p-4")}>
        {/* KPI Cards */}
        <ShadowKPICards
          stats={stats.data ?? null}
          isLoading={stats.isLoading}
        />

        {/* Corridor Selector + Timeline Grid */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Left: Corridor Analysis */}
          <div className="space-y-4">
            <CorridorSelector
              corridors={corridorOptions}
              selectedCorridor={selectedCorridor}
              onSelect={setSelectedCorridor}
              isLoading={corridors.isLoading}
            />

            {/* Corridor summary */}
            {corridors.data && (
              <div className="rounded-xl border border-slate-800/50 bg-slate-950/50 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Corridor Analysis
                  </span>
                  {corridors.data.drifting_count > 0 && (
                    <span className="rounded bg-red-500/20 px-2 py-0.5 text-[10px] font-bold text-red-400">
                      {corridors.data.drifting_count} DRIFTING
                    </span>
                  )}
                </div>
                <div className="mt-3 grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-2xl font-bold text-slate-100">
                      {corridors.data.total_corridors}
                    </span>
                    <p className="text-xs text-slate-500">Active Corridors</p>
                  </div>
                  <div>
                    <span className="text-2xl font-bold text-emerald-400">
                      {corridors.data.total_corridors - corridors.data.drifting_count}
                    </span>
                    <p className="text-xs text-slate-500">Healthy</p>
                  </div>
                </div>

                {/* Corridor list preview */}
                <div className="mt-4 space-y-2 max-h-40 overflow-y-auto">
                  {corridors.data.corridors.slice(0, 5).map((c) => (
                    <div
                      key={c.corridor}
                      className="flex items-center justify-between rounded-lg bg-slate-800/30 px-3 py-2 text-xs"
                    >
                      <span className="text-slate-300">{c.corridor}</span>
                      <div className="flex items-center gap-2">
                        <span
                          className={classNames(
                            "font-mono",
                            c.drift_flag ? "text-red-400" : "text-slate-500"
                          )}
                        >
                          P95: {(c.p95_delta * 100).toFixed(1)}%
                        </span>
                        {c.drift_flag && (
                          <span className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right: Event Timeline */}
          <ShadowEventTimeline
            events={eventsQuery.data?.events ?? []}
            isLoading={eventsQuery.isLoading}
            maxItems={compact ? 5 : 10}
          />
        </div>
      </div>
    </div>
  );
}

export default ShadowIntelligencePanel;
