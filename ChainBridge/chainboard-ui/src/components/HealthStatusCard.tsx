/**
 * HealthStatusCard Component
 *
 * DECISION CONTEXT:
 * Answers: "Can I trust the ChainBridge system for live operational decisions right now?"
 *
 * For operators/engineers:
 * - Is the backend responsive?
 * - What version is running? (critical for debugging after deploys)
 * - When was the last successful health check?
 *
 * UX:
 * - Non-blocking: loads independently, won't freeze the dashboard
 * - Clear states: loading, success, error with retry
 * - Minimal: fits in a compact card, SOC-style clean
 */

import { Activity, AlertCircle, RefreshCw } from 'lucide-react';
import { useEffect, useState } from 'react';

import { apiGet } from '../lib/apiClient';

type HealthResponse = {
  status: string;
  version: string;
  timestamp: string;
  modules_loaded?: number;
  active_pipelines?: number;
};

type LoadingState = 'idle' | 'loading' | 'success' | 'error';

export function HealthStatusCard() {
  const [state, setState] = useState<LoadingState>('idle');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    setState('loading');
    setError(null);

    try {
      const data = await apiGet<HealthResponse>('/health');
      setHealth(data);
      setState('success');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch health status');
      setState('error');
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  const formatTimestamp = (isoString: string): string => {
    try {
      const date = new Date(isoString);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-lg p-6 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-cyan-400" />
          <h2 className="text-lg font-semibold text-slate-100">System Health</h2>
        </div>

        {state === 'success' && (
          <button
            onClick={fetchHealth}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition-colors"
            title="Refresh health status"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Loading State */}
      {state === 'loading' && (
        <div className="space-y-3 animate-pulse">
          <div className="h-4 bg-slate-800 rounded w-3/4"></div>
          <div className="h-4 bg-slate-800 rounded w-1/2"></div>
          <div className="h-4 bg-slate-800 rounded w-2/3"></div>
        </div>
      )}

      {/* Success State */}
      {state === 'success' && health && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-400 font-mono">Status:</span>
            <span
              className={`px-2 py-1 rounded text-xs font-semibold uppercase ${
                health.status === 'healthy'
                  ? 'bg-emerald-500/10 text-emerald-300'
                  : 'bg-amber-500/10 text-amber-300'
              }`}
            >
              {health.status}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-400 font-mono">Version:</span>
            <span className="text-sm text-slate-200 font-mono">{health.version}</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-400 font-mono">Last Check:</span>
            <span className="text-sm text-slate-300">{formatTimestamp(health.timestamp)}</span>
          </div>

          {health.modules_loaded !== undefined && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-400 font-mono">Modules:</span>
              <span className="text-sm text-slate-300">{health.modules_loaded}</span>
            </div>
          )}
        </div>
      )}

      {/* Error State */}
      {state === 'error' && (
        <div className="space-y-3">
          <div className="flex items-start gap-2 text-red-400">
            <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium">Health check failed</p>
              <p className="text-xs text-red-300 mt-1 font-mono">{error}</p>
            </div>
          </div>

          <button
            onClick={fetchHealth}
            className="w-full px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded transition-colors text-sm font-medium"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
}
