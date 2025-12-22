import React from 'react';
import clsx from 'clsx';

import type { SettlementStatus, SettlementMilestone } from '../../types/chainpay';
import { formatSettlementProvider } from '../../types/chainpay';

interface ChainPaySettlementPanelProps {
  status?: SettlementStatus | null;
  loading?: boolean;
  error?: Error | null;
  onRefresh?: () => void;
  corridorLabel?: string;
  policyLabel?: string;
  assetLabel?: string;
}

const milestoneOrder: SettlementMilestone[] = [
  'PICKUP',
  'IN_TRANSIT',
  'DELIVERED',
  'CLAIM_WINDOW',
  'FINALIZED',
];

const milestoneLabels: Record<SettlementMilestone, string> = {
  PICKUP: 'Pickup',
  IN_TRANSIT: 'In Transit',
  DELIVERED: 'Delivered',
  CLAIM_WINDOW: 'Claim Window',
  FINALIZED: 'Finalized',
};

function riskBadge(score?: number) {
  if (typeof score !== 'number') {
    return (
      <span className="inline-flex items-center rounded-full border border-slate-700 bg-slate-800 px-2 py-0.5 text-[11px] text-slate-200">
        Risk: n/a
      </span>
    );
  }
  const level = score >= 70 ? 'high' : score >= 40 ? 'medium' : 'low';
  const classes = {
    high: 'border-red-400/70 bg-red-500/10 text-red-200',
    medium: 'border-amber-400/70 bg-amber-500/10 text-amber-200',
    low: 'border-emerald-400/70 bg-emerald-500/10 text-emerald-200',
  }[level];

  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold',
        classes,
      )}
    >
      Risk {score.toFixed(0)} / 100
    </span>
  );
}

