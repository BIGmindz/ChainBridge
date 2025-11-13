import { useState } from "react";
import { ExceptionRow } from "../types";
import { exportToCSV } from "../utils/formatting";
import { Download } from "lucide-react";

interface ExceptionsTableProps {
  exceptions: ExceptionRow[];
}

/**
 * Exceptions Table Component
 * Full-screen exceptions table with export functionality
 */
export default function ExceptionsTable({
  exceptions,
}: ExceptionsTableProps): JSX.Element {
  const [selectedPreset, setSelectedPreset] = useState<string>("all");

  const presets: Record<string, string> = {
    all: "All Exceptions",
    ops: "Ops View (Pickup/Delivery Delays)",
    finance: "Finance View (Payment Blocks)",
    high_risk: "High Risk (>70 score)",
  };

  const filterByPreset = (preset: string): ExceptionRow[] => {
    switch (preset) {
      case "ops":
        return exceptions.filter(
          (e) =>
            e.issue_types.includes("late_pickup") ||
            e.issue_types.includes("late_delivery")
        );
      case "finance":
        return exceptions.filter((e) => e.payment_state === "blocked");
      case "high_risk":
        return exceptions.filter((e) => e.risk_score >= 70);
      default:
        return exceptions;
    }
  };

  const filtered = filterByPreset(selectedPreset);

  const handleExport = (): void => {
    exportToCSV(filtered, `exceptions_${selectedPreset}_${new Date().toISOString().split("T")[0]}.csv`);
  };

  return (
    <div className="card">
      {/* Controls */}
      <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex items-center justify-between gap-4">
        <div>
          <label className="text-sm font-semibold text-gray-700 block mb-2">
            Saved Views
          </label>
          <select
            value={selectedPreset}
            onChange={(e) => setSelectedPreset(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            {Object.entries(presets).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={handleExport}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors self-end"
        >
          <Download size={18} />
          Export CSV
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-gray-200 bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">
                Shipment ID
              </th>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">Lane</th>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">
                Status
              </th>
              <th className="px-4 py-3 text-center font-semibold text-gray-700">
                Risk
              </th>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">
                Payment State
              </th>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">Age</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                  No exceptions found in this view
                </td>
              </tr>
            ) : (
              filtered.map((exception) => (
                <tr
                  key={exception.shipment_id}
                  className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                >
                  <td className="px-4 py-3 font-mono text-primary-600">
                    {exception.shipment_id}
                  </td>
                  <td className="px-4 py-3 text-gray-700">{exception.lane}</td>
                  <td className="px-4 py-3 capitalize text-gray-700">
                    {exception.current_status}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="px-2 py-1 rounded-full font-semibold text-xs bg-warning-100 text-warning-800">
                      {exception.risk_score}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-medium text-gray-700">
                      {exception.payment_state}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{exception.age_of_issue}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="px-6 py-3 border-t border-gray-200 bg-gray-50 text-xs text-gray-600">
        Showing {filtered.length} of {exceptions.length} exceptions
      </div>
    </div>
  );
}
