/**
 * RiskOverviewBar.tsx
 *
 * Mission control KPI overview for ChainIQ Payment Hold Queue.
 * Displays high-level risk metrics at a glance.
 */

import React from "react";

import { useRiskSummary } from "../hooks/useRiskSummary";
import { formatRiskScore, formatUSD } from "../lib/formatters";

const RiskOverviewBar: React.FC = () => {
  const { data, loading, error, refetch } = useRiskSummary();

  if (loading) {
    return (
      <div className="mb-6 rounded-xl border border-slate-800/70 bg-slate-950/60 px-4 py-3 text-sm text-slate-400">
        Synchronizing ChainIQ overview…
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mb-6 flex items-center justify-between rounded-xl border border-rose-500/40 bg-rose-950/20 px-4 py-3 text-sm text-rose-100">
        <span>Failed to load risk overview: {error?.message ?? "Unknown error"}</span>
        <button
          type="button"
          onClick={refetch}
          className="rounded-lg border border-rose-400/60 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-rose-100"
        >
          Retry
        </button>
      </div>
    );
  }

  const overview = data.overview;
  const averageRisk = formatRiskScore(overview.average_riskScore);

  return (
    <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <MetricCard
        label="Shipments in Queue"
        value={overview.total_shipments.toLocaleString()}
        helper="requiring review"
        accent="text-slate-50"
      />
      <MetricCard
        label="High-Risk Shipments"
        value={overview.high_risk_shipments.toLocaleString()}
        helper="≥ HIGH severity"
        accent="text-orange-300"
        border="border-orange-500/30"
        background="bg-orange-950/20"
      />
      <MetricCard
        label="Total Value at Risk"
        value={formatUSD(overview.total_valueUsd)}
        helper="shipment value (USD)"
        accent="text-red-300"
        border="border-red-500/30"
        background="bg-red-950/20"
      />
      <MetricCard
        label="Average Risk Score"
        value={overview.average_riskScore.toFixed(1)}
        helper={averageRisk.text}
        accent={averageRisk.color}
        border="border-amber-500/30"
        background="bg-amber-950/20"
      />
    </div>
  );
};


interface MetricCardProps {
  label: string;
  value: string;
  helper: string;
  accent?: string;
  border?: string;
  background?: string;
}

function MetricCard({ label, value, helper, accent, border, background }: MetricCardProps) {
  return (
    <div className={`rounded-xl border ${border ?? "border-slate-800/70"} ${background ?? "bg-slate-900/70"} px-4 py-3 shadow-lg`}>
      <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
        {label}
      </p>
      <p className={`mt-1.5 text-3xl font-bold ${accent ?? "text-slate-50"}`}>{value}</p>
      <p className="mt-0.5 text-[11px] text-slate-400">{helper}</p>
    </div>
  );
}

export default RiskOverviewBar;