function formatAmount(amount: number) {
  return amount.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

export const ChainPaySettlementPanel: React.FC<ChainPaySettlementPanelProps> = ({
  status,
  loading,
  error,
  onRefresh,
  corridorLabel,
  policyLabel,
  assetLabel,
}) => {
  const corridor = corridorLabel ?? status?.corridor ?? 'USD→MXN';
  const policy = policyLabel ?? 'P0';
  const asset = assetLabel ?? 'CB-USDx';
  const rail = formatSettlementProvider(status?.settlementProvider);

  const headerBadges = (
    <div className="flex flex-wrap items-center gap-2 text-[10px] text-slate-300">
      <span className="rounded-full border border-slate-700 bg-slate-800/70 px-2 py-0.5">
        Corridor {corridor}
      </span>
      <span className="rounded-full border border-slate-700 bg-slate-800/70 px-2 py-0.5">
        Policy {policy}
      </span>
      <span className="rounded-full border border-slate-700 bg-slate-800/70 px-2 py-0.5">
        Asset {asset}
      </span>
      <span className="rounded-full border border-slate-700 bg-slate-800/70 px-2 py-0.5">
        Rail {rail}
      </span>
    </div>
  );

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
        <div className="flex items-start justify-between mb-2">
          <h2 className="text-sm font-semibold text-slate-100 tracking-wide">
            ChainPay Settlement
          </h2>
          <span className="text-[11px] text-slate-400">Loading…</span>
        </div>
        {headerBadges}
        <div className="h-24 rounded-xl bg-slate-800/60 animate-pulse" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-red-700/60 bg-red-950/70 p-4 shadow-sm">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold text-red-100 tracking-wide">
            ChainPay Settlement
          </h2>
          <div className="flex items-center gap-3">
            {refreshButton}
            <span className="text-[11px] text-red-200">Error</span>
          </div>
        </div>
        {headerBadges}
        <p className="text-xs text-red-200">
          Unable to load settlement status. Please verify the ChainPay service.
        </p>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-sm">
        <div className="flex items-start justify-between mb-2">
          <h2 className="text-sm font-semibold text-slate-100 tracking-wide">
            ChainPay Settlement
          </h2>
          {refreshButton}
        </div>
        {headerBadges}
        <p className="text-xs text-slate-400 mt-1">
          No settlement data available for this shipment.
        </p>
      </div>
    );
  }

  const currentIndex = milestoneOrder.indexOf(status.currentMilestone);
  const percentReleased = status.cbUsd.total > 0
    ? Math.min(100, Math.round((status.cbUsd.released / status.cbUsd.total) * 100))
    : 0;
  const percentReserved = status.cbUsd.total > 0
    ? Math.min(100, Math.round((status.cbUsd.reserved / status.cbUsd.total) * 100))
    : 0;

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-100 tracking-wide">ChainPay Settlement</h2>
          <p className="text-xs text-slate-400 mt-1">Shipment {status.shipmentId}</p>
          <div className="mt-1">{headerBadges}</div>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Current milestone: <span className="text-slate-100">{milestoneLabels[status.currentMilestone]}</span>
          </p>
        </div>
        <div className="text-right">
          {riskBadge(status.riskScore)}
          <p className="text-[11px] text-slate-500 mt-1">CB-USDx</p>
          <p className="text-xs font-semibold text-slate-100">
            {formatAmount(status.cbUsd.total)} total
          </p>
          {refreshButton}
        </div>
      </div>

      <div className="mt-4">
        <div className="flex items-center justify-between text-[11px] text-slate-400 mb-2">
          <span>Milestones</span>
          <span>{currentIndex + 1} / {milestoneOrder.length}</span>
        </div>
        <div className="grid grid-cols-5 gap-2">
          {milestoneOrder.map((milestone, idx) => {
            const done = idx < currentIndex;
            const current = idx === currentIndex;
            return (
              <div
                key={milestone}
                className={clsx(
                  'rounded-lg border px-2 py-2 text-center text-[11px] font-medium transition',
                  done && 'border-emerald-500/60 bg-emerald-500/10 text-emerald-200',
                  current && !done && 'border-amber-500/70 bg-amber-500/10 text-amber-100',
                  !done && !current && 'border-slate-800 bg-slate-900 text-slate-400',
                )}
              >
                <div>{milestoneLabels[milestone]}</div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-3 text-xs text-slate-200">
        <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-3">
          <div className="text-[11px] text-slate-400">CB-USDx Total</div>
          <div className="text-lg font-semibold text-slate-100">
            {formatAmount(status.cbUsd.total)}
          </div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-3">
          <div className="text-[11px] text-slate-400">Released</div>
          <div className="text-lg font-semibold text-emerald-200">
            {formatAmount(status.cbUsd.released)}
          </div>
          <div className="mt-1 h-2 rounded bg-slate-800">
            <div
              className="h-2 rounded bg-emerald-500"
              style={{ width: `${percentReleased}%` }}
            />
          </div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-3">
          <div className="text-[11px] text-slate-400">Reserved</div>
          <div className="text-lg font-semibold text-amber-200">
            {formatAmount(status.cbUsd.reserved)}
          </div>
          <div className="mt-1 h-2 rounded bg-slate-800">
            <div
              className="h-2 rounded bg-amber-500"
              style={{ width: `${percentReserved}%` }}
            />
          </div>
        </div>
      </div>

      <div className="mt-4">
        <div className="text-[11px] font-semibold text-slate-300 mb-2">Event log</div>
        <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
          {status.events.map((evt) => (
            <div
              key={evt.id}
              className="rounded-lg border border-slate-800 bg-slate-900/90 px-3 py-2"
            >
              <div className="flex items-center justify-between text-[11px] text-slate-300">
                <span className="font-semibold">{milestoneLabels[evt.milestone]}</span>
                <span className="text-slate-500">
                  {new Date(evt.timestamp).toLocaleString(undefined, {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </div>
              {evt.notes && (
                <div className="text-[11px] text-slate-400 mt-1">{evt.notes}</div>
              )}
              {evt.riskTier && (
                <span
                  className={clsx(
                    'mt-1 inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wide',
                    evt.riskTier === 'HIGH' && 'border-red-400/70 bg-red-500/10 text-red-200',
                    evt.riskTier === 'MEDIUM' && 'border-amber-400/70 bg-amber-500/10 text-amber-200',
                    evt.riskTier === 'LOW' && 'border-emerald-400/70 bg-emerald-500/10 text-emerald-200',
                  )}
                >
                  {evt.riskTier} risk
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* TODO: Replace mock status with data from chainpay-service API */}
    </div>
  );
};
