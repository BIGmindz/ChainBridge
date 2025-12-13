import type {
    AtRiskShipmentSummary,
    ChainDocsDossier,
    ChainPayPlan,
    OperatorEventListItem,
    OperatorQueueItem,
    OperatorSummary,
    PaginatedShadowPilotShipments,
    PaymentIntentListItem,
    PaymentIntentSummary,
    SettlementEvent,
    ShadowPilotSummary,
    ShipmentEvent,
    ShipmentHealthResponse,
    SnapshotExportEvent,
} from "../types/chainbridge";

const DEFAULT_TIMEOUT_MS = 10_000;
const RAW_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";
if (!RAW_BASE_URL) {
  const message =
    "VITE_API_BASE_URL is not configured. Please set it in your .env.local to point at the FastAPI backend.";
  if (import.meta.env.DEV) {
    console.error(message);
  }
  throw new Error(message);
}
const API_BASE_URL = RAW_BASE_URL;

class ApiError extends Error {
  status: number | null;

  constructor(message: string, status: number | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function httpGet<T>(path: string, timeoutMs: number = DEFAULT_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        Accept: "application/json",
      },
      signal: controller.signal,
    });

    if (!response.ok) {
      const message = await safeReadError(response);
      throw new ApiError(message, response.status);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("Request timed out while contacting ChainBridge API.");
    }
    throw new ApiError(error instanceof Error ? error.message : "Network request failed.");
  } finally {
    clearTimeout(timeout);
  }
}

async function httpPost<T>(
  path: string,
  body: unknown,
  timeoutMs: number = DEFAULT_TIMEOUT_MS
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    if (!response.ok) {
      const message = await safeReadError(response);
      throw new ApiError(message, response.status);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("Request timed out while contacting ChainBridge API.");
    }
    throw new ApiError(error instanceof Error ? error.message : "Network request failed.");
  } finally {
    clearTimeout(timeout);
  }
}

async function safeReadError(response: Response): Promise<string> {
  try {
    const payload = await response.json();
    if (payload?.detail) {
      return typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
    }
    if (payload?.message) {
      return payload.message;
    }
  } catch (error) {
    console.warn("Failed to parse error payload", error);
  }
  return `Request failed with status ${response.status}`;
}

export async function fetchChainDocsDossier(shipmentId: string): Promise<ChainDocsDossier> {
  if (!shipmentId) {
    throw new ApiError("Shipment ID is required for ChainDocs dossier fetch.");
  }
  return httpGet<ChainDocsDossier>(`/chaindocs/shipments/${encodeURIComponent(shipmentId)}/dossier`);
}

export async function fetchChainPayPlan(shipmentId: string): Promise<ChainPayPlan> {
  if (!shipmentId) {
    throw new ApiError("Shipment ID is required for ChainPay plan fetch.");
  }
  return httpGet<ChainPayPlan>(`/chainpay/shipments/${encodeURIComponent(shipmentId)}/settlement_plan`);
}

interface DemoDocumentSeed {
  document_id: string;
  type: string;
  status: string;
  version: number;
  hash: string;
  mletr: boolean;
}

export async function seedDemoDocuments(shipmentId: string): Promise<ChainDocsDossier> {
  if (!shipmentId) {
    throw new ApiError("Shipment ID is required to seed demo documents.");
  }

  const demoDocuments: DemoDocumentSeed[] = [
    {
      document_id: `${shipmentId}-BOL-001`,
      type: "BILL_OF_LADING",
      status: "VERIFIED",
      version: 3,
      hash: "0xbolcafedeadbeef",
      mletr: true,
    },
    {
      document_id: `${shipmentId}-INV-001`,
      type: "COMMERCIAL_INVOICE",
      status: "PRESENT",
      version: 2,
      hash: "0xinvoicecafe1234",
      mletr: false,
    },
    {
      document_id: `${shipmentId}-PACK-001`,
      type: "PACKING_LIST",
      status: "PRESENT",
      version: 1,
      hash: "0xpacklistbead5678",
      mletr: false,
    },
    {
      document_id: `${shipmentId}-INS-001`,
      type: "INSURANCE_CERTIFICATE",
      status: "PRESENT",
      version: 1,
      hash: "0xinsurancefa11babe",
      mletr: false,
    },
  ];

  await Promise.all(
    demoDocuments.map((doc) =>
      httpPost(`/chaindocs/shipments/${encodeURIComponent(shipmentId)}/documents`, doc)
    )
  );

  return fetchChainDocsDossier(shipmentId);
}

