import {
  formatRiskScore,
  formatPaymentState,
  calculatePaymentProgress,
} from "../lib/formatters";
import type { Shipment } from "../lib/types";

interface ShipmentsTableProps {
  shipments: Shipment[];
}

/**
 * Shipments Table Component
 * Full shipment manifest with sorting and filtering
 */
export default function ShipmentsTable({ shipments }: ShipmentsTableProps): JSX.Element {
  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-950/60">
      <table className="min-w-full text-sm text-slate-200">
        <thead className="bg-slate-900/80 text-[11px] uppercase tracking-[0.16em] text-slate-400">
          <tr>
            <th className="px-4 py-3 text-left">Shipment ID</th>
            <th className="px-4 py-3 text-left">Carrier</th>
            <th className="px-4 py-3 text-left">Customer</th>
            <th className="px-4 py-3 text-left">Lane</th>
            <th className="px-4 py-3 text-left">Status</th>
            <th className="px-4 py-3 text-center">Risk</th>
            <th className="px-4 py-3 text-left">Payment</th>
            <th className="px-4 py-3 text-center">Progress</th>
          </tr>
        </thead>
        <tbody>
          {shipments.length === 0 ? (
            <tr>
              <td colSpan={8} className="px-4 py-8 text-center text-slate-500">
                No shipments found
              </td>
            </tr>
          ) : (
            shipments.map((shipment) => {
              const paymentProgress = calculatePaymentProgress(shipment);
              const clampedProgress = Math.min(100, Math.max(0, paymentProgress));
              return (
                <tr
                  key={shipment.id}
                  className="border-b border-slate-900/60 bg-slate-950/30 text-slate-100 transition hover:bg-slate-900/60"
                >
                  <td className="px-4 py-3 font-mono text-emerald-300">{shipment.id}</td>
                  <td className="px-4 py-3 text-slate-300">{shipment.carrier}</td>
                  <td className="px-4 py-3 text-slate-300">{shipment.customer}</td>
                  <td className="px-4 py-3 text-slate-300">
                    {shipment.corridor}
                  </td>
                  <td className="px-4 py-3 capitalize text-slate-200">{shipment.status.replace(/_/g, " ")}</td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`px-2 py-1 text-xs font-semibold ${formatRiskScore(shipment.risk.score).bgColor} ${formatRiskScore(shipment.risk.score).color}`}
                    >
                      {shipment.risk.score}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">
                    <span className={formatPaymentState(shipment.payment.state).color}>
                      {formatPaymentState(shipment.payment.state).text}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <svg className="h-2 w-24" viewBox="0 0 100 4" preserveAspectRatio="none" role="img" aria-label={`Payment progress ${Math.round(clampedProgress)} percent`}>
                        <rect x="0" y="0" width="100" height="4" rx="2" fill="rgb(30,41,59)" />
                        <rect x="0" y="0" width={clampedProgress} height="4" rx="2" fill="rgb(52,211,153)" />
                      </svg>
                      <span className="w-10 text-xs font-semibold text-slate-300">
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
