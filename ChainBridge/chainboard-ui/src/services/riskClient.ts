import { config } from "../config/env";
import { MOCK_SHIPMENTS } from "../lib/mockData";
import type { RiskOverviewSummary } from "../lib/risk";

import { fetchRiskOverview } from "./realApiClient";

const HAS_REAL_API = Boolean(config.apiBaseUrl);
const USE_REAL_API = !config.useMocks && HAS_REAL_API;

function buildMockRiskOverview(): RiskOverviewSummary {
  const totalShipments = MOCK_SHIPMENTS.length;
  const highRiskShipments = MOCK_SHIPMENTS.filter((shipment) => shipment.risk.category === "high").length;
  const totalValueUsd = MOCK_SHIPMENTS.reduce((sum, shipment) => sum + shipment.payment.total_valueUsd, 0);
  const averageRiskScore = totalShipments
    ? MOCK_SHIPMENTS.reduce((sum, shipment) => sum + shipment.risk.score, 0) / totalShipments
    : 0;

  return {
    total_shipments: totalShipments,
    high_risk_shipments: highRiskShipments,
    total_valueUsd: Number(totalValueUsd.toFixed(2)),
    average_riskScore: Number(averageRiskScore.toFixed(2)),
    updatedAt: new Date().toISOString(),
  };
}

export const riskClient = {
  async getOverview(): Promise<RiskOverviewSummary> {
    if (USE_REAL_API) {
      try {
        return await fetchRiskOverview();
      } catch (error) {
        if (config.isDevelopment) {
          console.warn("[riskClient] Falling back to mock risk overview:", error);
        }
      }
    }

    return buildMockRiskOverview();
  },
};
