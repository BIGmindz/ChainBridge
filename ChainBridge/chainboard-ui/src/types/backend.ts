/**
 * Backend API Type Definitions
 *
 * Shared interfaces for production backend integration.
 * All types match backend schemas exactly.
 */

// ===== Operator Queue =====

export interface OperatorQueueResponse {
  items: OperatorQueueItem[];
  total_count: number;
  filters_applied: {
    include_levels?: string;
    needs_snapshot_only?: boolean;
    max_results?: number;
  };
}

export interface OperatorQueueItem {
  shipmentId: string;
  risk_level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  riskScore: number;
  corridor_code?: string | null;
  mode?: "TRUCK_FTL" | "TRUCK_LTL" | "OCEAN" | "AIR" | "RAIL" | "INTERMODAL" | null;
  incoterm?: string | null;
  completeness_pct: number;
  blocking_gap_count: number;
  template_name?: string | null;
  days_delayed?: number | null;
  latestSnapshotStatus?: "PENDING" | "IN_PROGRESS" | "SUCCESS" | "FAILED" | null;
  latest_snapshot_updatedAt?: string | null; // ISO timestamp
  needs_snapshot: boolean;
  has_payment_hold: boolean; // Required by OCQueueTable/MoneyViewPanel
  last_event_at?: string | null; // ISO timestamp
  // Micro-settlement fields (R01)
  recon_state?: "CLEAN" | "PARTIAL_ESCROW" | "BLOCKED_DISPUTE" | null;
  reconScore?: number | null;
  approvedAmount?: number | null;
  heldAmount?: number | null;
  // Legal wrapper fields (LEGAL-R01)
  has_ricardian_wrapper?: boolean | null;
  ricardian_status?: RicardianInstrumentStatus | null;
}


// ===== Risk Snapshot =====

export interface RiskSnapshotResponse {
  shipmentId: string;
  snapshot_hash: string;
  risk_level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  riskScore: number;
  compliance_blocks: ComplianceBlock[];
  risk_factors: RiskFactor[];
  readiness_reason: string | null;
  snapshot_status: "PENDING" | "IN_PROGRESS" | "SUCCESS" | "FAILED";
  createdAt: string;
  metadata: {
    total_fields: number;
    completed_fields: number;
    blocking_gaps: number;
  };

  // CamelCase aliases consumed by UI components
  riskLevel?: RiskSnapshotResponse["risk_level"];
}

export interface ComplianceBlock {
  block_id: string;
  block_type: "DOCUMENT" | "COMMERCIAL" | "REGULATORY" | "FINANCIAL";
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  status: "PASSED" | "PENDING" | "FAILED";
  message: string;
  field_path?: string;
}

export interface RiskFactor {
  factor_id: string;
  category: string;
  description: string;
  impact_score: number;
  detected_at: string;
}

// ===== Event Timeline =====

export interface EventTimelineResponse {
  shipmentId: string;
  events: ShipmentEvent[];
  total_count: number;
}

export interface ShipmentEvent {
  eventId: string;
  eventType: "MILESTONE" | "RISK_CHANGE" | "SNAPSHOT_CREATED" | "PAYMENT_INITIATED" | "ALERT";
  timestamp: string;
  description: string;
  severity?: "INFO" | "WARNING" | "ERROR";
  metadata?: Record<string, unknown>;
  actor?: string;
}

// ===== IoT Health =====

export interface IoTHealthResponse {
  summary: {
    devices_online: number;
    devices_offline: number;
    devices_stale_gps: number;
    devices_stale_env: number;
    total_devices: number;
  };
  status: "healthy" | "degraded" | "critical";
  last_updated: string;
}

// ===== Operator Events Stream =====

export interface OperatorEventStreamResponse {
  events: OperatorEvent[];
  last_eventId: string;
  has_more: boolean;
}

