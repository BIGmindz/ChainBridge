/**
 * OCExceptionCockpitPage - The OC V0.1 Exception Cockpit
 *
 * The main "pilot cockpit" view for operators to manage exceptions.
 * Layout:
 *   - Top: KPI strip with high-level metrics
 *   - Main: Two-column layout (exception queue + detail pane)
 *   - Bottom: Audit/decision log
 *
 * "Operators are pilots, not spreadsheet janitors."
 */

import { Command, RefreshCw } from "lucide-react";
import { useState } from "react";

import { OCAuditLog } from "../components/oc/OCAuditLog";
import { OCExceptionDetailPane } from "../components/oc/OCExceptionDetailPane";
import { OCExceptionQueue } from "../components/oc/OCExceptionQueue";
import { OCKPIStrip } from "../components/oc/OCKPIStrip";
import { useExceptionDetail, useExceptions, useExceptionStats } from "../hooks/useExceptions";

export default function OCExceptionCockpitPage() {
  const [selectedExceptionId, setSelectedExceptionId] = useState<string | null>(null);

  // Pre-fetch data for refresh indicator
  const { isFetching: exceptionsRefetching, refetch: refetchExceptions } = useExceptions();
  const { isFetching: statsRefetching, refetch: refetchStats } = useExceptionStats();
  const { data: selectedExceptionData } = useExceptionDetail(selectedExceptionId);

  const isRefreshing = exceptionsRefetching || statsRefetching;

  const handleRefresh = () => {
    refetchExceptions();
    refetchStats();
  };

  return (
    <div className="h-screen bg-slate-950 flex flex-col overflow-hidden font-sans text-slate-200">
      {/* HEADER BAR */}
      <div className="bg-slate-900/80 border-b border-slate-800 px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-500/10 rounded-lg">
              <Command className="h-5 w-5 text-emerald-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">The OC — Exception Cockpit</h1>
              <p className="text-xs text-slate-400">Manage by exception · Monitor what matters</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Live Indicator */}
          <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800/50 rounded-full">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-xs font-medium text-emerald-400">LIVE</span>
          </div>

          {/* Refresh Button */}
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm text-slate-300 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="flex-1 flex flex-col overflow-hidden p-4 gap-4">
        {/* KPI STRIP */}
        <div className="shrink-0">
          <OCKPIStrip />
        </div>

        {/* TWO-COLUMN LAYOUT */}
        <div className="flex-1 flex gap-4 min-h-0">
          {/* LEFT PANE: Exception Queue */}
          <div className="w-[400px] lg:w-[450px] shrink-0 bg-slate-900/80 border border-slate-800/70 rounded-xl overflow-hidden flex flex-col">
            <OCExceptionQueue
              selectedExceptionId={selectedExceptionId}
              onSelectException={setSelectedExceptionId}
            />
          </div>

          {/* RIGHT PANE: Exception Detail */}
          <div className="flex-1 bg-slate-900/80 border border-slate-800/70 rounded-xl overflow-hidden">
            <OCExceptionDetailPane selectedExceptionId={selectedExceptionId} />
          </div>
        </div>

        {/* BOTTOM: Audit Log */}
        <div className="shrink-0">
          <OCAuditLog
            shipmentId={selectedExceptionData?.exception.shipment_id}
            exceptionId={selectedExceptionId ?? undefined}
            limit={5}
          />
        </div>
      </div>

      {/* KEYBOARD HINTS FOOTER */}
      <div className="bg-slate-900/60 border-t border-slate-800/50 px-6 py-2 flex items-center justify-center gap-6 shrink-0">
        <div className="flex items-center gap-2 text-[10px] text-slate-500">
          <kbd className="px-1.5 py-0.5 bg-slate-800 rounded text-slate-400">↑</kbd>
          <kbd className="px-1.5 py-0.5 bg-slate-800 rounded text-slate-400">↓</kbd>
          <span>Navigate queue</span>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-slate-500">
          <kbd className="px-1.5 py-0.5 bg-slate-800 rounded text-slate-400">Enter</kbd>
          <span>View details</span>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-slate-500">
          <kbd className="px-1.5 py-0.5 bg-slate-800 rounded text-slate-400">R</kbd>
          <span>Refresh</span>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-slate-500">
          <kbd className="px-1.5 py-0.5 bg-slate-800 rounded text-slate-400">?</kbd>
          <span>Help</span>
        </div>
      </div>
    </div>
  );
}
