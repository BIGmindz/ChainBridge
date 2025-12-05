import React from 'react';
import clsx from 'clsx';

import type { ChainPayAnalyticsSnapshot, RiskTier } from '../../types/chainpayAnalytics';
import { formatSettlementProvider } from '../../types/chainpay';

interface ChainPayAnalyticsPanelProps {
  snapshot: ChainPayAnalyticsSnapshot | null;
  loading?: boolean;
  error?: Error | null;
  onRefresh?: () => void;
  corridorLabel?: string;
  policyLabel?: string;
  assetLabel?: string;
}

const tierClasses: Record<RiskTier, string> = {
  LOW: 'bg-emerald-500/10 text-emerald-200 border-emerald-500/60',
  MEDIUM: 'bg-amber-500/10 text-amber-200 border-amber-500/60',
  HIGH: 'bg-orange-500/10 text-orange-200 border-orange-500/60',
  CRITICAL: 'bg-red-500/10 text-red-200 border-red-500/60',
};

function pct(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export const ChainPayAnalyticsPanel: React.FC<ChainPayAnalyticsPanelProps> = ({
  snapshot,
  loading,
  error,
  onRefresh,
  corridorLabel,
  policyLabel,
  assetLabel,
}) => {
  const corridor = corridorLabel ?? snapshot?.corridorId ?? 'USD→MXN';
  const policy = policyLabel ?? 'P0';
  const asset = assetLabel ?? 'CB-USDx';
  const rail = formatSettlementProvider(snapshot?.settlementProvider);

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
        <div className="flex items-start justify-between">
          <h2 className="text-sm font-semibold text-slate-100 tracking-wide">ChainPay Analytics</h2>
          <span className="text-[11px] text-slate-400">Loading…</span>
        </div>
        {headerBadges}
        <div className="mt-3 h-24 rounded-xl bg-slate-800/60 animate-pulse" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-red-700/60 bg-red-950/70 p-4 shadow-sm">
        <div className="flex items-start justify-between">
          <h2 className="text-sm font-semibold text-red-100 tracking-wide">ChainPay Analytics</h2>
          <div className="flex items-center gap-3">
            {refreshButton}
            <span className="text-[11px] text-red-200">Error</span>
          </div>
        </div>
        {headerBadges}
        <p className="text-xs text-red-200 mt-1">Unable to load analytics for USD→MXN.</p>
        <p className="text-[11px] text-red-200/80 mt-1">{error.message}</p>
      </div>
    );
  }

  if (!snapshot) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-sm">
        <div className="flex items-start justify-between">
          <h2 className="text-sm font-semibold text-slate-100 tracking-wide">ChainPay Analytics</h2>
          {refreshButton}
        </div>
        {headerBadges}
        <p className="text-xs text-slate-400 mt-1">
          No analytics data available yet for USD→MXN. Check the backend analytics service.
        </p>
      </div>
    );
  }

  const data = snapshot;

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-sm space-y-4">
      <div>
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-100 tracking-wide">
              ChainPay Analytics
            </h2>
            <p className="text-[11px] text-slate-400 mt-1">
              Tier health, days-to-cash, and SLA snapshots for USD→MXN (P0).
              Sourced from the live analytics endpoint.
            </p>
            <div className="mt-2">{headerBadges}</div>
          </div>
          <div className="text-right text-[11px] text-slate-400">
            <div>Corridor {data.corridorId}</div>
            <div className="opacity-70">As of {new Date(data.asOf).toLocaleString()}</div>
            {refreshButton}
          </div>
        </div>
      </div>

      {/* Tier Health */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-3">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-slate-100">Tier Health</h3>
          <span className="text-[11px] text-slate-400">Loss & Reserve Utilization</span>
        </div>
        <div className="grid grid-cols-4 gap-2 text-[11px]">
          {data.tierHealth.map((row) => (
            <div
              key={row.tier}
              className="rounded-lg border border-slate-800 bg-slate-950/50 p-3 space-y-1"
            >
              <div className="flex items-center justify-between">
                <span className={clsx('inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide', tierClasses[row.tier])}>
                  {row.tier}
                </span>
                <span className="text-[10px] text-slate-400">{row.shipmentCount} shp</span>
              </div>
              <div className="text-slate-200 text-xs">
                Loss rate: <span className="font-semibold">{pct(row.lossRate)}</span>
              </div>
              <div className="text-slate-200 text-xs">
                Reserve used: <span className="font-semibold">{pct(row.reserveUtilization)}</span>
              </div>
              <div className={clsx(
                'text-xs',
                row.unusedReserveRatio < 0 ? 'text-red-300' : 'text-slate-300'
              )}>
                Unused reserve: <span className="font-semibold">{pct(row.unusedReserveRatio)}</span>
              </div>
              {row.reserveUtilization > 1 && (
                <div className="text-[10px] text-red-300">Reserve breach</div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Days to Cash */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-3 space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-100">Days to Cash</h3>
          <span className="text-[11px] text-slate-400">Median / p95 (first → final)</span>
        </div>
        <div className="grid grid-cols-2 gap-2 text-[11px]">
          {data.daysToCash.map((row) => (
            <div
              key={`${row.corridorId}-${row.tier}`}
              className="rounded-lg border border-slate-800 bg-slate-950/50 p-3"
            >
              <div className="flex items-center justify-between mb-1">
                <span className={clsx('inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide', tierClasses[row.tier])}>
                  {row.tier}
                </span>
                <span className="text-[10px] text-slate-400">{row.corridorId}</span>
              </div>
              <div className="text-slate-200 text-xs">
                First cash: <span className="font-semibold">{row.medianDaysToFirstCash.toFixed(1)}d</span>{' '}
                (p95 {row.p95DaysToFirstCash.toFixed(1)}d)
              </div>
              <div className="text-slate-200 text-xs">
                Final cash: <span className="font-semibold">{row.medianDaysToFinalCash.toFixed(1)}d</span>{' '}
                (p95 {row.p95DaysToFinalCash.toFixed(1)}d)
              </div>
              <div className="text-[10px] text-slate-400 mt-1">{row.shipmentCount} shipments</div>
            </div>
          ))}
        </div>
      </div>

      {/* SLA & Reliability */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-3 space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-100">SLA & Reliability</h3>
          <span className="text-[11px] text-slate-400">Claim & manual review breaches</span>
        </div>
        <div className="grid grid-cols-2 gap-2 text-[11px]">
          {data.sla.map((row) => {
            const claimBreachAlert = row.claimReviewSlaBreachRate > 0.1;
            const manualBreachAlert = row.manualReviewSlaBreachRate > 0.1;
            return (
              <div
                key={`${row.corridorId}-${row.tier}`}
                className="rounded-lg border border-slate-800 bg-slate-950/50 p-3 space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className={clsx('inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide', tierClasses[row.tier])}>
                    {row.tier}
                  </span>
                  <span className="text-[10px] text-slate-400">{row.totalReviews} reviews</span>
                </div>
                <div className={clsx('text-xs', claimBreachAlert ? 'text-amber-200' : 'text-slate-300')}>
                  Claim review breach: <span className="font-semibold">{pct(row.claimReviewSlaBreachRate)}</span>
                  {claimBreachAlert && (
                    <span className="ml-1 text-[10px] text-amber-200">Needs attention</span>
                  )}
                </div>
                <div className={clsx('text-xs', manualBreachAlert ? 'text-amber-200' : 'text-slate-300')}>
                  Manual review breach: <span className="font-semibold">{pct(row.manualReviewSlaBreachRate)}</span>
                  {manualBreachAlert && (
                    <span className="ml-1 text-[10px] text-amber-200">Needs attention</span>
                  )}
                </div>
                <div className="text-[10px] text-slate-500">Corridor {row.corridorId}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
