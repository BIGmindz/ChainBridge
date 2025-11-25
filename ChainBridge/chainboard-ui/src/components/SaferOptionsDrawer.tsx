/*
Sunny: implement the SaferOptionsDrawer component for ChainBridge / ChainIQ.

Context reminder:
- ChainBridge = freight + payments control tower.
- ChainIQ = risk brain.
- This drawer = Better Options Advisor:
  "If this lane is risky, what safer routes / rails do I have, given my risk appetite?"
*/

import React, { useMemo, useState } from "react";

import type {
  RouteOption,
  PaymentRailOption,
  RiskAppetite,
  SimulationResultResponse,
  SimulationOptionType,
} from "../lib/apiClient";
import { simulateShipmentOption } from "../lib/apiClient";

interface SaferOptionsDrawerProps {
  shipmentId: string;
  currentRiskScore: number;
  routeOptions: RouteOption[];
  paymentOptions: PaymentRailOption[];
  riskAppetite: RiskAppetite;
  onRiskAppetiteChange: (value: RiskAppetite) => void;
  loading: boolean;
  error: string | null;
  onClose: () => void;
}

function simulationKey(optionType: SimulationOptionType, optionId: string): string {
  return `${optionType}:${optionId}`;
}

const SaferOptionsDrawer: React.FC<SaferOptionsDrawerProps> = ({
  shipmentId,
  currentRiskScore,
  routeOptions,
  paymentOptions,
  riskAppetite,
  onRiskAppetiteChange,
  loading,
  error,
  onClose,
}) => {
  // Simulation state
  const [simulationResults, setSimulationResults] = useState<Record<string, SimulationResultResponse>>({});
  const [simulationLoading, setSimulationLoading] = useState<Record<string, boolean>>({});
  const [simulationError, setSimulationError] = useState<Record<string, string | null>>({});

  // Handle simulation test run
  async function handleTestRun(optionType: SimulationOptionType, optionId: string): Promise<void> {
    if (!shipmentId) return;

    const key = simulationKey(optionType, optionId);

    setSimulationError(prev => ({ ...prev, [key]: null }));
    setSimulationLoading(prev => ({ ...prev, [key]: true }));

    try {
      const result = await simulateShipmentOption(shipmentId, optionType, optionId);
      setSimulationResults(prev => ({ ...prev, [key]: result }));
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to run simulation. Please try again.";
      setSimulationError(prev => ({ ...prev, [key]: message }));
    } finally {
      setSimulationLoading(prev => ({ ...prev, [key]: false }));
    }
  }

  // Compute risk vs reward summary
  const { bestRiskDelta, maxSavings } = useMemo(() => {
    const allOptions: (RouteOption | PaymentRailOption)[] = [
      ...routeOptions,
      ...paymentOptions,
    ];
    if (allOptions.length === 0) {
      return { bestRiskDelta: 0, maxSavings: 0 };
    }

    let best = -Infinity;
    let savings = 0;

    for (const opt of allOptions) {
      if (opt.risk_delta > best) {
        best = opt.risk_delta;
      }

      const costDelta =
        "cost_delta_usd" in opt ? opt.cost_delta_usd : opt.fees_delta_usd;
      if (costDelta < savings) {
        savings = costDelta; // negative = savings
      }
    }

    if (!Number.isFinite(best)) best = 0;
    return { bestRiskDelta: best, maxSavings: savings };
  }, [routeOptions, paymentOptions]);

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 z-50 w-full max-w-xl bg-slate-950/95 border-l border-slate-800/70 shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 px-4 pt-4 pb-2 border-b border-slate-800/70">
          <div>
            <div className="text-[10px] font-semibold tracking-[0.22em] uppercase text-slate-400">
              CHAINIQ // BETTER OPTIONS ADVISOR
            </div>
            <div className="mt-1 text-lg font-semibold text-slate-50">
              Shipment {shipmentId}
            </div>
            <div className="mt-0.5 text-xs text-slate-400">
              Current risk: {currentRiskScore}
            </div>

            {/* Risk appetite pill group */}
            <div className="mt-3 inline-flex rounded-full bg-slate-900/80 p-1 text-[10px] tracking-[0.18em] uppercase">
              {(["conservative", "balanced", "aggressive"] as RiskAppetite[]).map((value) => {
                const active = value === riskAppetite;
                return (
                  <button
                    key={value}
                    type="button"
                    onClick={() => onRiskAppetiteChange(value)}
                    className={
                      "px-3 py-1 rounded-full transition-colors " +
                      (active
                        ? "bg-emerald-500 text-slate-950"
                        : "text-slate-400 hover:text-slate-100")
                    }
                  >
                    {value}
                  </button>
                );
              })}
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-1.5 text-slate-400 hover:text-slate-100 hover:bg-slate-800/80"
          >
            <span className="sr-only">Close</span>
            <svg
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Risk vs Reward summary */}
        <div className="mt-3 px-4 text-[11px] text-slate-400 flex justify-between">
          <span>
            Best ΔRisk: {bestRiskDelta > 0 ? `+${bestRiskDelta}` : bestRiskDelta}
          </span>
          <span>
            Max savings: {maxSavings < 0 ? `$${Math.abs(maxSavings).toFixed(0)}` : "$0"}
          </span>
        </div>

        {/* Main content container */}
        <div className="mt-3 flex-1 overflow-y-auto px-4 pb-6 space-y-6">
          {/* Loading state */}
          {loading && !error && routeOptions.length === 0 && paymentOptions.length === 0 && (
            <div className="mt-10 text-center text-sm text-slate-400">
              Computing safer options...
            </div>
          )}

          {/* Error state */}
          {error && (
            <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-[11px] text-red-100">
              {error}
            </div>
          )}

          {/* Empty state */}
          {!loading && !error && routeOptions.length === 0 && paymentOptions.length === 0 && (
            <div className="mt-8 text-center text-sm text-slate-400">
              No safer options found within current policy and lane constraints.
              <div className="mt-1 text-[11px] text-slate-500">
                Consider escalation or manual override if this shipment must move on the current path.
              </div>
            </div>
          )}

          {/* Route alternatives section */}
          {routeOptions.length > 0 && (
            <section>
              <h3 className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                Route Alternatives
              </h3>
              <div className="mt-2 space-y-2">
                {routeOptions.map((opt) => {
                  const key = simulationKey("route", opt.option_id);
                  const sim = simulationResults[key];
                  const simLoading = simulationLoading[key] ?? false;
                  const simError = simulationError[key] ?? null;

                  return (
                    <div
                      key={opt.option_id}
                      className="rounded-lg border border-slate-800/70 bg-slate-900/70 p-3"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <div className="text-sm font-semibold text-slate-50">
                            {opt.route}
                          </div>
                          {opt.carrierId && (
                            <div className="text-[11px] text-slate-400">
                              Carrier: {opt.carrierId}
                            </div>
                          )}
                        </div>
                        <div className="flex flex-col items-end gap-1 text-[11px]">
                          <span className="rounded-full bg-slate-800/80 px-2 py-0.5 text-slate-100">
                            Risk {opt.riskScore} (Δ{opt.risk_delta})
                          </span>
                          <span className="rounded-full bg-slate-800/80 px-2 py-0.5 text-slate-200">
                            ETA Δ {opt.eta_delta_days} days
                          </span>
                          <span className="rounded-full bg-slate-800/80 px-2 py-0.5 text-slate-200">
                            Cost Δ ${opt.cost_delta_usd.toFixed(0)}
                          </span>
                        </div>
                      </div>
                      {opt.notes.length > 0 && (
                        <ul className="mt-2 list-disc space-y-0.5 pl-4 text-[11px] text-slate-300">
                          {opt.notes.map((note) => (
                            <li key={note}>{note}</li>
                          ))}
                        </ul>
                      )}
                      <div className="mt-2 flex items-center justify-end">
                        <button
                          type="button"
                          onClick={() => handleTestRun("route", opt.option_id)}
                          disabled={simLoading}
                          className="inline-flex items-center rounded-full border border-emerald-400 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-emerald-300 hover:bg-emerald-900/40 disabled:opacity-60 disabled:cursor-not-allowed"
                        >
                          {simLoading ? "Testing..." : "Test Run"}
                        </button>
                      </div>
                      {simError && (
                        <p className="mt-1 text-[11px] text-red-400">
                          {simError}
                        </p>
                      )}
                      {sim && (
                        <div className="mt-2 rounded-lg bg-slate-900/70 px-3 py-2 text-xs text-slate-100 border border-emerald-500/40">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-emerald-300">Simulation Result</span>
                            <span className="text-[10px] uppercase tracking-wide text-slate-400">
                              ΔRisk {sim.risk_delta >= 0 ? "+" : ""}
                              {sim.risk_delta}
                            </span>
                          </div>
                          <div className="mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5">
                            <div>
                              <span className="text-slate-400">Baseline:</span>{" "}
                              <span className="font-medium">
                                {sim.baseline_riskScore} ({sim.baseline_severity})
                              </span>
                            </div>
                            <div>
                              <span className="text-slate-400">Simulated:</span>{" "}
                              <span className="font-medium">
                                {sim.simulated_riskScore} ({sim.simulated_severity})
                              </span>
                            </div>
                          </div>
                          {sim.notes && sim.notes.length > 0 && (
                            <ul className="mt-1 list-disc pl-4 text-[11px] text-slate-400">
                              {sim.notes.map((note, idx) => (
                                <li key={idx}>{note}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {/* Payment rail alternatives section */}
          {paymentOptions.length > 0 && (
            <section>
              <h3 className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                Payment Rail Alternatives
              </h3>
              <div className="mt-2 space-y-2">
                {paymentOptions.map((opt) => {
                  const key = simulationKey("payment_rail", opt.option_id);
                  const sim = simulationResults[key];
                  const simLoading = simulationLoading[key] ?? false;
                  const simError = simulationError[key] ?? null;

                  return (
                    <div
                      key={opt.option_id}
                      className="rounded-lg border border-slate-800/70 bg-slate-900/70 p-3"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <div className="text-sm font-semibold text-slate-50">
                            {opt.payment_rail}
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-1 text-[11px]">
                          <span className="rounded-full bg-slate-800/80 px-2 py-0.5 text-slate-100">
                            Risk {opt.riskScore} (Δ{opt.risk_delta})
                          </span>
                          <span className="rounded-full bg-slate-800/80 px-2 py-0.5 text-slate-200">
                            Settlement {opt.settlement_speed}
                          </span>
                          <span className="rounded-full bg-slate-800/80 px-2 py-0.5 text-slate-200">
                            Fees Δ ${opt.fees_delta_usd.toFixed(0)}
                          </span>
                        </div>
                      </div>
                      {opt.notes.length > 0 && (
                        <ul className="mt-2 list-disc space-y-0.5 pl-4 text-[11px] text-slate-300">
                          {opt.notes.map((note) => (
                            <li key={note}>{note}</li>
                          ))}
                        </ul>
                      )}
                      <div className="mt-2 flex items-center justify-end">
                        <button
                          type="button"
                          onClick={() => handleTestRun("payment_rail", opt.option_id)}
                          disabled={simLoading}
                          className="inline-flex items-center rounded-full border border-emerald-400 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-emerald-300 hover:bg-emerald-900/40 disabled:opacity-60 disabled:cursor-not-allowed"
                        >
                          {simLoading ? "Testing..." : "Test Run"}
                        </button>
                      </div>
                      {simError && (
                        <p className="mt-1 text-[11px] text-red-400">
                          {simError}
                        </p>
                      )}
                      {sim && (
                        <div className="mt-2 rounded-lg bg-slate-900/70 px-3 py-2 text-xs text-slate-100 border border-emerald-500/40">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-emerald-300">Simulation Result</span>
                            <span className="text-[10px] uppercase tracking-wide text-slate-400">
                              ΔRisk {sim.risk_delta >= 0 ? "+" : ""}
                              {sim.risk_delta}
                            </span>
                          </div>
                          <div className="mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5">
                            <div>
                              <span className="text-slate-400">Baseline:</span>{" "}
                              <span className="font-medium">
                                {sim.baseline_riskScore} ({sim.baseline_severity})
                              </span>
                            </div>
                            <div>
                              <span className="text-slate-400">Simulated:</span>{" "}
                              <span className="font-medium">
                                {sim.simulated_riskScore} ({sim.simulated_severity})
                              </span>
                            </div>
                          </div>
                          {sim.notes && sim.notes.length > 0 && (
                            <ul className="mt-1 list-disc pl-4 text-[11px] text-slate-400">
                              {sim.notes.map((note, idx) => (
                                <li key={idx}>{note}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>
          )}
        </div>
      </div>
    </>
  );
};

export default SaferOptionsDrawer;
