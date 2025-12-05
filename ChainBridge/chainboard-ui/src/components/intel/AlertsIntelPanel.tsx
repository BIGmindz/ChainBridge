/**
 * AlertsIntelPanel Component
 *
 * Shows real-time alerts intelligence: total count, severity breakdown,
 * and most recent critical alerts.
 */

import { Bell, AlertCircle } from "lucide-react";

import type { ControlTowerAlert } from "../../core/types/alerts";
import { useAlertsFeed } from "../../hooks/useAlertsFeed";

interface AlertsIntelPanelProps {
  emphasize?: boolean;
  onAlertClick?: (alertId: string) => void;
}

export default function AlertsIntelPanel({ emphasize = false, onAlertClick }: AlertsIntelPanelProps): JSX.Element {
  const { alerts, loading, error } = useAlertsFeed({ limit: 10 });

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-800/70 bg-slate-900/50 p-6">
        <div className="flex items-center gap-3">
          <Bell className="h-5 w-5 text-slate-500" />
          <h3 className="text-base font-semibold text-slate-100">Alerts Intelligence</h3>
        </div>
        <div className="mt-4 text-sm text-slate-400">Loading alerts...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-slate-800/70 bg-slate-900/50 p-6">
        <div className="flex items-center gap-3">
          <Bell className="h-5 w-5 text-slate-500" />
          <h3 className="text-base font-semibold text-slate-100">Alerts Intelligence</h3>
        </div>
        <div className="mt-4 text-sm text-red-400">Failed to load alerts</div>
      </div>
    );
  }

  const activeAlerts = alerts || [];
  const criticalCount = activeAlerts.filter((a: ControlTowerAlert) => a.severity === "critical").length;
  const warningCount = activeAlerts.filter((a: ControlTowerAlert) => a.severity === "warning").length;
  const infoCount = activeAlerts.filter((a: ControlTowerAlert) => a.severity === "info").length;
  const recentAlerts = activeAlerts.slice(0, 3);

  const emphasisClass = emphasize
    ? "border-amber-500/50 bg-amber-500/5"
    : "border-slate-800/70 bg-slate-900/50";

  return (
    <div className={`rounded-xl border ${emphasisClass} p-6`}>
      {/* Header with LIVE badge */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Bell className="h-5 w-5 text-slate-400" />
          <h3 className="text-base font-semibold text-slate-100">Alerts Intelligence</h3>
        </div>
        <div className="flex items-center gap-1 rounded-full border border-emerald-500/50 bg-emerald-500/10 px-2 py-0.5">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
          <span className="text-[9px] font-semibold uppercase tracking-wider text-emerald-300">
            LIVE
          </span>
        </div>
      </div>

      {/* Severity Breakdown */}
      <div className="mb-4 grid grid-cols-3 gap-2">
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2">
          <div className="text-2xl font-bold text-red-400">{criticalCount}</div>
          <div className="text-[10px] uppercase tracking-wide text-red-300">Critical</div>
        </div>
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2">
          <div className="text-2xl font-bold text-amber-400">{warningCount}</div>
          <div className="text-[10px] uppercase tracking-wide text-amber-300">Warning</div>
        </div>
        <div className="rounded-lg border border-slate-500/30 bg-slate-500/10 px-3 py-2">
          <div className="text-2xl font-bold text-slate-400">{infoCount}</div>
          <div className="text-[10px] uppercase tracking-wide text-slate-300">Info</div>
        </div>
      </div>

      {/* Recent Alerts */}
      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Recent Alerts
        </h4>
        <div className="space-y-2">
          {recentAlerts.length === 0 ? (
            <p className="text-xs text-slate-600">No active alerts</p>
          ) : (
            recentAlerts.map((alert: ControlTowerAlert) => (
              <button
                key={alert.id}
                type="button"
                onClick={() => onAlertClick?.(alert.id)}
                className="flex w-full items-start gap-2 rounded-lg border border-slate-800/50 bg-slate-950/50 p-2 text-left transition-colors hover:border-slate-700 hover:bg-slate-900/70"
              >
                <AlertCircle className={`mt-0.5 h-3.5 w-3.5 flex-shrink-0 ${
                  alert.severity === "critical" ? "text-red-400" :
                  alert.severity === "warning" ? "text-amber-400" :
                  "text-slate-400"
                }`} />
                <div className="flex-1 overflow-hidden">
                  <p className="truncate text-xs font-medium text-slate-200">{alert.title}</p>
                  <p className="text-[10px] text-slate-500">
                    {alert.source} • {new Date(alert.createdAt).toLocaleTimeString()}
                  </p>
                </div>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
