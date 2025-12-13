/**
 * ChainIQ Risk Types
 *
 * Types for the real ChainIQ Risk API integration.
 * These types match the backend API contract from Cody/Maggie's risk endpoints.
 *
 * API Contract:
 * - POST /api/v1/risk/score → RiskScoreResponse
 * - POST /api/v1/risk/simulation → SimulationResponse
 * - GET /api/v1/risk/health → HealthResponse
 */

// =============================================================================
// CORE RISK TYPES
// =============================================================================

/**
 * Direction indicator for risk factors
 */
export type TopFactorDirection = "UP" | "DOWN";

/**
 * Risk decision outcomes from ChainIQ scoring
 */
export type RiskDecision = "APPROVE" | "HOLD" | "TIGHTEN_TERMS" | "ESCALATE";

/**
 * Individual risk factor explanation
 */
export interface TopFactor {
  name: string;
  description: string;
  direction: TopFactorDirection;
  weight: number;
}

// =============================================================================
// API REQUEST TYPES
// =============================================================================

/**
 * Context provided for risk scoring a shipment
 * Sent to POST /api/v1/risk/score
 */
export interface ShipmentRiskContext {
  shipmentId: string;
  origin?: string;
  destination?: string;
  carrierId?: string;
  carrierName?: string;
  mode?: string;
  valueUsd?: number;
  weightKg?: number;
  commodityType?: string;
  transitDays?: number;
  // TODO: extend with additional fields as backend & Maggie define them
}

/**
 * Request payload for risk scoring endpoint
 */
export interface RiskScoreRequest {
  shipments: ShipmentRiskContext[];
  include_factors?: boolean;
  max_factors?: number;
}

// =============================================================================
// API RESPONSE TYPES
// =============================================================================

/**
 * Risk assessment result from ChainIQ
 * Returned from POST /api/v1/risk/score
 */
export interface ShipmentRiskAssessment {
  shipmentId: string;
  riskScore: number;
  operationalRisk?: number;
  financialRisk?: number;
  fraudRisk?: number;
  esgRisk?: number;
  resilienceScore?: number;
  decision: RiskDecision;
  confidence: number;
  topFactors: TopFactor[];
  summaryReason: string;
  tags: string[];
  modelVersion?: string | null;
  scoredAt?: string;
}

/**
 * Response from POST /api/v1/risk/score
 */
export interface RiskScoreResponse {
  assessments: ShipmentRiskAssessment[];
  meta: {
    model_version: string;
    scored_at: string;
    request_id?: string;
  };
}

/**
 * Health check response from GET /api/v1/risk/health
 */
export interface RiskHealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  model_loaded: boolean;
  model_version?: string;
  last_score_at?: string;
  uptime_seconds?: number;
}

// =============================================================================
// BACKEND SNAKE_CASE TYPES (for API response mapping)
// =============================================================================

/**
 * Backend response format (snake_case)
 * We map this to camelCase for frontend use
 */
export interface BackendTopFactor {
  name: string;
  description: string;
  direction: TopFactorDirection;
  weight: number;
}

export interface BackendShipmentRiskAssessment {
  shipment_id: string;
  risk_score: number;
  operational_risk?: number;
  financial_risk?: number;
  fraud_risk?: number;
  esg_risk?: number;
  resilience_score?: number;
  decision: RiskDecision;
  confidence: number;
  top_factors: BackendTopFactor[];
  summary_reason: string;
  tags: string[];
  model_version?: string | null;
  scored_at?: string;
}

export interface BackendRiskScoreResponse {
  assessments: BackendShipmentRiskAssessment[];
  meta: {
    model_version: string;
    scored_at: string;
    request_id?: string;
  };
}

// =============================================================================
// MAPPING HELPERS
// =============================================================================

/**
 * Map backend snake_case assessment to frontend camelCase
 */
export function mapBackendAssessment(backend: BackendShipmentRiskAssessment): ShipmentRiskAssessment {
  return {
    shipmentId: backend.shipment_id,
    riskScore: backend.risk_score,
    operationalRisk: backend.operational_risk,
    financialRisk: backend.financial_risk,
    fraudRisk: backend.fraud_risk,
    esgRisk: backend.esg_risk,
    resilienceScore: backend.resilience_score,
    decision: backend.decision,
    confidence: backend.confidence,
    topFactors: backend.top_factors.map((f) => ({
      name: f.name,
      description: f.description,
      direction: f.direction,
      weight: f.weight,
    })),
    summaryReason: backend.summary_reason,
    tags: backend.tags,
    modelVersion: backend.model_version,
    scoredAt: backend.scored_at,
  };
}

/**
 * Map frontend camelCase context to backend snake_case request
 */
export function mapContextToBackend(context: ShipmentRiskContext): Record<string, unknown> {
  return {
    shipment_id: context.shipmentId,
    origin: context.origin,
    destination: context.destination,
    carrier_id: context.carrierId,
    carrier_name: context.carrierName,
    mode: context.mode,
    value_usd: context.valueUsd,
    weight_kg: context.weightKg,
    commodity_type: context.commodityType,
    transit_days: context.transitDays,
  };
}
