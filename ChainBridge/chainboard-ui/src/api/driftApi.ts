/**
 * Drift API Client & Types
 *
 * Wire-up to Maggie+Cody drift endpoints:
 * - GET /iq/drift/score
 * - GET /iq/drift/features
 * - GET /iq/drift/corridors
 *
 * @module api/driftApi
 */

// =============================================================================
// TYPES
// =============================================================================

/**
 * Overall drift score response.
 */
export interface DriftScoreResponse {
  score: number;
  p95_delta: number;
  trend: "rising" | "falling" | "stable";
  drift_detected: boolean;
  sample_count: number;
  last_updated: string;
  model_version: string;
  lookback_hours: number;
}

/**
 * Individual feature drift info.
 */
export interface DriftFeature {
  feature_name: string;
  drift_score: number;
  baseline_mean: number;
  current_mean: number;
  delta_pct: number;
  is_drifting: boolean;
  importance_rank: number;
}

/**
 * Drift features response.
 */
export interface DriftFeaturesResponse {
  features: DriftFeature[];
  total_features: number;
  drifting_count: number;
  top_drifting: DriftFeature[];
  model_version: string;
  lookback_hours: number;
}

/**
 * Per-corridor drift info.
 */
export interface CorridorDrift {
  corridor: string;
  drift_score: number;
  p95_delta: number;
  event_count: number;
  is_drifting: boolean;
  trend: "rising" | "falling" | "stable";
  health_score: number;
  last_updated: string;
}

/**
 * Drift corridors response.
 */
export interface DriftCorridorsResponse {
  corridors: CorridorDrift[];
  total_corridors: number;
  drifting_count: number;
  healthy_count: number;
  model_version: string;
  lookback_hours: number;
}

/**
 * Drift history data point.
 */
export interface DriftHistoryPoint {
  timestamp: string;
  score: number;
  p95_delta: number;
  sample_count: number;
}

/**
 * Drift history response.
 */
export interface DriftHistoryResponse {
  history: DriftHistoryPoint[];
  interval_minutes: number;
  lookback_hours: number;
  model_version: string;
}

// =============================================================================
// API CLIENT
// =============================================================================

const DEFAULT_TIMEOUT_MS = 8_000;
const RAW_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

class DriftApiError extends Error {
  status: number | null;
  constructor(message: string, status: number | null = null) {
    super(message);
    this.name = "DriftApiError";
    this.status = status;
  }
}

async function driftGet<T>(path: string, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${RAW_BASE_URL}${path}`, {
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });

    if (!response.ok) {
      const detail = await response.text();
      throw new DriftApiError(detail || `Request failed: ${response.status}`, response.status);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DriftApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new DriftApiError("Drift API request timed out");
    }
    throw new DriftApiError(error instanceof Error ? error.message : "Network error");
  } finally {
    clearTimeout(timeout);
  }
}

// =============================================================================
// ENDPOINT FUNCTIONS
// =============================================================================

/**
 * Fetch overall drift score.
 * Endpoint: GET /iq/drift/score
 */
export async function fetchDriftScore(
  lookbackHours = 24,
  threshold = 0.25
): Promise<DriftScoreResponse> {
  return driftGet<DriftScoreResponse>(
    `/iq/drift/score?lookback_hours=${lookbackHours}&threshold=${threshold}`
  );
}

/**
 * Fetch drifting features.
 * Endpoint: GET /iq/drift/features
 */
export async function fetchDriftFeatures(
  lookbackHours = 24,
  topN = 10
): Promise<DriftFeaturesResponse> {
  return driftGet<DriftFeaturesResponse>(
    `/iq/drift/features?lookback_hours=${lookbackHours}&top_n=${topN}`
  );
}

/**
 * Fetch corridor-level drift.
 * Endpoint: GET /iq/drift/corridors
 */
export async function fetchDriftCorridors(
  lookbackHours = 24,
  minEvents = 10
): Promise<DriftCorridorsResponse> {
  return driftGet<DriftCorridorsResponse>(
    `/iq/drift/corridors?lookback_hours=${lookbackHours}&min_events=${minEvents}`
  );
}

/**
 * Fetch drift score history.
 * Endpoint: GET /iq/drift/history
 */
export async function fetchDriftHistory(
  lookbackHours = 24,
  intervalMinutes = 15
): Promise<DriftHistoryResponse> {
  return driftGet<DriftHistoryResponse>(
    `/iq/drift/history?lookback_hours=${lookbackHours}&interval_minutes=${intervalMinutes}`
  );
}
