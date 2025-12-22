/*
Sunny: implement an EntityHistoryDrawer component to show ChainIQ scoring history
for a shipment as a right-side mission-control drawer.
*/

import React, { useMemo, useState } from "react";

import { getProofPack, type EntityHistoryResponse, type EntityHistoryRecord, type ProofPackResponse } from "../lib/apiClient";

import TimelineEvent from "./TimelineEvent";

interface EntityHistoryDrawerProps {
  shipmentId: string;
  history: EntityHistoryResponse | null;
  loading: boolean;
  error: string | null;
  onReplay: () => void;
  onClose: () => void;
}

const EntityHistoryDrawer: React.FC<EntityHistoryDrawerProps> = ({
  shipmentId,
  history,
  loading,
  error,
  onReplay,
  onClose,
}) => {
  // State for ProofPack download
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<boolean>(false);

  // Compute risk trend from history
  const riskTrend = useMemo(() => {
    if (!history || history.history.length < 2) {
      return "Not enough data for trend.";
    }

    // history.history is newest first, so reverse to get oldest/newest
    const oldest = history.history[history.history.length - 1];
    const newest = history.history[0];
    const firstScore = oldest.score;
    const lastScore = newest.score;

    if (lastScore > firstScore + 5) {
      return "Risk increased";
    } else if (lastScore < firstScore - 5) {
      return "Risk decreased";
    } else {
      return "Risk stable";
    }
  }, [history]);

  // Handle ProofPack download
  const handleDownloadProofPack = async (): Promise<void> => {
    if (!shipmentId) {
      return;
    }

    setDownloadError(null);
    setDownloading(true);

    try {
      const response: ProofPackResponse = await getProofPack(shipmentId);

      // Convert to pretty-printed JSON
      const blob = new Blob([JSON.stringify(response, null, 2)], {
        type: "application/json"
      });

      // Create temporary download link
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `proofpack-${shipmentId}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      const errorMessage = err instanceof Error
        ? err.message
        : "Failed to download ProofPack";
      setDownloadError(errorMessage);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 z-50 w-full max-w-xl bg-slate-950/95 border-l border-slate-800/70 shadow-2xl flex flex-col">
        {/* Header */}
        <div className="border-b border-slate-800/70 px-4 py-4">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="text-[10px] font-semibold tracking-[0.22em] uppercase text-slate-400">
                CHAINIQ // HISTORY
              </div>
              <h2 className="text-lg font-semibold text-slate-50 mt-1">
                Shipment {shipmentId}
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Records: {history?.total_records ?? 0}
              </p>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="rounded-full p-2 text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
              aria-label="Close drawer"
            >
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

          {/* Action Buttons */}
          <div className="mt-3 flex items-center gap-2">
            <button
              type="button"
              onClick={onReplay}
              className="inline-flex items-center rounded-full bg-emerald-500 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-950 hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={loading}
            >
              {loading ? "Replaying..." : "Replay Now"}
            </button>

            <button
              type="button"
              onClick={handleDownloadProofPack}
              className="inline-flex items-center rounded-full border border-slate-600 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-300 hover:bg-slate-800/80 hover:border-slate-500 disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={downloading}
            >
              {downloading ? "Downloading..." : "Download ProofPack"}
            </button>

            {/* Risk Trend */}
            <div className="ml-auto text-[11px] text-slate-400">
              Risk trend: <span className="font-semibold">{riskTrend}</span>
            </div>
          </div>

          {/* Download Error */}
          {downloadError && (
            <div className="mt-3 rounded-lg border border-red-800/50 bg-red-950/30 px-3 py-2">
              <div className="flex items-start gap-2">
                <svg
                  className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <p className="text-xs text-red-400">{downloadError}</p>
              </div>
            </div>
          )}
        </div>

        {/* Body */}
        <div className="mt-4 flex-1 overflow-y-auto px-4 pb-6">
          {/* Loading State */}
          {loading && !history && (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-emerald-500 border-r-transparent"></div>
                <p className="mt-3 text-sm text-slate-400">Loading history...</p>
              </div>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="rounded-lg border border-red-800/50 bg-red-950/30 p-4">
              <div className="flex items-start gap-3">
                <svg
                  className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <div>
                  <h3 className="text-sm font-semibold text-red-300">Error Loading History</h3>
                  <p className="mt-1 text-xs text-red-400">{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* Empty State */}
          {!loading && !error && history && history.history.length === 0 && (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <svg
                  className="mx-auto h-12 w-12 text-slate-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <p className="mt-3 text-sm text-slate-400">
                  No scoring history found for this shipment.
                </p>
              </div>
            </div>
          )}

          {/* Timeline */}
          {!loading && !error && history && history.history.length > 0 && (
            <ol className="relative border-l border-slate-800/70 pl-4 space-y-4">
              {history.history.map((record: EntityHistoryRecord, index: number) => {
                const isMostRecent = index === 0;

                return (
                  <TimelineEvent
                    key={record.timestamp + index}
                    event={record}
                    isLatest={isMostRecent}
                  />
                );
              })}
            </ol>
          )}
        </div>
      </div>
    </>
  );
};

export default EntityHistoryDrawer;
