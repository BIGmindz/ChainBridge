import { useState, useMemo, useEffect } from "react";
import {
  X,
  AlertTriangle,
  Shield,
  Activity,
  Truck,
  Box,
  Search,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { RiskEvaluationRecord, RiskModelMetrics } from "../features/chainiq/risk/types";
import { fetchRiskEvaluations, fetchRiskMetricsLatest, RiskBandFilter } from "../features/chainiq/risk/riskApi";
import { CardSkeleton } from "../components/ui/LoadingStates";

const PAGE_SIZE = 10;

export default function RiskConsolePage() {
  // Data State
  const [evaluations, setEvaluations] = useState<RiskEvaluationRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Metrics State
  const [modelMetrics, setModelMetrics] = useState<RiskModelMetrics | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(true);
  const [metricsError, setMetricsError] = useState<string | null>(null);

  // UI State
  const [selectedEvaluation, setSelectedEvaluation] = useState<RiskEvaluationRecord | null>(null);
  const [bandFilter, setBandFilter] = useState<RiskBandFilter>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);

  // Fetch Data
  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    setMetricsLoading(true);
    setMetricsError(null);

    try {
      // Fetch all data (or a large batch) to support client-side filtering and metrics
      const [evalsData, metricsData] = await Promise.all([
        fetchRiskEvaluations({ limit: 1000 }),
        fetchRiskMetricsLatest().catch((err) => {
          console.error("Failed to load metrics:", err);
          setMetricsError("Unable to load model metrics");
          return null;
        }),
      ]);

      setEvaluations(evalsData);
      setModelMetrics(metricsData);
    } catch (err) {
      setError("Failed to load risk evaluations.");
      console.error(err);
    } finally {
      setIsLoading(false);
      setMetricsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Derived Data: Metrics (from raw data)
  const metrics = useMemo(() => {
    const total = evaluations.length;
    const highRisk = evaluations.filter((r) => r.risk_band === "HIGH").length;
    const avgScore =
      total > 0
        ? Math.round(evaluations.reduce((acc, curr) => acc + curr.risk_score, 0) / total)
        : 0;
    const highRiskPercent = total > 0 ? Math.round((highRisk / total) * 100) : 0;

    return { total, highRisk, avgScore, highRiskPercent };
  }, [evaluations]);

  // Derived Data: Filtered & Paged
  const filteredEvaluations = useMemo(() => {
    return evaluations.filter((record) => {
      // Band Filter
      if (bandFilter !== "ALL" && record.risk_band !== bandFilter) return false;

      // Search Filter
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const match =
          record.shipment_id.toLowerCase().includes(q) ||
          record.carrier_id.toLowerCase().includes(q) ||
          record.lane_id.toLowerCase().includes(q);
        if (!match) return false;
      }

      return true;
    });
  }, [evaluations, bandFilter, searchQuery]);

  const pageCount = Math.max(1, Math.ceil(filteredEvaluations.length / PAGE_SIZE));
  const pagedEvaluations = useMemo(() => {
    // Clamp page if out of bounds
    const safePage = Math.min(page, pageCount);
    if (safePage !== page) setPage(safePage);

    const start = (safePage - 1) * PAGE_SIZE;
    return filteredEvaluations.slice(start, start + PAGE_SIZE);
  }, [filteredEvaluations, page, pageCount]);

  // Handlers
  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= pageCount) {
      setPage(newPage);
    }
  };

  const getRiskBadgeVariant = (band: string) => {
    switch (band) {
      case "HIGH":
        return "danger";
      case "MEDIUM":
        return "warning";
      case "LOW":
        return "success";
      default:
        return "default";
    }
  };

  return (
    <div className="flex h-full flex-col overflow-hidden bg-slate-950 p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-slate-100">ChainIQ – Risk Console</h1>
          <Badge variant="info" className="text-xs">
            v1.5 (Mock Data)
          </Badge>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="mb-4 rounded-lg border border-rose-500/50 bg-rose-500/10 p-4 text-rose-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              <span className="font-semibold">Error:</span> {error}
            </div>
            <button
              onClick={loadData}
              className="rounded bg-rose-500/20 px-3 py-1 text-xs font-medium hover:bg-rose-500/30 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Model Health / Metrics Bar */}
      <div className="mb-6">
        <div className="mb-3 flex items-center gap-2">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            Model Health (Maggie)
          </h2>
          {modelMetrics?.has_failures && (
            <Badge variant="danger" className="animate-pulse">
              Failures Detected
            </Badge>
          )}
          {modelMetrics?.has_warnings && !modelMetrics.has_failures && (
            <Badge variant="warning">Warnings Present</Badge>
          )}
        </div>

        {metricsLoading ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
        ) : metricsError ? (
          <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 text-sm text-slate-400">
            Model metrics unavailable
          </div>
        ) : !modelMetrics ? (
          <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 text-sm text-slate-400">
            Awaiting first metrics run
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <Card className="p-4 border-slate-800 bg-slate-900/40">
              <div className="flex flex-col gap-1">
                <span className="text-xs font-medium text-slate-500">Critical Incident Recall</span>
                <div className="flex items-baseline gap-2">
                  <span className="text-xl font-bold text-slate-200">
                    {modelMetrics.critical_incident_recall != null
                      ? `${(modelMetrics.critical_incident_recall * 100).toFixed(1)}%`
                      : "N/A"}
                  </span>
                </div>
              </div>
            </Card>
            <Card className="p-4 border-slate-800 bg-slate-900/40">
              <div className="flex flex-col gap-1">
                <span className="text-xs font-medium text-slate-500">Ops Workload</span>
                <div className="flex items-baseline gap-2">
                  <span className="text-xl font-bold text-slate-200">
                    {modelMetrics.ops_workload_percent != null
                      ? `${(modelMetrics.ops_workload_percent * 100).toFixed(1)}%`
                      : "N/A"}
                  </span>
                </div>
              </div>
            </Card>
            <Card className="p-4 border-slate-800 bg-slate-900/40">
              <div className="flex flex-col gap-1">
                <span className="text-xs font-medium text-slate-500">Loss Value Coverage</span>
                <div className="flex items-baseline gap-2">
                  <span className="text-xl font-bold text-slate-200">
                    {modelMetrics.loss_value_coverage_pct != null
                      ? `${(modelMetrics.loss_value_coverage_pct * 100).toFixed(1)}%`
                      : "N/A"}
                  </span>
                </div>
              </div>
            </Card>
            <Card className="p-4 border-slate-800 bg-slate-900/40">
              <div className="flex flex-col gap-1">
                <span className="text-xs font-medium text-slate-500">Eval Count (Window)</span>
                <div className="flex items-baseline gap-2">
                  <span className="text-xl font-bold text-slate-200">{modelMetrics.eval_count}</span>
                </div>
                <span className="text-[10px] text-slate-500 truncate">
                  {new Date(modelMetrics.evaluation_window_start).toLocaleDateString()} →{" "}
                  {new Date(modelMetrics.evaluation_window_end).toLocaleDateString()}
                </span>
              </div>
            </Card>
          </div>
        )}
      </div>

      {/* Metrics Row */}
      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-4">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-rose-500/10 text-rose-400">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-400">High-Risk Shipments (24h)</p>
              <p className="text-2xl font-bold text-slate-100">{metrics.highRisk}</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400">
              <Shield className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-400">Avg Risk Score (24h)</p>
              <p className="text-2xl font-bold text-slate-100">{metrics.avgScore}</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/10 text-amber-400">
              <Activity className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-400">% Volume Flagged HIGH</p>
              <p className="text-2xl font-bold text-slate-100">{metrics.highRiskPercent}%</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400">
              <Box className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-400">Model Version</p>
              <p className="text-lg font-bold text-slate-100">chainiq_v1_maggie</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Main Content Area */}
      <div className="flex flex-1 gap-6 overflow-hidden">
        {/* Table Section */}
        <Card className="flex flex-1 flex-col overflow-hidden">
          {/* Filter Bar */}
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/70 px-4 py-3">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                Risk Band:
              </span>
              <div className="flex rounded-lg border border-slate-800 bg-slate-950/50 p-1">
                {(["ALL", "HIGH", "MEDIUM", "LOW"] as const).map((band) => (
                  <button
                    key={band}
                    onClick={() => {
                      setBandFilter(band);
                      setPage(1);
                    }}
                    className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                      bandFilter === band
                        ? "bg-slate-800 text-slate-100 shadow-sm"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {band === "ALL" ? "All" : band.charAt(0) + band.slice(1).toLowerCase()}
                  </button>
                ))}
              </div>
            </div>

            <div className="relative w-full max-w-xs">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                placeholder="Search shipment, carrier..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setPage(1);
                }}
                className="w-full rounded-lg border border-slate-800 bg-slate-950/50 py-1.5 pl-9 pr-3 text-sm text-slate-200 placeholder-slate-500 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
              />
            </div>
          </div>

          {/* Table Content */}
          <div className="flex-1 overflow-auto relative">
            {isLoading ? (
              <div className="absolute inset-0 flex items-center justify-center bg-slate-950/50 backdrop-blur-sm">
                <div className="flex flex-col items-center gap-3">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-700 border-t-indigo-500" />
                  <p className="text-sm text-slate-400">Loading risk evaluations...</p>
                </div>
              </div>
            ) : (
              <table className="w-full text-left text-sm text-slate-400">
                <thead className="sticky top-0 z-10 bg-slate-900/95 text-xs uppercase text-slate-500 backdrop-blur-sm">
                  <tr>
                    <th className="px-4 py-3 font-medium">Timestamp (UTC)</th>
                    <th className="px-4 py-3 font-medium">Shipment ID</th>
                    <th className="px-4 py-3 font-medium">Carrier</th>
                    <th className="px-4 py-3 font-medium">Lane</th>
                    <th className="px-4 py-3 font-medium">Score</th>
                    <th className="px-4 py-3 font-medium">Band</th>
                    <th className="px-4 py-3 font-medium">Top Reason</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {pagedEvaluations.length > 0 ? (
                    pagedEvaluations.map((evalRec) => (
                      <tr
                        key={evalRec.evaluation_id}
                        onClick={() => setSelectedEvaluation(evalRec)}
                        className={`cursor-pointer transition-colors hover:bg-slate-800/30 ${
                          selectedEvaluation?.evaluation_id === evalRec.evaluation_id
                            ? "bg-slate-800/50"
                            : ""
                        }`}
                      >
                        <td className="px-4 py-3 text-slate-300">
                          {new Date(evalRec.timestamp).toLocaleString()}
                        </td>
                        <td className="px-4 py-3 font-medium text-indigo-400">
                          {evalRec.shipment_id}
                        </td>
                        <td className="px-4 py-3 text-slate-300">{evalRec.carrier_id}</td>
                        <td className="px-4 py-3 text-slate-300">{evalRec.lane_id}</td>
                        <td className="px-4 py-3 font-mono text-slate-200">
                          {evalRec.risk_score}
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant={getRiskBadgeVariant(evalRec.risk_band)}>
                            {evalRec.risk_band}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-slate-400 truncate max-w-[200px]">
                          {evalRec.primary_reasons[0] || "-"}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                        No evaluations found matching your filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
          </div>

          {/* Pagination Footer */}
          <div className="flex items-center justify-between border-t border-slate-800/70 px-4 py-3 bg-slate-900/30">
            <div className="text-xs text-slate-500">
              Showing {pagedEvaluations.length} of {filteredEvaluations.length} results
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handlePageChange(page - 1)}
                disabled={page === 1 || isLoading}
                className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200 disabled:opacity-50 disabled:hover:bg-transparent"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="text-xs font-medium text-slate-400">
                Page {page} of {pageCount}
              </span>
              <button
                onClick={() => handlePageChange(page + 1)}
                disabled={page === pageCount || isLoading}
                className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200 disabled:opacity-50 disabled:hover:bg-transparent"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </Card>

        {/* Details Panel */}
        {selectedEvaluation && (
          <Card className="w-96 flex flex-col overflow-hidden border-l border-slate-800 bg-slate-950/95">
            <div className="flex items-center justify-between border-b border-slate-800/70 px-4 py-3">
              <h3 className="font-semibold text-slate-200">Evaluation Details</h3>
              <button
                onClick={() => setSelectedEvaluation(null)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-6">
              {/* Header Info */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-slate-500">Evaluation ID</span>
                  <span className="text-xs font-mono text-slate-400">
                    {selectedEvaluation.evaluation_id}
                  </span>
                </div>
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs text-slate-500">Model Version</span>
                  <span className="text-xs font-mono text-slate-400">
                    {selectedEvaluation.model_version}
                  </span>
                </div>

                <div className="flex items-center gap-4 mb-4">
                  <div className="flex-1 bg-slate-900 rounded-lg p-3 text-center border border-slate-800">
                    <div className="text-xs text-slate-500 mb-1">Risk Score</div>
                    <div className="text-2xl font-bold text-slate-100">
                      {selectedEvaluation.risk_score}
                    </div>
                  </div>
                  <div className="flex-1 bg-slate-900 rounded-lg p-3 text-center border border-slate-800">
                    <div className="text-xs text-slate-500 mb-1">Risk Band</div>
                    <Badge variant={getRiskBadgeVariant(selectedEvaluation.risk_band)}>
                      {selectedEvaluation.risk_band}
                    </Badge>
                  </div>
                </div>
              </div>

              {/* Primary Reasons */}
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">
                  Primary Reasons
                </h4>
                {selectedEvaluation.primary_reasons.length > 0 ? (
                  <ul className="space-y-2">
                    {selectedEvaluation.primary_reasons.map((reason, idx) => (
                      <li
                        key={idx}
                        className="flex items-start gap-2 text-sm text-slate-300 bg-slate-900/50 p-2 rounded border border-slate-800/50"
                      >
                        <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
                        <span>{reason}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-500 italic">
                    No specific risk factors identified.
                  </p>
                )}
              </div>

              {/* Features Snapshot */}
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">
                  Features Snapshot
                </h4>

                <div className="space-y-4">
                  {/* Shipment */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs text-indigo-400">
                      <Box className="h-3 w-3" /> Shipment
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="bg-slate-900/30 p-2 rounded border border-slate-800/30">
                        <div className="text-slate-500">Value (USD)</div>
                        <div className="text-slate-200 font-mono">
                          ${selectedEvaluation.features_snapshot.value_usd.toLocaleString()}
                        </div>
                      </div>
                      <div className="bg-slate-900/30 p-2 rounded border border-slate-800/30">
                        <div className="text-slate-500">Hazmat</div>
                        <div
                          className={
                            selectedEvaluation.features_snapshot.is_hazmat
                              ? "text-rose-400"
                              : "text-slate-200"
                          }
                        >
                          {selectedEvaluation.features_snapshot.is_hazmat ? "YES" : "NO"}
                        </div>
                      </div>
                      <div className="bg-slate-900/30 p-2 rounded border border-slate-800/30">
                        <div className="text-slate-500">Temp Control</div>
                        <div
                          className={
                            selectedEvaluation.features_snapshot.is_temp_control
                              ? "text-sky-400"
                              : "text-slate-200"
                          }
                        >
                          {selectedEvaluation.features_snapshot.is_temp_control ? "YES" : "NO"}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Lane & Carrier */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs text-indigo-400">
                      <Truck className="h-3 w-3" /> Lane & Carrier
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="bg-slate-900/30 p-2 rounded border border-slate-800/30">
                        <div className="text-slate-500">Lane Risk Idx</div>
                        <div className="text-slate-200 font-mono">
                          {selectedEvaluation.features_snapshot.lane_risk_index}
                        </div>
                      </div>
                      <div className="bg-slate-900/30 p-2 rounded border border-slate-800/30">
                        <div className="text-slate-500">Border Crossings</div>
                        <div className="text-slate-200 font-mono">
                          {selectedEvaluation.features_snapshot.border_crossing_count}
                        </div>
                      </div>
                      <div className="bg-slate-900/30 p-2 rounded border border-slate-800/30">
                        <div className="text-slate-500">Carrier Incident Rate</div>
                        <div className="text-slate-200 font-mono">
                          {selectedEvaluation.features_snapshot.carrier_incident_rate_90d ?? "N/A"}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Events */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs text-indigo-400">
                      <Activity className="h-3 w-3" /> Events
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="bg-slate-900/30 p-2 rounded border border-slate-800/30">
                        <div className="text-slate-500">IoT Alerts</div>
                        <div
                          className={`font-mono ${
                            selectedEvaluation.features_snapshot.iot_alert_count > 0
                              ? "text-amber-400"
                              : "text-slate-200"
                          }`}
                        >
                          {selectedEvaluation.features_snapshot.iot_alert_count}
                        </div>
                      </div>
                      <div className="bg-slate-900/30 p-2 rounded border border-slate-800/30">
                        <div className="text-slate-500">Recent Delays</div>
                        <div
                          className={`font-mono ${
                            selectedEvaluation.features_snapshot.recent_delay_events > 0
                              ? "text-amber-400"
                              : "text-slate-200"
                          }`}
                        >
                          {selectedEvaluation.features_snapshot.recent_delay_events}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
