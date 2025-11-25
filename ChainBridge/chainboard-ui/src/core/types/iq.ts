/**
 * ChainIQ Risk Intelligence Types
 *
 * AI-powered risk scoring, posture analysis, and predictive alerts.
 * Aligned with backend api/schemas/chainboard.py RiskOverview schema.
 */

import type { ISODateString, RiskCategory } from "../../lib/types";

/**
 * Risk factor classification - why a shipment is risky
 */
export type RiskFactor =
  | "route_volatility"
  | "carrier_history"
  | "document_issues"
  | "iot_anomalies"
  | "payment_behavior";

/**
 * Risk score snapshot (embedded in shipment)
 */
export interface RiskScore {
  score: number; // 0-100
  category: RiskCategory;
  drivers: string[];
  assessed_at: ISODateString;
  watchlisted?: boolean;
}

/**
 * ChainIQ risk overview summary (from /risk/overview)
 * Matches backend RiskOverview Pydantic model
 */
export interface RiskOverview {
  total_shipments: number;
  high_risk_shipments: number;
  total_valueUsd: string; // Decimal as string from backend
  average_riskScore: number; // 0-100
  updatedAt: ISODateString;
}

/**
 * Risk overview API response envelope
 */
export interface RiskOverviewEnvelope {
  overview: RiskOverview;
  generatedAt: ISODateString;
}

/**
 * ChainIQ Risk Story - human-readable narrative explaining shipment risk
 * Matches backend RiskStory Pydantic model
 */
export interface RiskStory {
  shipmentId: string;
  reference: string;
  corridor: string;
  riskCategory: RiskCategory;
  score: number; // 0-100
  primary_factor: RiskFactor;
  factors: RiskFactor[];
  summary: string; // 1-2 sentence narrative
  recommended_action: string;
  last_updated: ISODateString;
}

/**
 * Risk stories API response envelope
 */
export interface RiskStoryEnvelope {
  stories: RiskStory[];
  total: number;
  generatedAt: ISODateString;
}

/**
 * Risk posture classification (for future use)
 */
export type RiskPosture = "defensive" | "balanced" | "aggressive";

/**
 * Type guards
 */
export function isRiskPosture(value: unknown): value is RiskPosture {
  return typeof value === "string" && ["defensive", "balanced", "aggressive"].includes(value);
}
