// =============================================================================
// CANONICAL TYPES - Must match api/models/canonical.py exactly
// =============================================================================

/**
 * Canonical transport modes across ChainBridge services.
 * Must match api/models/canonical.py TransportMode enum.
 */
export type TransportMode =
  | "TRUCK_FTL"
  | "TRUCK_LTL"
  | "OCEAN"
  | "AIR"
  | "RAIL"
  | "INTERMODAL";

/**
 * Lifecycle states for multimodal shipments.
 * Must match api/models/canonical.py ShipmentStatus enum.
 */
export type ShipmentStatus =
  | "PLANNED"
  | "IN_TRANSIT"
  | "AT_FACILITY"
  | "DELAYED"
  | "DELIVERED"
  | "CANCELLED"
  | "EXCEPTION";

/**
 * Risk severity bands shared across ChainIQ and downstream consumers.
 * Must match api/models/canonical.py RiskLevel enum.
 */
export type RiskLevel =
  | "LOW"
  | "MEDIUM"
  | "HIGH"
  | "CRITICAL";

/**
 * Shipment event lifecycle types recorded in the platform spine.
 * Must match api/models/canonical.py ShipmentEventType enum.
 */
export type ShipmentEventType =
  | "RISK_DECIDED"
  | "SNAPSHOT_REQUESTED"
  | "SNAPSHOT_CLAIMED"
  | "SNAPSHOT_COMPLETED"
  | "SNAPSHOT_FAILED";

/**
 * Operator event types emitted by EventBus v2.
 */
export type OperatorEventType =
  | "PAYMENT_INTENT_CREATED"
  | "PAYMENT_STATUS_UPDATED"
  | "SETTLEMENT_EVENT_CREATED"
  | "PROOF_ATTACHED"
  | "SNAPSHOT_REQUESTED"
  | "SNAPSHOT_COMPLETED"
  | "SNAPSHOT_FAILED";

export interface OperatorEventListItem {
  id: string;
  occurredAt: string;
  source: string; // "webhook" | "worker" | "api"
  actor: string;
  eventType: OperatorEventType;
  summary: string;
  payment_intent_id?: string;
  shipmentId?: string;
}

// =============================================================================
// LEGACY/EXISTING TYPES
// =============================================================================

export type ChainDocStatus = "VERIFIED" | "PRESENT" | "MISSING" | "FLAGGED";

export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
  modules_loaded: number;
  active_pipelines: number;
}

export interface ChainDocRecord {
  documentId: string;
  type: string;
  status: ChainDocStatus;
  version: number;
  hash: string;
  updatedAt: string;
  issuedBy: string;
  storageLocation: string;
  mletrReady: boolean;
  complianceTags: string[];
}

export interface ChainDocsDossier {
  shipmentId: string;
  documents: ChainDocRecord[];
  missingDocuments: string[];
  lastPolicyReview: string;
  aiConfidenceScore: number;
}

export type SettlementMilestoneState = "PAID" | "PENDING" | "HELD";

export interface SettlementMilestonePlan {
  id: string;
  label: string;
  payoutPercent: number;
  amountUsd: number;
  expectedRelease: string;
  status: SettlementMilestoneState;
  paidAt?: string;
  holdReason?: string;
}

export interface ChainPayAlert {
  id: string;
  severity: "info" | "warning" | "critical";
  message: string;
  createdAt: string;
}

export interface ChainPayPlan {
  shipmentId: string;
  templateId: string;
  customer: string;
  totalValueUsd: number;
  floatReductionEstimate: number; // % reduction vs legacy factoring
  coveragePercent: number; // % of total value ChainPay advances
  creditTermsDays: number;
  milestones: SettlementMilestonePlan[];
  alerts: ChainPayAlert[];
  docRisk?: DocRiskSnapshot;
}

export interface DocRiskSnapshot {
  score: number;
  level: RiskLevel;
  missingBlockingDocs: string[];
}

export interface DocumentHealth {
  presentCount: number;
  missingCount: number;
  missingDocuments: string[];
  completenessPct: number;
  requiredTotal: number;
  optionalTotal: number;
  blockingGapCount: number;
}

export interface SettlementHealth {
  milestonesTotal: number;
  milestonesPaid: number;
  milestonesPending: number;
  milestonesHeld: number;
  completionPct: number;
  floatReductionEstimate?: number | null;
  nextMilestone?: string | null;
}

export interface RiskSnapshot {
  score: number;
  level: RiskLevel;
  drivers: string[];
}

