import { TrendingUp, AlertTriangle, Clock, Zap } from "lucide-react";

import type { NetworkVitals } from "../lib/types";

interface KPIStripProps {
  vitals: NetworkVitals;
}

/**
 * KPI Strip Component
 * Displays network vital signs as card indicators
 */
export default function KPIStrip({ vitals }: KPIStripProps): JSX.Element {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      {/* Active Shipments */}
      <div className="card p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">Active Shipments</p>
            <p className="text-3xl font-bold text-gray-900 mt-2">
              {vitals.active_shipments}
            </p>
          </div>
          <div className="p-3 bg-primary-50 rounded-lg">
            <TrendingUp className="w-6 h-6 text-primary-600" />
          </div>
        </div>
      </div>

      {/* On-Time % */}
      <div className="card p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">On-Time %</p>
            <p className="text-3xl font-bold text-gray-900 mt-2">
              {vitals.on_time_percent}%
            </p>
          </div>
          <div className="p-3 bg-success-50 rounded-lg">
            <Clock className="w-6 h-6 text-success-600" />
          </div>
        </div>
      </div>

      {/* At-Risk Shipments */}
      <div className="card p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">At-Risk</p>
            <p className="text-3xl font-bold text-gray-900 mt-2">
              {vitals.at_risk_shipments}
            </p>
          </div>
          <div className="p-3 bg-warning-50 rounded-lg">
            <AlertTriangle className="w-6 h-6 text-warning-600" />
          </div>
        </div>
      </div>

      {/* Open Payment Holds */}
      <div className="card p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">Payment Holds</p>
            <p className="text-3xl font-bold text-gray-900 mt-2">
              {vitals.open_payment_holds}
            </p>
          </div>
          <div className="p-3 bg-danger-50 rounded-lg">
            <Zap className="w-6 h-6 text-danger-600" />
          </div>
        </div>
      </div>
    </div>
  );
}
