import type {
  SettlementMilestone,
  SettlementStatus,
  RiskTier,
  SettlementProvider,
} from '../types/chainpay';
import type {
  ChainPayAnalyticsSnapshot,
  RiskTier as AnalyticsRiskTier,
} from '../types/chainpayAnalytics';
import type {
  GuardrailStatusSnapshot,
  GuardrailState,
} from '../types/chainpayGuardrails';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

export interface SettlementEventDto {
  id: string;
  shipment_id: string;
  timestamp: string;
  milestone: string;
  risk_tier?: string | null;
  notes?: string | null;
}

export interface SettlementStatusDto {
  shipment_id: string;
  cb_usd: {
    total: number;
    released: number;
    reserved: number;
  };
  events: SettlementEventDto[];
  current_milestone: string;
  risk_score?: number | null;
  settlement_provider: string;
}

export function mapSettlementDtoToStatus(dto: SettlementStatusDto): SettlementStatus {
  return {
    shipmentId: dto.shipment_id,
    cbUsd: {
      total: dto.cb_usd.total,
      released: dto.cb_usd.released,
      reserved: dto.cb_usd.reserved,
    },
    events: dto.events.map((e) => ({
      id: e.id,
      shipmentId: e.shipment_id,
      timestamp: e.timestamp,
      milestone: e.milestone as SettlementMilestone,
      riskTier: (e.risk_tier as RiskTier | null | undefined) ?? undefined,
      notes: e.notes ?? undefined,
    })),
    currentMilestone: dto.current_milestone as SettlementMilestone,
    riskScore: dto.risk_score ?? undefined,
    settlementProvider: dto.settlement_provider as SettlementProvider,
  };
}

export async function fetchSettlementStatus(shipmentId: string): Promise<SettlementStatus> {
  const response = await fetch(
    `${API_BASE}/api/chainpay/settlements/${encodeURIComponent(shipmentId)}`,
    {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    },
  );

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: failed to fetch settlement ${shipmentId}`);
  }

  const data: SettlementStatusDto = await response.json();
  return mapSettlementDtoToStatus(data);
}

// -----------------------------------------------------------------------------
// ChainPay Analytics (USD→MXN P0)
// -----------------------------------------------------------------------------

interface TierHealthMetricDto {
  tier: AnalyticsRiskTier;
  loss_rate: number;
  reserve_utilization: number;
  unused_reserve_ratio: number;
  shipment_count: number;
}

interface DaysToCashMetricDto {
  tier: AnalyticsRiskTier;
  corridor_id: string;
  median_days_to_first_cash: number;
  p95_days_to_first_cash: number;
  median_days_to_final_cash: number;
  p95_days_to_final_cash: number;
  shipment_count: number;
}

interface SlaMetricDto {
  corridor_id: string;
  tier: AnalyticsRiskTier;
  claim_review_sla_breach_rate: number;
  manual_review_sla_breach_rate: number;
  total_reviews: number;
}

interface ChainPayAnalyticsSnapshotDto {
  as_of: string;
  corridor_id: string;
  settlement_provider: string;
  tier_health: TierHealthMetricDto[];
  days_to_cash: DaysToCashMetricDto[];
  sla: SlaMetricDto[];
}

function mapAnalyticsDto(dto: ChainPayAnalyticsSnapshotDto): ChainPayAnalyticsSnapshot {
  return {
    asOf: dto.as_of,
    corridorId: dto.corridor_id,
    settlementProvider: dto.settlement_provider as SettlementProvider,
    tierHealth: dto.tier_health.map((row) => ({
      tier: row.tier,
      lossRate: row.loss_rate,
      reserveUtilization: row.reserve_utilization,
      unusedReserveRatio: row.unused_reserve_ratio,
      shipmentCount: row.shipment_count,
    })),
    daysToCash: dto.days_to_cash.map((row) => ({
      tier: row.tier,
      corridorId: row.corridor_id,
      medianDaysToFirstCash: row.median_days_to_first_cash,
      p95DaysToFirstCash: row.p95_days_to_first_cash,
      medianDaysToFinalCash: row.median_days_to_final_cash,
      p95DaysToFinalCash: row.p95_days_to_final_cash,
      shipmentCount: row.shipment_count,
    })),
    sla: dto.sla.map((row) => ({
      corridorId: row.corridor_id,
      tier: row.tier,
      claimReviewSlaBreachRate: row.claim_review_sla_breach_rate,
      manualReviewSlaBreachRate: row.manual_review_sla_breach_rate,
      totalReviews: row.total_reviews,
    })),
  };
}

// Fetches analytics snapshot for USD→MXN P0 corridor.
export async function fetchChainPayAnalyticsUsdMxn(): Promise<ChainPayAnalyticsSnapshot> {
  const response = await fetch(`${API_BASE}/api/chainpay/analytics/usd-mxn`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(
      `HTTP ${response.status}: failed to fetch ChainPay analytics (USD→MXN)`,
    );
  }

  const data: ChainPayAnalyticsSnapshotDto = await response.json();
  return mapAnalyticsDto(data);
}

// -----------------------------------------------------------------------------
// ChainPay Guardrails (USD→MXN P0)
// -----------------------------------------------------------------------------

interface GuardrailTierDto {
  tier: string;
  state: GuardrailState;
  loss_rate: number;
  cash_sla_breach_rate: number;
  d2_p95_days: number;
  unused_reserve_ratio: number;
}

interface GuardrailStatusSnapshotDto {
  corridor_id: string;
  payout_policy_version?: string;
  overall_state: GuardrailState;
  settlement_provider?: string;
  per_tier: GuardrailTierDto[];
  last_evaluated_at: string;
}

function mapGuardrailStatusSnapshot(dto: GuardrailStatusSnapshotDto): GuardrailStatusSnapshot {
  return {
    corridorId: dto.corridor_id,
    payoutPolicyVersion: dto.payout_policy_version,
    overallState: dto.overall_state,
    settlementProvider: dto.settlement_provider as SettlementProvider | undefined,
    perTier: dto.per_tier.map((tier) => ({
      tier: tier.tier,
      state: tier.state,
      lossRate: tier.loss_rate,
      cashSlaBreachRate: tier.cash_sla_breach_rate,
      d2P95Days: tier.d2_p95_days,
      unusedReserveRatio: tier.unused_reserve_ratio,
    })),
    lastEvaluatedAt: dto.last_evaluated_at,
  };
}

// Fetches guardrail status snapshot for USD→MXN corridor (P0 policy).
export async function fetchUsdMxnGuardrails(): Promise<GuardrailStatusSnapshot> {
  const response = await fetch(`${API_BASE}/api/chainpay/guardrails/usd-mxn`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: failed to fetch guardrails (USD→MXN)`);
  }

  const data: GuardrailStatusSnapshotDto = await response.json();
  return mapGuardrailStatusSnapshot(data);
}