export interface ShipmentHealthResponse {
  shipmentId: string;
  documentHealth: DocumentHealth;
  settlementHealth: SettlementHealth;
  risk: RiskSnapshot;
  recommendedActions: string[];
}

export interface AtRiskShipmentSummary {
  shipmentId: string;
  corridorCode?: string | null;
  mode?: TransportMode | null;
  incoterm?: string | null;
  templateName?: string | null;
  completenessPct: number;
  blockingGapCount: number;
  riskScore: number;
  riskLevel: RiskLevel;
  last_snapshot_at: string; // ISO timestamp
  latestSnapshotStatus?: string | null; // NONE, PENDING, IN_PROGRESS, SUCCESS, FAILED
  latestSnapshotUpdatedAt?: string | null; // ISO timestamp

  // Legacy/snake_case aliases from backend responses
  corridor_code?: string | null;
  template_name?: string | null;
  completeness_pct?: number;
  blocking_gap_count?: number;
  risk_level?: RiskLevel;
}

export interface SnapshotExportEvent {
  eventId: string;
  shipmentId: string;
  status: string; // PENDING, IN_PROGRESS, SUCCESS, FAILED
  createdAt: string;
  updatedAt: string;
  notes?: string | null;
  claimedBy?: string | null;
  retryCount: number;
  failureReason?: string | null;
}

export interface OperatorSummary {
  totalAtRisk: number;
  criticalCount: number;
  highCount: number;
  needsSnapshotCount: number;
  paymentHoldsCount: number;
  lastUpdatedAt: string; // ISO timestamp
}

export interface OperatorQueueItem {
  shipmentId: string;
  riskLevel: RiskLevel;
  riskScore: number;
  corridorCode?: string | null;
  mode?: TransportMode | null;
  incoterm?: string | null;
  completenessPct: number;
  blockingGapCount: number;
  templateName?: string | null;
  daysDelayed?: number | null;
  latestSnapshotStatus?: string | null; // SUCCESS, FAILED, IN_PROGRESS, PENDING, None
  latestSnapshotUpdatedAt?: string | null; // ISO timestamp
  needsSnapshot: boolean;
  hasPaymentHold: boolean;
  lastEventAt?: string | null; // ISO timestamp
  // Micro-settlement fields (R01)
  reconState?: "CLEAN" | "PARTIAL_ESCROW" | "BLOCKED_DISPUTE" | null;
  reconScore?: number | null;
  approvedAmount?: number | null;
  heldAmount?: number | null;
  // Legal wrapper fields (LEGAL-R01)
  hasRicardianWrapper?: boolean | null;
  ricardianStatus?: "ACTIVE" | "FROZEN" | "TERMINATED" | null;
  // Digital Supremacy fields (SONNY PACK)
  supremacyEnabled?: boolean | null;
  materialAdverseOverride?: boolean | null;
  // Finance fields (FINANCE-R01) - TODO: Replace with actual backend field
  declaredValueUsd?: number | null;

  // Legacy/snake_case aliases from backend responses
  corridor_code?: string | null;
  completeness_pct?: number;
  blocking_gap_count?: number;
  template_name?: string | null;
  days_delayed?: number | null;
  latest_snapshot_updatedAt?: string | null;
  needs_snapshot?: boolean;
  has_payment_hold?: boolean;
  last_event_at?: string | null;
  recon_state?: "CLEAN" | "PARTIAL_ESCROW" | "BLOCKED_DISPUTE" | null;
  has_ricardian_wrapper?: boolean | null;
  ricardian_status?: "ACTIVE" | "FROZEN" | "TERMINATED" | null;
  declared_valueUsd?: number | null;
}

export interface ShipmentEvent {
  eventId: string;
  shipmentId: string;
  eventType: ShipmentEventType;
  occurredAt: string; // ISO timestamp
  payload: Record<string, unknown>; // Event-specific data
  createdAt: string; // ISO timestamp
}

// =============================================================================
// PAYMENT INTENT TYPES (ChainPay Integration)
// =============================================================================

/**
 * Payment intent status lifecycle.
 * Must match backend PaymentIntentStatus enum.
 */
export type PaymentIntentStatus =
  | "PENDING"
  | "READY_FOR_PAYMENT"
  | "AWAITING_PROOF"
  | "BLOCKED_BY_RISK"
  | "CANCELLED";

/**
 * Payment intent list item for operator console Money View.
 */
