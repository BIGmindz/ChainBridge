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

import { AlertCircle, AlertTriangle, CheckCircle, Clock, MapPin, Thermometer, Wifi, WifiOff } from "lucide-react";

import { useIoTHealth } from "../../hooks/useIoTHealth";
import { useSLA } from "../../hooks/useSLA";
import { classNames } from "../../utils/classNames";
import { Skeleton } from "../ui/Skeleton";

export function SLAWidget() {
  const { data: sla, isLoading: slaLoading, error: slaError } = useSLA();
  const { data: iot, isLoading: iotLoading, error: iotError } = useIoTHealth();

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
      <div className="flex items-center gap-2 px-4 py-2 bg-rose-950/20 rounded-lg border border-rose-700/50">
        <AlertCircle className="h-4 w-4 text-rose-400" />
        <span className="text-xs text-rose-300">SLA Unavailable</span>
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
          {/* Devices Online */}
          <div className="flex items-center gap-1.5">
            <Wifi className="h-3.5 w-3.5 text-emerald-400" />
            <span className="text-xs text-slate-400">Online:</span>
            <span className="text-sm font-mono font-semibold text-emerald-300">
              {iot.summary.devices_online}
            </span>
          </div>

          {/* Devices Offline */}
          {iot.summary.devices_offline > 0 && (
            <div className="flex items-center gap-1.5">
              <WifiOff className="h-3.5 w-3.5 text-rose-400" />
              <span className="text-xs text-slate-400">Offline:</span>
              <span className="text-sm font-mono font-semibold text-rose-300">
                {iot.summary.devices_offline}
              </span>
            </div>
          )}

          {/* Stale GPS */}
          {iot.summary.devices_stale_gps > 0 && (
            <div className="flex items-center gap-1.5">
              <MapPin className="h-3.5 w-3.5 text-amber-400" />
              <span className="text-xs text-slate-400">Stale GPS:</span>
              <span className="text-sm font-mono font-semibold text-amber-300">
                {iot.summary.devices_stale_gps}
              </span>
            </div>
          )}

          {/* Stale Environment Sensors */}
          {iot.summary.devices_stale_env > 0 && (
            <div className="flex items-center gap-1.5">
              <Thermometer className="h-3.5 w-3.5 text-amber-400" />
              <span className="text-xs text-slate-400">Stale Env:</span>
              <span className="text-sm font-mono font-semibold text-amber-300">
                {iot.summary.devices_stale_env}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
