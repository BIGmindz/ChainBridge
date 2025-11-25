/**
 * ChainBridge API Client
 *
 * Centralized HTTP client for all backend communication.
 * Uses VITE_API_BASE_URL from environment config.
 *
 * Design philosophy:
 * - Lightweight, no external HTTP libraries
 * - Centralized error handling with actionable messages
 * - Dev-friendly logging without production spam
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const isDev = import.meta.env.DEV;

/**
 * Generic GET request
 */
export async function apiGet<T>(path: string): Promise<T> {
  const url = `${BASE_URL}${path}`;

  if (isDev) {
    console.log(`[API] GET ${url}`);
  }

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await parseErrorResponse(response);
      throw new Error(`HTTP ${response.status}: ${errorData}`);
    }

    return await response.json();
  } catch (error) {
    if (isDev) {
      console.error(`[API] GET ${url} failed:`, error);
    }
    throw error;
  }
}

/**
 * Generic POST request
 */
export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const url = `${BASE_URL}${path}`;

  if (isDev) {
    console.log(`[API] POST ${url}`, body);
  }

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorData = await parseErrorResponse(response);
      throw new Error(`HTTP ${response.status}: ${errorData}`);
    }

    return await response.json();
  } catch (error) {
    if (isDev) {
      console.error(`[API] POST ${url} failed:`, error);
    }
    throw error;
  }
}

/**
 * Parse error response body safely
 */
async function parseErrorResponse(response: Response): Promise<string> {
  try {
    const json = await response.json();

    // FastAPI validation errors have a "detail" field
    if (json.detail) {
      if (Array.isArray(json.detail)) {
        // Validation error list
        return json.detail.map((e: Record<string, unknown>) => e.msg || JSON.stringify(e)).join(', ');
      }
      return String(json.detail);
    }

    return JSON.stringify(json);
  } catch {
    // If JSON parsing fails, return status text
    return response.statusText || 'Unknown error';
  }
}
/**
 * ChainIQ: Score Shipment Risk
 *
 * Business Decision: "Should we release payment for this shipment?"
 */

export interface ShipmentRiskRequest {
  shipmentId: string;
  route: string;
  carrierId: string;
  shipment_valueUsd: number;
  days_in_transit: number;
  expected_days: number;
  documents_complete: boolean;
  shipper_payment_score: number;
}

export interface ShipmentRiskResponse {
  shipmentId: string;
  riskScore: number;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  reasonCodes: string[];
  recommended_action: 'RELEASE_PAYMENT' | 'MANUAL_REVIEW' | 'HOLD_PAYMENT' | 'ESCALATE_COMPLIANCE';
}

export async function scoreShipment(request: ShipmentRiskRequest): Promise<ShipmentRiskResponse> {
  return apiPost<ShipmentRiskResponse>('/iq/score-shipment', request);
}

/**
 * ChainIQ: Risk History & Replay
 *
 * Intelligence memory layer for audit trail and deterministic replay.
 */

export interface RiskHistoryItem {
  id: number;
  shipmentId: string;
  scored_at: string;
  riskScore: number;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  recommended_action: string;
  reasonCodes: string[];
}

export interface RiskHistoryResponse {
  shipmentId: string;
  total_scores: number;
  history: RiskHistoryItem[];
}

export interface RecentRiskResponse {
  total: number;
  scores: RiskHistoryItem[];
}

export interface ReplayResponse {
  shipmentId: string;
  original_score: number;
  original_severity: string;
  original_scored_at: string;
  replayed_score: number;
  replayed_severity: string;
  replayed_reasonCodes: string[];
  replayed_action: string;
  match: boolean;
}

export async function getRiskHistory(shipmentId: string): Promise<RiskHistoryResponse> {
  return apiGet<RiskHistoryResponse>(`/iq/risk-history/${shipmentId}`);
}

export async function getRecentRisk(limit: number = 50): Promise<RecentRiskResponse> {
  return apiGet<RecentRiskResponse>(`/iq/risk-recent?limit=${limit}`);
}

export async function replayRisk(shipmentId: string): Promise<ReplayResponse> {
  return apiPost<ReplayResponse>(`/iq/risk-replay/${shipmentId}`, {});
}

/**
 * ChainPay: Payment Hold Queue
 *
 * Read-only decision surface showing shipments requiring manual payment review.
 */

export interface PaymentQueueItem {
  shipmentId: string;
  riskScore: number;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  recommended_action: string;
  route: string;
  carrierId: string;
  shipment_valueUsd: number;
  last_scored_at: string;
}

