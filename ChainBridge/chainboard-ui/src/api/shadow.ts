/**
 * Shadow Mode API Client
 *
 * Provides access to shadow mode analytics endpoints for visualizing
 * dummy vs real model performance comparison.
 *
 * ⚠️ REALITY GUARDRAIL: These are STUBS only.
 * Backend endpoints not yet exposed by ChainIQ service.
 * TODO: Wire to real endpoints once Cody/Dan add shadow REST API.
 *
 * @module api/shadow
 */

// import { httpGet } from "../services/apiClient"; // TODO: Uncomment when backend ready

/**
 * Shadow event representing one parallel scoring execution.
 */
export interface ShadowEvent {
  /** Event ID */
  id: number;
  /** Shipment identifier */
  shipment_id: string;
  /** Dummy model score [0-1] */
  dummy_score: number;
  /** Real model score [0-1] */
  real_score: number;
  /** Absolute delta |dummy - real| */
  delta: number;
  /** Real model version */
  model_version: string;
  /** Trade corridor (e.g., "US-MX") */
  corridor: string | null;
  /** Timestamp of scoring */
  created_at: string;
}

/**
 * Summary statistics for shadow mode performance.
 */
export interface ShadowStats {
  /** Total number of shadow events logged */
  total_events: number;
  /** Average delta across all events */
  avg_delta: number;
  /** 95th percentile delta */
  p95_delta: number;
  /** 99th percentile delta */
  p99_delta: number;
  /** Current real model version */
  model_version: string;
  /** Count of high-delta events (delta > 0.2) */
  high_delta_count: number;
  /** Time window for stats (hours) */
  window_hours: number;
}

/**
 * Per-corridor statistics for shadow mode.
 */
export interface CorridorStats {
  /** Trade corridor identifier */
  corridor: string;
  /** Number of events for this corridor */
  event_count: number;
  /** Average delta for corridor */
  avg_delta: number;
  /** Max delta observed in corridor */
  max_delta: number;
  /** Most recent event timestamp */
  last_event_at: string;
}

/**
 * Fetch shadow mode summary statistics.
 *
 * TODO: Backend endpoint not yet implemented.
 * Endpoint will be: GET /iq/ml/shadow/stats
 *
 * @param windowHours - Time window for statistics (default 24)
 * @returns Promise resolving to shadow statistics
 * @throws Error indicating endpoint not available
 */
export async function fetchShadowStats(
  _windowHours: number = 24
): Promise<ShadowStats> {
  // TODO: Uncomment once backend endpoint exists
  // return httpGet<ShadowStats>(`/iq/ml/shadow/stats?window_hours=${windowHours}`);

  throw new Error(
    "Shadow stats endpoint not yet available. Backend implementation pending."
  );
}

/**
 * Fetch recent shadow events.
 *
 * TODO: Backend endpoint not yet implemented.
 * Endpoint will be: GET /iq/ml/shadow/events
 *
 * @param limit - Maximum number of events to return
 * @param corridor - Optional corridor filter
 * @returns Promise resolving to list of shadow events
 * @throws Error indicating endpoint not available
 */
export async function fetchShadowEvents(
  _limit: number = 50,
  _corridor?: string
): Promise<ShadowEvent[]> {
  // TODO: Uncomment once backend endpoint exists
  // const params = new URLSearchParams();
  // params.set("limit", limit.toString());
  // if (corridor) params.set("corridor", corridor);
  // return httpGet<ShadowEvent[]>(`/iq/ml/shadow/events?${params.toString()}`);

  throw new Error(
    "Shadow events endpoint not yet available. Backend implementation pending."
  );
}

/**
 * Fetch per-corridor shadow statistics.
 *
 * TODO: Backend endpoint not yet implemented.
 * Endpoint will be: GET /iq/ml/shadow/corridors
 *
 * @param windowHours - Time window for statistics
 * @returns Promise resolving to corridor statistics
 * @throws Error indicating endpoint not available
 */
export async function fetchCorridorStats(
  _windowHours: number = 24
): Promise<CorridorStats[]> {
  // TODO: Uncomment once backend endpoint exists
  // return httpGet<CorridorStats[]>(`/iq/ml/shadow/corridors?window_hours=${windowHours}`);

  throw new Error(
    "Shadow corridor stats endpoint not yet available. Backend implementation pending."
  );
}

/**
 * Fetch high-delta shadow events (potential drift indicators).
 *
 * TODO: Backend endpoint not yet implemented.
 * Endpoint will be: GET /iq/ml/shadow/high-deltas
 *
 * @param threshold - Delta threshold for "high" (default 0.2)
 * @param limit - Maximum number of events
 * @returns Promise resolving to high-delta events
 * @throws Error indicating endpoint not available
 */
export async function fetchHighDeltaEvents(
  _threshold: number = 0.2,
  _limit: number = 20
): Promise<ShadowEvent[]> {
  // TODO: Uncomment once backend endpoint exists
  // return httpGet<ShadowEvent[]>(
  //   `/iq/ml/shadow/high-deltas?threshold=${threshold}&limit=${limit}`
  // );

  throw new Error(
    "Shadow high-delta endpoint not yet available. Backend implementation pending."
  );
}