export interface PaymentIntentListItem {
  id: string;
  shipmentId: string;
  corridorCode: string | null;
  mode: string | null;
  incoterm: string | null;
  status: PaymentIntentStatus;
  riskLevel: string | null;
  riskScore: number | null;
  has_proof: boolean;
  ready_for_payment: boolean;
  createdAt: string; // ISO timestamp
  updatedAt: string; // ISO timestamp
  // Optional pricing breakdown (may not be present for all intents)
  pricing?: PricingBreakdown | null;
  // Reconciliation fields (from ChainAudit)
  payout_confidence?: number | null; // 0.0–1.0 confidence score
  final_payout_amount?: number | null; // Final adjusted payout amount
  adjustment_reason?: string | null; // Reason for adjustment if any

  // Legacy/snake_case aliases
  corridor_code?: string | null;
  risk_level?: string | null;
}

/**
 * Pricing breakdown for settlement calculations.
 */
export interface PricingBreakdown {
  base_rate: number;
  fuel_surcharge: number;
  accessorials: number;
  volatility_buffer: number;
  total_price: number;
  currency: string;
}

/**
 * Payment intent summary KPIs for operator console.
 */
export interface PaymentIntentSummary {
  total: number;
  ready_for_payment: number;
  awaiting_proof: number;
  blocked_by_risk: number;
}

// =============================================================================
// SETTLEMENT EVENT TYPES (ChainPay Timeline Integration)
// =============================================================================

/**
 * Settlement event for payment intent lifecycle tracking.
 * Tracks the progression of a payment through the settlement pipeline.
 */
export interface SettlementEvent {
  id: string;
  payment_intent_id: string;
  eventType: "CREATED" | "AUTHORIZED" | "CAPTURED" | "FAILED" | "REFUNDED";
  status: "PENDING" | "SUCCESS" | "FAILED";
  amount: number;
  currency: string;
  occurredAt: string; // ISO timestamp
  metadata?: Record<string, unknown>;
}

// =============================================================================
// STAKING & COLLATERAL TYPES (ChainStake Integration)
// =============================================================================

/**
 * Audit vector for fuzzy logic decision visualization.
 * Used to explain why a reconciliation decision was made.
 */
export interface AuditVector {
  label: string;
  value: number;
  unit: string;
  impact: number; // Negative percentage (e.g., -0.5 for -0.5%)
  severity: "LOW" | "MEDIUM" | "HIGH";
}

/**
 * Staking position representing locked collateral for a shipment loan.
 * Used in ChainStake LiquidityDashboard and risk monitoring.
 */
export interface StakingPosition {
  tokenId: string;
  shipmentId: string;
  collateralValue: number; // Total value of staked collateral
  loanAmount: number; // Amount borrowed against collateral
  apy: number; // Annual percentage yield on staked amount
  liquidationHealth: number; // 0-100 health factor
  status: "HEALTHY" | "AT_RISK" | "LIQUIDATED";
  yieldAccrued?: number; // Yield generated so far
  createdAt?: string; // ISO timestamp
  lastUpdatedAt?: string; // ISO timestamp
}

/**
 * Collateral breach event indicating critical risk.
 * Triggers the CollateralBreachModal when liquidation is imminent.
 */
export interface CollateralBreach {
  positionId: string;
  shipmentId: string;
  currentLTV: number; // Loan-to-value ratio as percentage (e.g., 116)
  requiredDeposit: number; // Amount needed to restore health
  liquidationCountdownMs: number; // Milliseconds until liquidation
  collateralValue: number;
  loanAmount: number;
  severity: "WARNING" | "CRITICAL"; // WARNING for 80-90%, CRITICAL for >90%
}

/**
 * Fuzzy logic vector for ChainAudit decision explanation.
 * More flexible than AuditVector - supports custom operators and weightings.
 */
export interface FuzzyVector {
  id: string;
  label: string;
  value: number;
  unit?: string;
  operator: "eq" | "gt" | "lt" | "gte" | "lte" | "in_range"; // Fuzzy logic operator
  threshold: number; // Comparison value
  weight: number; // 0.0-1.0: How much this vector contributes to final score
  impactDirection: "positive" | "negative"; // Does this favor or penalize reconciliation?
  impact: number; // Percentage impact on confidence score (e.g., -1.5 for -1.5%)
  severity: "LOW" | "MEDIUM" | "HIGH";
  dataSource: string; // Where did this signal come from? (e.g., "IOT_SENSOR", "BLOCKCHAIN", "MANUAL")
}

/**
 * Reconciliation result from ChainAudit fuzzy logic engine.
 * Shows why a payment was approved, deducted, or rejected.
 */
