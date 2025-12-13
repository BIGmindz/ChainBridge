import { useEffect, useMemo } from "react";

import ShipmentsTable from "../components/ShipmentsTable";
import { useDemo } from "../core/demo/DemoContext";
import { useShipmentsOverview } from "../hooks/useShipmentsOverview";
import { useShipmentsViews } from "../hooks/useShipmentsViews";
import type { Shipment } from "../lib/types";

export default function ShipmentsPage(): JSX.Element {
  useEffect(() => {
    if (import.meta.env.DEV) {
      console.log("[ShipmentsPage] MOUNTED");
    }
    return () => {
      if (import.meta.env.DEV) {
        console.log("[ShipmentsPage] UNMOUNTED");
      }
    };
  }, []);

  // Demo mode highlight key
  const { state: demoState } = useDemo();
  const highlightKey = demoState.currentStep?.highlightKey;

  // View engine manages filters, saved views, and localStorage
  const {
    views,
    currentView,
    currentFilters,
    setFilters,
    selectView,
  } = useShipmentsViews();

  // Build API filters from current view filters
  const apiFilters = useMemo(() => {
    const filters: Record<string, unknown> = {};

    if (currentFilters.riskCategory) {
      filters.risk = currentFilters.riskCategory;
    }

    if (currentFilters.corridor) {
      filters.corridor = currentFilters.corridor;
    }

    return Object.keys(filters).length > 0 ? filters : undefined;
  }, [currentFilters]);

  const { data: shipments, total, loading, error, refresh } = useShipmentsOverview(apiFilters);

  // Apply client-side filters that backend doesn't support yet
  const filteredShipments = useMemo(() => {
    if (shipments.length === 0) {
      return [];
    }

    return shipments.filter((shipment: Shipment) => {
      // Search filter (reference, corridor, customer)
      if (currentFilters.search) {
        const searchLower = currentFilters.search.toLowerCase();
        const matchesSearch =
          shipment.reference.toLowerCase().includes(searchLower) ||
          shipment.corridor.toLowerCase().includes(searchLower) ||
          shipment.customer.toLowerCase().includes(searchLower);
        if (!matchesSearch) return false;
      }

      // Payment state filter
      if (currentFilters.paymentState && shipment.payment.state !== currentFilters.paymentState) {
        return false;
      }

      // IoT alerts filter (check if shipment has IoT anomalies)
      if (currentFilters.hasIoTAlerts) {
        // For now, use risk score as proxy for IoT alerts
        // In production, this would check actual IoT data
        if (shipment.risk.score < 60) return false;
      }

      // Payment hold filter
      if (currentFilters.hasPaymentHold) {
        if (shipment.payment.state !== "blocked" && shipment.payment.state !== "partially_paid") {
          return false;
        }
      }

      return true;
    });
  }, [shipments, currentFilters]);

  return (
    <div className="space-y-6 text-slate-100">
      <header className="space-y-2 border-b border-slate-800/60 pb-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-slate-500">
          Shipments Intelligence
        </p>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-slate-50">Manifest Drilldown</h1>
            <p className="text-sm text-slate-400">
              Filter shipments by saved views, search, and Control Tower intelligence.
            </p>
          </div>
        </div>
      </header>

      {/* View Bar + Search */}
      <section
        className={`space-y-3 ${
          highlightKey === "view_bar" ? "ring-2 ring-emerald-400 rounded-lg p-2" : ""
        }`}
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* View Pills */}
          <div className="flex flex-wrap items-center gap-2">
            {views.map((view) => (
              <button
                key={view.id}
                type="button"
                onClick={() => selectView(view.id)}
                className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                  view.id === currentView.id
                    ? "border-emerald-500 bg-emerald-500 text-white"
                    : "border-slate-700 bg-slate-900/70 text-slate-300 hover:bg-slate-800"
                }`}
              >
                {view.name}
              </button>
            ))}
          </div>

          {/* Search Input */}
          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Search by reference, corridor, customer..."
              className="w-64 rounded-lg border border-slate-700 bg-slate-900/70 px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-emerald-400"
              value={currentFilters.search ?? ""}
              onChange={(e) =>
                setFilters({
                  ...currentFilters,
                  search: e.target.value || null,
                })
              }
            />
            <button
              type="button"
              onClick={refresh}
              disabled={loading}
              className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-slate-200 transition hover:border-emerald-400 disabled:opacity-50"
            >
              {loading ? "Refreshing" : "Refresh"}
            </button>
          </div>
        </div>

        {/* View Description */}
        {currentView.description && (
          <p className="text-xs text-slate-400">{currentView.description}</p>
        )}

        {/* Results Count */}
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>
            Showing {filteredShipments.length} of {total || "–"} shipments
          </span>
          {currentFilters.search && (
            <button
              type="button"
              onClick={() => setFilters({ ...currentFilters, search: null })}
              className="text-emerald-400 hover:underline"
            >
              Clear search
            </button>
          )}
        </div>
      </section>

      {/* Shipments Table */}
      {loading ? (
        <div className="flex h-72 items-center justify-center rounded-2xl border border-slate-800 bg-slate-950/60">
          <div className="text-center text-sm text-slate-400">
            <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-2 border-slate-800 border-t-emerald-400" />
            Fetching manifest telemetry…
          </div>
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-danger-500/40 bg-danger-500/10 p-6 text-sm text-danger-200">
          {error}
        </div>
      ) : (
        <ShipmentsTable shipments={filteredShipments} />
      )}
    </div>
  );
}
