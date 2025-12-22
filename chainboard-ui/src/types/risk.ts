export type RiskBand = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface RiskScoreResponse {
  risk_score: number; // 0–1
  anomaly_score: number; // 0–1
  risk_band: RiskBand;
  top_features: string[];
  reason_codes: string[];
  trace_id: string;
  version: string;
}

export interface ContextRiskEvent {
  event_id: string;
  shipment_id: string;
  corridor_id: string;
  counterparty_id: string;
  counterparty_role: 'buyer' | 'seller' | 'carrier' | 'broker' | 'anchor';
  settlement_channel: string; // e.g. XRPL, BANK, ONCHAIN_TOKEN
  event_type: string; // e.g. SETTLED, REVERSAL
  occurred_at: string; // ISO-8601
  amount: number;
  currency: string;
  risk_score: number;
  anomaly_score: number;
  risk_band: RiskBand;
  top_features: string[];
  reason_codes: string[];
  trace_id: string;
  version: string;
}