export interface PaymentQueueResponse {
  items: PaymentQueueItem[];
  total_pending: number;
}

export async function getPaymentQueue(limit: number = 50): Promise<PaymentQueueResponse> {
  return apiGet<PaymentQueueResponse>(`/iq/pay/queue?limit=${limit}`);
}

export interface EntityHistoryRecord {
  timestamp: string;
  score: number;
  severity: string;
  recommended_action: string;
  reasonCodes: string[];
  payload: Record<string, unknown>;
}

export interface EntityHistoryResponse {
  entity_id: string;
  total_records: number;
  history: EntityHistoryRecord[];
}

export async function getEntityHistory(
  shipmentId: string,
  limit: number = 50
): Promise<EntityHistoryResponse> {
  return apiGet<EntityHistoryResponse>(`/iq/history/${shipmentId}?limit=${limit}`);
}

/**
 * ChainIQ: Better Options Advisor
 *
 * Suggests alternative routes and payment rails to reduce risk.
 */

export type RiskAppetite = "conservative" | "balanced" | "aggressive";

export interface RouteOption {
  option_id: string;
  route: string;
  carrierId?: string | null;
  riskScore: number;
  risk_delta: number;       // positive = safer than current
  eta_delta_days: number;   // +2 = 2 days slower, -1 = 1 day faster
  cost_delta_usd: number;   // negative = cheaper, positive = more expensive
  notes: string[];
}

export interface PaymentRailOption {
  option_id: string;
  payment_rail: string;
  riskScore: number;
  risk_delta: number;
  settlement_speed: string; // e.g. "T+0", "T+1", "T+3"
  fees_delta_usd: number;   // negative = lower fees
  notes: string[];
}

export interface OptionsAdvisorResponse {
  shipmentId: string;
  current_riskScore: number;
  current_route?: string | null;
  current_carrierId?: string | null;
  current_payment_rail?: string | null;
  risk_appetite: RiskAppetite;
  route_options: RouteOption[];
  payment_options: PaymentRailOption[];
}

export async function getShipmentOptions(
  shipmentId: string,
  limit: number = 5,
  riskAppetite: RiskAppetite = "balanced"
): Promise<OptionsAdvisorResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    risk_appetite: riskAppetite,
  });

  return apiGet<OptionsAdvisorResponse>(
    `/iq/options/${shipmentId}?${params.toString()}`
  );
}

/**
 * ChainIQ: ProofPack
 *
 * Bundles all ChainIQ/ChainPay state for a shipment into a single verifiable package.
 * Used for Space and Time integration, on-chain attestation, and audit trails.
 */

export interface RiskSnapshot {
  shipmentId: string;
  riskScore: number;
  severity: string;
  recommended_action: string;
  reasonCodes: string[];
  last_scored_at: string;
}

export interface ProofPackResponse {
  shipmentId: string;
  version: string;
  generatedAt: string;
  risk_snapshot?: RiskSnapshot | null;
  history?: EntityHistoryResponse | null;
  payment_queue_entry?: PaymentQueueItem | null;
  options_advisor?: OptionsAdvisorResponse | null;
}

export async function getProofPack(shipmentId: string): Promise<ProofPackResponse> {
  return apiGet<ProofPackResponse>(`/iq/proofpack/${encodeURIComponent(shipmentId)}`);
}

/**
 * ChainIQ: Option Sandbox v0
 *
 * Simulates risk score changes for alternative routes or payment rails
 * without persisting to database. Pure read-only sandbox for testing recommendations.
 */

export type SimulationOptionType = "route" | "payment_rail";

export interface SimulationRequest {
  option_type: SimulationOptionType;
  option_id: string;
}

export interface SimulationResultResponse {
  shipmentId: string;
  option_type: SimulationOptionType;
  option_id: string;
  baseline_riskScore: number;
  simulated_riskScore: number;
  baseline_severity: string;
  simulated_severity: string;
  risk_delta: number;
  notes: string[];
}

export async function simulateShipmentOption(
  shipmentId: string,
  optionType: SimulationOptionType,
  optionId: string
): Promise<SimulationResultResponse> {
  const body: SimulationRequest = {
    option_type: optionType,
    option_id: optionId,
  };

  return apiPost<SimulationResultResponse>(
    `/iq/options/${encodeURIComponent(shipmentId)}/simulate`,
    body
  );
}