export interface OperatorEvent {
  eventId: string;
  eventType: "PAYMENT_ERROR" | "SLA_DEGRADED" | "INFO" | "PAYMENT_CONFIRMED";
  severity: "ERROR" | "WARNING" | "INFO" | "SUCCESS";
  title: string;
  message: string;
  shipmentId?: string;
  payment_intent_id?: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

// ===== Pricing Breakdown =====

export interface PricingBreakdownResponse {
  shipmentId: string;
  base_rate: number;
  fuel_surcharge: number;
  accessorials: number;
  volatility_buffer: number;
  total_price: number;
  currency: string;
  pricing_timestamp: string;
}

// ===== Reconciliation & Micro-Settlement =====

export type ReconciliationDecision = "AUTO_APPROVE" | "PARTIAL_APPROVE" | "BLOCK";

export type ReconciliationLineStatus =
  | "MATCHED"
  | "UNDER_DELIVERED"
  | "OVER_DELIVERED"
  | "PRICE_DELTA"
  | "QUALITY_VIOLATION"
  | "MISSING_INVOICE_LINE"
  | "EXTRA_INVOICE_LINE";

export interface ReconciliationLineResult {
  lineId: string;
  sku?: string | null;
  description?: string | null;
  status: ReconciliationLineStatus;
  reasonCode: string;
  poQty?: number | null;
  execQty?: number | null;
  invoiceQty?: number | null;
  poUnitPrice?: number | null;
  invoiceUnitPrice?: number | null;
  approvedAmount: number;
  heldAmount: number;
}

export interface ReconciliationSummary {
  settlementId: string;
  decision: ReconciliationDecision;
  approvedAmount: number;
  heldAmount: number;
  reconScore: number;
  policyId: string;
  flags: string[];
  lines: ReconciliationLineResult[];
  reconciledAt: string;
}

// ===== Audit Pack =====

export interface AuditLaneSummary {
  originCountry?: string | null;
  originCity?: string | null;
  destinationCountry?: string | null;
  destinationCity?: string | null;
  corridor?: string | null;
}

export interface AuditCoreSummary {
  amount?: number | null;
  currency?: string | null;
  shipperId?: string | null;
  carrierId?: string | null;
  brokerId?: string | null;
  state?: string | null;
  lane?: AuditLaneSummary | null;
}

export type AuditProofStatus =
  | "NOT_AVAILABLE"
  | "VERIFIED"
  | "FAILED"
  | "PENDING";

export type AuditProofProvider = "NONE" | "SXT" | "XRPL" | "CHAINLINK" | "OTHER";

export interface AuditProofSummary {
  intentHash?: string | null;
  status: AuditProofStatus;
  provider: AuditProofProvider;
  lastVerifiedAt?: string | null;
}

export interface AuditRiskSnapshot {
  score: number;
  band: string;
  createdAt: string;
}

export interface AuditRiskSummary {
  latestScore?: number | null;
  latestBand?: string | null;
  engineMode?: string | null;
  snapshots: AuditRiskSnapshot[];
}

export interface AuditEventItem {
  eventType: string;
  at: string;
  severity?: string | null;
}

export interface AuditEventTimeline {
  count: number;
  firstAt?: string | null;
  lastAt?: string | null;
  items: AuditEventItem[];
}

export interface AuditSLASummary {
  slaBand?: string | null;
  expectedP95Seconds?: number | null;
  actualSeconds?: number | null;
  breach?: boolean | null;
}

export interface AuditIoTSummary {
  hasIot?: boolean | null;
  alertsCount?: number | null;
  tempExcursions?: number | null;
  gpsGaps?: number | null;
}

export interface AuditDocumentRef {
  externalId?: string | null;
  source?: string | null;
  available: boolean;
}

export interface AuditDocuments {
  bol: AuditDocumentRef;
  customs: AuditDocumentRef;
  pod: AuditDocumentRef;
}

export interface AuditMetadata {
  triggeredByRules: string[];
  autoGenerated: boolean;
}

export interface AuditPackResponse {
  settlementId: string;
  generatedAt: string;
  source: string;
  core: AuditCoreSummary;
  proofSummary: AuditProofSummary;
  riskSummary: AuditRiskSummary;
  events: AuditEventTimeline;
  slaSummary?: AuditSLASummary | null;
  iotSummary?: AuditIoTSummary | null;
  documents: AuditDocuments;
  auditMetadata: AuditMetadata;
  legalWrapper?: RicardianInstrument | null;
}

// ===== Legal Wrapper (Ricardian) =====

export type RicardianInstrumentStatus =
  | "ACTIVE"
  | "FROZEN"
  | "TERMINATED";

// Digital Supremacy - SONNY PACK
export interface DigitalSupremacy {
  enabled: boolean;
  precedence: "code_over_prose";
  uccReference: string;
  ukEtda2023: boolean;
  hashBinding: string;
  killSwitch: {
    enabled: boolean;
    conditions: string[];
  };
}

export interface RicardianInstrument {
  id: string;
  instrumentType: "BILL_OF_LADING" | "PLEDGE_AGREEMENT" | "FINANCING_AGREEMENT";
  physicalReference: string;

  pdfUri: string;
  pdfIpfsUri?: string | null;
  pdfHash: string;

  ricardianVersion: string;
  governingLaw: string;

  smartContractChain?: string | null;
  smartContractAddress?: string | null;
  lastSignedTxHash?: string | null;

  status: RicardianInstrumentStatus;
  freezeReason?: string | null;

  // Digital Supremacy - SONNY PACK
  supremacyEnabled: boolean;
  materialAdverseOverride: boolean;
  ricardianMetadata?: {
    digitalSupremacy?: DigitalSupremacy;
    [key: string]: unknown;
  } | null;
}

// ===== Financing (FINANCE-R01) =====

export type InventoryStakeStatus =
  | "PENDING"
  | "ACTIVE"
  | "REPAID"
  | "LIQUIDATED"
  | "CANCELLED";

export interface FinancingQuote {
  physicalReference: string;
  instrument_id: string;
  notional_value: string;   // decimal string
  currency: string;
  max_advance_rate: string;   // percent as string
  max_advance_amount: string; // currency as string
  base_apr: string;
  risk_adjusted_apr: string;
  reasonCodes: string[];
}

export interface InventoryStake {
  id: string;
  status: InventoryStakeStatus;
  ricardian_instrument_id: string;
  principal_amount: string;
  currency: string;
  max_advance_rate: string;
  applied_advance_rate: string;
  base_apr: string;
  risk_adjusted_apr: string;
  notional_value: string;
  lender_name?: string | null;
  borrower_name?: string | null;
  createdAt: string;
  activated_at?: string | null;
  repaid_at?: string | null;
  liquidated_at?: string | null;
}

// ===== Error Response =====

export interface ApiErrorResponse {
  error: string;
  message: string;
  status_code: number;
  timestamp: string;
}
