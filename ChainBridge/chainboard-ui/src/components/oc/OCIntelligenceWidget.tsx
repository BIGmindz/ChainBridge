/**
 * OCIntelligenceWidget - Compact Intelligence Widget for Operator Console
 *
 * Shows Shadow Mode drift status in the OC right panel.
 * Integrates with Cody's /iq/shadow/* endpoints.
 */

import { AlertTriangle, Zap } from "lucide-react";

import { classNames } from "../../utils/classNames";
import { useShadowStats, useShadowDrift } from "../../hooks/useShadowMode";
import { DriftSignalBadge, DriftDot } from "../intel/DriftSignalBadge";
import { Skeleton } from "../ui/Skeleton";

interface OCIntelligenceWidgetProps {
  className?: string;
}

/**
 * Widget skeleton for loading state.
 */
function WidgetSkeleton(): JSX.Element {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <Skeleton className="h-16 rounded-lg" />
        <Skeleton className="h-16 rounded-lg" />
      </div>
      <Skeleton className="h-1.5 w-full rounded-full" />
    </div>
  );
}

export function OCIntelligenceWidget({ className }: OCIntelligenceWidgetProps): JSX.Element {
  const stats = useShadowStats(24);
  const drift = useShadowDrift(24);

  const isLoading = stats.isLoading || drift.isLoading;
  const isError = stats.isError || drift.isError;

  if (isLoading) {
    return (
      <div className={classNames("p-3 bg-black/40 rounded-lg border border-slate-800", className)}>
        <WidgetSkeleton />
      </div>
    );
  }

  if (isError) {
    return (
      <div className={classNames("p-3 bg-red-500/5 rounded-lg border border-red-500/30", className)}>
        <div className="flex items-center gap-2 text-xs text-red-400">
          <AlertTriangle className="h-4 w-4" />
          <span>Intelligence feed unavailable</span>
        </div>
      </div>
    );
  }

  const statsData = stats.data;
  const driftData = drift.data;

  if (!statsData || !driftData) {
    return (
      <div className={classNames("p-3 bg-black/40 rounded-lg border border-slate-800", className)}>
        <div className="text-xs text-slate-500 text-center py-4">Loading intelligence...</div>
      </div>
    );
  }

  const p95Pct = statsData.p95_delta * 100;

  return (
    <div className={classNames("p-3 bg-black/40 rounded-lg border border-slate-800", className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Zap className="h-4 w-4 text-indigo-400" />
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
            Shadow Intel
          </span>
        </div>
        <DriftSignalBadge
          driftDetected={driftData.drift_detected}
          p95Delta={driftData.p95_delta}
          size="sm"
        />
      </div>

      {/* Mini KPIs */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="bg-slate-900/50 rounded-lg p-2 text-center">
          <div className="text-lg font-bold tabular-nums text-slate-100">
            {statsData.count.toLocaleString()}
          </div>
          <div className="text-[10px] text-slate-500">Events (24h)</div>
        </div>
        <div className="bg-slate-900/50 rounded-lg p-2 text-center">
          <div
            className={classNames(
              "text-lg font-bold tabular-nums",
              p95Pct < 15 ? "text-emerald-400" : p95Pct < 25 ? "text-amber-400" : "text-red-400"
            )}
          >
            {p95Pct.toFixed(1)}%
          </div>
          <div className="text-[10px] text-slate-500">P95 Delta</div>
        </div>
      </div>

      {/* P95 Progress Bar */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-[10px]">
          <span className="text-slate-500">Model Alignment</span>
          <span
            className={classNames(
              "font-medium",
              p95Pct < 15 ? "text-emerald-400" : p95Pct < 25 ? "text-amber-400" : "text-red-400"
            )}
          >
            {p95Pct < 15 ? "Excellent" : p95Pct < 25 ? "Good" : "Degraded"}
          </span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
          <div
            className={classNames(
              "h-full transition-all duration-500 ease-out",
              p95Pct < 15
                ? "bg-emerald-500"
                : p95Pct < 25
                  ? "bg-amber-500"
                  : "bg-red-500"
            )}
            style={{ width: `${Math.min(100 - p95Pct * 4, 100)}%` }}
          />
        </div>
      </div>

      {/* Drift indicator */}
      {driftData.drift_detected && (
        <div className="mt-3 flex items-center gap-2 rounded-lg bg-red-500/10 border border-red-500/30 px-2 py-1.5">
          <DriftDot driftDetected={true} p95Delta={driftData.p95_delta} />
          <span className="text-[10px] text-red-400">
            {driftData.high_delta_count} high-delta events detected
          </span>
        </div>
      )}

      {/* Model version */}
      <div className="mt-3 text-[9px] text-slate-600 text-right">
        Model {statsData.model_version}
      </div>
    </div>
  );
}
