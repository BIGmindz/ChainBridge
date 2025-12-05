import { AlertTriangle, Radio } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

import { useIoTHealth } from "../../hooks/useIoTHealth";
import { CardSkeleton, EmptyState, ErrorState } from "../ui/LoadingStates";
import { classNames } from "../../utils/classNames";

// TODO(SONNY, optional): Consider a compact variant of this panel for the
// Operator Console right rail, plus filters (severity, lane, shipment) and
// drill-through into shipment detail views when OC layout and navigation
// stories are finalized.

const severityBadge = {
  LOW: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  MEDIUM: "border-amber-500/30 bg-amber-500/10 text-amber-300",
  HIGH: "border-orange-500/40 bg-orange-500/10 text-orange-300",
  CRITICAL: "border-rose-500/40 bg-rose-500/15 text-rose-300",
} as const;

type SeverityKey = keyof typeof severityBadge;

function formatRelativeTime(timestamp: string | undefined): string {
  if (!timestamp) {
    return "Unknown";
  }

  const asDate = new Date(timestamp);
  if (Number.isNaN(asDate.getTime())) {
    return "Unknown";
  }

  return formatDistanceToNow(asDate, { addSuffix: true });
}

function MetricStat({ label, value, tone }: { label: string; value: string; tone?: "good" | "warn" | "bad" }) {
  const toneClass = tone === "good"
    ? "text-emerald-300"
    : tone === "warn"
      ? "text-amber-300"
      : tone === "bad"
        ? "text-rose-300"
        : "text-slate-100";

  return (
    <div className="rounded-xl border border-slate-800/70 bg-slate-900/60 p-4 shadow-inner shadow-slate-950/40">
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className={classNames("mt-2 text-xl font-semibold", toneClass)}>{value}</p>
    </div>
  );
}

export function IoTHealthPanel(): JSX.Element {
  const { data, isLoading, error, refetch, isFetching } = useIoTHealth();

  if (isLoading) {
    return <CardSkeleton className="rounded-2xl border border-slate-800 bg-slate-950/60" />;
  }

  if (error || !data) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-6">
        <div className="mb-4 flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-rose-300" />
          <h3 className="text-base font-semibold text-slate-100">IoT Fleet Health</h3>
        </div>
        <ErrorState
          title="IoT feed unavailable"
          message={error instanceof Error ? error.message : "Unable to connect to ChainSense telemetry."}
          onRetry={() => refetch()}
          className="bg-transparent p-0"
        />
      </div>
    );
  }

  const { fleetId, deviceCount, online, offline, degraded, anomalies, asOf, latencySeconds } = data;
  const freshness = formatRelativeTime(asOf);
  const latencyText = typeof latencySeconds === "number" && latencySeconds > 0
    ? `${latencySeconds}s latency`
    : null;

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-950/80 p-6 shadow-inner shadow-slate-950/40">
      <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">ChainSense IoT</p>
          <div className="mt-2 flex items-center gap-2">
            <Radio className="h-4 w-4 text-emerald-300" aria-hidden />
            <h3 className="text-xl font-semibold text-slate-100">IoT Fleet Health</h3>
          </div>
          <p className="mt-1 text-xs text-slate-400">{fleetId}</p>
        </div>
        <div className="flex flex-col items-start gap-2 text-xs text-slate-400 md:items-end">
          <span className="rounded-full border border-slate-700/70 bg-slate-900/60 px-3 py-1 font-semibold uppercase tracking-[0.14em] text-slate-300">
            {freshness === "Unknown" ? "Last sync unknown" : `Synced ${freshness}`}
            {isFetching ? " · Updating…" : ""}
          </span>
          {latencyText && (
            <span className="rounded-full border border-slate-700/70 bg-slate-900/60 px-3 py-1 text-[11px] text-slate-300">
              {latencyText}
            </span>
          )}
        </div>
      </header>

      <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <MetricStat label="Devices Monitored" value={deviceCount.toLocaleString()} tone="good" />
        <MetricStat label="Online" value={online.toLocaleString()} tone="good" />
        <MetricStat label="Offline" value={offline.toLocaleString()} tone={offline > 0 ? "bad" : "good"} />
        <MetricStat label="Degraded" value={degraded.toLocaleString()} tone={degraded > 0 ? "warn" : "good"} />
      </div>

      <div className="mt-6">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Active Anomalies</p>
          <span className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
            {anomalies.length} issue{anomalies.length === 1 ? "" : "s"}
          </span>
        </div>

        {anomalies.length === 0 ? (
          <EmptyState
            title="No anomalies detected"
            subtitle="ChainSense telemetry is clean across the fleet."
            className="rounded-xl border border-slate-800/70 bg-slate-900/40"
          />
        ) : (
          <div className="space-y-3">
            {anomalies.map((anomaly) => {
              const severity: SeverityKey = (anomaly.severity in severityBadge
                ? anomaly.severity
                : "LOW") as SeverityKey;

              return (
                <article
                  key={`${anomaly.deviceId}-${anomaly.lastSeen}`}
                  className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-4"
                >
                  <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <div className="flex items-center gap-3">
                      <span
                        className={classNames(
                          "flex items-center gap-1 rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em]",
                          severityBadge[severity]
                        )}
                      >
                        {severity}
                      </span>
                      <div>
                        <p className="text-sm font-semibold text-slate-100">{anomaly.label}</p>
                        <p className="text-xs text-slate-400">
                          Device {anomaly.deviceId}
                          {anomaly.shipmentReference ? ` · ${anomaly.shipmentReference}` : ""}
                          {anomaly.lane ? ` · ${anomaly.lane}` : ""}
                        </p>
                      </div>
                    </div>
                    <p className="text-xs text-slate-500">Last seen {formatRelativeTime(anomaly.lastSeen)}</p>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}

export default IoTHealthPanel;
