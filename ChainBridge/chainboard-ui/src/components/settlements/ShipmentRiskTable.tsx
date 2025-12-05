import { AlertTriangle, ChevronLeft, ChevronRight, Download, Loader2 } from "lucide-react";
import { useState } from "react";

import type { AtRiskFilters } from "../../hooks/useAtRiskShipments";
import type { AtRiskShipmentSummary } from "../../types/chainbridge";
import { classNames } from "../../utils/classNames";
import { Badge } from "../ui/Badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/Card";
import { Skeleton } from "../ui/Skeleton";

interface ShipmentRiskTableProps {
  data: AtRiskShipmentSummary[] | undefined;
  isLoading: boolean;
  isError: boolean;
  error?: Error | null;
  filters: AtRiskFilters;
  onFiltersChange: (partial: Partial<AtRiskFilters>) => void;
  onPageChange: (page: number, pageSize: number) => void;
  onSelectShipment: (shipmentId: string) => void;
  onExportSnapshot: (shipmentId: string) => void;
  onLoadDemoData?: () => void;
}

const riskLevelVariantMap = {
  LOW: "success",
  MODERATE: "warning",
  HIGH: "danger",
} as const;

function formatTimestamp(isoString: string): string {
  try {
    const date = new Date(isoString);
    return date.toLocaleString();
  } catch {
    return "—";
  }
}

function formatCorridor(corridorCode?: string | null): string {
  if (!corridorCode) return "—";
  // Convert corridor code to readable format (e.g., "IN_US" -> "IN → US")
  return corridorCode.replace("_", " → ");
}

function getSnapshotStatusInfo(status?: string | null): { text: string; variant: "info" | "warning" | "success" | "danger" } {
  switch (status) {
    case "SUCCESS":
      return { text: "Exported", variant: "success" };
    case "PENDING":
    case "IN_PROGRESS":
      return { text: "Exporting…", variant: "warning" };
    case "FAILED":
      return { text: "Failed", variant: "danger" };
    default:
      return { text: "Not exported", variant: "info" };
  }
}

