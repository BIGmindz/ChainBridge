import type { SettlementProvider } from './chainpay';

export type GuardrailState = 'GREEN' | 'AMBER' | 'RED';

export interface TierGuardrailStatus {
  tier: string; // expected: LOW | MEDIUM | HIGH | CRITICAL
  state: GuardrailState;
  lossRate: number;
  cashSlaBreachRate: number;
  d2P95Days: number;
  unusedReserveRatio: number;
}

export interface GuardrailStatusSnapshot {
  corridorId: string;
  payoutPolicyVersion?: string;
  overallState: GuardrailState;
  settlementProvider?: SettlementProvider;
  perTier: TierGuardrailStatus[];
  lastEvaluatedAt: string;
}

export function formatGuardrailStateLabel(state?: GuardrailState): string {
  switch (state) {
    case 'GREEN':
      return 'Green – On Target';
    case 'AMBER':
      return 'Amber – Watch Closely';
    case 'RED':
      return 'Red – Guardrail Breach';
    default:
      return 'Unknown';
  }
}
