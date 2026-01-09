// ═══════════════════════════════════════════════════════════════════════════════
// ChainTrust API Client — External Trust Center
// PAC-JEFFREY-P19R: ChainTrust UI Implementation (Sonny GID-02)
//
// READ-ONLY API client for ChainTrust governance visualization.
// All data originates from lint_v2 / governance APIs.
//
// INVARIANTS:
// - No POST / PUT / PATCH / DELETE operations
// - No state mutation
// - All responses are cryptographically verifiable
// ═══════════════════════════════════════════════════════════════════════════════

import type {
  GovernanceStatusDTO,
  AgentUniformPanelDTO,
  PDOLifecycleViewerDTO,
  InvariantCoveragePanelDTO,
  ChainTrustOverviewDTO,
  ChainTrustAuditViewDTO,
} from '../types/chaintrust';

const API_BASE = '/api/trust';

/**
 * Fetch helper with error handling.
 * READ-ONLY — no mutation methods.
 */
async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    const error = await response.text();
    throw new Error(`ChainTrust API error: ${response.status} - ${error}`);
  }
  return response.json();
}

// ═══════════════════════════════════════════════════════════════════════════════
// GOVERNANCE STATUS ENDPOINTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get current governance status.
 * Maps to: lint_v2.LintV2Engine.get_activation_status()
 */
export async function getGovernanceStatus(): Promise<GovernanceStatusDTO> {
  return fetchJson<GovernanceStatusDTO>(`${API_BASE}/status`);
}

/**
 * Get runtime activation details.
 */
export async function getRuntimeActivation(): Promise<GovernanceStatusDTO['runtime_activation']> {
  return fetchJson<GovernanceStatusDTO['runtime_activation']>(`${API_BASE}/runtime`);
}

// ═══════════════════════════════════════════════════════════════════════════════
// AGENT UNIFORM ENDPOINTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get agent uniform panel data.
 * Maps to: gid_registry + lint_v2 uniform invariants
 */
export async function getAgentUniformPanel(): Promise<AgentUniformPanelDTO> {
  return fetchJson<AgentUniformPanelDTO>(`${API_BASE}/agents/uniform`);
}

/**
 * Get agent uniform status for a specific agent.
 */
export async function getAgentUniformStatus(gid: string): Promise<AgentUniformPanelDTO['agents'][0]> {
  return fetchJson<AgentUniformPanelDTO['agents'][0]>(`${API_BASE}/agents/uniform/${gid}`);
}

// ═══════════════════════════════════════════════════════════════════════════════
// PDO LIFECYCLE ENDPOINTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get PDO lifecycle viewer data.
 * Maps to: PDO registry + BER pipeline
 */
export async function getPDOLifecycleViewer(): Promise<PDOLifecycleViewerDTO> {
  return fetchJson<PDOLifecycleViewerDTO>(`${API_BASE}/pdo/lifecycle`);
}

/**
 * Get PDO lifecycle for a specific PDO.
 */
export async function getPDOLifecycle(pdoId: string): Promise<PDOLifecycleViewerDTO['pdos'][0]> {
  return fetchJson<PDOLifecycleViewerDTO['pdos'][0]>(`${API_BASE}/pdo/lifecycle/${pdoId}`);
}

// ═══════════════════════════════════════════════════════════════════════════════
// INVARIANT COVERAGE ENDPOINTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get invariant coverage panel data.
 * Maps to: INVARIANT_REGISTRY from lint_v2
 */
export async function getInvariantCoverage(): Promise<InvariantCoveragePanelDTO> {
  return fetchJson<InvariantCoveragePanelDTO>(`${API_BASE}/invariants/coverage`);
}

/**
 * Get invariant details by ID.
 */
export async function getInvariantDetails(invariantId: string): Promise<InvariantCoveragePanelDTO['invariants'][0]> {
  return fetchJson<InvariantCoveragePanelDTO['invariants'][0]>(`${API_BASE}/invariants/${invariantId}`);
}

// ═══════════════════════════════════════════════════════════════════════════════
// CHAINTRUST OVERVIEW ENDPOINTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get ChainTrust overview for main dashboard.
 */
export async function getChainTrustOverview(): Promise<ChainTrustOverviewDTO> {
  return fetchJson<ChainTrustOverviewDTO>(`${API_BASE}/overview`);
}

// ═══════════════════════════════════════════════════════════════════════════════
// EXTERNAL AUDIT MODE ENDPOINTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Generate external audit view.
 * Creates a shareable, deterministic snapshot.
 */
export async function generateAuditView(): Promise<ChainTrustAuditViewDTO> {
  return fetchJson<ChainTrustAuditViewDTO>(`${API_BASE}/audit/generate`);
}

/**
 * Get existing audit view by trust ID.
 */
export async function getAuditView(trustId: string): Promise<ChainTrustAuditViewDTO> {
  return fetchJson<ChainTrustAuditViewDTO>(`${API_BASE}/audit/${trustId}`);
}

/**
 * Verify audit view hash.
 */
export async function verifyAuditView(trustId: string, hash: string): Promise<{ valid: boolean; message: string }> {
  return fetchJson<{ valid: boolean; message: string }>(`${API_BASE}/audit/${trustId}/verify?hash=${hash}`);
}
