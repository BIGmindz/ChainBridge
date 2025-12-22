// COPILOT SYSTEM BRIEFING - CHAINBRIDGE PROOFPACK UI V1.5
// You are enhancing the Settlements UI to consume stronger ProofPack + SSE identity.
//
// ChainBridge Mantra:
// - No hacks, no lies, no shortcuts.
// - If something is mock, the backend will label it. The UI only reflects truth.
//
// Objectives:
// 1) Use the canonical milestoneId coming from the queue + ProofPack, not local heuristics.
// 2) Show a "Proof available" indicator where proofpack_hint.has_proofpack === true.
// 3) Refine the ProofPack section to:
//      - Highlight real fields (amount/currency/state/corridor/customer).
//      - Clearly label "Derived from live payment data" vs "Mock evidence".
/**
 * SettlementTimelinePanel Component
 *
 * Horizontal timeline showing payment milestone progression.
 * Re-uses pattern from ShipmentChainStrip but focused on settlement states.
 *
 * V2: Adds ProofPack/Evidence card for on-chain traceability.
 */

import {
  Circle,
  DollarSign,
  Lock,
  Unlock,
  CheckCircle2,
  Package,
  AlertCircle,
  RefreshCw,
  Eye,
  EyeOff,
} from "lucide-react";
import { useState } from "react";

import { useProofPack } from "../../hooks/useProofPack";

import type { PaymentMilestoneSummary } from "./SettlementsTable";

type TimelineStage = "pending" | "eligible" | "released" | "settled";

interface StageConfig {
  id: TimelineStage;
  label: string;
  Icon: React.ElementType;
}

const TIMELINE_STAGES: StageConfig[] = [
  { id: "pending", label: "Pending", Icon: Circle },
  { id: "eligible", label: "Eligible", Icon: DollarSign },
  { id: "released", label: "Released", Icon: Unlock },
  { id: "settled", label: "Settled", Icon: CheckCircle2 },
];

export interface SettlementTimelinePanelProps {
  milestone?: PaymentMilestoneSummary;
}

