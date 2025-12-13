/**
 * Exceptions API Client
 *
 * API service for Exception Cockpit (The OC V0.1)
 * Handles CRUD operations for exceptions, playbooks, and decision records.
 *
 * Endpoints:
 * - /api/v1/oc/exceptions
 * - /api/v1/oc/exceptions/stats
 * - /api/v1/oc/decisions
 */

import type {
  DecisionRecord,
  DecisionRecordsListResponse,
  Exception,
  ExceptionDetailResponse,
  ExceptionSeverity,
  ExceptionsListResponse,
  ExceptionStats,
  ExceptionStatus,
  Playbook,
  PlaybooksListResponse,
  ShipmentRiskSummary,
  ShipmentSettlementSummary,
} from "../types/exceptions";

// API base URL - defaults to localhost:8001 for development
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8001";

// Flag to use mock data (set to false to use real backend)
const USE_MOCK_DATA = import.meta.env.VITE_USE_MOCK_DATA === "true";

// =============================================================================
// MOCK DATA - Used when USE_MOCK_DATA is true or backend is unavailable
// =============================================================================

const MOCK_EXCEPTIONS: Exception[] = [
  {
    id: "exc-001",
    type: "RISK_THRESHOLD",
    severity: "CRITICAL",
    status: "OPEN",
    summary: "Risk score exceeded critical threshold (92/100)",
    description: "ChainIQ detected multiple risk factors including Red Sea conflict zone transit and carrier reliability concerns.",
    shipment_id: "SHP-2025-0042",
    shipment_reference: "MAERSK-LA-SH-0042",
    playbook_id: "pb-risk-001",
    owner_id: "op-001",
    owner_name: "John Operator",
    created_at: new Date(Date.now() - 2 * 3600000).toISOString(),
    updated_at: new Date(Date.now() - 1800000).toISOString(),
  },
  {
    id: "exc-002",
    type: "PAYMENT_HOLD",
    severity: "HIGH",
    status: "IN_PROGRESS",
    summary: "Settlement milestone 2 blocked - documentation pending",
    description: "ChainPay has placed a hold on the 30% in-transit release pending BoL verification.",
    shipment_id: "SHP-2025-0038",
    shipment_reference: "COSCO-SH-NY-0038",
    playbook_id: "pb-payment-001",
    owner_id: "op-002",
    owner_name: "Sarah Finance",
    created_at: new Date(Date.now() - 6 * 3600000).toISOString(),
    updated_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: "exc-003",
    type: "ETA_BREACH",
    severity: "HIGH",
    status: "OPEN",
    summary: "ETA slippage detected: +48h from original schedule",
    description: "Port congestion at Singapore has caused significant delay. Customer notification pending.",
    shipment_id: "SHP-2025-0055",
    shipment_reference: "MSC-TK-SG-0055",
    created_at: new Date(Date.now() - 4 * 3600000).toISOString(),
    updated_at: new Date(Date.now() - 2 * 3600000).toISOString(),
  },
  {
    id: "exc-004",
    type: "COMPLIANCE_FLAG",
    severity: "MEDIUM",
    status: "OPEN",
    summary: "ESG compliance review required for carrier",
    description: "Carrier flagged for environmental compliance review based on recent audit findings.",
    shipment_id: "SHP-2025-0061",
    shipment_reference: "EVERGREEN-HK-LA-0061",
    created_at: new Date(Date.now() - 12 * 3600000).toISOString(),
    updated_at: new Date(Date.now() - 8 * 3600000).toISOString(),
  },
  {
    id: "exc-005",
    type: "DOCUMENT_MISSING",
    severity: "MEDIUM",
    status: "OPEN",
    summary: "Certificate of Origin missing for customs clearance",
    description: "Customs hold at destination port. COO required to release shipment.",
    shipment_id: "SHP-2025-0048",
    shipment_reference: "HAPAG-SH-HH-0048",
    playbook_id: "pb-docs-001",
    created_at: new Date(Date.now() - 18 * 3600000).toISOString(),
    updated_at: new Date(Date.now() - 6 * 3600000).toISOString(),
  },
  {
    id: "exc-006",
    type: "IOT_ALERT",
    severity: "LOW",
    status: "RESOLVED",
    summary: "Temperature deviation detected - within tolerance",
    description: "Reefer unit reported 2°C deviation. Monitoring continues, no action required.",
    shipment_id: "SHP-2025-0033",
    shipment_reference: "ONE-JP-LA-0033",
    resolved_at: new Date(Date.now() - 3600000).toISOString(),
    created_at: new Date(Date.now() - 24 * 3600000).toISOString(),
    updated_at: new Date(Date.now() - 3600000).toISOString(),
  },
];

