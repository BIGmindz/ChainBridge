/**
 * ChainBridge Trace API Client
 * PAC-009: Full End-to-End Traceability — ORDER 4 (Sonny GID-02)
 * 
 * API client for trace visibility endpoints.
 * 
 * GOVERNANCE INVARIANTS:
 * - INV-TRACE-004: OC renders full chain without inference
 * - All endpoints are READ-ONLY
 */

import type {
  OCTraceView,
  OCTraceTimeline,
  PACTraceSummary,
  TraceGapsResponse,
  TraceLinkListResponse,
  TraceNavigationContext,
  TraceChainVerification,
  TraceDomain,
} from '../types/trace';

// ═══════════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

const BASE_URL = '/api/oc/trace';

// ═══════════════════════════════════════════════════════════════════════════════
// ERROR HANDLING
// ═══════════════════════════════════════════════════════════════════════════════

export class TraceAPIError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'TraceAPIError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new TraceAPIError(
      detail.message || `HTTP ${response.status}`,
      response.status,
      detail
    );
  }
  return response.json();
}

// ═══════════════════════════════════════════════════════════════════════════════
// PDO TRACE ENDPOINTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get full trace view for a PDO.
 * 
 * @param pdoId - PDO identifier
 * @param includeGaps - Whether to include gap indicators
 * @returns Complete trace view
 */
export async function getPDOTraceView(
  pdoId: string,
  includeGaps = true
): Promise<OCTraceView> {
  const url = new URL(`${BASE_URL}/pdo/${pdoId}`, window.location.origin);
  url.searchParams.set('include_gaps', String(includeGaps));
  
  const response = await fetch(url.toString());
  return handleResponse<OCTraceView>(response);
}

/**
 * Get trace timeline for a PDO.
 * 
 * @param pdoId - PDO identifier
 * @returns Chronological timeline of trace events
 */
export async function getPDOTraceTimeline(
  pdoId: string
): Promise<OCTraceTimeline> {
  const response = await fetch(`${BASE_URL}/pdo/${pdoId}/timeline`);
  return handleResponse<OCTraceTimeline>(response);
}

/**
 * Get trace gaps for a PDO.
 * INV-TRACE-005: Missing links are explicit and non-silent.
 * 
 * @param pdoId - PDO identifier
 * @returns List of trace gaps
 */
export async function getPDOTraceGaps(
  pdoId: string
): Promise<TraceGapsResponse> {
  const response = await fetch(`${BASE_URL}/pdo/${pdoId}/gaps`);
  return handleResponse<TraceGapsResponse>(response);
}

// ═══════════════════════════════════════════════════════════════════════════════
// PAC TRACE ENDPOINTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get trace summary for all PDOs in a PAC.
 * 
 * @param pacId - PAC identifier
 * @returns PAC-level trace summary
 */
export async function getPACTraceSummary(
  pacId: string
): Promise<PACTraceSummary> {
  const response = await fetch(`${BASE_URL}/pac/${pacId}`);
  return handleResponse<PACTraceSummary>(response);
}

/**
 * Get all trace links for a PAC.
 * 
 * @param pacId - PAC identifier
 * @param domain - Optional domain filter
 * @returns List of trace links
 */
export async function getPACTraceLinks(
  pacId: string,
  domain?: TraceDomain
): Promise<TraceLinkListResponse> {
  const url = new URL(`${BASE_URL}/pac/${pacId}/links`, window.location.origin);
  if (domain) {
    url.searchParams.set('domain', domain);
  }
  
  const response = await fetch(url.toString());
  return handleResponse<TraceLinkListResponse>(response);
}

// ═══════════════════════════════════════════════════════════════════════════════
// NAVIGATION ENDPOINTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get trace navigation context for click-through.
 * 
 * @param domain - Entity domain
 * @param entityId - Entity identifier
 * @returns Navigation context with inbound/outbound links
 */
export async function getTraceNavigationContext(
  domain: TraceDomain,
  entityId: string
): Promise<TraceNavigationContext> {
  const response = await fetch(`${BASE_URL}/navigate/${domain}/${entityId}`);
  return handleResponse<TraceNavigationContext>(response);
}

// ═══════════════════════════════════════════════════════════════════════════════
// VERIFICATION ENDPOINTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Verify trace chain integrity.
 * INV-TRACE-003: Ledger hash links all phases.
 * 
 * @returns Chain verification result
 */
export async function verifyTraceChain(): Promise<TraceChainVerification> {
  const response = await fetch(`${BASE_URL}/verify/chain`);
  return handleResponse<TraceChainVerification>(response);
}

// ═══════════════════════════════════════════════════════════════════════════════
// EXPORTS
// ═══════════════════════════════════════════════════════════════════════════════

export const traceApi = {
  getPDOTraceView,
  getPDOTraceTimeline,
  getPDOTraceGaps,
  getPACTraceSummary,
  getPACTraceLinks,
  getTraceNavigationContext,
  verifyTraceChain,
};

export default traceApi;
