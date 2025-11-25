import type { FC } from "react";

import { useIoTHealth } from "../hooks/useIoTHealth";

export const IoTHealthPanel: FC = () => {
  const { data, isLoading: loading, error, refetch } = useIoTHealth();

  if (loading) {
    return (
      <section className="rounded-2xl border border-slate-800 bg-slate-950/80 p-5 shadow-inner shadow-slate-900/40">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">ChainSense IoT</p>
        <p className="mt-3 text-base text-slate-300">Loading IoT health…</p>
      </section>
    );
  }

  if (error || !data) {
    return (
      <section className="rounded-2xl border border-rose-500/40 bg-rose-950/30 p-5 shadow-inner shadow-rose-900/30">
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-rose-200">ChainSense IoT</p>
          <button
            type="button"
            onClick={() => refetch()}
            className="rounded-md border border-rose-500/60 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.15em] text-rose-100"
          >
            Retry
          </button>
        </div>
        <p className="mt-3 text-sm text-rose-100">
          Failed to load IoT health: {error?.message ?? "Unknown error"}
        </p>
      </section>
    );
  }

  // M04: Map new backend structure to component expectations
  const {
    devices_online,
    devices_offline,
    devices_stale_gps,
    devices_stale_env,
    total_devices,
  } = data.summary;

  // Derive metrics from new structure
  const shipments_with_iot = total_devices; // Approximate - each device = 1 shipment
  const active_sensors = devices_online;
  const alerts_last_24h = devices_stale_gps + devices_stale_env;
  const critical_alerts_last_24h = devices_offline;
  const coverage_percent = total_devices > 0
    ? Math.round((devices_online / total_devices) * 100)
    : 0;

  // Derive status from metrics
  const overall_status =
    critical_alerts_last_24h > 2
      ? "CRITICAL"
      : alerts_last_24h > 5
        ? "DEGRADED"
        : coverage_percent >= 80
          ? "HEALTHY"
          : "DEGRADED";

  const statusTone =
    overall_status === "HEALTHY"
      ? "bg-emerald-500/15 text-emerald-300"
      : overall_status === "CRITICAL"
        ? "bg-rose-500/15 text-rose-300"
        : "bg-amber-500/15 text-amber-300";

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-950/80 p-5 shadow-inner shadow-slate-900/40">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">ChainSense IoT</p>
          <p className="mt-2 text-lg font-semibold text-slate-100">{overall_status}</p>
          <p className="text-xs text-slate-400">Telemetry + sensor health feed</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusTone}`}>
          {coverage_percent.toFixed(1)}% coverage
        </span>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-4 text-sm">
        <Metric label="Shipments w/ IoT" value={shipments_with_iot.toLocaleString()} accent="text-sky-300" />
        <Metric label="Active Sensors" value={active_sensors.toLocaleString()} accent="text-emerald-300" />
        <Metric label="Alerts (24h)" value={alerts_last_24h.toLocaleString()} accent="text-amber-300" />
        <Metric label="Critical Alerts" value={critical_alerts_last_24h.toLocaleString()} accent="text-rose-300" />
      </div>

      <div className="mt-5 flex items-center justify-between text-xs text-slate-400">
        <p>
          Alerts:
          <span className="ml-1 font-semibold text-rose-300">{critical_alerts_last_24h}</span> critical /
          <span className="ml-1 font-semibold text-amber-300">{Math.max(alerts_last_24h - critical_alerts_last_24h, 0)}</span> warning
        </p>

        <p>Updated {new Date(data.last_updated).toLocaleTimeString()}</p>
      </div>
    </section>
  );
};

function Metric({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className={`mt-1 text-base font-semibold text-slate-100 ${accent ?? ""}`}>{value}</p>
    </div>
  );
}