const MOCK_DECISION_RECORDS: DecisionRecord[] = [
  {
    id: "dr-001",
    type: "RISK_DECISION",
    actor: "ChainIQ Risk Engine",
    actor_type: "SYSTEM",
    policy_id: "policy-risk-001",
    policy_name: "Critical Risk Threshold Policy",
    shipment_id: "SHP-2025-0042",
    summary: "Risk score elevated to CRITICAL (92/100) - Red Sea transit + carrier risk factors",
    created_at: new Date(Date.now() - 2 * 3600000).toISOString(),
  },
  {
    id: "dr-002",
    type: "SETTLEMENT_DECISION",
    actor: "ChainPay Settlement Engine",
    actor_type: "SYSTEM",
    policy_id: "policy-settle-001",
    policy_name: "Standard 4-Milestone Policy",
    shipment_id: "SHP-2025-0038",
    summary: "HOLD: Milestone 2 (30% in-transit) pending BoL verification",
    created_at: new Date(Date.now() - 5 * 3600000).toISOString(),
  },
  {
    id: "dr-003",
    type: "MANUAL_OVERRIDE",
    actor: "Sarah Finance",
    actor_type: "OPERATOR",
    exception_id: "exc-002",
    shipment_id: "SHP-2025-0038",
    summary: "Exception assigned for manual review - awaiting shipper response",
    created_at: new Date(Date.now() - 4 * 3600000).toISOString(),
  },
  {
    id: "dr-004",
    type: "EXCEPTION_RESOLUTION",
    actor: "John Operator",
    actor_type: "OPERATOR",
    exception_id: "exc-006",
    shipment_id: "SHP-2025-0033",
    summary: "IoT alert resolved - temperature within acceptable range, monitoring continues",
    created_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: "dr-005",
    type: "AUTOMATED_ACTION",
    actor: "ChainBridge Event Bus",
    actor_type: "SYSTEM",
    shipment_id: "SHP-2025-0055",
    summary: "ETA breach notification sent to customer (reference: CUST-NOTIFY-0055)",
    created_at: new Date(Date.now() - 3 * 3600000).toISOString(),
  },
];

const MOCK_PLAYBOOKS: Playbook[] = [
  {
    id: "pb-risk-001",
    name: "Critical Risk Response",
    description: "Standard operating procedure for handling critical risk threshold breaches",
    exception_type: "RISK_THRESHOLD",
    steps: [
      { id: "s1", order: 1, title: "Review Risk Factors", description: "Analyze ChainIQ risk breakdown", status: "COMPLETED" },
      { id: "s2", order: 2, title: "Assess Mitigation Options", description: "Evaluate rerouting or carrier alternatives", status: "IN_PROGRESS" },
      { id: "s3", order: 3, title: "Notify Stakeholders", description: "Alert customer and internal teams", status: "PENDING" },
      { id: "s4", order: 4, title: "Document Resolution", description: "Record outcome and lessons learned", status: "PENDING" },
    ],
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-06-01T00:00:00Z",
    is_active: true,
  },
];

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Helper to make API requests with error handling
 */
async function apiRequest<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Helper to filter mock data by severity
 */
