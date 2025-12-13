/**
 * Shadow Events Table Component
 *
 * Displays recent shadow mode events showing individual shipment scorings
 * with dummy vs real model comparisons.
 *
 * UX: Scrollable event stream with color-coded deltas and clear timestamps.
 *
 * @module features/shadow/ShadowEventsTable
 */

import type { ShadowEvent } from "../../api/shadow";
import { Card, CardHeader, CardContent } from "../../components/ui/Card";


interface ShadowEventsTableProps {
  /** Shadow events list (null when loading or unavailable) */
  events: ShadowEvent[] | null;
  /** Loading state indicator */
  isLoading: boolean;
  /** Error message if fetch failed */
  error: string | null;
}

export default function ShadowEventsTable({
  events,
  isLoading,
  error,
}: ShadowEventsTableProps): JSX.Element {
  return (
    <Card>
      <CardHeader>
        <h2 className="text-xl font-semibold text-white">
          Recent Shadow Events
        </h2>
        <p className="text-sm text-slate-400 mt-1">
          Latest parallel scoring executions
        </p>
      </CardHeader>
      <CardContent>
        {/* Loading State */}
        {isLoading && (
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-16 bg-slate-800 rounded animate-pulse" />
            ))}
          </div>
        )}

        {/* Error State */}
        {error && !isLoading && (
          <div className="p-4 bg-amber-900/20 border border-amber-700 rounded-lg">
            <p className="text-sm text-amber-400">
              ⚠️ Event data not available
            </p>
            <p className="text-xs text-slate-400 mt-1">{error}</p>
          </div>
        )}

        {/* Events Table */}
        {events && events.length > 0 && !isLoading && !error && (
          <div className="overflow-x-auto max-h-96 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-slate-950">
                <tr className="border-b border-slate-700">
                  <th className="text-left py-3 px-4 text-slate-400 font-medium">
                    Shipment ID
                  </th>
                  <th className="text-left py-3 px-4 text-slate-400 font-medium">
                    Corridor
                  </th>
                  <th className="text-right py-3 px-4 text-slate-400 font-medium">
                    Dummy
                  </th>
                  <th className="text-right py-3 px-4 text-slate-400 font-medium">
                    Real
                  </th>
                  <th className="text-right py-3 px-4 text-slate-400 font-medium">
                    Delta (Δ)
                  </th>
                  <th className="text-right py-3 px-4 text-slate-400 font-medium">
                    Timestamp
                  </th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <tr
                    key={event.id}
                    className="border-b border-slate-800 hover:bg-slate-900/30 transition-colors"
                  >
                    <td className="py-3 px-4 font-mono text-sm text-white">
                      {event.shipment_id}
                    </td>
                    <td className="py-3 px-4 text-slate-300">
                      {event.corridor || "—"}
                    </td>
                    <td className="py-3 px-4 text-right text-slate-300">
                      {event.dummy_score.toFixed(3)}
                    </td>
                    <td className="py-3 px-4 text-right text-slate-300">
                      {event.real_score.toFixed(3)}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <span
                        className={`font-semibold px-2 py-1 rounded ${
                          event.delta < 0.05
                            ? "bg-green-900/30 text-green-400"
                            : event.delta < 0.15
                            ? "bg-yellow-900/30 text-yellow-400"
                            : "bg-red-900/30 text-red-400"
                        }`}
                      >
                        {event.delta.toFixed(3)}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right text-xs text-slate-400">
                      {new Date(event.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Empty State */}
        {events && events.length === 0 && !isLoading && !error && (
          <div className="p-8 text-center text-slate-500">
            <p>No shadow events logged yet</p>
            <p className="text-xs mt-2">
              Events will appear here as shadow mode executes
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
