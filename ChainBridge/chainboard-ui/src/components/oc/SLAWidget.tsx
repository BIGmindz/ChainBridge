/**
 * SLAWidget - Operational health status display
 *
 * M04-FRONTEND-FUSION: Enhanced with real IoT device health metrics.
 *
 * Shows real-time SLA metrics + IoT health in OC header:
 * - Queue depth
 * - P95 processing time
 * - Ready/blocked counts
 * - Heartbeat age
 * - Overall health status
 * - IoT device badges (online/offline/stale GPS/stale env)
 */

import { Activity, AlertCircle, AlertTriangle, CheckCircle, Clock, Wifi, WifiOff } from "lucide-react";

import { useIoTHealth } from "../../hooks/useIoTHealth";
import { useSLA } from "../../hooks/useSLA";
import { classNames } from "../../utils/classNames";
import { Skeleton } from "../ui/Skeleton";

export function SLAWidget() {
  const { data: sla, isLoading: slaLoading, error: slaError } = useSLA();
  const { data: iot, isLoading: iotLoading, error: iotError } = useIoTHealth();
  const severeAnomalyCount = iot?.anomalies
    ? iot.anomalies.filter((anomaly) => anomaly.severity === "HIGH" || anomaly.severity === "CRITICAL").length
    : 0;

  if (slaLoading) {
    return (
      <div className="flex items-center gap-3 px-4 py-2 bg-slate-800/50 rounded-lg border border-slate-700">
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-5 w-28" />
      </div>
    );
  }

  if (slaError || !sla) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 rounded-lg border border-slate-700/50">
        <div className="w-2 h-2 rounded-full bg-amber-400/60" />
        <span className="text-xs text-slate-400">SLA data refreshing...</span>
      </div>
    );
  }

  // Determine status color
  const statusConfig = {
    healthy: {
      icon: CheckCircle,
      color: "text-emerald-400",
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/30",
    },
    degraded: {
      icon: AlertTriangle,
      color: "text-amber-400",
      bg: "bg-amber-500/10",
      border: "border-amber-500/30",
    },
    critical: {
      icon: AlertCircle,
      color: "text-rose-400",
      bg: "bg-rose-500/10",
      border: "border-rose-500/30",
    },
  };

  const config = statusConfig[sla.status];
  const StatusIcon = config.icon;

  return (
    <div
      className={classNames(
        "flex items-center gap-4 px-4 py-2 rounded-lg border transition-colors",
        config.bg,
        config.border
      )}
    >
      {/* Status Indicator */}
      <div className="flex items-center gap-2">
        <StatusIcon className={classNames("h-4 w-4", config.color)} />
        <span className={classNames("text-xs font-medium uppercase", config.color)}>
          {sla.status}
        </span>
      </div>

      {/* Queue Depth */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs text-slate-400">Queue:</span>
        <span className="text-sm font-mono font-semibold text-slate-200">
          {sla.queue_depth}
        </span>
      </div>

      {/* P95 Processing Time */}
      <div className="flex items-center gap-1.5">
        <Clock className="h-3.5 w-3.5 text-slate-400" />
        <span className="text-xs text-slate-400">P95:</span>
        <span className="text-sm font-mono font-semibold text-slate-200">
          {sla.p95_processing_time_seconds.toFixed(1)}s
        </span>
      </div>

      {/* Ready vs Blocked */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-emerald-400" />
          <span className="text-xs text-slate-400">Ready:</span>
          <span className="text-sm font-mono font-semibold text-emerald-300">
            {sla.ready_count}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-rose-400" />
          <span className="text-xs text-slate-400">Blocked:</span>
          <span className="text-sm font-mono font-semibold text-rose-300">
            {sla.blocked_count}
          </span>
        </div>
      </div>

      {/* Heartbeat Age */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs text-slate-400">Heartbeat:</span>
        <span
          className={classNames(
            "text-sm font-mono font-semibold",
            sla.heartbeat_age_seconds < 60
              ? "text-emerald-300"
              : sla.heartbeat_age_seconds < 120
              ? "text-amber-300"
              : "text-rose-300"
          )}
        >
          {sla.heartbeat_age_seconds}s
        </span>
      </div>

      {/* Vertical Divider */}
      <div className="h-6 w-px bg-slate-600" />

      {/* IoT Health Badges */}
      {iotLoading ? (
        <Skeleton className="h-5 w-48" />
      ) : iotError || !iot ? (
        <div className="flex items-center gap-1.5">
          <WifiOff className="h-3.5 w-3.5 text-slate-500" />
          <span className="text-xs text-slate-500">IoT Unavailable</span>
        </div>
      ) : (
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <Wifi className="h-3.5 w-3.5 text-emerald-400" />
            <span className="text-xs text-slate-400">Online:</span>
            <span className="text-sm font-mono font-semibold text-emerald-300">
              {iot.online.toLocaleString()}
            </span>
          </div>

          {iot.offline > 0 && (
            <div className="flex items-center gap-1.5">
              <WifiOff className="h-3.5 w-3.5 text-rose-400" />
              <span className="text-xs text-slate-400">Offline:</span>
              <span className="text-sm font-mono font-semibold text-rose-300">
                {iot.offline.toLocaleString()}
              </span>
            </div>
          )}

          {iot.degraded > 0 && (
            <div className="flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5 text-amber-400" />
              <span className="text-xs text-slate-400">Degraded:</span>
              <span className="text-sm font-mono font-semibold text-amber-300">
                {iot.degraded.toLocaleString()}
              </span>
            </div>
          )}

          {severeAnomalyCount > 0 && (
            <div className="flex items-center gap-1.5">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
              <span className="text-xs text-slate-400">Critical Alerts:</span>
              <span className="text-sm font-mono font-semibold text-amber-300">
                {severeAnomalyCount}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
