import { Anchor, ShieldAlert, ShieldCheck } from 'lucide-react';

import type { PortRiskInfo } from '@/types/chainbridge';

type OCIntelPortHotspotsProps = {
  ports: PortRiskInfo[];
  onHoverPort?: (portCode: string | null) => void;
};

const getRiskColor = (riskScore: number) => {
  if (riskScore >= 80) return 'text-red-400';
  if (riskScore >= 50) return 'text-orange-400';
  return 'text-emerald-400';
};

const getRiskIcon = (riskScore: number) => {
  if (riskScore >= 50) {
    return <ShieldAlert className="h-4 w-4" />;
  }
  return <ShieldCheck className="h-4 w-4" />;
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

export default function OCIntelPortHotspots({ ports, onHoverPort }: OCIntelPortHotspotsProps) {
  const top10Ports = ports.slice(0, 10);

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/50">
      <div className="border-b border-slate-700 px-4 py-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
          Port Hotspots
        </h3>
        <p className="text-xs text-slate-400">Top 10 by congestion + risk</p>
      </div>

      <div className="divide-y divide-slate-700/50">
        {top10Ports.map((port) => {
          const riskScore = port.riskScore ?? port.congestionScore ?? 0;
          const riskColor = getRiskColor(riskScore);
          const riskIcon = getRiskIcon(riskScore);
          const portCode = port.port_code ?? port.portCode ?? "UNKNOWN";
          const portName = port.port_name ?? port.portName ?? "Unknown Port";
          const activeShipments = port.active_shipments ?? port.activeShipments ?? 0;
          const atRiskValue = port.at_risk_valueUsd ?? 0;

          return (
            <div
              key={portCode}
              onMouseEnter={() => onHoverPort?.(portCode)}
              onMouseLeave={() => onHoverPort?.(null)}
              className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-slate-700/30"
            >
              <div className={riskColor}>{riskIcon}</div>

              <div className="flex-1">
                <div className="flex items-baseline gap-2">
                  <span className="text-sm font-semibold text-slate-200">{portName}</span>
                  <span className="font-mono text-xs text-slate-400">{portCode}</span>
                </div>
                {port.country && <span className="text-xs text-slate-500">{port.country}</span>}
              </div>

              <div className="text-right">
                <div className="flex items-center gap-1">
                  <Anchor className="h-3 w-3 text-slate-400" />
                  <span className="font-mono text-xs text-slate-300">{activeShipments}</span>
                </div>
                <span className="font-mono text-xs text-amber-300">
                  {formatCurrency(atRiskValue)}
                </span>
              </div>

              <div className="flex items-center gap-1">
                <span className={`font-mono text-sm font-bold ${riskColor}`}>
                  {riskScore.toFixed(0)}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {ports.length === 0 && (
        <div className="px-4 py-8 text-center text-sm text-slate-400">No port data available</div>
      )}
    </div>
  );
}
