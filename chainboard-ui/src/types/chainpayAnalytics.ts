import type { SettlementProvider } from './chainpay';

export type RiskTier = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface TierHealthMetric {
  tier: RiskTier;
  lossRate: number; // fraction e.g., 0.012 = 1.2%
  reserveUtilization: number; // fraction of reserve used
  unusedReserveRatio: number; // fraction remaining (can go negative on breach)
  shipmentCount: number;
}

export interface DaysToCashMetric {
  tier: RiskTier;
  corridorId: string;
  medianDaysToFirstCash: number;
  p95DaysToFirstCash: number;
  medianDaysToFinalCash: number;
  p95DaysToFinalCash: number;
  shipmentCount: number;
}

export interface SlaMetric {
  corridorId: string;
  tier: RiskTier;
  claimReviewSlaBreachRate: number; // fraction breaching SLA
  manualReviewSlaBreachRate: number; // fraction breaching SLA
  totalReviews: number;
}

export interface ChainPayAnalyticsSnapshot {
  asOf: string; // ISO timestamp
  corridorId: string;
  settlementProvider: SettlementProvider;
  tierHealth: TierHealthMetric[];
  daysToCash: DaysToCashMetric[];
  sla: SlaMetric[];
}