export async function fetchShipmentHealth(shipmentId: string): Promise<ShipmentHealthResponse> {
  if (!shipmentId) {
    throw new ApiError("Shipment ID is required for health fetch.");
  }
  return httpGet<ShipmentHealthResponse>(`/chainiq/shipments/${encodeURIComponent(shipmentId)}/health`);
}

export async function fetchAtRiskShipments(params?: {
  min_riskScore?: number;
  max_results?: number;
  offset?: number;
  corridor_code?: string;
  mode?: string;
  incoterm?: string;
  risk_level?: string;
}): Promise<AtRiskShipmentSummary[]> {
  const search = new URLSearchParams();

  // Add defined parameters only
  if (params?.min_riskScore !== undefined) {
    search.append('min_riskScore', String(params.min_riskScore));
  } else {
    search.append('min_riskScore', '70'); // default
  }

  if (params?.max_results !== undefined) {
    search.append('max_results', String(params.max_results));
  } else {
    search.append('max_results', '50'); // default
  }

  if (params?.offset !== undefined) {
    search.append('offset', String(params.offset));
  }

  if (params?.corridor_code && params.corridor_code.trim()) {
    search.append('corridor_code', params.corridor_code.trim());
  }

  if (params?.mode && params.mode.trim()) {
    search.append('mode', params.mode.trim());
  }

  if (params?.incoterm && params.incoterm.trim()) {
    search.append('incoterm', params.incoterm.trim());
  }

  if (params?.risk_level && params.risk_level.trim()) {
    search.append('risk_level', params.risk_level.trim());
  }

  return httpGet<AtRiskShipmentSummary[]>(`/chainiq/shipments/at_risk?${search.toString()}`);
}

export async function createSnapshotExport(shipmentId: string): Promise<SnapshotExportEvent> {
  if (!shipmentId) {
    throw new ApiError("Shipment ID is required for snapshot export creation.");
  }

  return httpPost<SnapshotExportEvent>(`/chainiq/admin/snapshot_exports`, {
    shipmentId: shipmentId,
  });
}

export async function fetchSnapshotExports(shipmentId: string): Promise<SnapshotExportEvent[]> {
  if (!shipmentId) {
    throw new ApiError("Shipment ID is required to fetch snapshot history.");
  }
  return httpGet<SnapshotExportEvent[]>(`/chainiq/admin/snapshot_exports?shipmentId=${shipmentId}`);
}

export async function fetchOperatorSummary(): Promise<OperatorSummary> {
  return httpGet<OperatorSummary>("/chainiq/operator/summary");
}

interface OperatorQueueParams {
  max_results?: number;
  include_levels?: string;
  needs_snapshot_only?: boolean;
}

export async function fetchOperatorQueue(params?: OperatorQueueParams): Promise<OperatorQueueItem[]> {
  const search = new URLSearchParams();

  if (params?.max_results !== undefined) {
    search.append("max_results", String(params.max_results));
  }

  if (params?.include_levels !== undefined && params.include_levels.trim()) {
    search.append("include_levels", params.include_levels.trim());
  }

  if (params?.needs_snapshot_only) {
    search.append("needs_snapshot_only", "true");
  }

  const query = search.toString();
  return httpGet<OperatorQueueItem[]>(`/chainiq/operator/queue${query ? "?" + query : ""}`);
}

export async function fetchShipmentEvents(shipmentId: string): Promise<ShipmentEvent[]> {
  if (!shipmentId) {
    throw new ApiError("Shipment ID is required to fetch shipment events.");
  }
  return httpGet<ShipmentEvent[]>(`/debug/shipments/${encodeURIComponent(shipmentId)}/events`);
}

export interface EventFeedParams {
  limit?: number;
  cursor?: string | null;
  payment_intent_id?: string;
  shipmentId?: string;
}

export interface EventFeedResponse {
  items: OperatorEventListItem[];
  next_cursor: string | null;
}

