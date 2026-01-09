/**
 * Audit API Client — Fetch Functions for Audit OC Endpoints
 * ════════════════════════════════════════════════════════════════════════════════
 *
 * PAC Reference: PAC-013A (CORRECTED · GOLD STANDARD)
 * Agent: Sonny (GID-02) — Audit UI
 * Order: ORDER 3
 * Effective Date: 2025-12-30
 *
 * READ-ONLY: All functions perform GET requests only.
 *
 * ════════════════════════════════════════════════════════════════════════════════
 */

import {
  ChainReconstruction,
  ChainVerificationResult,
  AuditExportResponse,
  RegulatorySummary,
  AuditMetadata,
} from "../types/audit";

// ═══════════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const AUDIT_OC_PREFIX = "/oc/audit";

// ═══════════════════════════════════════════════════════════════════════════════
// FETCH HELPER
// ═══════════════════════════════════════════════════════════════════════════════

async function fetchAuditApi<T>(
  endpoint: string,
  params?: Record<string, string | number | boolean | undefined>
): Promise<T> {
  const url = new URL(`${API_BASE_URL}${AUDIT_OC_PREFIX}${endpoint}`);

  // Add query parameters
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, String(value));
      }
    });
  }

  const response = await fetch(url.toString(), {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Audit API error: ${response.status} ${response.statusText}`
    );
  }

  return response.json();
}

// ═══════════════════════════════════════════════════════════════════════════════
// CHAIN RECONSTRUCTION API
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get complete chain reconstruction for audit.
 * INV-AUDIT-002: Complete chain reconstruction without inference.
 */
export async function getChainReconstruction(
  chainId: string
): Promise<ChainReconstruction> {
  return fetchAuditApi<ChainReconstruction>(`/chains/${chainId}`);
}

/**
 * Verify chain hash integrity.
 * INV-AUDIT-004: Hash verification at every link.
 */
export async function verifyChain(
  chainId: string
): Promise<ChainVerificationResult> {
  return fetchAuditApi<ChainVerificationResult>(`/chains/${chainId}/verify`);
}

/**
 * List all available chain IDs.
 */
export async function listChains(params?: {
  start_date?: string;
  end_date?: string;
  limit?: number;
}): Promise<string[]> {
  return fetchAuditApi<string[]>("/chains", params);
}

// ═══════════════════════════════════════════════════════════════════════════════
// AUDIT EXPORT API
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Export audit trail as JSON.
 * INV-AUDIT-003: Export formats include JSON.
 */
export async function exportAuditTrailJson(params?: {
  start_date?: string;
  end_date?: string;
  limit?: number;
}): Promise<AuditExportResponse> {
  return fetchAuditApi<AuditExportResponse>("/export", params);
}

/**
 * Export audit trail as CSV (returns blob URL).
 * INV-AUDIT-003: Export formats include CSV.
 */
export async function exportAuditTrailCsv(params?: {
  start_date?: string;
  end_date?: string;
  limit?: number;
}): Promise<string> {
  const url = new URL(`${API_BASE_URL}${AUDIT_OC_PREFIX}/export/csv`);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, String(value));
      }
    });
  }

  const response = await fetch(url.toString(), {
    method: "GET",
  });

  if (!response.ok) {
    throw new Error(`CSV export failed: ${response.status}`);
  }

  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

// ═══════════════════════════════════════════════════════════════════════════════
// REGULATORY SUMMARY API
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get regulatory summary with computed metrics.
 */
export async function getRegulatorySummary(params?: {
  period_start?: string;
  period_end?: string;
}): Promise<RegulatorySummary> {
  return fetchAuditApi<RegulatorySummary>("/regulatory/summary", params);
}

/**
 * Get governance violations list.
 */
export async function getGovernanceViolations(params?: {
  start_date?: string;
  end_date?: string;
  limit?: number;
}): Promise<{
  violations: unknown[];
  total: number;
  period_start: string;
  period_end: string;
  query_timestamp: string;
  api_version: string;
}> {
  return fetchAuditApi("/regulatory/violations", params);
}

// ═══════════════════════════════════════════════════════════════════════════════
// METADATA API
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get audit API metadata including capabilities and invariants.
 */
export async function getAuditMetadata(): Promise<AuditMetadata> {
  return fetchAuditApi<AuditMetadata>("/metadata");
}

/**
 * Health check for audit API.
 */
export async function checkAuditHealth(): Promise<{
  status: string;
  api_version: string;
  governance_mode: string;
  timestamp: string;
}> {
  return fetchAuditApi("/health");
}
