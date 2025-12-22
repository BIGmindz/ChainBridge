/**
 * OCIntelligenceWidget - Compact Intelligence Widget for Operator Console
 *
 * NEUTRALIZED: PAC-BENSON-SONNY-ACTIVATION-BLOCK-UI-ENFORCEMENT-02
 * - No semantic colors
 * - No icons
 * - No marketing language ("Excellent", "Good", "Degraded")
 */

import { classNames } from "../../utils/classNames";
import { useShadowStats, useShadowDrift } from "../../hooks/useShadowMode";
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
      <div className={classNames("p-3 bg-slate-900/50 border border-slate-700/50", className)}>
        <p className="text-xs text-slate-500 font-mono">
          status: feed_unavailable
        </p>
      </div>
    );
  }

  const statsData = stats.data;
  const driftData = drift.data;

  if (!statsData || !driftData) {
    return (
      <div className={classNames("p-3 bg-slate-900/50 border border-slate-700/50", className)}>
        <p className="text-xs text-slate-600 font-mono text-center py-4">loading...</p>
      </div>
    );
  }

  const p95Pct = statsData.p95_delta * 100;

  return (
    <div className={classNames("p-3 bg-slate-900/50 border border-slate-700/50 font-mono", className)}>
      {/* Header */}
      <div className="border-b border-slate-800/50 pb-2 mb-3">
        <p className="text-xs text-slate-600 uppercase tracking-wider">
          shadow_intel
        </p>
      </div>

      {/* Mini KPIs */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="bg-slate-900/50 border border-slate-800/50 p-2">
          <p className="text-lg text-slate-400 tabular-nums">
            {statsData.count.toLocaleString()}
          </p>
          <p className="text-xs text-slate-600">events_24h</p>
        </div>
        <div className="bg-slate-900/50 border border-slate-800/50 p-2">
          <p className="text-lg text-slate-400 tabular-nums">
            {p95Pct.toFixed(1)}%
          </p>
          <p className="text-xs text-slate-600">p95_delta</p>
        </div>
      </div>

      {/* P95 Progress Bar - neutral gray */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-600">model_alignment:</span>
          <span className="text-slate-500">{(100 - p95Pct).toFixed(1)}%</span>
        </div>
        <div className="h-1.5 w-full overflow-hidden bg-slate-800">
          <div
            className="h-full bg-slate-600 transition-all duration-500 ease-out"
            style={{ width: `${Math.min(100 - p95Pct * 4, 100)}%` }}
          />
        </div>
      </div>

      {/* Drift indicator - neutral */}
      {driftData.drift_detected && (
        <div className="mt-3 border border-slate-600 bg-slate-900/50 px-2 py-1.5">
          <p className="text-xs text-slate-500">
            drift_detected: {driftData.high_delta_count} high_delta_events
          </p>
        </div>
      )}

      {/* Model version */}
      <div className="mt-3 text-xs text-slate-600 text-right">
        model: {statsData.model_version}
      </div>
    </div>
  );
}
