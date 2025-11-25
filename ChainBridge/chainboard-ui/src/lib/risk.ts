/**
 * ChainIQ risk contracts shared between services, hooks, and components.
 * These interfaces mirror the FastAPI Pydantic models to keep the
 * backend ↔ frontend contract in lockstep.
 */

export interface RiskOverviewSummary {
  total_shipments: number;
  high_risk_shipments: number;
  total_valueUsd: number;
  average_riskScore: number;
  updatedAt: string;
}
