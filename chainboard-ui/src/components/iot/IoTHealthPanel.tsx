import React from 'react';

import { useIoTHealth } from '../../hooks/useIoTHealth';
import { IoTDeviceHealth } from '../../types/iot';

function statusColor(status: string): string {
  switch (status) {
    case 'online':
      return 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/40';
    case 'degraded':
      return 'bg-amber-500/15 text-amber-300 border border-amber-500/40';
    case 'offline':
      return 'bg-rose-500/15 text-rose-300 border border-rose-500/40';
    default:
      return 'bg-slate-500/15 text-slate-300 border border-slate-500/40';
  }
}

function formatHeartbeat(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString();
}

function confidencePercent(conf?: number): number | null {
  if (typeof conf !== 'number' || !Number.isFinite(conf)) return null;
  return Math.round(conf * 100);
}

function confidenceLabel(conf?: number): string | null {
  if (typeof conf !== 'number' || !Number.isFinite(conf)) return null;
  if (conf >= 0.9) return 'High';
  if (conf >= 0.7) return 'Medium';
  return 'Low';
}

export const IoTHealthPanel: React.FC = () => {
  const { data, isLoading, error, refetch } = useIoTHealth();

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold tracking-wide text-slate-100 uppercase">
            IoT Health
          </h2>
          <div className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
        </div>
        <div className="space-y-2">
          <div className="h-4 w-1/3 rounded-full bg-slate-800 animate-pulse" />
          <div className="h-3 w-2/3 rounded-full bg-slate-800 animate-pulse" />
          <div className="h-20 w-full rounded-2xl bg-slate-900 animate-pulse" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-2xl border border-rose-800/60 bg-rose-950/60 p-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold tracking-wide text-rose-100 uppercase">
            IoT Health
          </h2>
          <span className="inline-flex items-center rounded-full bg-rose-500/20 px-2 py-0.5 text-[10px] font-medium text-rose-200">
            Fault
          </span>
        </div>
        <p className="text-xs text-rose-100 mb-3">
          Unable to load IoT health. Check connectivity to the ChainSense
          service and retry.
        </p>
        <button
          type="button"
          onClick={refetch}
          className="inline-flex items-center rounded-full bg-rose-500/90 px-3 py-1 text-xs font-medium text-rose-50 hover:bg-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-400/70 focus:ring-offset-2 focus:ring-offset-slate-950"
        >
          Retry
        </button>
      </div>
    );
  }

  const devices: IoTDeviceHealth[] = data.devices ?? [];
  const onlineCount = devices.filter((d) => d.status === 'online').length;
  const degradedCount = devices.filter((d) => d.status === 'degraded').length;
  const offlineCount = devices.filter((d) => d.status === 'offline').length;

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-sm backdrop-blur">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h2 className="text-sm font-semibold tracking-wide text-slate-100 uppercase">
            IoT Health
          </h2>
          <p className="text-[11px] text-slate-400">
            ChainSense device heartbeat, risk & signal confidence
          </p>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-slate-300">
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>{onlineCount} online</span>
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
            <span>{degradedCount} degraded</span>
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/10 px-2 py-0.5">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
            <span>{offlineCount} offline</span>
          </span>
        </div>
      </div>

      <div className="space-y-2 max-h-56 overflow-y-auto pr-1 custom-scrollbars">
        {devices.map((device) => (
          <div
            key={device.id}
            className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2"
          >
            <div>
              <p className="text-xs font-medium text-slate-100">
                {device.name}
              </p>
              <p className="text-[10px] text-slate-400">
                Last heartbeat: {formatHeartbeat(device.last_heartbeat)}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span
                className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium capitalize ${statusColor(
                  device.status,
                )}`}
              >
                {device.status}
              </span>
              <div className="flex flex-col items-end">
                <span className="text-[10px] font-semibold text-slate-100">
                  Risk {device.risk_score.toFixed(1)}
                </span>
                {(() => {
                  const percent = confidencePercent(device.signal_confidence);
                  const label = confidenceLabel(device.signal_confidence);
                  if (percent === null || !label) return null;
                  return (
                    <span className="text-[10px] text-slate-400">
                      Conf: {percent}% ({label})
                    </span>
                  );
                })()}
              </div>
            </div>
          </div>
        ))}

        {devices.length === 0 && (
          <p className="text-xs text-slate-400">
            No IoT devices reported by ChainSense yet.
          </p>
        )}
      </div>
    </div>
  );
};