function filterMockBySeverity(
  exceptions: Exception[],
  params?: { status?: ExceptionStatus; severity?: ExceptionSeverity }
): Exception[] {
  let filtered = [...exceptions];

  if (params?.status) {
    filtered = filtered.filter((e) => e.status === params.status);
  }
  if (params?.severity) {
    filtered = filtered.filter((e) => e.severity === params.severity);
  }

  // Sort by severity (CRITICAL first) then by created_at (newest first)
  const severityOrder: Record<ExceptionSeverity, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
  filtered.sort((a, b) => {
    const severityDiff = severityOrder[a.severity] - severityOrder[b.severity];
    if (severityDiff !== 0) return severityDiff;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  return filtered;
}

// =============================================================================
// API FUNCTIONS
// =============================================================================

/**
 * Fetch exceptions list with optional filters
 */
export async function fetchExceptions(params?: {
  status?: ExceptionStatus;
  severity?: ExceptionSeverity;
  page?: number;
  page_size?: number;
}): Promise<ExceptionsListResponse> {
  // Try real API first
  if (!USE_MOCK_DATA) {
    try {
      const searchParams = new URLSearchParams();
      if (params?.status) searchParams.set("status", params.status);
      if (params?.severity) searchParams.set("severity", params.severity);
      if (params?.page) searchParams.set("page", String(params.page));
      if (params?.page_size) searchParams.set("page_size", String(params.page_size));

      const url = `${API_BASE_URL}/api/v1/oc/exceptions?${searchParams.toString()}`;
      console.log(`[exceptionsApi] Fetching exceptions from backend`, { url, source: "api" });

      return await apiRequest<ExceptionsListResponse>(url);
    } catch (error) {
      console.warn(`[exceptionsApi] Backend unavailable, falling back to mock data:`, error);
    }
  }

  // Fallback to mock data
  console.log(`[exceptionsApi] Fetching exceptions (mock)`, { params, source: "mock" });
  await new Promise((resolve) => setTimeout(resolve, 300));

  const filtered = filterMockBySeverity(MOCK_EXCEPTIONS, params);

  return {
    exceptions: filtered,
    total: filtered.length,
    page: params?.page ?? 1,
    page_size: params?.page_size ?? 20,
  };
}

/**
 * Fetch a single exception by ID with related data
 */
export async function fetchExceptionDetail(exceptionId: string): Promise<ExceptionDetailResponse | null> {
  // Try real API first
  if (!USE_MOCK_DATA) {
    try {
      const url = `${API_BASE_URL}/api/v1/oc/exceptions/${exceptionId}`;
      console.log(`[exceptionsApi] Fetching exception detail from backend`, { url, source: "api" });

      return await apiRequest<ExceptionDetailResponse>(url);
    } catch (error) {
      console.warn(`[exceptionsApi] Backend unavailable, falling back to mock data:`, error);
    }
  }

  // Fallback to mock data
  console.log(`[exceptionsApi] Fetching exception detail (mock)`, { exceptionId, source: "mock" });
  await new Promise((resolve) => setTimeout(resolve, 200));

  const exception = MOCK_EXCEPTIONS.find((e) => e.id === exceptionId);
  if (!exception) return null;

  const playbook = exception.playbook_id
    ? MOCK_PLAYBOOKS.find((p) => p.id === exception.playbook_id)
    : undefined;

  const recent_decisions = MOCK_DECISION_RECORDS.filter(
    (d) => d.exception_id === exceptionId || d.shipment_id === exception.shipment_id
  ).slice(0, 5);

  return { exception, playbook, recent_decisions };
}

/**
 * Fetch exception statistics for KPI display
 */
export async function fetchExceptionStats(): Promise<ExceptionStats> {
  // Try real API first
  if (!USE_MOCK_DATA) {
    try {
      const url = `${API_BASE_URL}/api/v1/oc/exceptions/stats`;
      console.log(`[exceptionsApi] Fetching exception stats from backend`, { url, source: "api" });

      return await apiRequest<ExceptionStats>(url);
    } catch (error) {
      console.warn(`[exceptionsApi] Backend unavailable, falling back to mock data:`, error);
    }
  }

  // Fallback to mock data
  console.log(`[exceptionsApi] Fetching exception stats (mock)`, { source: "mock" });
  await new Promise((resolve) => setTimeout(resolve, 150));

  const open = MOCK_EXCEPTIONS.filter((e) => e.status !== "RESOLVED" && e.status !== "DISMISSED");

  return {
    total_open: open.length,
    critical_count: open.filter((e) => e.severity === "CRITICAL").length,
    high_count: open.filter((e) => e.severity === "HIGH").length,
    medium_count: open.filter((e) => e.severity === "MEDIUM").length,
    low_count: open.filter((e) => e.severity === "LOW").length,
    resolved_today: MOCK_EXCEPTIONS.filter(
      (e) => e.resolved_at && new Date(e.resolved_at).toDateString() === new Date().toDateString()
    ).length,
    avg_resolution_time_hours: 4.2,
  };
}

/**
 * Fetch decision records with optional filters
 */
export async function fetchDecisionRecords(params?: {
  shipment_id?: string;
  exception_id?: string;
  limit?: number;
}): Promise<DecisionRecordsListResponse> {
  // Try real API first
  if (!USE_MOCK_DATA) {
    try {
      const searchParams = new URLSearchParams();
      if (params?.shipment_id) searchParams.set("shipment_id", params.shipment_id);
      if (params?.exception_id) searchParams.set("exception_id", params.exception_id);
      if (params?.limit) searchParams.set("limit", String(params.limit));

      const url = `${API_BASE_URL}/api/v1/oc/decisions?${searchParams.toString()}`;
      console.log(`[exceptionsApi] Fetching decision records from backend`, { url, source: "api" });

      return await apiRequest<DecisionRecordsListResponse>(url);
    } catch (error) {
      console.warn(`[exceptionsApi] Backend unavailable, falling back to mock data:`, error);
    }
  }

  // Fallback to mock data
  console.log(`[exceptionsApi] Fetching decision records (mock)`, { params, source: "mock" });
  await new Promise((resolve) => setTimeout(resolve, 200));

  let filtered = [...MOCK_DECISION_RECORDS];

  if (params?.shipment_id) {
    filtered = filtered.filter((d) => d.shipment_id === params.shipment_id);
  }
  if (params?.exception_id) {
    filtered = filtered.filter((d) => d.exception_id === params.exception_id);
  }

  const limit = params?.limit ?? 10;
  filtered = filtered.slice(0, limit);

  return {
    records: filtered,
    total: filtered.length,
    page: 1,
    page_size: limit,
  };
}

/**
 * Fetch playbooks list
 */
export async function fetchPlaybooks(): Promise<PlaybooksListResponse> {
  // TODO: Wire to real API when playbooks endpoint is ready
  console.log(`[exceptionsApi] Fetching playbooks (mock)`, { source: "mock" });

  await new Promise((resolve) => setTimeout(resolve, 150));

  return {
    playbooks: MOCK_PLAYBOOKS,
    total: MOCK_PLAYBOOKS.length,
  };
}

/**
 * Fetch risk summary for a shipment (ChainIQ stub)
 */
export async function fetchShipmentRiskSummary(shipmentId: string): Promise<ShipmentRiskSummary> {
  // TODO: Wire to ChainIQ API when available
  console.log(`[exceptionsApi] Fetching shipment risk summary (stub)`, { shipmentId, source: "stub" });

  await new Promise((resolve) => setTimeout(resolve, 200));

  return {
    shipment_id: shipmentId,
    risk_score: 72,
    resilience_score: 65,
    esg_score: 78,
    risk_factors: [
      { factor: "Geopolitical", impact: 25, description: "Red Sea conflict zone transit" },
      { factor: "Carrier Reliability", impact: 15, description: "Below-average on-time performance" },
      { factor: "Weather", impact: 8, description: "Monsoon season in origin region" },
    ],
    last_updated: new Date().toISOString(),
  };
}

/**
 * Fetch settlement summary for a shipment (ChainPay stub)
 */
export async function fetchShipmentSettlementSummary(shipmentId: string): Promise<ShipmentSettlementSummary> {
  // TODO: Wire to ChainPay API when available
  console.log(`[exceptionsApi] Fetching shipment settlement summary (stub)`, { shipmentId, source: "stub" });

  await new Promise((resolve) => setTimeout(resolve, 200));

  return {
    shipment_id: shipmentId,
    policy_id: "policy-settle-001",
    policy_name: "Standard 4-Milestone Policy",
    total_amount: 125000,
    released_amount: 25000,
    held_amount: 100000,
    currency: "USD",
    milestones: [
      { name: "Booking Confirmed", percentage: 20, status: "COMPLETED", completed_at: new Date(Date.now() - 7 * 24 * 3600000).toISOString() },
      { name: "Pickup Complete", percentage: 30, status: "PENDING" },
      { name: "In Transit", percentage: 30, status: "PENDING" },
      { name: "Delivered", percentage: 20, status: "PENDING" },
    ],
    last_updated: new Date().toISOString(),
  };
}

/**
 * Update exception status (action handler)
 */
export async function updateExceptionStatus(
  exceptionId: string,
  status: ExceptionStatus
): Promise<Exception | null> {
  // Try real API first
  if (!USE_MOCK_DATA) {
    try {
      const url = `${API_BASE_URL}/api/v1/oc/exceptions/${exceptionId}/status?status=${status}`;
      console.log(`[exceptionsApi] Updating exception status via backend`, { url, source: "api" });

      return await apiRequest<Exception>(url, { method: "PATCH" });
    } catch (error) {
      console.warn(`[exceptionsApi] Backend unavailable, falling back to mock data:`, error);
    }
  }

  // Fallback to mock data
  console.log(`[exceptionsApi] Updating exception status (mock)`, { exceptionId, status, source: "mock" });
  await new Promise((resolve) => setTimeout(resolve, 300));

  const exception = MOCK_EXCEPTIONS.find((e) => e.id === exceptionId);
  if (!exception) return null;

  // Update mock data in-memory
  exception.status = status;
  exception.updated_at = new Date().toISOString();
  if (status === "RESOLVED") {
    exception.resolved_at = new Date().toISOString();
  }

  return exception;
}
