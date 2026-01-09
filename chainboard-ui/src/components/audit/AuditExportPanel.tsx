/**
 * AuditExportPanel — Export controls for audit data
 * ════════════════════════════════════════════════════════════════════════════════
 *
 * PAC Reference: PAC-013A (CORRECTED · GOLD STANDARD)
 * Agent: Sonny (GID-02) — Audit UI
 * Order: ORDER 3
 * Effective Date: 2025-12-30
 *
 * INV-AUDIT-003: Export formats: JSON, CSV
 *
 * ════════════════════════════════════════════════════════════════════════════════
 */

import React, { useState } from "react";
import { AuditExportResponse, AuditExportFormat } from "../../types/audit";

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

interface AuditExportPanelProps {
  onExportJson: (params: ExportParams) => Promise<AuditExportResponse>;
  onExportCsv: (params: ExportParams) => Promise<string>;
}

interface ExportParams {
  start_date?: string;
  end_date?: string;
  limit?: number;
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export default function AuditExportPanel({
  onExportJson,
  onExportCsv,
}: AuditExportPanelProps): JSX.Element {
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [limit, setLimit] = useState<number>(1000);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [lastExport, setLastExport] = useState<AuditExportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleExportJson = async () => {
    setIsExporting(true);
    setError(null);
    try {
      const params: ExportParams = { limit };
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;

      const result = await onExportJson(params);
      setLastExport(result);

      // Download as JSON file
      const blob = new Blob([JSON.stringify(result, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit_export_${result.export_id}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportCsv = async () => {
    setIsExporting(true);
    setError(null);
    try {
      const params: ExportParams = { limit };
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;

      const blobUrl = await onExportCsv(params);

      // Download CSV file
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = `audit_export_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(blobUrl);
    } catch (err) {
      setError(err instanceof Error ? err.message : "CSV export failed");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      {/* Header */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Audit Data Export</h3>
        <p className="text-sm text-gray-500 mt-1">
          Export audit trail data for external verification. INV-AUDIT-003: JSON and CSV
          formats supported.
        </p>
      </div>

      {/* Filter Controls */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Start Date (ISO 8601)
          </label>
          <input
            type="datetime-local"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            End Date (ISO 8601)
          </label>
          <input
            type="datetime-local"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Max Records
          </label>
          <input
            type="number"
            min={1}
            max={10000}
            value={limit}
            onChange={(e) => setLimit(parseInt(e.target.value, 10) || 1000)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
      </div>

      {/* Export Buttons */}
      <div className="flex gap-4 mb-6">
        <button
          onClick={handleExportJson}
          disabled={isExporting}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isExporting ? (
            <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
          )}
          Export JSON
        </button>

        <button
          onClick={handleExportCsv}
          disabled={isExporting}
          className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isExporting ? (
            <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          )}
          Export CSV
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Last Export Info */}
      {lastExport && (
        <div className="border-t border-gray-200 pt-4">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Last Export</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Export ID:</span>
              <br />
              <span className="font-mono text-xs">{lastExport.export_id}</span>
            </div>
            <div>
              <span className="text-gray-500">Records:</span>
              <br />
              <span>{lastExport.total_records}</span>
            </div>
            <div>
              <span className="text-gray-500">Format:</span>
              <br />
              <span className="uppercase">{lastExport.format}</span>
            </div>
            <div>
              <span className="text-gray-500">Hash:</span>
              <br />
              <span className="font-mono text-xs">
                {lastExport.export_hash.slice(0, 16)}...
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Invariant Notice */}
      <div className="mt-6 p-3 bg-gray-50 rounded-md">
        <p className="text-xs text-gray-500">
          <strong>INV-AUDIT-003:</strong> Export formats include JSON and CSV.
          <br />
          <strong>INV-AUDIT-006:</strong> Temporal bounds are explicit on all exports.
        </p>
      </div>
    </div>
  );
}
