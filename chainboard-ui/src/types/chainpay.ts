export type RiskBand = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | null;

export interface RiskSnapshot {
  settlement_id: string;
  intent_id: string;
  risk_score: number | null;
  risk_band: RiskBand;
  engine_mode: string | null;
  factors: string[];
  created_at: string;
}

export type SettlementMilestone =
  | 'PICKUP'
  | 'IN_TRANSIT'
  | 'DELIVERED'
  | 'CLAIM_WINDOW'
  | 'FINALIZED';

export type RiskTier = 'LOW' | 'MEDIUM' | 'HIGH';

export type SettlementProvider = 'INTERNAL_LEDGER' | 'CB_USDX';

export interface SettlementEvent {
  id: string;
  shipmentId: string;
  timestamp: string; // ISO timestamp
  milestone: SettlementMilestone;
  riskTier?: RiskTier;
  notes?: string;
}

export interface CbUsdAmount {
  total: number; // total CB-USDx locked for this shipment
  released: number; // released to date
  reserved: number; // held for claims/escrow
}

export interface SettlementStatus {
  shipmentId: string;
  cbUsd: CbUsdAmount;
  events: SettlementEvent[];
  currentMilestone: SettlementMilestone;
  riskScore?: number; // ChainIQ score if available
  corridor?: string;
  settlementProvider: SettlementProvider;
}

export function formatSettlementProvider(provider?: SettlementProvider): string {
  if (provider === 'CB_USDX') {
    return 'CB-USDx (tokenized)';
  }
  return 'Internal Ledger (USD)';
}
