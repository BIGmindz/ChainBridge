import { Plane, Ship, Truck } from 'lucide-react';

import type { ModeIntelStats } from '@/types/chainbridge';

type OCIntelModesProps = {
  modes: ModeIntelStats[];
};

const getModeIcon = (mode: string) => {
  switch (mode.toUpperCase()) {
    case 'AIR':
      return <Plane className="h-5 w-5" />;
    case 'OCEAN':
      return <Ship className="h-5 w-5" />;
    case 'TRUCK':
    case 'RAIL':
      return <Truck className="h-5 w-5" />;
    default:
      return <Ship className="h-5 w-5" />;
  }
};

const formatHours = (hours?: number) => {
  if (!hours) return '0.0h';
  const sign = hours >= 0 ? '+' : '';
  return `${sign}${hours.toFixed(1)}h`;
};

const formatCurrency = (value: number) => {
  if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `$${(value / 1_000).toFixed(0)}K`;
  }
  return `$${value.toFixed(0)}`;
};

export default function OCIntelModes({ modes }: OCIntelModesProps) {
  const totalShipments = modes.reduce((sum, m) => sum + m.shipment_count, 0);

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/50">
      <div className="border-b border-slate-700 px-4 py-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
          Mode Intelligence
        </h3>
        <p className="text-xs text-slate-400">Delay delta · Risk distribution · Volume</p>
      </div>

      <div className="divide-y divide-slate-700/50">
        {modes.map((mode) => {
          const volumePct =
            totalShipments > 0 ? ((mode.shipment_count / totalShipments) * 100).toFixed(1) : '0.0';
          const highRisk = mode.risk_distribution.high + mode.risk_distribution.critical;

          return (
            <div key={mode.mode} className="px-4 py-4">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="text-indigo-400">{getModeIcon(mode.mode)}</div>
                  <div>
                    <h4 className="text-sm font-semibold text-slate-200">
                      {mode.mode.toUpperCase()}
                    </h4>
                    <p className="text-xs text-slate-400">
                      {mode.shipment_count} shipments · {volumePct}% of total
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xs text-slate-400">Avg Delay</p>
                  <p
                    className={`font-mono text-sm font-semibold ${
                      (mode.avg_delay_hours ?? 0) > 0 ? 'text-red-300' : 'text-emerald-300'
                    }`}
                  >
                    {formatHours(mode.avg_delay_hours)}
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Value in Transit</span>
                  <span className="font-mono font-semibold text-slate-200">
                    {formatCurrency(mode.valueUsd)}
                  </span>
                </div>

                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">High Risk Count</span>
                  <span className="font-mono font-semibold text-orange-300">{highRisk}</span>
                </div>

                {/* Risk Distribution Bar */}
                <div className="mt-2">
                  <p className="mb-1 text-xs text-slate-400">Risk Distribution</p>
                  <div className="flex h-2 overflow-hidden rounded-full bg-slate-700">
                    <div
                      className="bg-emerald-500"
                      style={{
                        width: `${((mode.risk_distribution.low / mode.shipment_count) * 100).toFixed(0)}%`,
                      }}
                    />
                    <div
                      className="bg-amber-400"
                      style={{
                        width: `${((mode.risk_distribution.medium / mode.shipment_count) * 100).toFixed(0)}%`,
                      }}
                    />
                    <div
                      className="bg-orange-500"
                      style={{
                        width: `${((mode.risk_distribution.high / mode.shipment_count) * 100).toFixed(0)}%`,
                      }}
                    />
                    <div
                      className="bg-red-500"
                      style={{
                        width: `${((mode.risk_distribution.critical / mode.shipment_count) * 100).toFixed(0)}%`,
                      }}
                    />
                  </div>
                  <div className="mt-1 flex justify-between text-xs text-slate-500">
                    <span>Low</span>
                    <span>Critical</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {modes.length === 0 && (
        <div className="px-4 py-8 text-center text-sm text-slate-400">No mode data available</div>
      )}
    </div>
  );
}
