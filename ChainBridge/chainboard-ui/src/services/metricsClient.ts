import type { GlobalSummary } from "../lib/metrics";
import { config } from "../config/env";

const MOCK_GLOBAL_SUMMARY: GlobalSummary = {
  threat_level: "elevated",
  shipments: {
    total_shipments: 148,
    active_shipments: 92,
    on_time_percent: 81,
    exception_count: 7,
    high_risk_count: 5,
    delayed_or_blocked_count: 4,
  },
  payments: {
    blocked_payments: 3,
    partially_paid: 14,
    completed: 86,
    not_started: 12,
    in_progress: 33,
    payment_health_score: 78,
    capital_locked_hours: 420,
  },
  governance: {
    proofpack_ok_percent: 92,
    open_audits: 3,
    watchlisted_shipments: 5,
  },
  top_corridor: {
    corridor_id: "asia-us-west",
    label: "Asia → US West",
    shipment_count: 42,
    active_count: 28,
    high_risk_count: 3,
    blocked_payments: 1,
    avg_risk_score: 63,
    trend: "rising",
  },
  iot: {
    shipments_with_iot: 58,
    active_sensors: 247,
    alerts_last_24h: 6,
    critical_alerts_last_24h: 1,
    coverage_percent: 72,
  },
};

async function fetchSummaryFromApi(): Promise<GlobalSummary> {
  const response = await fetch(`${config.apiBaseUrl}/metrics/summary`, {
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to load /metrics/summary (${response.status})`);
  }

  return (await response.json()) as GlobalSummary;
}

export async function fetchGlobalSummary(): Promise<GlobalSummary> {
  if (config.useMocks) {
    return MOCK_GLOBAL_SUMMARY;
  }

  try {
    return await fetchSummaryFromApi();
  } catch (error) {
    if (config.isDevelopment) {
      const message = error instanceof Error ? error.message : String(error);
      console.warn(`[metrics] Falling back to mock summary: ${message}`);
    }
    return MOCK_GLOBAL_SUMMARY;
  }
}
