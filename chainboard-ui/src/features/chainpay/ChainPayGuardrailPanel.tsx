import React from 'react';
import clsx from 'clsx';

import type { GuardrailStatusSnapshot, GuardrailState, TierGuardrailStatus } from '../../types/chainpayGuardrails';
import { formatGuardrailStateLabel } from '../../types/chainpayGuardrails';
import { formatSettlementProvider } from '../../types/chainpay';

interface ChainPayGuardrailPanelProps {
  snapshot?: GuardrailStatusSnapshot | null;
  loading?: boolean;
  error?: Error | null;
  onRefresh?: () => void;
}

function guardrailBadgeClasses(state?: GuardrailState) {
  if (state === 'GREEN') return 'bg-emerald-500/15 text-emerald-200 border-emerald-400/60';
  if (state === 'AMBER') return 'bg-amber-500/15 text-amber-200 border-amber-400/60';
  if (state === 'RED') return 'bg-red-500/15 text-red-200 border-red-400/60';
  return 'bg-slate-700/60 text-slate-200 border-slate-500/60';
}

function tierBadgeClasses(state: GuardrailState) {
  if (state === 'GREEN') return 'bg-emerald-500/10 text-emerald-200 border-emerald-400/60';
  if (state === 'AMBER') return 'bg-amber-500/10 text-amber-200 border-amber-400/60';
  return 'bg-red-500/10 text-red-200 border-red-400/60';
}

function renderTierMetrics(tier: TierGuardrailStatus) {
  const lossPct = `${(tier.lossRate * 100).toFixed(1)}%`;
  const slaPct = `${(tier.cashSlaBreachRate * 100).toFixed(1)}%`;
  const d2p95 = `${tier.d2P95Days.toFixed(1)}d`;
  const reserve = `${(tier.unusedReserveRatio * 100).toFixed(1)}%`;

  return (
    <div className="text-[11px] text-slate-300">
      Loss {lossPct} · Cash SLA {slaPct} · D2 p95 {d2p95} · Unused reserve {reserve}
    </div>
  );
}

export const ChainPayGuardrailPanel: React.FC<ChainPayGuardrailPanelProps> = ({
  snapshot,
  loading,
  error,
  onRefresh,
}) => {
  const refreshButton = onRefresh ? (
    <button
      type="button"
      onClick={onRefresh}
      disabled={loading}
      className="text-[11px] text-slate-300 hover:text-slate-100 disabled:opacity-50"
    >
      Refresh
    </button>
  ) : null;

  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-sm">
        <div className="flex items-start justify-between">
          <h2 className="text-sm font-semibold text-slate-100 tracking-wide">Guardrails – USD→MXN</h2>
          <span className="text-[11px] text-slate-400">Loading…</span>
        </div>
        <div className="mt-3 h-24 rounded-xl bg-slate-800/60 animate-pulse" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-red-700/60 bg-red-950/70 p-4 shadow-sm">
        <div className="flex items-start justify-between">
          <h2 className="text-sm font-semibold text-red-100 tracking-wide">Guardrails – USD→MXN</h2>
          <div className="flex items-center gap-3">
            {refreshButton}
            <span className="text-[11px] text-red-200">Error</span>
          </div>
        </div>
        <p className="text-xs text-red-200 mt-1">Unable to load guardrail status. Please retry.</p>
      </div>
    );
  }

  if (!snapshot) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-sm">
        <div className="flex items-start justify-between">
          <h2 className="text-sm font-semibold text-slate-100 tracking-wide">Guardrails – USD→MXN</h2>
          {refreshButton}
        </div>
        <p className="text-xs text-slate-400 mt-1">No guardrail data available yet.</p>
      </div>
    );
  }

  const badgeClass = guardrailBadgeClasses(snapshot.overallState);
  const providerLabel = snapshot.settlementProvider
    ? formatSettlementProvider(snapshot.settlementProvider)
    : 'Unknown';

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-sm space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-100 tracking-wide">Guardrails – USD→MXN</h2>
          <p className="text-[11px] text-slate-400 mt-1">
            Corridor USD→MXN · Policy P0 · Rail {providerLabel}
          </p>
          <p className="text-[10px] text-slate-500 mt-0.5">
            Last evaluated {new Date(snapshot.lastEvaluatedAt).toLocaleString()}
          </p>
        </div>
        <div className="text-right space-y-1">
          <span
            className={clsx(
              'inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-semibold',
              badgeClass,
            )}
          >
            {formatGuardrailStateLabel(snapshot.overallState)}
          </span>
          <div className="text-[11px] text-slate-400">{refreshButton}</div>
        </div>
      </div>

      {snapshot.perTier.length > 0 ? (
        <div className="space-y-2">
          <div className="text-[11px] font-semibold text-slate-300">Per tier</div>
          <div className="space-y-2">
            {snapshot.perTier.map((tier) => (
              <div
                key={`${tier.tier}-${tier.state}`}
                className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/50 px-3 py-2"
              >
                <div className="space-y-1">
                  <div className="text-xs font-semibold text-slate-100">Tier {tier.tier}</div>
                  {renderTierMetrics(tier)}
                </div>
                <span
                  className={clsx(
                    'inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
                    tierBadgeClasses(tier.state),
                  )}
                >
                  {tier.state}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="text-[11px] text-slate-400">No per-tier guardrail data available.</div>
      )}
    </div>
  );
};