export default function SettlementTimelinePanel({
  milestone,
}: SettlementTimelinePanelProps): JSX.Element {
  const [showRawJson, setShowRawJson] = useState(false);

  // Fetch ProofPack evidence for the selected milestone
  // Use canonical milestoneId from backend, not local heuristics
  const { data: proofpack, loading: proofpackLoading, error: proofpackError, refetch } = useProofPack(
    milestone?.milestoneId ?? null
  );

  if (!milestone) {
    return (
      <div className="rounded-xl border border-slate-800/70 bg-slate-900/50 p-6">
        <h4 className="mb-4 text-sm font-semibold text-slate-100">Settlement Timeline</h4>
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <DollarSign className="mb-3 h-12 w-12 text-slate-700" />
          <p className="text-sm text-slate-400">Select a milestone to view timeline</p>
        </div>
      </div>
    );
  }

  // Map milestone state to timeline stage
  let currentStage: TimelineStage;
  if (milestone.state === "blocked") {
    currentStage = "pending"; // Blocked is a variant of pending
  } else if (milestone.state === "settled") {
    currentStage = "settled";
  } else if (milestone.state === "released") {
    currentStage = "released";
  } else if (milestone.state === "eligible") {
    currentStage = "eligible";
  } else {
    currentStage = "pending";
  }

  const currentIndex = TIMELINE_STAGES.findIndex((s) => s.id === currentStage);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <div className="rounded-xl border border-slate-800/70 bg-slate-900/50 p-6">
      {/* Header */}
      <div className="mb-6">
        <h4 className="text-sm font-semibold text-slate-100">Settlement Timeline</h4>
        <p className="mt-1 text-xs text-slate-400">
          {milestone.shipmentRef} · {milestone.milestoneLabel}
        </p>
      </div>

      {/* Timeline Visualization */}
      <div className="relative mb-6">
        {/* Connector Line */}
        <div className="absolute top-6 left-8 right-8 h-0.5 bg-slate-800">
          <div
            className="h-full bg-gradient-to-r from-emerald-500 to-blue-500 transition-all duration-500"
            style={{ width: `${(currentIndex / (TIMELINE_STAGES.length - 1)) * 100}%` }}
            aria-label={`Progress: ${Math.round((currentIndex / (TIMELINE_STAGES.length - 1)) * 100)}%`}
          />
        </div>

        {/* Stage Nodes */}
        <div className="relative flex items-center justify-between">
          {TIMELINE_STAGES.map((stage, index) => {
            const isActive = index === currentIndex;
            const isPast = index < currentIndex;

            return (
              <div key={stage.id} className="flex flex-col items-center">
                {/* Node Circle */}
                <div
                  className={`z-10 flex h-12 w-12 items-center justify-center rounded-full border-2 transition-all ${
                    isActive
                      ? "border-blue-500 bg-blue-500/20 shadow-lg shadow-blue-500/50"
                      : isPast
                      ? "border-emerald-500 bg-emerald-500/20"
                      : "border-slate-700 bg-slate-900"
                  }`}
                >
                  <stage.Icon
                    className={`h-5 w-5 ${
                      isActive ? "text-blue-400" : isPast ? "text-emerald-400" : "text-slate-600"
                    }`}
                  />
                </div>

                {/* Label */}
                <span
                  className={`mt-2 text-[10px] font-medium ${
                    isActive ? "text-blue-400" : isPast ? "text-emerald-400" : "text-slate-600"
                  }`}
                >
                  {stage.label}
                </span>

                {/* Active Indicator */}
                {isActive && (
                  <div className="mt-1 flex items-center gap-1">
                    <span className="relative flex h-2 w-2">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75"></span>
                      <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-500"></span>
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Details */}
      <div className="space-y-3">
        <div className="flex items-center justify-between rounded-lg border border-slate-800/50 bg-slate-950/50 px-4 py-2">
          <span className="text-xs text-slate-400">Amount</span>
          <span className="text-sm font-semibold text-slate-200">
            {formatCurrency(milestone.amount)}
          </span>
        </div>

        <div className="flex items-center justify-between rounded-lg border border-slate-800/50 bg-slate-950/50 px-4 py-2">
          <span className="text-xs text-slate-400">Status</span>
          <span
            className={`text-sm font-semibold ${
              milestone.state === "blocked"
                ? "text-red-400"
                : milestone.state === "released" || milestone.state === "settled"
                ? "text-emerald-400"
                : "text-slate-300"
            }`}
          >
            {milestone.state === "blocked" && (
              <span className="inline-flex items-center gap-1.5">
                <Lock className="h-3.5 w-3.5" />
                Blocked
              </span>
            )}
            {(milestone.state === "released" || milestone.state === "settled") && (
              <span className="inline-flex items-center gap-1.5">
                <Unlock className="h-3.5 w-3.5" />
                {milestone.state === "settled" ? "Settled" : "Released"}
              </span>
            )}
            {milestone.state !== "blocked" &&
              milestone.state !== "released" &&
              milestone.state !== "settled" && <span className="capitalize">{milestone.state}</span>}
          </span>
        </div>

        <div className="flex items-center justify-between rounded-lg border border-slate-800/50 bg-slate-950/50 px-4 py-2">
          <span className="text-xs text-slate-400">Corridor</span>
          <span className="text-sm font-medium text-slate-300">{milestone.corridor}</span>
        </div>
      </div>

      {/* Proof & Evidence Section */}
      <div className="mt-6 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Package className="h-4 w-4 text-blue-400" />
            <h5 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Proof & Evidence
            </h5>
          </div>
          {proofpack && (
            <button
              onClick={() => setShowRawJson(!showRawJson)}
              className="flex items-center gap-1 rounded px-2 py-1 text-[10px] text-slate-400 transition-colors hover:bg-slate-800/50 hover:text-slate-300"
            >
              {showRawJson ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
              {showRawJson ? "Hide" : "View"} JSON
            </button>
          )}
        </div>

        {/* Loading State */}
        {proofpackLoading && (
          <div className="flex items-center justify-center rounded-lg border border-slate-800/50 bg-slate-950/30 p-6">
            <div className="text-center">
              <div className="mb-2 inline-block h-6 w-6 animate-spin rounded-full border-2 border-slate-700 border-t-blue-500"></div>
              <p className="text-xs text-slate-500">Loading ProofPack...</p>
            </div>
          </div>
        )}

        {/* Error State */}
        {proofpackError && !proofpackLoading && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4">
            <div className="mb-2 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-red-400" />
              <p className="text-xs font-medium text-red-400">Failed to load ProofPack</p>
            </div>
            <p className="mb-3 text-[10px] text-red-300">{proofpackError.message}</p>
            <button
              onClick={refetch}
              className="flex items-center gap-1.5 rounded bg-red-500/20 px-3 py-1.5 text-[10px] font-medium text-red-300 transition-colors hover:bg-red-500/30"
            >
              <RefreshCw className="h-3 w-3" />
              Retry
            </button>
          </div>
        )}

        {/* Success State - ProofPack Data */}
        {proofpack && !proofpackLoading && (
          <>
            {/* Data Source Indicators */}
            <div className="mb-3 space-y-1 text-[10px]">
              <div className="flex items-center gap-1.5">
                <div className="h-1.5 w-1.5 rounded-full bg-emerald-500"></div>
                <span className="font-medium text-emerald-400">Payment data: LIVE from ChainPay</span>
              </div>
              {/* Check if evidence bundles are marked as mock */}
              {(() => {
                const riskSource = (proofpack.risk_assessment as { source?: string })?.source;
                const docSources = proofpack.documents.map((doc: Record<string, unknown>) => doc.source as string);
                const iotSources = proofpack.iot_signals.map((sig: Record<string, unknown>) => sig.source as string);
                const auditSources = proofpack.audit_trail.map((entry: Record<string, unknown>) => entry.source as string);

                const hasMockEvidence =
                  riskSource === "mock" ||
                  docSources.some(s => s === "mock") ||
                  iotSources.some(s => s === "mock") ||
                  auditSources.some(s => s === "mock");

                return hasMockEvidence ? (
                  <div className="flex items-center gap-1.5">
                    <div className="h-1.5 w-1.5 rounded-full bg-amber-500"></div>
                    <span className="font-medium text-amber-400">Evidence bundles: MARKED AS MOCK (not wired yet)</span>
                  </div>
                ) : null;
              })()}
            </div>

            {/* Summary Info */}
            <div className="space-y-2 rounded-lg border border-slate-800/50 bg-slate-950/30 p-3">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-slate-500">Shipment Ref</span>
                <span className="font-mono text-slate-300">{proofpack.shipment_reference}</span>
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-slate-500">Customer</span>
                <span className="font-mono text-slate-300">{proofpack.customer_name}</span>
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-slate-500">Corridor</span>
                <span className="font-mono text-slate-300">{proofpack.corridor}</span>
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-slate-500">Amount</span>
                <span className="font-mono text-emerald-400">
                  {new Intl.NumberFormat("en-US", {
                    style: "currency",
                    currency: proofpack.currency,
                  }).format(proofpack.amount)}
                </span>
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-slate-500">Freight Token</span>
                <span className="font-mono text-slate-400">
                  {proofpack.freight_token_id ? `#${proofpack.freight_token_id}` : "N/A"}
                </span>
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-slate-500">Last Updated</span>
                <span className="font-mono text-slate-400">
                  {new Date(proofpack.last_updated).toLocaleString([], {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
            </div>

            {/* Evidence Summary */}
            <div className="grid grid-cols-2 gap-2">
              {/* Documents Card */}
              <div className="rounded border border-slate-800/50 bg-slate-950/30 p-2">
                <div className="flex items-center justify-between">
                  <p className="text-[9px] text-slate-500">Documents</p>
                  {proofpack.documents.some((doc: Record<string, unknown>) => doc.source === "mock") && (
                    <span className="text-[7px] text-amber-500">MOCK</span>
                  )}
                </div>
                <p className="text-sm font-semibold text-slate-300">{proofpack.documents.length}</p>
              </div>

              {/* IoT Signals Card */}
              <div className="rounded border border-slate-800/50 bg-slate-950/30 p-2">
                <div className="flex items-center justify-between">
                  <p className="text-[9px] text-slate-500">IoT Signals</p>
                  {proofpack.iot_signals.some((sig: Record<string, unknown>) => sig.source === "mock") && (
                    <span className="text-[7px] text-amber-500">MOCK</span>
                  )}
                </div>
                <p className="text-sm font-semibold text-slate-300">{proofpack.iot_signals.length}</p>
              </div>

              {/* Audit Trail Card */}
              <div className="rounded border border-slate-800/50 bg-slate-950/30 p-2">
                <div className="flex items-center justify-between">
                  <p className="text-[9px] text-slate-500">Audit Trail</p>
                  {proofpack.audit_trail.some((entry: Record<string, unknown>) => entry.source === "mock") && (
                    <span className="text-[7px] text-amber-500">MOCK</span>
                  )}
                </div>
                <p className="text-sm font-semibold text-slate-300">{proofpack.audit_trail.length}</p>
              </div>

              {/* Risk Score Card */}
              <div className="rounded border border-slate-800/50 bg-slate-950/30 p-2">
                <div className="flex items-center justify-between">
                  <p className="text-[9px] text-slate-500">Risk Score</p>
                  {(proofpack.risk_assessment as { source?: string })?.source === "mock" && (
                    <span className="text-[7px] text-amber-500">MOCK</span>
                  )}
                </div>
                <p className="text-sm font-semibold text-slate-300">
                  {(proofpack.risk_assessment as { score?: string | number })?.score ?? "N/A"}
                </p>
              </div>
            </div>

            {/* Raw JSON Toggle */}
            {showRawJson && (
              <div className="space-y-1.5">
                <p className="text-[10px] font-medium text-slate-500">ProofPack JSON</p>
                <pre className="max-h-64 overflow-auto rounded-md border border-slate-800/60 bg-slate-950/60 p-2 text-[10px] leading-relaxed text-slate-400">
                  {JSON.stringify(proofpack, null, 2)}
                </pre>
              </div>
            )}
          </>
        )}

        {/* Fallback - No ProofPack (not loading, not error) */}
        {!proofpack && !proofpackLoading && !proofpackError && (
          <div className="rounded-lg border border-slate-800/50 bg-slate-950/30 p-4 text-center">
            <Package className="mb-2 inline-block h-8 w-8 text-slate-700" />
            <p className="text-xs text-slate-500">Select a milestone to view ProofPack</p>
          </div>
        )}
      </div>
    </div>
  );
}
