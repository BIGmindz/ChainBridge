/**
 * SettlementsTable Component
 *
 * Displays payment milestones with state coloring and clickable rows.
 * Part of the Smart Settlements Console.
 */

import { Circle } from "lucide-react";

import type { PaymentQueueItem } from "../../core/types/payments";

export interface PaymentMilestoneSummary {
  id: string;
  milestoneId: string; // Canonical milestone ID from backend
  shipmentRef: string;
  milestoneLabel: string;
  state: "pending" | "eligible" | "released" | "blocked" | "settled";
  amount: number;
  lastUpdated: string;
  corridor: string;
  customer: string;
  freightTokenId?: number | null;
  proofpackHint?: {
    milestoneId: string;
    hasProofpack: boolean;
    version: string;
  } | null;
}

export interface SettlementsTableProps {
  milestones: PaymentMilestoneSummary[];
  onRowClick?: (milestoneId: string) => void;
  selectedId?: string;
}

/**
 * Helper to derive milestone summaries from payment queue items
 * TODO: Enhance this when backend provides granular milestone-level data
 */
export function derivePaymentMilestones(items: PaymentQueueItem[]): PaymentMilestoneSummary[] {
  return items.map((item, idx) => {
    const milestoneId = item.milestone_id || `${item.shipmentId}-M${idx + 1}`;
    const holdsAmount = Number(item.holds_usd);
    const releasedAmount = Number(item.released_usd);

    // Derive state from holds/released amounts
    let state: PaymentMilestoneSummary["state"];
    if (holdsAmount > 0) {
      state = "blocked";
    } else if (releasedAmount > 0) {
      state = "released";
    } else {
      state = "pending";
    }

    // TODO: Get real milestone labels from backend when available
    const milestoneLabel = holdsAmount > 0
      ? "Blocked Milestone"
      : releasedAmount > 0
      ? "Released Milestone"
      : "Pending Milestone";

    return {
      id: milestoneId,
      milestoneId, // Canonical milestone ID
      shipmentRef: item.reference,
      milestoneLabel,
      state,
      amount: holdsAmount > 0 ? holdsAmount : releasedAmount,
      lastUpdated: new Date().toISOString(), // TODO: Get from backend
      corridor: item.corridor,
      customer: item.customer,
      freightTokenId: item.freight_token_id ?? null,
      proofpackHint: item.proofpack_hint ? {
        milestoneId: item.proofpack_hint.milestone_id,
        hasProofpack: item.proofpack_hint.has_proofpack,
        version: item.proofpack_hint.version,
      } : null,
    };
  });
}

export default function SettlementsTable({
  milestones,
  onRowClick,
  selectedId,
}: SettlementsTableProps): JSX.Element {
  const stateConfig = {
    pending: {
      label: "Pending",
      color: "text-slate-400",
      bg: "bg-slate-500/10",
      border: "border-slate-500/30",
    },
    eligible: {
      label: "Eligible",
      color: "text-blue-400",
      bg: "bg-blue-500/10",
      border: "border-blue-500/30",
    },
    released: {
      label: "Released",
      color: "text-emerald-400",
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/30",
    },
    blocked: {
      label: "Blocked",
      color: "text-red-400",
      bg: "bg-red-500/10",
      border: "border-red-500/30",
    },
    settled: {
      label: "Settled",
      color: "text-emerald-400",
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/30",
    },
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDateTime = (isoString: string) => {
    return new Date(isoString).toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (milestones.length === 0) {
    return (
      <div className="rounded-xl border border-slate-800/70 bg-slate-900/50 p-8 text-center">
        <p className="text-sm text-slate-400">No payment milestones found</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-800/70 bg-slate-900/50">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-800/70 bg-slate-950/50">
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">
                Shipment
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">
                Milestone
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">
                State
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-400">
                Amount
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">
                Corridor
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">
                Last Updated
              </th>
            </tr>
          </thead>
          <tbody>
            {milestones.map((milestone, idx) => {
              const config = stateConfig[milestone.state];
              const isSelected = milestone.id === selectedId;

              return (
                <tr
                  key={milestone.id}
                  onClick={() => onRowClick?.(milestone.id)}
                  className={`cursor-pointer border-b border-slate-800/50 transition-colors ${
                    idx % 2 === 0 ? "bg-slate-900/30" : "bg-slate-950/30"
                  } ${
                    isSelected
                      ? "bg-blue-500/10 ring-1 ring-inset ring-blue-500/30"
                      : "hover:bg-slate-800/50"
                  }`}
                >
                  <td className="px-4 py-3">
                    <p className="font-mono text-sm font-medium text-slate-200">
                      {milestone.shipmentRef}
                    </p>
                    <p className="mt-0.5 text-xs text-slate-500">{milestone.customer}</p>
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-sm text-slate-300">{milestone.milestoneLabel}</p>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${config.border} ${config.bg} ${config.color}`}
                    >
                      <Circle className="h-2 w-2 fill-current" />
                      {config.label}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <p className="font-semibold text-slate-200">{formatCurrency(milestone.amount)}</p>
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-sm text-slate-400">{milestone.corridor}</p>
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-xs text-slate-500">{formatDateTime(milestone.lastUpdated)}</p>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
