import type { FC } from "react";

import { usePaymentQueue } from "../hooks/usePaymentQueue";
import { formatUSD } from "../lib/formatters";

import RiskOverviewBar from "./RiskOverviewBar";

/**
 * PaymentHoldQueueCard
 *
 * ChainPay Level 1: Payment hold queue for manual review.
 * Shows shipments with payment holds, sorted by hold amount.
 */

export const PaymentHoldQueueCard: FC = () => {
  const { data, loading, error, refetch } = usePaymentQueue(20);

  return (
    <div className="rounded-2xl border border-slate-800/70 bg-slate-950/80 p-6 shadow-xl">
      {/* Risk Overview KPIs */}
      <RiskOverviewBar />

      <div className="mb-6 flex items-center justify-between">
        <div>
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            ChainPay // Level 1
          </p>
          <h3 className="text-xl font-semibold tracking-tight text-slate-50">Payment Hold Queue</h3>
          <p className="mt-1 text-xs text-slate-400">
            Shipments with payment holds — manual review required
          </p>
        </div>
        <div className="flex items-center gap-4">
          {data && data.total_items > 0 && (
            <div className="rounded-lg border border-orange-500/30 bg-orange-500/10 px-4 py-2">
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-orange-400">HOLDS</p>
              <p className="text-center text-2xl font-bold text-orange-300">{data.total_items}</p>
            </div>
          )}
          {data && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2">
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-red-400">VALUE</p>
              <p className="text-center text-lg font-bold text-red-300">{formatUSD(data.total_holds_usd)}</p>
            </div>
          )}
          <button
            onClick={refetch}
            disabled={loading}
            className="rounded-lg bg-slate-800/70 px-3 py-1.5 text-sm text-slate-300 transition-colors hover:bg-slate-700 disabled:opacity-50 disabled:bg-slate-800"
          >
            {loading ? "Loading..." : "Refresh"}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-red-500/30 bg-red-500/10 p-4">
          <p className="text-sm text-red-400">{error.message}</p>
        </div>
      )}

      {loading && !data && (
        <div className="rounded-lg border border-slate-800 bg-slate-900/50 py-12 text-center">
          <p className="text-slate-400">Loading payment queue...</p>
        </div>
      )}

      {!loading && data && data.items.length === 0 && !error && (
        <div className="rounded-lg border border-slate-800 bg-slate-900/50 py-12 text-center">
          <div className="mb-3">
            <svg className="mx-auto h-16 w-16 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p className="mb-1 text-xl font-semibold text-emerald-400">No Payment Holds</p>
          <p className="text-sm text-slate-400">All clear for release</p>
        </div>
      )}

      {data && data.items.length > 0 && (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800">
                  <th className="px-3 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Shipment</th>
                  <th className="px-3 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Customer</th>
                  <th className="px-3 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Corridor</th>
                  <th className="px-3 py-3 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Total Value</th>
                  <th className="px-3 py-3 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Hold Amount</th>
                  <th className="px-3 py-3 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Released</th>
                  <th className="px-3 py-3 text-center text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Aging</th>
                  <th className="px-3 py-3 text-center text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Risk</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr
                    key={item.shipmentId}
                    className="border-b border-slate-800/50 transition-colors hover:bg-slate-900/40"
                  >
                    <td className="px-3 py-3">
                      <div>
                        <span className="font-mono text-sm font-medium text-slate-100">{item.shipmentId}</span>
                        <p className="mt-0.5 font-mono text-xs text-slate-400">{item.reference}</p>
                      </div>
                    </td>
                    <td className="px-3 py-3">
                      <span className="text-sm text-slate-300">{item.customer}</span>
                    </td>
                    <td className="px-3 py-3">
                      <span className="font-mono text-xs text-slate-400">{item.corridor}</span>
                    </td>
                    <td className="px-3 py-3 text-right">
                      <span className="font-semibold text-slate-50">{formatUSD(item.total_valueUsd)}</span>
                    </td>
                    <td className="px-3 py-3 text-right">
                      <span className="font-bold text-red-300">{formatUSD(item.holds_usd)}</span>
                    </td>
                    <td className="px-3 py-3 text-right">
                      <span className="text-sm text-emerald-300">{formatUSD(item.released_usd)}</span>
                    </td>
                    <td className="px-3 py-3 text-center">
                      <span className="inline-flex items-center rounded-full bg-amber-500/15 px-2.5 py-1 text-xs font-semibold text-amber-300">
                        {item.aging_days}d
                      </span>
                    </td>
                    <td className="px-3 py-3 text-center">
                      {item.riskCategory && renderRiskBadge(item.riskCategory)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 border-t border-slate-800 pt-4">
            <div className="flex items-center justify-between text-xs text-slate-500">
              <p>
                Showing {data.items.length} of {data.total_items} shipment{data.total_items !== 1 ? "s" : ""} with holds
              </p>
              <p className="text-slate-400">Level 1: Read-Only Queue</p>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

function renderRiskBadge(category: string): JSX.Element {
  let chipClasses = "";

  switch (category.toLowerCase()) {
    case "low":
      chipClasses = "bg-slate-700 text-slate-100";
      break;
    case "medium":
      chipClasses = "bg-amber-600 text-amber-50";
      break;
    case "high":
      chipClasses = "bg-orange-600 text-orange-50";
      break;
    case "critical":
      chipClasses = "bg-red-600 text-red-50";
      break;
    default:
      chipClasses = "bg-slate-600 text-slate-100";
  }

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${chipClasses}`}
    >
      {category}
    </span>
  );
}
