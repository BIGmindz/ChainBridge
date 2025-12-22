/**
 * Shadow Mode API Client
 *
 * Wire-up to Cody's shadow mode endpoints (PAC-CODY-019).
 * Live endpoints: GET /iq/shadow/stats, /events, /corridors, /drift
 *
 * @module api/shadowMode
 */

// =============================================================================
// TYPES (Matching backend schemas_shadow.py)
// =============================================================================

/**
 * Individual shadow event from model comparison.
 */
export interface ShadowEvent {
  id: number;
  shipment_id: string;
  dummy_score: number;
  real_score: number;
  delta: number;
  model_version: string;
  corridor: string | null;
  created_at: string;
}

/**
 * Aggregated shadow statistics response.
 */
export interface ShadowStatsResponse {
  count: number;
  mean_delta: number;
  median_delta: number;
  std_delta: number;
  p50_delta: number;
  p95_delta: number;
  p99_delta: number;
  max_delta: number;
  drift_flag: boolean;
  model_version: string;
  time_window_hours: number;
}

/**
 * Per-corridor statistics.
 */
export interface ShadowCorridorStats {
  corridor: string;
  event_count: number;
  mean_delta: number;
  median_delta: number;
  p95_delta: number;
  max_delta: number;
  drift_flag: boolean;
  time_window_hours: number;
}

/**
 * Multi-corridor response.
 */
export interface ShadowCorridorsResponse {
  corridors: ShadowCorridorStats[];
  total_corridors: number;
  drifting_count: number;
  model_version: string;
  time_window_hours: number;
}

/**
 * Shadow events list response.
 */
export interface ShadowEventsResponse {
  events: ShadowEvent[];
  total_count: number;
  limit: number;
  corridor: string | null;
  model_version: string;
  time_window_hours: number;
}

/**
 * Drift detection response.
 */
export interface ShadowDriftResponse {
  drift_detected: boolean;
  p95_delta: number;
  high_delta_count: number;
  total_events: number;
  model_version: string;
  lookback_hours: number;
  drift_threshold: number;
}

// =============================================================================
// API CLIENT
// =============================================================================

const DEFAULT_TIMEOUT_MS = 8_000;
const RAW_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

class ShadowApiError extends Error {
  status: number | null;
  constructor(message: string, status: number | null = null) {
    super(message);
    this.name = "ShadowApiError";
    this.status = status;
  }
}

async function shadowGet<T>(path: string, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${RAW_BASE_URL}${path}`, {
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });

    if (!response.ok) {
      const detail = await response.text();
      throw new ShadowApiError(detail || `Request failed: ${response.status}`, response.status);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ShadowApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ShadowApiError("Shadow API request timed out");
    }
    throw new ShadowApiError(error instanceof Error ? error.message : "Network error");
  } finally {
    clearTimeout(timeout);
  }
}

// =============================================================================
// ENDPOINT FUNCTIONS
// =============================================================================

/**
 * Fetch shadow mode statistics.
 * Endpoint: GET /iq/shadow/stats
 */
export async function fetchShadowStats(hours = 24): Promise<ShadowStatsResponse> {
  return shadowGet<ShadowStatsResponse>(`/iq/shadow/stats?hours=${hours}`);
}

/**
 * Fetch shadow events list.
 * Endpoint: GET /iq/shadow/events
 */
export async function fetchShadowEvents(
  limit = 100,
  corridor?: string,
  hours = 24
): Promise<ShadowEventsResponse> {
  const params = new URLSearchParams();
  params.set("limit", limit.toString());
  params.set("hours", hours.toString());
  if (corridor) params.set("corridor", corridor);
  return shadowGet<ShadowEventsResponse>(`/iq/shadow/events?${params.toString()}`);
}

/**
 * Fetch corridor-level statistics.
 * Endpoint: GET /iq/shadow/corridors
 */
export async function fetchShadowCorridors(
  hours = 24,
  minEvents = 10
): Promise<ShadowCorridorsResponse> {
  return shadowGet<ShadowCorridorsResponse>(
    `/iq/shadow/corridors?hours=${hours}&min_events=${minEvents}`
  );
}

/**
 * Fetch drift detection metrics.
 * Endpoint: GET /iq/shadow/drift
 */
export async function fetchShadowDrift(
  lookbackHours = 24,
  threshold = 0.25
): Promise<ShadowDriftResponse> {
  return shadowGet<ShadowDriftResponse>(
    `/iq/shadow/drift?lookback_hours=${lookbackHours}&threshold=${threshold}`
  );
}
