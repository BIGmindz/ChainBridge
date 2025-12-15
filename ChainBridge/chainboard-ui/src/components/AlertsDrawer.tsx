import React, { useState } from "react";

import { AlertStatus, ControlTowerAlert } from "../core/types/alerts";
import { useAlertsFeed } from "../hooks/useAlertsFeed";

interface AlertsDrawerProps {
  open: boolean;
  onClose: () => void;
  onNavigateToShipment?: (shipmentRef: string) => void;
}

export const AlertsDrawer: React.FC<AlertsDrawerProps> = ({
  open,
  onClose,
  onNavigateToShipment,
}) => {
  const { alerts, loading, error, refresh, isLive } = useAlertsFeed({
    status: "open",
    limit: 50,
  });

  const [localStatus, setLocalStatus] = useState<Record<string, AlertStatus>>({});

  if (!open) return null;

  const visibleAlerts: ControlTowerAlert[] =
    alerts?.map((a) => ({
      ...a,
      status: localStatus[a.id] ?? a.status,
    })) ?? [];

  const handleUpdate = (id: string, status: AlertStatus) => {
    setLocalStatus((prev) => ({ ...prev, [id]: status }));
  };

  const severityClass = (severity: string) => {
    const base = "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold";
    if (severity === "critical") return `${base} bg-rose-100 text-rose-700`;
    if (severity === "warning") return `${base} bg-amber-100 text-amber-700`;
    return `${base} bg-slate-100 text-slate-600`;
  };

  return (
    <aside className="fixed right-0 top-0 z-40 h-full w-full max-w-md border-l border-slate-200 bg-white shadow-xl">
      <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-slate-900">Alerts</h2>
            {isLive && (
              <span className="flex items-center gap-1 text-[10px] text-emerald-500 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Live
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500">
            Open issues across risk, IoT, payments, and customs.
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-xs text-slate-500 hover:text-slate-900"
        >
          Close
        </button>
      </header>

      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-2 text-xs">
        <button
          type="button"
          onClick={refresh}
          className="rounded border border-slate-200 px-2 py-1 text-slate-600 hover:bg-slate-50"
        >
          Refresh
        </button>
        {loading && <span className="text-slate-400">Loading…</span>}
        {error && <span className="text-rose-500">Failed to load alerts. Try again.</span>}
      </div>

      <div className="h-[calc(100%-96px)] overflow-y-auto px-4 py-3">
        {visibleAlerts.length === 0 && !loading && (
          <p className="text-xs text-slate-500">No open alerts. You&apos;re all clear.</p>
        )}

        <ul className="space-y-3">
          {visibleAlerts.map((alert) => (
            <li key={alert.id} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="text-xs font-semibold text-slate-900">{alert.title}</span>
                <span className={severityClass(alert.severity)}>
                  {alert.severity.toUpperCase()}
                </span>
              </div>

              <p className="mb-1 text-[11px] text-slate-600">{alert.description}</p>

              <div className="mb-2 flex flex-wrap items-center gap-2 text-[10px] text-slate-500">
                {alert.source === "iot" && onNavigateToShipment ? (
                  <button
                    type="button"
                    onClick={() => onNavigateToShipment(alert.shipment_reference)}
                    className="text-blue-600 hover:text-blue-700 font-medium underline"
                  >
                    Shipment: {alert.shipment_reference}
                  </button>
                ) : (
                  <span>Shipment: {alert.shipment_reference}</span>
                )}
                <span>Source: {alert.source}</span>
                <span>
                  Created:{" "}
                  {new Date(alert.createdAt).toLocaleString(undefined, {
                    month: "short",
                    day: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
                {alert.tags?.length > 0 && (
                  <span>
                    Tags: {alert.tags.slice(0, 3).join(",")}
                    {alert.tags.length > 3 ? "…" : ""}
                  </span>
                )}
              </div>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => handleUpdate(alert.id, "acknowledged")}
                  className="rounded border border-slate-200 px-2 py-1 text-[11px] text-slate-700 hover:bg-slate-100"
                >
                  Acknowledge
                </button>
                <button
                  type="button"
                  onClick={() => handleUpdate(alert.id, "resolved")}
                  className="rounded bg-emerald-500 px-2 py-1 text-[11px] font-semibold text-white hover:bg-emerald-400"
                >
                  Resolve
                </button>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
};
