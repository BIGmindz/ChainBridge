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
  const iotCoverage = (() => {
    if (!iot.data) return 0;
    const { deviceCount, online } = iot.data;
    return deviceCount > 0 ? (online / deviceCount) * 100 : 0;
  })();

  // Derive IoT status from coverage and alerts
  let iotStatus: "HEALTHY" | "DEGRADED" | "CRITICAL" | "unknown" = "unknown";
  if (iot.data) {
    const { offline, degraded, anomalies, deviceCount, online } = iot.data;
    const severeAnomalies = anomalies.filter((anomaly) =>
      anomaly.severity === "HIGH" || anomaly.severity === "CRITICAL"
    ).length;
    const coveragePercent = deviceCount > 0 ? (online / deviceCount) * 100 : 0;

    if (offline > 3 || severeAnomalies > 3) {
      iotStatus = "CRITICAL";
    } else if (degraded > 5 || coveragePercent < 80) {
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
