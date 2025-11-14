import { MOCK_PAYMENT_RAILS_METRICS } from "./mockData";
export { MOCK_PAYMENT_RAILS_METRICS } from "./mockData";
import type { PaymentRailId, PaymentRailMetrics } from "./types";
export type { PaymentRailMetrics } from "./types";

export const TRADITIONAL_BENCHMARK_ID: PaymentRailId = "swift";
export const BLOCKCHAIN_BENCHMARK_ID: PaymentRailId = "blockchain";
export const DEFAULT_TRANSFER_BENCHMARK_USD = 1_000_000;

export interface PaymentRailBenchmarkPair {
  traditional: PaymentRailMetrics;
  swift: PaymentRailMetrics;
  blockchain: PaymentRailMetrics;
}

export interface PaymentRailDeltas {
  settlementHoursSaved: number;
  capitalUnlockedHours: number;
  avgFeeSavingsUsd: number;
  fxSpreadSavingsBps: number;
  fxSpreadSavingsUsd: number;
  failRateImprovementBps: number;
}

export function selectRailById(id: PaymentRailId): PaymentRailMetrics | undefined {
  return MOCK_PAYMENT_RAILS_METRICS.find((rail) => rail.id === id);
}

export function getBenchmarkRails(): PaymentRailBenchmarkPair {
  const traditional = selectRailById(TRADITIONAL_BENCHMARK_ID);
  const blockchain = selectRailById(BLOCKCHAIN_BENCHMARK_ID);

  if (!traditional || !blockchain) {
    throw new Error("Benchmark payment rail metrics are missing");
  }

  return { traditional, swift: traditional, blockchain };
}

export function computePaymentRailDeltas(
  traditional: PaymentRailMetrics,
  blockchain: PaymentRailMetrics,
  transferAmountUsd: number = DEFAULT_TRANSFER_BENCHMARK_USD,
): PaymentRailDeltas {
  return {
    settlementHoursSaved: clampDelta(traditional.avg_settlement_hours - blockchain.avg_settlement_hours),
    capitalUnlockedHours: clampDelta(traditional.capital_locked_hours - blockchain.capital_locked_hours),
    avgFeeSavingsUsd: clampDelta(traditional.avg_fee_usd - blockchain.avg_fee_usd),
    fxSpreadSavingsBps: clampDelta(traditional.avg_fx_spread_bps - blockchain.avg_fx_spread_bps),
    fxSpreadSavingsUsd: clampDelta(
      ((traditional.avg_fx_spread_bps - blockchain.avg_fx_spread_bps) / 10_000) * transferAmountUsd,
    ),
    failRateImprovementBps: clampDelta(traditional.fail_rate_bps - blockchain.fail_rate_bps),
  };
}

function clampDelta(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.round(value * 100) / 100;
}