export async function fetchEventFeed(params: EventFeedParams = {}): Promise<EventFeedResponse> {
  const search = new URLSearchParams();

  if (params.limit !== undefined) {
    search.append("limit", String(params.limit));
  }

  if (params.cursor) {
    search.append("cursor", params.cursor);
  }

  if (params.payment_intent_id?.trim()) {
    search.append("payment_intent_id", params.payment_intent_id.trim());
  }

  if (params.shipmentId?.trim()) {
    search.append("shipmentId", params.shipmentId.trim());
  }

  const query = search.toString();
  const suffix = query ? `?${query}` : "";
  return httpGet<EventFeedResponse>(`/events/settlement_feed${suffix}`);
}

export interface EventsHeartbeatResponse {
  last_event_at: string | null;
  last_worker_heartbeat_at: string | null;
}

export async function fetchEventsHeartbeat(): Promise<EventsHeartbeatResponse> {
  return httpGet<EventsHeartbeatResponse>("/events/heartbeat");
}

// =============================================================================
// PAYMENT INTENT API (ChainPay Integration)
// =============================================================================

export interface PaymentIntentListParams {
  status?: string;
  corridor_code?: string;
  mode?: string;
  has_proof?: boolean;
  ready_for_payment?: boolean;
}

export async function fetchPaymentIntents(
  params: PaymentIntentListParams = {},
): Promise<PaymentIntentListItem[]> {
  const search = new URLSearchParams();

  if (params.status?.trim()) {
    search.append("status", params.status.trim());
  }

  if (params.corridor_code?.trim()) {
    search.append("corridor_code", params.corridor_code.trim());
  }

  if (params.mode?.trim()) {
    search.append("mode", params.mode.trim());
  }

  if (params.has_proof !== undefined) {
    search.append("has_proof", String(params.has_proof));
  }

  if (params.ready_for_payment !== undefined) {
    search.append("ready_for_payment", String(params.ready_for_payment));
  }

  const query = search.toString();
  return httpGet<PaymentIntentListItem[]>(`/payment_intents${query ? "?" + query : ""}`);
}

export async function fetchPaymentIntentSummary(): Promise<PaymentIntentSummary> {
  return httpGet<PaymentIntentSummary>("/payment_intents/summary");
}

// =============================================================================
// SETTLEMENT EVENT API (ChainPay Timeline Integration)
// =============================================================================

export async function fetchSettlementEvents(paymentIntentId: string): Promise<SettlementEvent[]> {
  if (!paymentIntentId) return [];
  return httpGet<SettlementEvent[]>(`/payment_intents/${encodeURIComponent(paymentIntentId)}/settlement_events`);
}

// =============================================================================
// RECONCILIATION API (ChainAudit Integration)
// =============================================================================

export interface ReconciliationPayload {
  issues?: string[];
  blocked?: boolean;
}

export async function reconcilePaymentIntent(
  paymentIntentId: string,
  payload: ReconciliationPayload = {}
): Promise<void> {
  if (!paymentIntentId) {
    throw new ApiError("Payment intent ID is required for reconciliation");
  }
  return httpPost<void>(`/audit/payment_intents/${encodeURIComponent(paymentIntentId)}/reconcile`, payload);
}

// =============================================================================
// SHADOW PILOT API - Commercial Impact Analysis
// =============================================================================

export async function fetchShadowPilotSummaries(): Promise<ShadowPilotSummary[]> {
  return httpGet<ShadowPilotSummary[]>('/api/shadow-pilot/summaries');
}

export async function fetchShadowPilotSummary(runId: string): Promise<ShadowPilotSummary> {
  return httpGet<ShadowPilotSummary>(`/api/shadow-pilot/summaries/${encodeURIComponent(runId)}`);
}

export async function fetchShadowPilotShipments(
  runId: string,
  cursor?: string
): Promise<PaginatedShadowPilotShipments> {
  const params: Record<string, string> = {};
  if (cursor) params.cursor = cursor;
  const queryString = new URLSearchParams(params).toString();
  const path = `/api/shadow-pilot/runs/${encodeURIComponent(runId)}/shipments${queryString ? `?${queryString}` : ''}`;
  return httpGet<PaginatedShadowPilotShipments>(path);
}

// Export utilities for feature-specific API clients
export { httpGet, httpPost };
export type { ApiError };
