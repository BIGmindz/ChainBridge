/**
 * Shadow Pilot Charts Component
 *
 * Visualization components for Shadow Pilot commercial impact data.
 * Uses minimal, high-signal charts consistent with The OC aesthetics.
 */

import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import type { ShadowPilotSummary } from '../../types/chainbridge';

interface ShadowPilotChartsProps {
  summary: ShadowPilotSummary;
}

// Custom tooltip for currency formatting
interface TooltipPayload {
  value: number;
  name: string;
  color: string;
}

interface CurrencyTooltipProps {
  active?: boolean;
  payload?: TooltipPayload[];
  label?: string;
}

function CurrencyTooltip({ active, payload, label }: CurrencyTooltipProps) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-lg">
        <p className="text-slate-300 font-medium mb-1">{label}</p>
        {payload.map((entry: TooltipPayload, index: number) => (
          <p key={index} className="text-slate-100">
            <span className="font-medium">
              {new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD',
                minimumFractionDigits: 0,
                maximumFractionDigits: 0,
              }).format(entry.value)}
            </span>
          </p>
        ))}
      </div>
    );
  }
  return null;
}

export function ShadowPilotCharts({ summary }: ShadowPilotChartsProps): JSX.Element {
  // GMV breakdown chart data
  const gmvData = [
    {
      name: 'Total GMV',
      value: summary.total_gmv_usd,
      fill: '#64748b', // slate-500
    },
    {
      name: 'Financeable GMV',
      value: summary.financeable_gmv_usd,
      fill: '#0ea5e9', // sky-500
    },
    {
      name: 'Financed GMV',
      value: summary.financed_gmv_usd,
      fill: '#10b981', // emerald-500
    },
  ];

  // Financial impact chart data
  const impactData = [
    {
      name: 'Protocol Revenue',
      value: summary.protocolRevenueUsd,
      fill: '#8b5cf6', // violet-500
    },
    {
      name: 'Working Capital Saved',
      value: summary.working_capital_saved_usd,
      fill: '#f59e0b', // amber-500
    },
    {
      name: 'Losses Avoided',
      value: summary.losses_avoided_usd,
      fill: '#ef4444', // red-500
    },
    {
      name: 'Salvage Revenue',
      value: summary.salvageRevenueUsd,
      fill: '#06b6d4', // cyan-500
    },
  ].filter(item => item.value > 0); // Only show non-zero values

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* GMV Breakdown Chart */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-slate-100 mb-4">
          GMV Breakdown
        </h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={gmvData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <XAxis
                dataKey="name"
                tick={{ fill: '#94a3b8', fontSize: 12 }}
                axisLine={{ stroke: '#475569' }}
                tickLine={{ stroke: '#475569' }}
              />
              <YAxis
                tick={{ fill: '#94a3b8', fontSize: 12 }}
                axisLine={{ stroke: '#475569' }}
                tickLine={{ stroke: '#475569' }}
                tickFormatter={(value) => `$${(value / 1000000).toFixed(1)}M`}
              />
              <Tooltip content={<CurrencyTooltip />} />
              <Bar dataKey="value" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Financial Impact Chart */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-slate-100 mb-4">
          Financial Impact
        </h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={impactData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <XAxis
                dataKey="name"
                tick={{ fill: '#94a3b8', fontSize: 12 }}
                axisLine={{ stroke: '#475569' }}
                tickLine={{ stroke: '#475569' }}
                interval={0}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis
                tick={{ fill: '#94a3b8', fontSize: 12 }}
                axisLine={{ stroke: '#475569' }}
                tickLine={{ stroke: '#475569' }}
                tickFormatter={(value) =>
                  value >= 1000000
                    ? `$${(value / 1000000).toFixed(1)}M`
                    : `$${(value / 1000).toFixed(0)}K`
                }
              />
              <Tooltip content={<CurrencyTooltip />} />
              <Bar dataKey="value" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
