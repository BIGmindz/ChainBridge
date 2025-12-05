// ChainBridge Event Types (extended for XRPL)
export interface XRPLMetadata {
  xrplTxHash?: string;
  xrplLedgerIndex?: number;
  xrplRationale?: string;
  xrplTraceId?: string;
  settlementHash?: string;
}

export type EventType =
  | "SHIPMENT_UPDATE"
  | "RISK_OK"
  | "RISK_FAIL"
  | "PAYMENT_TRIGGER"
  | "TOKEN_EVENT"
  | "SHIPMENT_DELIVERED"
  | "IOT_ANOMALY"
  | "RULE_TRIGGER"
  | "SETTLEMENT_STARTED"
  | "SETTLEMENT_MILESTONE_PAID"
  | "SETTLEMENT_FINALIZED"
  | "SETTLEMENT_HELD_RISK"
  | "XRPL_ANCHOR_SUCCESS"
  | "XRPL_ANCHOR_FAILURE"
  | "XRPL_TOKEN_ISSUE"
  | "XRPL_TOKEN_TRANSFER"
  | "XRPL_TOKEN_BURN";

export interface ChainBridgeEvent {
  eventType: EventType;
  shipmentId?: string;
  amount?: number;
  traceId?: string;
  rationale?: string;
  xrpl?: XRPLMetadata;
  // ...other fields
}
