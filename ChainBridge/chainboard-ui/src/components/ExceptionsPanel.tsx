import { useState } from "react";
import { ExceptionRow, IssueType } from "../types";
import { formatRiskScore, formatStatus, formatPaymentState } from "../utils/formatting";

interface ExceptionsPanelProps {
  onSelectShipment: (shipmentId: string) => void;
}

/**
 * Exceptions Panel Component
 * Table of exception shipments with filtering
 */
export default function ExceptionsPanel({
  onSelectShipment,
}: ExceptionsPanelProps): JSX.Element {
  const [riskRange, setRiskRange] = useState([0, 100]);
  const [selectedIssueTypes, setSelectedIssueTypes] = useState<Set<IssueType>>(
    new Set()
  );
  const [timeWindow, setTimeWindow] = useState<"2h" | "24h" | "7d">("24h");

  // Mock data - would come from API with filters
  const mockExceptions: ExceptionRow[] = [];

  const issueTypes: IssueType[] = [
    "high_risk",
    "late_pickup",
    "late_delivery",
    "no_update",
    "payment_blocked",
  ];

  const toggleIssueType = (issue: IssueType): void => {
    const newSet = new Set(selectedIssueTypes);
    if (newSet.has(issue)) {
      newSet.delete(issue);
    } else {
      newSet.add(issue);
    }
    setSelectedIssueTypes(newSet);
  };

  return (
    <div className="card">
      {/* Filters */}
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <div className="space-y-4">
          <div>
            <label className="text-sm font-semibold text-gray-700">
              Issue Type
            </label>
            <div className="flex flex-wrap gap-2 mt-2">
              {issueTypes.map((issue) => (
                <button
                  key={issue}
                  onClick={() => toggleIssueType(issue)}
                  className={`px-3 py-1 text-xs rounded-full font-medium transition-colors ${
                    selectedIssueTypes.has(issue)
                      ? "bg-primary-600 text-white"
                      : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                  }`}
                >
                  {issue.replace(/_/g, " ")}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-semibold text-gray-700">
                Risk Score Range
              </label>
              <div className="flex gap-2 mt-2">
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={riskRange[0]}
                  onChange={(e) => setRiskRange([parseInt(e.target.value), riskRange[1]])}
                  className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                />
                <span className="self-center text-gray-600">-</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={riskRange[1]}
                  onChange={(e) => setRiskRange([riskRange[0], parseInt(e.target.value)])}
                  className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                />
              </div>
            </div>

            <div>
              <label className="text-sm font-semibold text-gray-700">
                Time Window
              </label>
              <select
                value={timeWindow}
                onChange={(e) => setTimeWindow(e.target.value as "2h" | "24h" | "7d")}
                className="w-full mt-2 px-3 py-1 border border-gray-300 rounded text-sm"
              >
                <option value="2h">Last 2 hours</option>
                <option value="24h">Last 24 hours</option>
                <option value="7d">Last 7 days</option>
              </select>
            </div>
          </div>
        </div>
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
              <th className="px-4 py-3 text-left font-semibold text-gray-700">Status</th>
              <th className="px-4 py-3 text-center font-semibold text-gray-700">
                Risk
              </th>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">
                Payment
              </th>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">Age</th>
            </tr>
          </thead>
          <tbody>
            {mockExceptions.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                  No exceptions found. All systems nominal.
                </td>
              </tr>
            ) : (
              mockExceptions.map((exception) => (
                <tr
                  key={exception.shipment_id}
                  onClick={() => onSelectShipment(exception.shipment_id)}
                  className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3 font-mono text-primary-600">
                    {exception.shipment_id}
                  </td>
                  <td className="px-4 py-3 text-gray-700">{exception.lane}</td>
                  <td className="px-4 py-3">
                    <span
                      className={
                        formatStatus(exception.current_status).color
                      }
                    >
                      {formatStatus(exception.current_status).text}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`px-2 py-1 rounded font-semibold text-xs ${
                        formatRiskScore(exception.risk_score).bgColor
                      } ${formatRiskScore(exception.risk_score).color}`}
                    >
                      {exception.risk_score}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={formatPaymentState(exception.payment_state).color}>
                      {formatPaymentState(exception.payment_state).text}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{exception.age_of_issue}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