export function ShipmentRiskTable({
  data,
  isLoading,
  isError,
  error,
  filters,
  onFiltersChange,
  onPageChange,
  onSelectShipment,
  onExportSnapshot,
  onLoadDemoData,
}: ShipmentRiskTableProps): JSX.Element {
  const [exportingIds, setExportingIds] = useState<Set<string>>(new Set());
  const currentPage = Math.floor(filters.offset / filters.maxResults) + 1;
  const hasNextPage = data && data.length === filters.maxResults;

  const handlePreviousPage = () => {
    if (currentPage > 1) {
      onPageChange(currentPage - 1, filters.maxResults);
    }
  };

  const handleNextPage = () => {
    if (hasNextPage) {
      onPageChange(currentPage + 1, filters.maxResults);
    }
  };

  const handlePageSizeChange = (newPageSize: number) => {
    onPageChange(1, newPageSize); // Reset to page 1 when changing page size
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-orange-400" />
          <div>
            <CardTitle>Fleet Risk Overview</CardTitle>
            <CardDescription>
              Monitor and filter at-risk shipments across your fleet
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Risk Level Quick Filters */}
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-slate-400 mr-2">Filter by Risk:</span>
          {(['All', 'CRITICAL', 'HIGH', 'MODERATE', 'LOW'] as const).map((level) => (
            <button
              key={level}
              onClick={() => {
                onFiltersChange({ riskLevel: level === 'All' ? undefined : level, offset: 0 });
              }}
              className={classNames(
                'px-3 py-1.5 rounded-full text-xs font-medium transition-all',
                filters.riskLevel === (level === 'All' ? undefined : level)
                  ? level === 'CRITICAL'
                    ? 'bg-red-600 text-white border border-red-500'
                    : level === 'HIGH'
                    ? 'bg-orange-600 text-white border border-orange-500'
                    : level === 'MODERATE'
                    ? 'bg-yellow-600 text-white border border-yellow-500'
                    : level === 'LOW'
                    ? 'bg-green-600 text-white border border-green-500'
                    : 'bg-blue-600 text-white border border-blue-500'
                  : 'bg-slate-800 text-slate-300 border border-slate-700 hover:border-slate-600'
              )}
            >
              {level}
            </button>
          ))}
        </div>

        {/* Filters Row */}
        <div className="mb-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 p-4 bg-slate-900/50 rounded-lg border border-slate-800">
          {/* Min Risk Score */}
          <div>
            <label htmlFor="risk-score" className="block text-xs font-medium text-slate-400 mb-1.5">
              Min Risk Score
            </label>
            <input
              id="risk-score"
              type="number"
              min="0"
              max="100"
              value={filters.minRiskScore}
              onChange={(e) => onFiltersChange({ minRiskScore: parseInt(e.target.value) || 0 })}
              className="w-full px-3 py-2 text-sm bg-slate-950/50 border border-slate-700 rounded-md text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Corridor */}
          <div>
            <label htmlFor="corridor" className="block text-xs font-medium text-slate-400 mb-1.5">
              Corridor
            </label>
            <input
              id="corridor"
              type="text"
              placeholder="e.g., TRANSPACIFIC"
              value={filters.corridorCode || ''}
              onChange={(e) => onFiltersChange({ corridorCode: e.target.value || undefined })}
              className="w-full px-3 py-2 text-sm bg-slate-950/50 border border-slate-700 rounded-md text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Mode */}
          <div>
            <label htmlFor="mode" className="block text-xs font-medium text-slate-400 mb-1.5">
              Mode
            </label>
            <select
              id="mode"
              value={filters.mode || ''}
              onChange={(e) => onFiltersChange({ mode: e.target.value || undefined })}
              className="w-full px-3 py-2 text-sm bg-slate-950/50 border border-slate-700 rounded-md text-slate-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            >
              <option value="">All Modes</option>
              <option value="OCEAN">Ocean</option>
              <option value="AIR">Air</option>
              <option value="ROAD">Road</option>
              <option value="RAIL">Rail</option>
            </select>
          </div>

          {/* Incoterm */}
          <div>
            <label htmlFor="incoterm" className="block text-xs font-medium text-slate-400 mb-1.5">
              Incoterm
            </label>
            <select
              id="incoterm"
              value={filters.incoterm || ''}
              onChange={(e) => onFiltersChange({ incoterm: e.target.value || undefined })}
              className="w-full px-3 py-2 text-sm bg-slate-950/50 border border-slate-700 rounded-md text-slate-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            >
              <option value="">All Terms</option>
              <option value="FOB">FOB</option>
              <option value="CIF">CIF</option>
              <option value="DAP">DAP</option>
              <option value="DDP">DDP</option>
              <option value="EXW">EXW</option>
            </select>
          </div>

          {/* Risk Level */}
          <div>
            <label htmlFor="risk-level" className="block text-xs font-medium text-slate-400 mb-1.5">
              Risk Level
            </label>
            <select
              id="risk-level"
              value={filters.riskLevel || ''}
              onChange={(e) => onFiltersChange({ riskLevel: e.target.value || undefined })}
              className="w-full px-3 py-2 text-sm bg-slate-950/50 border border-slate-700 rounded-md text-slate-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            >
              <option value="">All Levels</option>
              <option value="LOW">Low</option>
              <option value="MODERATE">Moderate</option>
              <option value="HIGH">High</option>
              <option value="CRITICAL">Critical</option>
            </select>
          </div>

          {/* Page Size */}
          <div>
            <label htmlFor="page-size" className="block text-xs font-medium text-slate-400 mb-1.5">
              Page Size
            </label>
            <select
              id="page-size"
              value={filters.maxResults}
              onChange={(e) => handlePageSizeChange(parseInt(e.target.value))}
              className="w-full px-3 py-2 text-sm bg-slate-950/50 border border-slate-700 rounded-md text-slate-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
            </select>
          </div>
        </div>
        {/* Loading State */}
        {isLoading && (
          <div className="space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
          </div>
        )}

        {/* Error State */}
        {isError && !isLoading && (
          <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-100">
            <p className="font-semibold">Unable to load at-risk shipments. Please retry.</p>
            {import.meta.env.DEV && error && (
              <p className="mt-1 text-xs text-rose-200">
                {error instanceof Error ? error.message : "Unknown error"}
              </p>
            )}
          </div>
        )}

        {/* Data State */}
        {data && !isError && !isLoading && (
          <>
            {data.length === 0 ? (
              <div className="text-center py-12 text-slate-400">
                <AlertTriangle className="h-12 w-12 mx-auto mb-4 opacity-30" />
                <p className="text-base font-medium mb-2">No at-risk shipments found</p>
                <p className="text-sm mb-6">Try adjusting your filter criteria or load demo data to explore the Fleet Cockpit.</p>
                {import.meta.env.VITE_DEMO_MODE === 'true' && onLoadDemoData && (
                  <button
                    onClick={onLoadDemoData}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    <span>📊</span> Load Demo Data
                  </button>
                )}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-800">
                      <th className="text-left py-3 px-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Shipment ID
                      </th>
                      <th className="text-left py-3 px-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Corridor
                      </th>
                      <th className="text-left py-3 px-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Mode
                      </th>
                      <th className="text-left py-3 px-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Incoterm
                      </th>
                      <th className="text-left py-3 px-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Completeness
                      </th>
                      <th className="text-left py-3 px-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Blocking
                      </th>
                      <th className="text-left py-3 px-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Risk Level
                      </th>
                      <th className="text-left py-3 px-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Risk Score
                      </th>
                      <th className="text-left py-3 px-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Last Snapshot
                      </th>
                      <th className="text-left py-3 px-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Export Status
                      </th>
                      <th className="text-center py-3 px-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Export
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((shipment) => {
                      const completeness = shipment.completeness_pct ?? shipment.completenessPct ?? 0;
                      const blockingGaps = shipment.blocking_gap_count ?? shipment.blockingGapCount ?? 0;
                      const riskLevel = shipment.risk_level ?? shipment.riskLevel;
                      return (
                      <tr
                        key={shipment.shipmentId}
                        className="border-b border-slate-800/50 transition-colors cursor-pointer hover:bg-slate-800/30"
                        onClick={() => onSelectShipment(shipment.shipmentId)}
                      >
                        <td className="py-3 px-2">
                          <span className="text-sm font-medium text-slate-100">
                            {shipment.shipmentId}
                          </span>
                          {shipment.template_name && (
                            <div className="text-xs text-slate-500 mt-1">
                              {shipment.template_name}
                            </div>
                          )}
                        </td>
                        <td className="py-3 px-2 text-sm text-slate-300">
                          {formatCorridor(shipment.corridor_code)}
                        </td>
                        <td className="py-3 px-2 text-sm text-slate-300">
                          {shipment.mode || "—"}
                        </td>
                        <td className="py-3 px-2 text-sm text-slate-300">
                          {shipment.incoterm || "—"}
                        </td>
                        <td className="py-3 px-2">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-slate-100">
                              {completeness}%
                            </span>
                            <div className="w-12 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                              <div
                                className={classNames(
                                  "h-full transition-all duration-300",
                                  completeness >= 80 ? "bg-emerald-500" :
                                  completeness >= 60 ? "bg-yellow-500" : "bg-rose-500",
                                  completeness === 0 && "w-0",
                                  completeness > 0 && completeness < 25 && "w-1/4",
                                  completeness >= 25 && completeness < 50 && "w-1/2",
                                  completeness >= 50 && completeness < 75 && "w-3/4",
                                  completeness >= 75 && "w-full"
                                )}
                              />
                            </div>
                          </div>
                        </td>
                        <td className="py-3 px-2">
                          {blockingGaps > 0 ? (
                            <div className="flex items-center gap-1">
                              <AlertTriangle className="h-3 w-3 text-rose-400" />
                              <span className="text-sm font-medium text-rose-300">
                                {blockingGaps}
                              </span>
                            </div>
                          ) : (
                            <span className="text-sm text-slate-500">0</span>
                          )}
                        </td>
                        <td className="py-3 px-2">
                          <Badge
                            variant={riskLevelVariantMap[riskLevel as keyof typeof riskLevelVariantMap] || "info"}
                            className="text-xs"
                          >
                            {riskLevel}
                          </Badge>
                        </td>
                        <td className="py-3 px-2">
                          <span className="text-sm font-medium text-slate-100">
                            {shipment.riskScore}
                          </span>
                          <span className="text-xs text-slate-500">/100</span>
                        </td>
                        <td className="py-3 px-2 text-xs text-slate-400">
                          {formatTimestamp(shipment.last_snapshot_at)}
                        </td>
                        <td className="py-3 px-2">
                          <Badge
                            variant={getSnapshotStatusInfo(shipment.latestSnapshotStatus).variant}
                            className="text-xs"
                          >
                            {getSnapshotStatusInfo(shipment.latestSnapshotStatus).text}
                          </Badge>
                        </td>
                        <td className="py-3 px-2 text-center">
                          <button
                            onClick={async (e) => {
                              e.stopPropagation(); // Prevent row selection when clicking export button
                              if (exportingIds.has(shipment.shipmentId)) return;

                              setExportingIds(prev => new Set(prev).add(shipment.shipmentId));
                              try {
                                await onExportSnapshot(shipment.shipmentId);
                              } finally {
                                setExportingIds(prev => {
                                  const next = new Set(prev);
                                  next.delete(shipment.shipmentId);
                                  return next;
                                });
                              }
                            }}
                            disabled={
                              shipment.latestSnapshotStatus === "PENDING" ||
                              shipment.latestSnapshotStatus === "IN_PROGRESS" ||
                              exportingIds.has(shipment.shipmentId)
                            }
                            className={classNames(
                              "inline-flex items-center justify-center p-1.5 rounded-md transition-colors",
                              shipment.latestSnapshotStatus === "PENDING" ||
                              shipment.latestSnapshotStatus === "IN_PROGRESS" ||
                              exportingIds.has(shipment.shipmentId)
                                ? "text-slate-500 bg-slate-800/50 cursor-not-allowed"
                                : "text-slate-300 bg-slate-700 hover:bg-slate-600 hover:text-slate-100"
                            )}
                            title={
                              shipment.latestSnapshotStatus === "PENDING" ||
                              shipment.latestSnapshotStatus === "IN_PROGRESS" ||
                              exportingIds.has(shipment.shipmentId)
                                ? "Export in progress"
                                : "Export snapshot for this shipment"
                            }
                          >
                            {exportingIds.has(shipment.shipmentId) ||
                             shipment.latestSnapshotStatus === "PENDING" ||
                             shipment.latestSnapshotStatus === "IN_PROGRESS" ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <Download className="h-3 w-3" />
                            )}
                          </button>
                        </td>
                      </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination Footer */}
            {data.length > 0 && (
              <div className="mt-4 flex items-center justify-between">
                <div className="text-xs text-slate-500">
                  Showing {data.length} shipment{data.length !== 1 ? 's' : ''}
                  {filters.minRiskScore > 0 && ` with risk score ≥ ${filters.minRiskScore}`}
                  {currentPage > 1 && ` (page ${currentPage})`}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handlePreviousPage}
                    disabled={currentPage <= 1}
                    className={classNames(
                      "px-3 py-1 text-xs rounded-md border transition-colors",
                      currentPage <= 1
                        ? "border-slate-700 bg-slate-800/50 text-slate-500 cursor-not-allowed"
                        : "border-slate-600 bg-slate-700 text-slate-300 hover:bg-slate-600"
                    )}
                  >
                    <ChevronLeft className="h-3 w-3 mr-1 inline" />
                    Previous
                  </button>

                  <span className="text-xs text-slate-400 px-2">
                    Page {currentPage}
                  </span>

                  <button
                    onClick={handleNextPage}
                    disabled={!hasNextPage}
                    className={classNames(
                      "px-3 py-1 text-xs rounded-md border transition-colors",
                      !hasNextPage
                        ? "border-slate-700 bg-slate-800/50 text-slate-500 cursor-not-allowed"
                        : "border-slate-600 bg-slate-700 text-slate-300 hover:bg-slate-600"
                    )}
                  >
                    Next
                    <ChevronRight className="h-3 w-3 ml-1 inline" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
