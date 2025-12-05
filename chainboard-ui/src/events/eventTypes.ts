// Canonical event types for ChainBridge Event Bus


export type EventSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';

export interface ChainBridgeEvent {
  event_id: string;
  canonical_shipment_id: string;
  event_type: string;
  timestamp: string;
  payload: Record<string, any>;
  trace_id: string;
  severity?: EventSeverity;
  // --- TOKENOMICS FIELDS ---
  tokenAmount?: number;
  burnAmount?: number;
  riskMultiplier?: number;
  mlAdjustment?: number;
  rationale?: string;
  // traceId is already present
}


export interface TokenEvent extends ChainBridgeEvent {
  tokenAmount?: number;
  burnAmount?: number;
  finalAmount?: number;
  riskMultiplier?: number;
  mlAdjustment?: number;
  netToken?: number;
  severity?: EventSeverity;
  rationale?: string;
  traceId?: string;
  economicReliability?: number;
  timestamp?: string;
}

// Event type constants

enum EventTypes {
  SHIPMENT_STATUS_UPDATE = 'SHIPMENT_STATUS_UPDATE',
  IOT_ANOMALY = 'IOT_ANOMALY',
  DELAY_ETA_CHANGE = 'DELAY_ETA_CHANGE',
  RISK_SCORE = 'RISK_SCORE',
  SETTLEMENT_TRIGGER = 'SETTLEMENT_TRIGGER',
  TOKEN_EVENT = 'TOKEN_EVENT',
  TOKEN_EARNED = 'TOKEN_EARNED',
  TOKEN_FINAL = 'TOKEN_FINAL',
  TOKEN_BURN = 'TOKEN_BURN',
  TOKEN_PENALTY = 'TOKEN_PENALTY',
  ALERT = 'ALERT',
  SYSTEM_EVENT = 'SYSTEM_EVENT',
  AGENT_TELEMETRY = 'AGENT_TELEMETRY',
}

export default EventTypes;
