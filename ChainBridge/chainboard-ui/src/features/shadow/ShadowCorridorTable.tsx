/**
 * Shadow Corridor Table Component
 *
 * Displays per-corridor shadow mode statistics showing which trade lanes
 * have the highest model divergence.
 *
 * UX: Clean table design with sortable columns and color-coded deltas.
 *
 * @module features/shadow/ShadowCorridorTable
 */

import type { CorridorStats } from "../../api/shadow";
import { Card, CardHeader, CardContent } from "../../components/ui/Card";


interface ShadowCorridorTableProps {
  /** Corridor statistics (null when loading or unavailable) */
  corridors: CorridorStats[] | null;
  /** Loading state indicator */
  isLoading: boolean;
  /** Error message if fetch failed */
  error: string | null;
}

export default function ShadowCorridorTable({
  corridors,
  isLoading,
  error,
}: ShadowCorridorTableProps): JSX.Element {
  return (
    <Card>
      <CardHeader>
        <h2 className="text-xl font-semibold text-white">
          Corridor Breakdown
        </h2>
        <p className="text-sm text-slate-400 mt-1">
          Model divergence by trade corridor
        </p>
      </CardHeader>
      <CardContent>
        {/* Loading State */}
        {isLoading && (
          <div className="space-y-2">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-12 bg-slate-800 rounded animate-pulse" />
            ))}
          </div>
        )}

        {/* Error State */}
        {error && !isLoading && (
          <div className="p-4 bg-amber-900/20 border border-amber-700 rounded-lg">
            <p className="text-sm text-amber-400">
              ⚠️ Corridor data not available
            </p>
            <p className="text-xs text-slate-400 mt-1">{error}</p>
          </div>
        )}

        {/* Data Table */}
        {corridors && corridors.length > 0 && !isLoading && !error && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="text-left py-3 px-4 text-slate-400 font-medium">
                    Corridor
                  </th>
                  <th className="text-right py-3 px-4 text-slate-400 font-medium">
                    Events
                  </th>
                  <th className="text-right py-3 px-4 text-slate-400 font-medium">
                    Avg Δ
                  </th>
                  <th className="text-right py-3 px-4 text-slate-400 font-medium">
                    Max Δ
                  </th>
                  <th className="text-right py-3 px-4 text-slate-400 font-medium">
                    Last Event
                  </th>
                </tr>
              </thead>
              <tbody>
                {corridors.map((corridor) => (
                  <tr
                    key={corridor.corridor}
                    className="border-b border-slate-800 hover:bg-slate-900/30 transition-colors"
                  >
                    <td className="py-3 px-4 font-mono text-white">
                      {corridor.corridor}
                    </td>
                    <td className="py-3 px-4 text-right text-slate-300">
                      {corridor.event_count}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <span
                        className={`font-semibold ${
                          corridor.avg_delta < 0.1
                            ? "text-green-400"
                            : corridor.avg_delta < 0.2
                            ? "text-yellow-400"
                            : "text-red-400"
                        }`}
                      >
                        {corridor.avg_delta.toFixed(3)}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <span
                        className={`font-semibold ${
                          corridor.max_delta < 0.15
                            ? "text-green-400"
                            : corridor.max_delta < 0.3
                            ? "text-yellow-400"
                            : "text-red-400"
                        }`}
                      >
                        {corridor.max_delta.toFixed(3)}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right text-xs text-slate-400">
                      {new Date(corridor.last_event_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Empty State */}
        {corridors && corridors.length === 0 && !isLoading && !error && (
          <div className="p-8 text-center text-slate-500">
            <p>No corridor data available</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
