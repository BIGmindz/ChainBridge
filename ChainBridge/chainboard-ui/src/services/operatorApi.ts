/**
 * Operator API Client
 *
 * Production-ready API service for Operator Console.
 * All endpoints return typed responses matching backend schemas.
 *
 * Source: backend API (replaces all mock data)
 */

import type {
    ApiErrorResponse,
    AuditPackResponse,
    DigitalSupremacy,
    EventTimelineResponse,
    FinancingQuote,
    InventoryStake,
    IoTHealthResponse,
    OperatorEventStreamResponse,
    OperatorQueueResponse,
    PricingBreakdownResponse,
    ReconciliationSummary,
    RicardianInstrument,
    RiskSnapshotResponse
} from "../types/backend";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8001";

/**
 * Generic API error handler
 */
class ApiError extends Error {
  constructor(
    public status: number,
    public response: ApiErrorResponse
  ) {
    super(response.message);
    this.name = "ApiError";
  }
}

/**
 * Generic fetch wrapper with error handling
 */
async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  console.log(`[operatorApi] Fetching from backend: ${endpoint}`, { source: "backend" });

  try {
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const errorData: ApiErrorResponse = await response.json();
      throw new ApiError(response.status, errorData);
    }

    return response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    // Network error or JSON parse error
    throw new Error(`Failed to fetch ${endpoint}: ${error instanceof Error ? error.message : "Unknown error"}`);
  }
}

// ===== Queue API =====

export interface FetchOperatorQueueParams {
  max_results?: number;
  include_levels?: string; // e.g., "CRITICAL,HIGH"
  needs_snapshot_only?: boolean;
}

/**
 * Fetch operator queue with filters
 * GET /operator/queue
 */
export async function fetchOperatorQueue(
  params: FetchOperatorQueueParams = {}
): Promise<OperatorQueueResponse> {
  const searchParams = new URLSearchParams();

  if (params.max_results) searchParams.set("max_results", params.max_results.toString());
  if (params.include_levels) searchParams.set("include_levels", params.include_levels);
  if (params.needs_snapshot_only) searchParams.set("needs_snapshot_only", "true");

  const query = searchParams.toString();
  const endpoint = `/operator/queue${query ? `?${query}` : ""}`;

  return apiFetch<OperatorQueueResponse>(endpoint);
}

// ===== Risk Snapshot API =====

/**
 * Fetch risk snapshot for a shipment
 * GET /operator/risk-snapshot/:shipmentId
 */
export async function fetchRiskSnapshot(shipmentId: string): Promise<RiskSnapshotResponse> {
  return apiFetch<RiskSnapshotResponse>(`/operator/risk-snapshot/${shipmentId}`);
}

// ===== Event Timeline API =====

/**
 * Fetch event timeline for a shipment
 * GET /operator/events/:shipmentId
 */
export async function fetchEventTimeline(shipmentId: string): Promise<EventTimelineResponse> {
  return apiFetch<EventTimelineResponse>(`/operator/events/${shipmentId}`);
}

// ===== IoT Health API =====

/**
 * Fetch IoT health summary
 * GET /operator/iot-health
 */
export async function fetchIoTHealth(): Promise<IoTHealthResponse> {
  return apiFetch<IoTHealthResponse>("/operator/iot-health");
}

// ===== Operator Events Stream API =====

export interface FetchOperatorEventsStreamParams {
  since_eventId?: string;
  limit?: number;
}

/**
 * Fetch operator events stream (for toast notifications)
 * GET /operator/events/stream
 */
export async function fetchOperatorEventsStream(
  params: FetchOperatorEventsStreamParams = {}
): Promise<OperatorEventStreamResponse> {
  const searchParams = new URLSearchParams();

  if (params.since_eventId) searchParams.set("since_eventId", params.since_eventId);
  if (params.limit) searchParams.set("limit", params.limit.toString());

  const query = searchParams.toString();
  const endpoint = `/operator/events/stream${query ? `?${query}` : ""}`;

  return apiFetch<OperatorEventStreamResponse>(endpoint);
}

// ===== Pricing Breakdown API =====

/**
 * Fetch pricing breakdown for a shipment
 * GET /operator/pricing/:shipmentId
 */
export async function fetchPricingBreakdown(shipmentId: string): Promise<PricingBreakdownResponse> {
  return apiFetch<PricingBreakdownResponse>(`/operator/pricing/${shipmentId}`);
}

/**
 * Fetch audit pack for a settlement
 * GET /operator/settlements/{id}/auditpack
 */
export async function fetchAuditPack(settlementId: string): Promise<AuditPackResponse> {
  return apiFetch<AuditPackResponse>(`/operator/settlements/${settlementId}/auditpack`);
}

/**
 * Fetch reconciliation summary for a settlement
 * GET /operator/settlements/{id}/reconciliation
 */
export async function fetchReconciliationSummary(settlementId: string): Promise<ReconciliationSummary> {
  return apiFetch<ReconciliationSummary>(`/operator/settlements/${settlementId}/reconciliation`);
}

/**
 * Fetch Ricardian legal wrapper for a shipment
 * GET /legal/ricardian/instruments/by-physical/{ref}
 */
export async function fetchRicardianInstrumentForShipment(shipmentId: string): Promise<RicardianInstrument | null> {
  try {
    return await apiFetch<RicardianInstrument>(
      `/legal/ricardian/instruments/by-physical/${encodeURIComponent(shipmentId)}`
    );
  } catch {
    // Return null if no legal wrapper exists (404 is expected for unwrapped shipments)
    console.log(`[operatorApi] No legal wrapper found for ${shipmentId}`);
    return null;
  }
}

/**
 * Fetch financing quote for a shipment
 * POST /finance/quote
 */
export async function fetchFinancingQuote(
  physicalReference: string,
  notionalValue: number
): Promise<FinancingQuote> {
  return apiFetch<FinancingQuote>('/finance/quote', {
    method: 'POST',
    body: JSON.stringify({
      physicalReference: physicalReference,
      notional_value: notionalValue.toString(),
      currency: 'USD'
    })
  });
}

/**
 * Fetch inventory stakes for a shipment
 * GET /finance/stakes/by-physical/{ref}
 */
export async function fetchInventoryStakesForShipment(
  physicalReference: string
): Promise<InventoryStake[]> {
  try {
    return await apiFetch<InventoryStake[]>(
      `/finance/stakes/by-physical/${encodeURIComponent(physicalReference)}`
    );
  } catch {
    // Return empty array if no stakes exist (404 is expected)
    console.log(`[operatorApi] No stakes found for ${physicalReference}`);
    return [];
  }
}

/**
 * Fetch Digital Supremacy metadata for a Ricardian instrument (SONNY PACK)
 * GET /legal/ricardian/supremacy/{id}
 */
export async function fetchSupremacyInfo(
  instrumentId: string
): Promise<DigitalSupremacy> {
  return apiFetch<DigitalSupremacy>(
    `/legal/ricardian/supremacy/${encodeURIComponent(instrumentId)}`
  );
}

// ===== Export for convenience =====

export const operatorApi = {
  fetchOperatorQueue,
  fetchRiskSnapshot,
  fetchEventTimeline,
  fetchIoTHealth,
  fetchOperatorEventsStream,
  fetchPricingBreakdown,
  fetchAuditPack,
  fetchReconciliationSummary,
  fetchRicardianInstrumentForShipment,
  fetchFinancingQuote,
  fetchInventoryStakesForShipment,
  fetchSupremacyInfo,
};
