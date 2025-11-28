/**
 * useControlTowerOverview Hook
 *
 * Aggregates KPIs from all Control Tower modules:
 * - ChainFreight (Shipments)
 * - ChainIQ (Risk)
 * - ChainPay (Payments)
 * - ChainSense (IoT)
 *
 * Provides unified loading/error states and refresh capability.
 */

import { useIoTHealth } from "./useIoTHealth";
import { usePaymentQueue } from "./usePaymentQueue";
import { useRiskSummary } from "./useRiskSummary";
import { useShipmentsOverview } from "./useShipmentsOverview";

export interface ControlTowerKPIs {
  totalShipments: number;
  highRiskCount: number;
  holdsQueued: number;
  holdsValue: string | number;
  iotCoverage: number;
  iotStatus: "HEALTHY" | "DEGRADED" | "CRITICAL" | "unknown";
}

export interface UseControlTowerOverviewResult {
  kpis: ControlTowerKPIs;
  loading: boolean;
  error: Error | string | null;
  refreshAll: () => void;
}

export function useControlTowerOverview(): UseControlTowerOverviewResult {
  const shipments = useShipmentsOverview();
  const risk = useRiskSummary();
  const pay = usePaymentQueue(20);
  const iot = useIoTHealth();

  // Derive KPIs from each module
  const totalShipments = shipments.total ?? 0;
  const highRiskCount = risk.data?.overview.high_risk_shipments ?? 0;
  const holdsQueued = pay.data?.total_items ?? 0;
  const holdsValue = pay.data?.total_holds_usd ?? 0;
  const iotCoverage = 0; // M04: TODO - Add coverage_percent to backend if needed

  // Derive IoT status from coverage and alerts
  let iotStatus: "HEALTHY" | "DEGRADED" | "CRITICAL" | "unknown" = "unknown";
  if (iot.data) {
    // M04: Backend structure changed - using summary.devices_offline as critical metric
    const critical_alerts_last_24h = iot.data.summary.devices_offline;
    const alerts_last_24h = iot.data.summary.devices_stale_gps + iot.data.summary.devices_stale_env;
    const coverage_percent = 0; // TODO: Add to backend if needed
    if (critical_alerts_last_24h > 2) {
      iotStatus = "CRITICAL";
    } else if (alerts_last_24h > 5 || coverage_percent < 80) {
      iotStatus = "DEGRADED";
    } else {
      iotStatus = "HEALTHY";
    }
  }

  // Loading state: true if any module is loading and has no data yet
  const loading =
    (shipments.loading && shipments.data.length === 0) ||
    (risk.loading && !risk.data) ||
    (pay.loading && !pay.data) ||
    (iot.isLoading && !iot.data);

  // Error state: first error encountered
  const error = shipments.error || risk.error || pay.error || iot.error || null;

  // Refresh all modules
  const refreshAll = () => {
    shipments.refresh?.();
    risk.refetch?.();
    pay.refetch?.();
    iot.refetch?.();
  };

  return {
    kpis: {
      totalShipments,
      highRiskCount,
      holdsQueued,
      holdsValue,
      iotCoverage,
      iotStatus,
    },
    loading,
    error,
    refreshAll,
  };
}
