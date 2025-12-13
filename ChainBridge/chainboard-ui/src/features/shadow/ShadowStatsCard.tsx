/**
 * Shadow Stats Card Component
 *
 * Displays high-level shadow mode statistics:
 * - Total events
 * - Average delta
 * - P95/P99 deltas
 * - Model version
 *
 * UX: Neurodivergent-friendly design with clear labels and visual hierarchy.
 *
 * @module features/shadow/ShadowStatsCard
 */

import type { ShadowStats } from "../../api/shadow";
import { Card, CardHeader, CardContent } from "../../components/ui/Card";


interface ShadowStatsCardProps {
  /** Shadow statistics data (null when loading or unavailable) */
  stats: ShadowStats | null;
  /** Loading state indicator */
  isLoading: boolean;
  /** Error message if fetch failed */
  error: string | null;
}

export default function ShadowStatsCard({
  stats,
  isLoading,
  error,
}: ShadowStatsCardProps): JSX.Element {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-white">
            Shadow Mode Statistics
          </h2>
          {stats && (
            <span className="text-xs text-slate-400">
              Model: {stats.model_version}
            </span>
          )}
        </div>
        <p className="text-sm text-slate-400 mt-1">
          Dummy vs Real model performance comparison
        </p>
      </CardHeader>
      <CardContent>
        {/* Loading State */}
        {isLoading && (
          <div className="space-y-3">
            <div className="h-16 bg-slate-800 rounded-lg animate-pulse" />
            <div className="grid grid-cols-3 gap-3">
              <div className="h-16 bg-slate-800 rounded-lg animate-pulse" />
              <div className="h-16 bg-slate-800 rounded-lg animate-pulse" />
              <div className="h-16 bg-slate-800 rounded-lg animate-pulse" />
            </div>
          </div>
        )}

        {/* Error State */}
        {error && !isLoading && (
          <div className="p-4 bg-amber-900/20 border border-amber-700 rounded-lg">
            <p className="text-sm text-amber-400 font-medium mb-1">
              ⚠️ Backend Endpoints Not Available
            </p>
            <p className="text-xs text-amber-300">
              {error}
            </p>
            <p className="text-xs text-slate-400 mt-2">
              TODO: Wire to real shadow API once Cody adds endpoints
            </p>
          </div>
        )}

        {/* Data Display */}
        {stats && !isLoading && !error && (
          <div className="space-y-4">
            {/* Primary Metrics */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-slate-900/50 rounded-lg border border-slate-700">
                <span className="text-xs uppercase tracking-wide text-slate-400">
                  Total Events
                </span>
                <div className="text-2xl font-bold text-white mt-1">
                  {stats.total_events.toLocaleString()}
                </div>
              </div>
              <div className="p-4 bg-slate-900/50 rounded-lg border border-slate-700">
                <span className="text-xs uppercase tracking-wide text-slate-400">
                  Avg Delta
                </span>
                <div className="text-2xl font-bold text-white mt-1">
                  {stats.avg_delta.toFixed(3)}
                </div>
              </div>
            </div>

            {/* Percentile Metrics */}
            <div className="grid grid-cols-3 gap-3">
              <div className="p-3 bg-slate-900/30 rounded-lg">
                <span className="text-[0.65rem] uppercase tracking-wide text-slate-400">
                  P95 Delta
                </span>
                <div className="text-lg font-semibold text-white mt-1">
                  {stats.p95_delta.toFixed(3)}
                </div>
              </div>
              <div className="p-3 bg-slate-900/30 rounded-lg">
                <span className="text-[0.65rem] uppercase tracking-wide text-slate-400">
                  P99 Delta
                </span>
                <div className="text-lg font-semibold text-white mt-1">
                  {stats.p99_delta.toFixed(3)}
                </div>
              </div>
              <div className="p-3 bg-slate-900/30 rounded-lg">
                <span className="text-[0.65rem] uppercase tracking-wide text-slate-400">
                  High Deltas
                </span>
                <div className="text-lg font-semibold text-white mt-1">
                  {stats.high_delta_count}
                </div>
              </div>
            </div>

            {/* Time Window Info */}
            <div className="text-xs text-slate-500 text-center">
              Statistics from last {stats.window_hours} hours
            </div>
          </div>
        )}

        {/* Empty State (no data, no error, not loading) */}
        {!stats && !isLoading && !error && (
          <div className="p-8 text-center text-slate-500">
            <p className="text-lg">No shadow data available</p>
            <p className="text-sm mt-2">
              Shadow mode may be disabled or no events have been logged yet.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
