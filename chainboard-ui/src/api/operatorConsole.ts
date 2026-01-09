/**
 * Operator Console API Client — READ-ONLY API Access
 * 
 * PAC Reference: PAC-BENSON-CHAINBRIDGE-PDO-OC-VISIBILITY-EXEC-007C
 * Agent: Sonny (GID-02) — UI
 * Effective Date: 2025-12-30
 * 
 * INVARIANTS:
 *   INV-OC-001: UI may not mutate PDO or settlement state
 *   INV-OC-005: Non-GET requests fail closed
 * 
 * This client ONLY uses GET requests. No POST/PUT/PATCH/DELETE methods exist.
 */

import type {
  OCPDOView,
  OCPDOListResponse,
  OCPDOFilters,
  OCSettlementView,
  OCSettlementListResponse,
  OCSettlementFilters,
  OCTimelineResponse,
  OCLedgerEntry,
  OCLedgerVerifyResponse,
  OCHealthResponse,
} from '../types/operatorConsole';

// ═══════════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';
const OC_PREFIX = '/oc';

// ═══════════════════════════════════════════════════════════════════════════════
// HTTP HELPERS (GET ONLY — INV-OC-001, INV-OC-005)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Execute GET request only.
 * INV-OC-005: This is the ONLY HTTP method available in this client.
 */
async function ocGet<T>(path: string, params?: Record<string, string | number | boolean>): Promise<T> {
  const url = new URL(`${API_BASE}${OC_PREFIX}${path}`, window.location.origin);
  
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, String(value));
      }
    });
  }
  
  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ message: response.statusText }));
    throw new OCAPIError(
      response.status,
      errorBody.error || 'OC_API_ERROR',
      errorBody.message || `HTTP ${response.status}`,
    );
  }
  
  return response.json();
}

// ═══════════════════════════════════════════════════════════════════════════════
// ERROR CLASS
// ═══════════════════════════════════════════════════════════════════════════════

export class OCAPIError extends Error {
  constructor(
    public statusCode: number,
    public errorCode: string,
    message: string,
  ) {
    super(message);
    this.name = 'OCAPIError';
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// HEALTH API
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Check OC API health.
 */
export async function fetchOCHealth(): Promise<OCHealthResponse> {
  return ocGet<OCHealthResponse>('/health');
}

// ═══════════════════════════════════════════════════════════════════════════════
// PDO API (GET ONLY)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * List PDO views for Operator Console.
 */
export async function fetchPDOList(filters?: OCPDOFilters): Promise<OCPDOListResponse> {
  const params: Record<string, string | number | boolean> = {};
  
  if (filters?.outcome_status) params.outcome_status = filters.outcome_status;
  if (filters?.pac_id) params.pac_id = filters.pac_id;
  if (filters?.has_settlement !== undefined) params.has_settlement = filters.has_settlement;
  if (filters?.limit) params.limit = filters.limit;
  if (filters?.offset) params.offset = filters.offset;
  
  return ocGet<OCPDOListResponse>('/pdo', params);
}

/**
 * Get single PDO view.
 */
export async function fetchPDOView(pdoId: string): Promise<OCPDOView> {
  return ocGet<OCPDOView>(`/pdo/${encodeURIComponent(pdoId)}`);
}

/**
 * Get PDO timeline.
 */
export async function fetchPDOTimeline(pdoId: string): Promise<OCTimelineResponse> {
  return ocGet<OCTimelineResponse>(`/pdo/${encodeURIComponent(pdoId)}/timeline`);
}

// ═══════════════════════════════════════════════════════════════════════════════
// SETTLEMENT API (GET ONLY)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * List settlement views for Operator Console.
 */
export async function fetchSettlementList(filters?: OCSettlementFilters): Promise<OCSettlementListResponse> {
  const params: Record<string, string | number | boolean> = {};
  
  if (filters?.pdo_id) params.pdo_id = filters.pdo_id;
  if (filters?.status) params.status = filters.status;
  if (filters?.limit) params.limit = filters.limit;
  if (filters?.offset) params.offset = filters.offset;
  
  return ocGet<OCSettlementListResponse>('/settlements', params);
}

/**
 * Get single settlement view.
 */
export async function fetchSettlementView(settlementId: string): Promise<OCSettlementView> {
  return ocGet<OCSettlementView>(`/settlements/${encodeURIComponent(settlementId)}`);
}

/**
 * Get settlement timeline.
 */
export async function fetchSettlementTimeline(settlementId: string): Promise<OCTimelineResponse> {
  return ocGet<OCTimelineResponse>(`/settlements/${encodeURIComponent(settlementId)}/timeline`);
}

// ═══════════════════════════════════════════════════════════════════════════════
// LEDGER API (GET ONLY)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * List ledger entries with hash visibility (INV-OC-003).
 */
export async function fetchLedgerEntries(
  limit = 100,
  offset = 0,
): Promise<OCLedgerEntry[]> {
  return ocGet<OCLedgerEntry[]>('/ledger/entries', { limit, offset });
}

/**
 * Get single ledger entry.
 */
export async function fetchLedgerEntry(entryId: string): Promise<OCLedgerEntry> {
  return ocGet<OCLedgerEntry>(`/ledger/entry/${encodeURIComponent(entryId)}`);
}

/**
 * Verify ledger chain integrity.
 */
export async function verifyLedgerChain(): Promise<OCLedgerVerifyResponse> {
  return ocGet<OCLedgerVerifyResponse>('/ledger/verify');
}

// ═══════════════════════════════════════════════════════════════════════════════
// EXPORTS
// ═══════════════════════════════════════════════════════════════════════════════

export const ocApi = {
  // Health
  fetchHealth: fetchOCHealth,
  
  // PDO (GET only)
  fetchPDOList,
  fetchPDOView,
  fetchPDOTimeline,
  
  // Settlement (GET only)
  fetchSettlementList,
  fetchSettlementView,
  fetchSettlementTimeline,
  
  // Ledger (GET only)
  fetchLedgerEntries,
  fetchLedgerEntry,
  verifyLedgerChain,
};

export default ocApi;
