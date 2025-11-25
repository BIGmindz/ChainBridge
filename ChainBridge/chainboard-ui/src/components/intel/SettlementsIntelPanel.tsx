/**
 * SettlementsIntelPanel Component
 *
 * Shows Smart Settlements intelligence: capital metrics, blocked milestones.
 * Integrates with real-time payment event stream.
 */

import { DollarSign, Lock, Unlock } from "lucide-react";

import { usePaymentQueue } from "../../hooks/usePaymentQueue";

interface SettlementsIntelPanelProps {
  emphasize?: boolean;
  onBlockedCapitalClick?: () => void;
}

export default function SettlementsIntelPanel({
  emphasize = false,
  onBlockedCapitalClick,
}: SettlementsIntelPanelProps): JSX.Element {
  const { data: queue, loading, error } = usePaymentQueue();

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-800/70 bg-slate-900/50 p-6">
        <div className="flex items-center gap-3">
          <DollarSign className="h-5 w-5 text-slate-500" />
          <h3 className="text-base font-semibold text-slate-100">Smart Settlements</h3>
        </div>
        <div className="mt-4 text-sm text-slate-400">Loading settlements...</div>
      </div>
    );
  }

  if (error || !queue) {
    return (
      <div className="rounded-xl border border-slate-800/70 bg-slate-900/50 p-6">
        <div className="flex items-center gap-3">
          <DollarSign className="h-5 w-5 text-slate-500" />
          <h3 className="text-base font-semibold text-slate-100">Smart Settlements</h3>
        </div>
        <div className="mt-4 text-sm text-red-400">Failed to load settlements</div>
      </div>
    );
  }

  const blockedCount = queue.items.length;
  const blockedCapital = queue.items.reduce((sum, item) => sum + Number(item.holds_usd), 0);

  // Mock data for released/settled (TODO: get from actual API)
  const releasedLast24h = 127500;
  const settledLast7d = 842000;

  const emphasisClass = emphasize
    ? "border-emerald-500/50 bg-emerald-500/5"
    : "border-slate-800/70 bg-slate-900/50";

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <div className={`rounded-xl border ${emphasisClass} p-6`}>
      {/* Header with LIVE badge */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <DollarSign className="h-5 w-5 text-slate-400" />
          <h3 className="text-base font-semibold text-slate-100">Smart Settlements</h3>
        </div>
        <div className="flex items-center gap-1 rounded-full border border-emerald-500/50 bg-emerald-500/10 px-2 py-0.5">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
          <span className="text-[9px] font-semibold uppercase tracking-wider text-emerald-300">
            LIVE
          </span>
        </div>
      </div>

      {/* Capital Metrics */}
      <div className="mb-4 space-y-3">
        <button
          type="button"
          onClick={() => onBlockedCapitalClick?.()}
          className="w-full rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-left transition-colors hover:border-red-500/50 hover:bg-red-500/20"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Lock className="h-4 w-4 text-red-400" />
              <span className="text-xs font-medium text-red-300">Blocked Capital</span>
            </div>
            <div className="text-right">
              <div className="text-lg font-bold text-red-400">{formatCurrency(blockedCapital)}</div>
              <div className="text-[10px] text-red-300">{blockedCount} milestones</div>
            </div>
          </div>
        </button>

        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-2">
            <div className="flex items-center gap-1.5">
              <Unlock className="h-3.5 w-3.5 text-emerald-400" />
              <span className="text-[10px] font-medium text-emerald-300">Released (24h)</span>
            </div>
            <div className="mt-1 text-sm font-bold text-emerald-400">
              {formatCurrency(releasedLast24h)}
            </div>
          </div>
          <div className="rounded-lg border border-blue-500/30 bg-blue-500/10 p-2">
            <div className="flex items-center gap-1.5">
              <DollarSign className="h-3.5 w-3.5 text-blue-400" />
              <span className="text-[10px] font-medium text-blue-300">Settled (7d)</span>
            </div>
            <div className="mt-1 text-sm font-bold text-blue-400">
              {formatCurrency(settledLast7d)}
            </div>
          </div>
        </div>
      </div>

      {/* Status */}
      <div className="flex items-center justify-between rounded-lg border border-slate-800/50 bg-slate-950/50 p-2">
        <span className="text-xs text-slate-400">Settlement velocity</span>
        <span className="text-xs font-semibold text-emerald-400">Normal</span>
      </div>

      {/* TODO Comment */}
      <p className="mt-3 text-[9px] text-slate-600">
        TODO: Add trend charts and milestone timeline.
      </p>
    </div>
  );
}