export interface ReconciliationResult {
  reconciliationId: string;
  shipmentId: string;
  paymentIntentId: string;
  baseAmount: number; // Original invoice amount (USD)
  adjustedAmount: number; // Amount after fuzzy deductions
  deductionUsd: number; // baseAmount - adjustedAmount
  payoutConfidence: number; // 0-100: How confident is the engine in this decision?
  recommendedAction: "APPROVE" | "PARTIAL" | "REJECT" | "MANUAL_REVIEW";
  fuzzyVectors: FuzzyVector[]; // All decision factors
  timestamp: string; // ISO timestamp when decision was made
  expiresAt: string; // ISO timestamp: When does this decision expire?
}

/**
 * Audit trace for decision history and compliance.
 * Used to replay decisions and explain historical reconciliations.
 */
export interface AuditTrace {
  traceId: string;
  reconciliationId: string;
  shipmentId: string;
  actor: string; // "SYSTEM" | "USER_ID" | "API_CLIENT"
  action: "CREATED" | "APPROVED" | "REJECTED" | "ADJUSTED" | "EXPIRED";
  previousState: ReconciliationResult | null;
  newState: ReconciliationResult | null;
  reasonText?: string; // Human explanation if manually overridden
  timestamp: string; // ISO timestamp
  metadata?: Record<string, unknown>; // Additional context
}

/**
 * Treasury summary for ChainStake LiquidityDashboard.
 * Shows aggregate staking health, available liquidity, and yield.
 */
export interface TreasurySummary {
  walletAddress: string;
  totalValueStaked: number; // Sum of all collateralValue in active positions (USD)
  totalLoansOutstanding: number; // Sum of all loanAmount (USD)
  liquidCapital: number; // Available liquidity NOT staked (USD)
  totalYieldAccrued: number; // Cumulative yield generated (USD)
  yieldPerSecond: number; // Real-time yield generation rate (USD/sec)
  apy: number; // Blended annual percentage yield across all positions
  healthFactor: number; // 0-100: Overall portfolio health
  riskLevel: RiskLevel; // LOW | MEDIUM | HIGH | CRITICAL
  pendingLiquidations: number; // Count of positions with LTV > 90%
  activePositionCount: number;
  lastUpdated: string; // ISO timestamp
}

// =============================================================================
// SHADOW PILOT TYPES - Commercial Impact Analysis
// =============================================================================

export interface ShadowPilotSummary {
  run_id: string;
  prospect_name: string;
  period_months: number;
  total_gmv_usd: number;
  financeable_gmv_usd: number;
  financed_gmv_usd: number;
  protocolRevenueUsd: number;
  working_capital_saved_usd: number;
  losses_avoided_usd: number;
  salvageRevenueUsd: number;
  average_daysPulledForward: number;
  shipments_evaluated: number;
  shipments_financeable: number;
  createdAt: string;
}

export interface ShadowPilotShipmentResult {
  shipmentId: string;
  corridor: string;
  cargoValueUsd: number;
  eventTruthScore: number;
  eligibleForFinance: boolean;
  financedAmountUsd: number;
  daysPulledForward: number;
  wcSavedUsd: number;
  protocolRevenueUsd: number;
  avoidedLossUsd: number;
  salvageRevenueUsd: number;
  exceptionFlag: number;
  lossFlag: number;
  mode: string;
  customerSegment: string;
}

export interface PaginatedShadowPilotShipments {
  items: ShadowPilotShipmentResult[];
  next_cursor?: string | null;
}

// =============================================================================
// GLOBAL INTELLIGENCE TYPES - Live shipment tracking with money + settlement
// =============================================================================

export type SettlementState = 'UNFINANCED' | 'FINANCED_UNPAID' | 'PARTIALLY_PAID' | 'PAID';

export type LiveShipmentStatus = 'ON_TIME' | 'DELAYED' | 'AT_RISK';

export interface LiveShipmentPosition {
  shipmentId: string;
  canonicalShipmentRef: string;
  externalRef?: string;
  lat: number;
  lon: number;
  corridor: string;
  corridorId?: string;
  corridorName?: string;
  corridorNormalized?: string;
  mode: string;
  modeNormalized?: string;
  status: string;
  riskScore: number;
  riskScoreRaw?: number;
  riskCategory?: RiskLevel;
  riskBand?: string;
  riskSource?: string;

  cargoValueUsd: number;
  financedAmountUsd: number;
  paidAmountUsd: number;
  settlementState: string;
  stakeApr?: number;
  stakeCapacityUsd?: number;

