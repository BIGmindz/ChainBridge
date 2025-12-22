// NOTE: MOCK DATA ONLY.
// Kept for story/demo/testing. The Operator Console now uses the live
// /api/chainpay/analytics/usd-mxn endpoint via useChainPayAnalyticsUsdMxn.
import type { ChainPayAnalyticsSnapshot } from '../../types/chainpayAnalytics';

export const mockChainPayAnalyticsSnapshot: ChainPayAnalyticsSnapshot = {
  asOf: '2025-12-05T12:00:00Z',
  corridorId: 'USD_MXN',
  tierHealth: [
    {
      tier: 'LOW',
      lossRate: 0.003,
      reserveUtilization: 0.45,
      unusedReserveRatio: 0.55,
      shipmentCount: 120,
    },
    {
      tier: 'MEDIUM',
      lossRate: 0.009,
      reserveUtilization: 0.72,
      unusedReserveRatio: 0.28,
      shipmentCount: 60,
    },
    {
      tier: 'HIGH',
      lossRate: 0.022,
      reserveUtilization: 0.95,
      unusedReserveRatio: 0.05,
      shipmentCount: 20,
    },
    {
      tier: 'CRITICAL',
      lossRate: 0.08,
      reserveUtilization: 1.1,
      unusedReserveRatio: -0.1,
      shipmentCount: 3,
    },
  ],
  daysToCash: [
    {
      tier: 'LOW',
      corridorId: 'USD_MXN',
      medianDaysToFirstCash: 1.2,
      p95DaysToFirstCash: 2.5,
      medianDaysToFinalCash: 4.0,
      p95DaysToFinalCash: 7.0,
      shipmentCount: 120,
    },
    {
      tier: 'MEDIUM',
      corridorId: 'USD_MXN',
      medianDaysToFirstCash: 1.8,
      p95DaysToFirstCash: 3.6,
      medianDaysToFinalCash: 5.2,
      p95DaysToFinalCash: 8.9,
      shipmentCount: 60,
    },
    {
      tier: 'HIGH',
      corridorId: 'USD_MXN',
      medianDaysToFirstCash: 2.4,
      p95DaysToFirstCash: 4.8,
      medianDaysToFinalCash: 7.5,
      p95DaysToFinalCash: 11.2,
      shipmentCount: 20,
    },
    {
      tier: 'CRITICAL',
      corridorId: 'USD_MXN',
      medianDaysToFirstCash: 3.8,
      p95DaysToFirstCash: 6.5,
      medianDaysToFinalCash: 10.0,
      p95DaysToFinalCash: 15.5,
      shipmentCount: 3,
    },
  ],
  sla: [
    {
      corridorId: 'USD_MXN',
      tier: 'LOW',
      claimReviewSlaBreachRate: 0.02,
      manualReviewSlaBreachRate: 0.05,
      totalReviews: 30,
    },
    {
      corridorId: 'USD_MXN',
      tier: 'MEDIUM',
      claimReviewSlaBreachRate: 0.06,
      manualReviewSlaBreachRate: 0.11,
      totalReviews: 20,
    },
    {
      corridorId: 'USD_MXN',
      tier: 'HIGH',
      claimReviewSlaBreachRate: 0.12,
      manualReviewSlaBreachRate: 0.18,
      totalReviews: 12,
    },
    {
      corridorId: 'USD_MXN',
      tier: 'CRITICAL',
      claimReviewSlaBreachRate: 0.22,
      manualReviewSlaBreachRate: 0.31,
      totalReviews: 4,
    },
  ],
};
