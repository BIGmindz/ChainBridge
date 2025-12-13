/**
 * ShadowKPICards - Three KPI cards for Shadow Mode Intelligence
 *
 * Cards: Event Count, P95 Delta, Drift Status
 * Cinematic design with loading skeletons.
 */

import { Activity, AlertTriangle, Gauge, TrendingUp } from "lucide-react";

import { classNames } from "../../utils/classNames";
import { Skeleton } from "../ui/Skeleton";

import { DriftSignalBadge } from "./DriftSignalBadge";

interface ShadowKPICardsProps {
  stats: {
    count: number;
    p95_delta: number;
    drift_flag: boolean;
    mean_delta: number;
    model_version: string;
    time_window_hours: number;
  } | null;
  isLoading?: boolean;
  className?: string;
}

/**
 * Single KPI card skeleton.
 */
function KPICardSkeleton(): JSX.Element {
  return (
    <div className="rounded-xl border border-slate-800/50 bg-slate-900/50 p-4">
      <div className="flex items-start justify-between">
        <Skeleton className="h-4 w-4 rounded" />
        <Skeleton className="h-4 w-16" />
      </div>
      <Skeleton className="mt-3 h-8 w-20" />
      <Skeleton className="mt-2 h-3 w-24" />
    </div>
  );
}

export function ShadowKPICards({
  stats,
  isLoading,
  className,
}: ShadowKPICardsProps): JSX.Element {
  if (isLoading || !stats) {
    return (
      <div className={classNames("grid grid-cols-1 gap-4 sm:grid-cols-3", className)}>
        <KPICardSkeleton />
        <KPICardSkeleton />
        <KPICardSkeleton />
      </div>
    );
  }

  // Determine P95 severity
  const p95Level =
    stats.p95_delta < 0.15 ? "good" : stats.p95_delta < 0.25 ? "warning" : "critical";

  return (
    <div className={classNames("grid grid-cols-1 gap-4 sm:grid-cols-3", className)}>
      {/* Card 1: Event Count */}
      <div className="rounded-xl border border-slate-800/50 bg-slate-900/50 p-4 transition-all hover:border-slate-700/70">
        <div className="flex items-start justify-between">
          <Activity className="h-4 w-4 text-indigo-400" />
          <span className="text-[10px] font-medium uppercase tracking-wider text-slate-500">
            {stats.time_window_hours}h window
          </span>
        </div>
        <div className="mt-3">
          <span className="text-3xl font-bold tabular-nums text-slate-100">
            {stats.count.toLocaleString()}
          </span>
        </div>
        <p className="mt-1 text-xs text-slate-400">Shadow Events</p>
        <div className="mt-3 flex items-center gap-1.5 text-[10px] text-slate-500">
          <TrendingUp className="h-3 w-3" />
          <span>
            {(stats.count / stats.time_window_hours).toFixed(1)} events/hr
          </span>
        </div>
      </div>

      {/* Card 2: P95 Delta */}
      <div
        className={classNames(
          "rounded-xl border p-4 transition-all hover:border-slate-700/70",
          p95Level === "good"
            ? "border-slate-800/50 bg-slate-900/50"
            : p95Level === "warning"
              ? "border-amber-500/30 bg-amber-500/5"
              : "border-red-500/30 bg-red-500/5"
        )}
      >
        <div className="flex items-start justify-between">
          <Gauge className="h-4 w-4 text-slate-400" />
          <span
            className={classNames(
              "text-[10px] font-medium uppercase tracking-wider",
              p95Level === "good"
                ? "text-emerald-400"
                : p95Level === "warning"
                  ? "text-amber-400"
                  : "text-red-400"
            )}
          >
            P95
          </span>
        </div>
        <div className="mt-3">
          <span
            className={classNames(
              "text-3xl font-bold tabular-nums",
              p95Level === "good"
                ? "text-emerald-400"
                : p95Level === "warning"
                  ? "text-amber-400"
                  : "text-red-400"
            )}
          >
            {(stats.p95_delta * 100).toFixed(1)}%
          </span>
        </div>
        <p className="mt-1 text-xs text-slate-400">Score Delta</p>
        <div className="mt-3">
          {/* Delta bar visualization */}
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
            <div
              className={classNames(
                "h-full transition-all duration-500",
                p95Level === "good"
                  ? "bg-emerald-500"
                  : p95Level === "warning"
                    ? "bg-amber-500"
                    : "bg-red-500"
              )}
              style={{ width: `${Math.min(stats.p95_delta * 100 * 4, 100)}%` }}
            />
          </div>
          <div className="mt-1 flex justify-between text-[9px] text-slate-600">
            <span>0%</span>
            <span className="text-slate-500">25% threshold</span>
          </div>
        </div>
      </div>

      {/* Card 3: Drift Status */}
      <div
        className={classNames(
          "rounded-xl border p-4 transition-all hover:border-slate-700/70",
          stats.drift_flag
            ? "border-red-500/30 bg-red-500/5"
            : "border-slate-800/50 bg-slate-900/50"
        )}
      >
        <div className="flex items-start justify-between">
          <AlertTriangle
            className={classNames(
              "h-4 w-4",
              stats.drift_flag ? "text-red-400" : "text-slate-400"
            )}
          />
          <DriftSignalBadge
            driftDetected={stats.drift_flag}
            p95Delta={stats.p95_delta}
            size="sm"
          />
        </div>
        <div className="mt-3">
          <span
            className={classNames(
              "text-2xl font-bold",
              stats.drift_flag ? "text-red-400" : "text-emerald-400"
            )}
          >
            {stats.drift_flag ? "DETECTED" : "STABLE"}
          </span>
        </div>
        <p className="mt-1 text-xs text-slate-400">Model Drift</p>
        <div className="mt-3 text-[10px] text-slate-500">
          <span>Model: {stats.model_version}</span>
        </div>
      </div>
    </div>
  );
}
