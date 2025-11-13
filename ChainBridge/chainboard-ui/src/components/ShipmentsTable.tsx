import { Shipment } from "../types";
import { formatRiskScore, formatPaymentState, calculatePaymentProgress } from "../utils/formatting";

interface ShipmentsTableProps {
  shipments: Shipment[];
}

/**
 * Shipments Table Component
 * Full shipment manifest with sorting and filtering
 */
export default function ShipmentsTable({ shipments }: ShipmentsTableProps): JSX.Element {
  return (
    <div className="card overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="border-b border-gray-200 bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-semibold text-gray-700">
              Shipment ID
            </th>
            <th className="px-4 py-3 text-left font-semibold text-gray-700">Carrier</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-700">Customer</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-700">Lane</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-700">Status</th>
            <th className="px-4 py-3 text-center font-semibold text-gray-700">Risk</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-700">
              Payment
            </th>
            <th className="px-4 py-3 text-center font-semibold text-gray-700">
              Progress
            </th>
          </tr>
        </thead>
        <tbody>
          {shipments.length === 0 ? (
            <tr>
              <td colSpan={8} className="px-4 py-8 text-center text-gray-500">
                No shipments found
              </td>
            </tr>
          ) : (
            shipments.map((shipment) => {
              const paymentProgress = calculatePaymentProgress(shipment);
              return (
                <tr
                  key={shipment.shipment_id}
                  className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                >
                  <td className="px-4 py-3 font-mono text-primary-600">
                    {shipment.shipment_id}
                  </td>
                  <td className="px-4 py-3 text-gray-700">{shipment.carrier}</td>
                  <td className="px-4 py-3 text-gray-700">{shipment.customer}</td>
                  <td className="px-4 py-3 text-gray-700">
                    {shipment.origin} → {shipment.destination}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`capitalize`}>{shipment.current_status}</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`px-2 py-1 rounded font-semibold text-xs ${
                        formatRiskScore(shipment.risk.risk_score).bgColor
                      } ${formatRiskScore(shipment.risk.risk_score).color}`}
                    >
                      {shipment.risk.risk_score}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={formatPaymentState(shipment.payment_state).color}>
                      {formatPaymentState(shipment.payment_state).text}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-20 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-primary-600 h-2 rounded-full"
                          style={{ width: `${paymentProgress}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-gray-600 w-8">
                        {Math.round(paymentProgress)}%
                      </span>
                    </div>
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
