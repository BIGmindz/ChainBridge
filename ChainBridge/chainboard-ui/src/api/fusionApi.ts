/**
 * Fusion API Client & Types
 *
 * Wire-up to Fusion Mode endpoints:
 * - GET /iq/fusion/overview
 * - GET /iq/fusion/stress
 *
 * @module api/fusionApi
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

// =============================================================================
// TYPES
// =============================================================================

export interface FusionSignal {
  id: string;
  source: "market" | "logistics" | "risk" | "sentiment";
  severity: "low" | "medium" | "high" | "critical";
  message: string;
  timestamp: string;
  confidence: number;
}

export interface FusionOverviewResponse {
  fusion_score: number; // 0-100
  status: "optimal" | "stable" | "warning" | "critical";
  active_signals: FusionSignal[];
  last_updated: string;
  mode: "standard" | "heightened" | "emergency";
}

export interface CorridorStress {
  corridor_id: string;
  name: string;
  stress_score: number; // 0-100
  bottleneck_probability: number;
  active_shipments: number;
  trend: "improving" | "stable" | "worsening";
}

export interface CorridorStressResponse {
  corridors: CorridorStress[];
  global_stress_index: number;
  timestamp: string;
}

// =============================================================================
// FETCH FUNCTIONS
// =============================================================================

/**
 * Fetch the main Fusion Intelligence overview.
 */
export async function fetchFusionOverview(): Promise<FusionOverviewResponse> {
  const response = await fetch(`${API_BASE_URL}/iq/fusion/overview`);
  if (!response.ok) {
    throw new Error(`Fusion API Error: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Fetch corridor stress metrics.
 */
export async function fetchCorridorStress(): Promise<CorridorStressResponse> {
  const response = await fetch(`${API_BASE_URL}/iq/fusion/stress`);
  if (!response.ok) {
    throw new Error(`Fusion Stress API Error: ${response.statusText}`);
  }
  return response.json();
}
