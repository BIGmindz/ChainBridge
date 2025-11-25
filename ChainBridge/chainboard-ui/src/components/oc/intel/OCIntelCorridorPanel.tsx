import { TrendingDown, TrendingUp } from 'lucide-react';

import type { CorridorIntelStats } from '@/types/chainbridge';

type OCIntelCorridorPanelProps = {
  corridors: CorridorIntelStats[];
  onSelectCorridor: (corridorId: string) => void;
  selectedCorridor?: string;
};

const formatHours = (hours?: number) => {
  if (!hours) return '—';
  const sign = hours >= 0 ? '+' : '';
  return `${sign}${hours.toFixed(1)}h`;
};

const formatPct = (count: number, total: number) => {
  if (total === 0) return '0.0%';
  return `${((count / total) * 100).toFixed(1)}%`;
};

export default function OCIntelCorridorPanel({
  corridors,
  onSelectCorridor,
  selectedCorridor,
}: OCIntelCorridorPanelProps) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/50">
      <div className="border-b border-slate-700 px-4 py-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
          Corridor KPIs
        </h3>
        <p className="text-xs text-slate-400">Click row to filter queue + map</p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-700 bg-slate-900/50 text-xs uppercase tracking-wider text-slate-400">
              <th className="px-4 py-2 text-left font-semibold">Corridor</th>
              <th className="px-4 py-2 text-right font-semibold">Avg ETA Δ</th>
              <th className="px-4 py-2 text-right font-semibold">High Risk</th>
              <th className="px-4 py-2 text-right font-semibold">At Risk</th>
              <th className="px-4 py-2 text-right font-semibold">STP%</th>
            </tr>
          </thead>
          <tbody>
            {corridors.map((corridor) => {
              const isSelected = selectedCorridor === corridor.corridorId;
              const stpPct = formatPct(corridor.on_time_count, corridor.shipment_count);
              const highRisk = corridor.high_risk_count + corridor.critical_risk_count;
              const atRiskPct = formatPct(corridor.at_risk_valueUsd, corridor.valueUsd || 1);

              return (
                <tr
                  key={corridor.corridorId}
                  onClick={() => onSelectCorridor(corridor.corridorId)}
                  className={`cursor-pointer border-b border-slate-700/50 transition-colors ${
                    isSelected
                      ? 'bg-emerald-900/20 hover:bg-emerald-900/30'
                      : 'hover:bg-slate-700/30'
                  }`}
                >
                  <td className="px-4 py-3">
                    <span
                      className={`text-sm font-medium ${isSelected ? 'text-emerald-300' : 'text-slate-200'}`}
                    >
                      {corridor.corridorLabel || corridor.corridorId}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {corridor.avg_eta_delta_hours && corridor.avg_eta_delta_hours > 0 ? (
                        <TrendingDown className="h-3 w-3 text-red-400" />
                      ) : corridor.avg_eta_delta_hours && corridor.avg_eta_delta_hours < 0 ? (
                        <TrendingUp className="h-3 w-3 text-emerald-400" />
                      ) : null}
                      <span
                        className={`font-mono text-sm ${
                          !corridor.avg_eta_delta_hours
                            ? 'text-slate-400'
                            : corridor.avg_eta_delta_hours > 0
                              ? 'text-red-300'
                              : 'text-emerald-300'
                        }`}
                      >
                        {formatHours(corridor.avg_eta_delta_hours)}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="font-mono text-sm text-orange-300">{highRisk}</span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="font-mono text-sm text-amber-300">{atRiskPct}</span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="font-mono text-sm text-emerald-300">{stpPct}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {corridors.length === 0 && (
        <div className="px-4 py-8 text-center text-sm text-slate-400">
          No corridor data available
        </div>
      )}
    </div>
  );
}
