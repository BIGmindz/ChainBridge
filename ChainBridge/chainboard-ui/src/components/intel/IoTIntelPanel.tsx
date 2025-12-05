/**
 * IoTIntelPanel Component
 *
 * Shows IoT intelligence: sensor coverage, active sensors, recent anomalies.
 * Integrates with real-time IoT health monitoring.
 */

import { Activity, Radio } from "lucide-react";

import { useIoTHealth } from "../../hooks/useIoTHealth";

interface IoTIntelPanelProps {
  emphasize?: boolean;
  onAnomalyClick?: () => void;
}

export default function IoTIntelPanel({ emphasize = false, onAnomalyClick }: IoTIntelPanelProps): JSX.Element {
  const { data: iotHealth, isLoading: loading, error } = useIoTHealth();

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-800/70 bg-slate-900/50 p-6">
        <div className="flex items-center gap-3">
          <Radio className="h-5 w-5 text-slate-500" />
          <h3 className="text-base font-semibold text-slate-100">IoT Intelligence</h3>
        </div>
        <div className="mt-4 text-sm text-slate-400">Loading IoT data...</div>
      </div>
    );
  }

  if (error || !iotHealth) {
    return (
      <div className="rounded-xl border border-slate-800/70 bg-slate-900/50 p-6">
        <div className="flex items-center gap-3">
          <Radio className="h-5 w-5 text-slate-500" />
          <h3 className="text-base font-semibold text-slate-100">IoT Intelligence</h3>
        </div>
        <div className="mt-4 text-sm text-red-400">Failed to load IoT data</div>
      </div>
    );
  }

  const coveragePercent = iotHealth.deviceCount > 0
    ? Math.round((iotHealth.online / iotHealth.deviceCount) * 100)
    : 0;
  const activeSensors = iotHealth.online;
  const criticalAlerts = Math.max(iotHealth.offline, iotHealth.anomalies.filter((anomaly) =>
    anomaly.severity === "HIGH" || anomaly.severity === "CRITICAL"
  ).length);

  const emphasisClass = emphasize
    ? "border-blue-500/50 bg-blue-500/5"
    : "border-slate-800/70 bg-slate-900/50";

  return (
    <div className={`rounded-xl border ${emphasisClass} p-6`}>
      {/* Header with LIVE badge */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Radio className="h-5 w-5 text-slate-400" />
          <h3 className="text-base font-semibold text-slate-100">IoT Intelligence</h3>
        </div>
        <div className="flex items-center gap-1 rounded-full border border-emerald-500/50 bg-emerald-500/10 px-2 py-0.5">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
          <span className="text-[9px] font-semibold uppercase tracking-wider text-emerald-300">
            LIVE
          </span>
        </div>
      </div>

      {/* IoT Metrics Grid */}
      <div className="mb-4 grid grid-cols-2 gap-3">
        <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2">
          <div className="text-2xl font-bold text-emerald-400">{coveragePercent}%</div>
          <div className="text-[10px] uppercase tracking-wide text-emerald-300">Coverage</div>
        </div>
        <div className="rounded-lg border border-blue-500/30 bg-blue-500/10 px-3 py-2">
          <div className="text-2xl font-bold text-blue-400">{activeSensors.toLocaleString()}</div>
          <div className="text-[10px] uppercase tracking-wide text-blue-300">Active</div>
        </div>
      </div>

      {/* Critical Alerts */}
      <button
        type="button"
        onClick={() => onAnomalyClick?.()}
        className="w-full rounded-lg border border-slate-800/50 bg-slate-950/50 p-3 text-left transition-colors hover:border-slate-700 hover:bg-slate-900/70"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-red-400" />
            <span className="text-xs font-medium text-slate-300">Alerts (24h)</span>
          </div>
          <span className={`text-lg font-bold ${
            criticalAlerts > 5 ? "text-red-400" :
            criticalAlerts > 0 ? "text-amber-400" :
            "text-emerald-400"
          }`}>
            {criticalAlerts}
          </span>
        </div>
      </button>

      {/* Status Message */}
      <div className="mt-3 flex items-center gap-2 text-[10px] text-slate-500">
        <span className="h-1 w-1 rounded-full bg-emerald-500"></span>
        <span>Sensor network operational</span>
      </div>
    </div>
  );
}
