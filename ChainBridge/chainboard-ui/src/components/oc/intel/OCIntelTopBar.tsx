import { Activity, AlertTriangle, Anchor, TrendingUp } from 'lucide-react';

import type { GlobalIntelSnapshot } from '@/types/chainbridge';

type OCIntelTopBarProps = {
  snapshot: GlobalIntelSnapshot;
  selectedCorridor?: string;
};

const formatPct = (value: number) => `${value.toFixed(1)}%`;

export default function OCIntelTopBar({ snapshot, selectedCorridor }: OCIntelTopBarProps) {
  // Calculate global STP%
  const totalShipments = snapshot.by_corridor.reduce((sum, c) => sum + c.shipment_count, 0);
  const globalSTP = totalShipments > 0 ? (snapshot.on_time_count / totalShipments) * 100 : 0;

  // Calculate corridor-specific STP%
  const corridorData = selectedCorridor
    ? snapshot.by_corridor.find((c) => c.corridorId === selectedCorridor)
    : null;
  const corridorSTP = corridorData
    ? (corridorData.on_time_count / corridorData.shipment_count) * 100
    : 0;

  // High-risk count
  const highRiskCount = snapshot.by_corridor.reduce(
    (sum, c) => sum + c.high_risk_count + c.critical_risk_count,
    0,
  );

  // Ports in alert state (riskScore > 70)
  const alertPorts = snapshot.top_ports_by_risk.filter((p) => p.riskScore > 70).length;

  // Settlement in flight (financed value)
  const settlementInFlight = snapshot.financed_valueUsd;

  return (
    <div className="flex flex-wrap items-center gap-4 rounded-lg border border-slate-700 bg-slate-800/50 px-4 py-3">
      {/* Global STP% */}
      <div className="flex items-center gap-2">
        <TrendingUp className="h-4 w-4 text-emerald-400" />
        <div className="flex flex-col">
          <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
            Global STP%
          </span>
          <span className="text-lg font-bold text-emerald-400">{formatPct(globalSTP)}</span>
        </div>
      </div>

      {/* Divider */}
      <div className="h-8 w-px bg-slate-700" />

      {/* Corridor STP% */}
      <div className="flex items-center gap-2">
        <Activity className="h-4 w-4 text-indigo-400" />
        <div className="flex flex-col">
          <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
            {selectedCorridor ? `${selectedCorridor} STP%` : 'Corridor STP%'}
          </span>
          <span className="text-lg font-bold text-indigo-400">
            {corridorData ? formatPct(corridorSTP) : '—'}
          </span>
        </div>
      </div>

      {/* Divider */}
      <div className="h-8 w-px bg-slate-700" />

      {/* High-Risk Count */}
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 text-orange-400" />
        <div className="flex flex-col">
          <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
            High Risk
          </span>
          <span className="text-lg font-bold text-orange-400">{highRiskCount}</span>
        </div>
      </div>

      {/* Divider */}
      <div className="h-8 w-px bg-slate-700" />

      {/* Ports in Alert */}
      <div className="flex items-center gap-2">
        <Anchor className="h-4 w-4 text-red-400" />
        <div className="flex flex-col">
          <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
            Ports in Alert
          </span>
          <span className="text-lg font-bold text-red-400">{alertPorts}</span>
        </div>
      </div>

      {/* Divider */}
      <div className="h-8 w-px bg-slate-700" />

      {/* Settlement in Flight */}
      <div className="flex items-center gap-2">
        <TrendingUp className="h-4 w-4 text-emerald-400" />
        <div className="flex flex-col">
          <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
            Settlement In-Flight
          </span>
          <span className="text-lg font-bold text-slate-200">
            ${(settlementInFlight / 1_000_000).toFixed(1)}M
          </span>
        </div>
      </div>
    </div>
  );
}
