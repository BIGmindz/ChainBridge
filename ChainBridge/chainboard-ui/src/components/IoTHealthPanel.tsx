import { Activity, AlertTriangle, Radio, Satellite } from "lucide-react";
import type { ReactNode } from "react";
import type { IoTHealthSummary } from "../lib/iot";

interface IoTHealthPanelProps {
  iot: IoTHealthSummary | null;
}

const labelStyles = "text-[10px] uppercase tracking-[0.2em] text-slate-500";

export function IoTHealthPanel({ iot }: IoTHealthPanelProps) {
  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-950/80 p-5">
      <header className="flex items-center justify-between">
        <div>
          <p className={labelStyles}>IoT Coverage</p>
          <p className="mt-1 text-sm font-semibold text-slate-100">Telemetry + Sensor Health</p>
          <p className="text-xs text-slate-400">ChainSense feeds across temp, humidity, shock, door, and GPS sensors.</p>
        </div>
        <Radio className="h-5 w-5 text-emerald-300" />
      </header>

      {iot ? (
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <IoTStat
            icon={<Satellite className="h-4 w-4 text-emerald-300" />}
            label="Coverage"
            primary={`${iot.coverage_percent.toFixed(0)}%`}
            helper={`${iot.shipments_with_iot.toLocaleString()} shipments instrumented`}
          />
          <IoTStat
            icon={<Activity className="h-4 w-4 text-sky-300" />}
            label="Active sensors"
            primary={iot.active_sensors.toLocaleString()}
            helper="Streams online"
          />
          <IoTStat
            icon={<AlertTriangle className="h-4 w-4 text-amber-300" />}
            label="Alerts (24h)"
            primary={iot.alerts_last_24h.toLocaleString()}
            helper={`${iot.critical_alerts_last_24h} critical`}
          />
          <IoTStat
            icon={<Activity className="h-4 w-4 text-rose-300" />}
            label="Critical alerts"
            primary={iot.critical_alerts_last_24h.toLocaleString()}
            helper="Escalated to watch desk"
          />
        </div>
      ) : (
        <div className="mt-4 rounded-xl border border-slate-800/70 bg-slate-900/60 p-4 text-sm text-slate-400">
          IoT telemetry feed not available yet. Once the backend exposes /metrics/iot endpoints, realtime coverage will appear here.
        </div>
      )}
    </section>
  );
}

function IoTStat({
  label,
  primary,
  helper,
  icon,
}: {
  label: string;
  primary: string;
  helper: string;
  icon: ReactNode;
}) {
  return (
    <article className="rounded-2xl border border-slate-800/80 bg-slate-950/50 p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className={labelStyles}>{label}</p>
          <p className="mt-2 text-xl font-semibold text-slate-100">{primary}</p>
          <p className="text-xs text-slate-400">{helper}</p>
        </div>
        {icon}
      </div>
    </article>
  );
}