  originPortCode?: string;
  originPortName?: string;
  destPortCode?: string;
  destPortName?: string;
  distanceToNearestPortKm?: number;
  eta?: string;
  etaIso?: string;
  etaBandHours?: string;
  etaConfidence?: string;
  etaDeltaHours?: number;
  geoAccuracyKm?: number;
  shipperName?: string;
  carrierName?: string;
  nearestPort?: string;

  lastEventCode: string;
  lastEventTs: string;

  // Legacy/snake_case aliases surfaced by backend
  settlement_state?: string;
  destPort_name?: string;
  distance_to_nearest_port_km?: number;
  eta_band_hours?: string;
  eta_confidence?: string;
  eta_delta_hours?: number;
  last_event_code?: string;
}

export interface CorridorIntelStats {
  corridorId: string;
  corridorName: string;
  stpRate: number;
  avgEtaDeltaMinutes: number;
  highRiskShipments: number;
  atRiskShipments: number;

  // Legacy/snake_case aliases
  corridorLabel?: string;
  shipment_count?: number;
  on_time_count?: number;
  high_risk_count?: number;
  critical_risk_count?: number;
  at_risk_valueUsd?: number;
  valueUsd?: number;
  avg_eta_delta_hours?: number;
}

export interface ModeIntelStats {
  mode: string;
  stpRate: number;
  avgEtaDeltaMinutes: number;
  activeShipments: number;
  highRiskShipments: number;

  // Legacy/snake_case aliases
  shipment_count?: number;
  risk_distribution?: {
    low: number;
    medium: number;
    high: number;
    critical: number;
  };
  avg_delay_hours?: number;
  valueUsd?: number;
}

export interface PortRiskInfo {
  portCode: string;
  portName: string;
  country?: string;
  congestionScore: number;
  highRiskShipments: number;
  activeShipments: number;

  // Legacy/snake_case aliases
  port_code?: string;
  port_name?: string;
  active_shipments?: number;
  at_risk_valueUsd?: number;
  riskScore?: number;
}

export interface GlobalIntelSnapshot {
  corridorKpis: CorridorIntelStats[];
  modeKpis: ModeIntelStats[];
  portHotspots: PortRiskInfo[];
  globalTotals: {
    totalShipments: number;
    activeShipments: number;
    blockedShipments: number;
    settlementsInFlight: number;
  };
  timestamp: string;

  // Legacy/snake_case aliases used by existing UI components
  by_corridor?: Array<
    CorridorIntelStats & {
      corridorId: string;
      shipment_count: number;
      on_time_count: number;
      high_risk_count: number;
      critical_risk_count: number;
      at_risk_valueUsd?: number;
      valueUsd?: number;
      avg_eta_delta_hours?: number;
    }
  >;
  on_time_count?: number;
  top_ports_by_risk?: Array<
    PortRiskInfo & {
      riskScore: number;
      port_code?: string;
      port_name?: string;
      active_shipments?: number;
      at_risk_valueUsd?: number;
    }
  >;
  financed_valueUsd?: number;
}

export interface OCQueueCardMeta {
  shipmentId: string;
  corridorId: string;
  mode: string | null;
  riskBand: string | null;
  settlementState: string | null;
  etaIso: string | null;
  nearestPort: string | null;
}

export interface LivePositionsMeta {
  activeShipments: number;
  corridorsCovered: number;
  portsCovered: number;
}

export interface OCIntelFeedResponse {
  queueCards: OCQueueCardMeta[];
  globalSnapshot: GlobalIntelSnapshot;
  livePositionsMeta: LivePositionsMeta;
}



// =============================================================================
// GEOSPATIAL / FLEET TELEMETRY TYPES (For GlobalOpsMap)
// =============================================================================

/**
 * Enhanced shipment type with real-time geospatial telemetry
 * Used for 3D globe visualization in Operator Console
 */
export interface Shipment {
  shipmentId: string;
  coordinates: [number, number]; // [Longitude, Latitude]
  heading: number; // 0-360 degrees
  velocity: number; // Knots
  riskLevel: 'HEALTHY' | 'DELAYED' | 'CRITICAL';
  riskScore: number;
  corridor?: string;
  mode?: TransportMode;
  cargoValueUsd: number;
  status: ShipmentStatus;
  eta?: string; // ISO timestamp
  originPort?: string;
  destPort?: string;
}

/**
 * Fleet telemetry response from ChainIQ
 * Returns all active shipments with live positions
 */
export interface FleetTelemetryResponse {
  shipments: Shipment[];
  timestamp: string;
  totalCount: number;
}
