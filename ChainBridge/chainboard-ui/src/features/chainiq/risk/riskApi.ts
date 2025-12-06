import { RiskEvaluationRecord, RiskModelMetrics } from "./types";

const API_BASE = import.meta.env.VITE_CHAINIQ_API_BASE_URL ?? "http://localhost:8001";

export type RiskBandFilter = "ALL" | "HIGH" | "MEDIUM" | "LOW";

export interface FetchRiskEvaluationsParams {
  limit?: number;
  offset?: number;
}

/**
 * Fetches risk evaluations from the ChainIQ backend.
 *
 * This uses the real API. Tests must mock this function.
 */
export async function fetchRiskEvaluations(params: FetchRiskEvaluationsParams = {}): Promise<RiskEvaluationRecord[]> {
  const { limit = 1000, offset = 0 } = params;

  const url = new URL("/iq/risk/evaluations", API_BASE);
  url.searchParams.set("limit", String(limit));
  url.searchParams.set("offset", String(offset));

  const res = await fetch(url.toString());
  if (!res.ok) {
    throw new Error(`Failed to fetch risk evaluations: ${res.status} ${res.statusText}`);
  }

  const data = (await res.json()) as RiskEvaluationRecord[];
  return data;
}

/**
 * Fetches the latest risk model metrics.
 * Returns null if no metrics are found (404).
 */
export async function fetchRiskMetricsLatest(): Promise<RiskModelMetrics | null> {
  const url = new URL("/iq/risk/metrics/latest", API_BASE);

  const res = await fetch(url.toString());

  if (res.status === 404) {
    return null;
  }

  if (!res.ok) {
    throw new Error(`Failed to fetch risk metrics: ${res.status} ${res.statusText}`);
  }

  const data = (await res.json()) as RiskModelMetrics;
  return data;
}
