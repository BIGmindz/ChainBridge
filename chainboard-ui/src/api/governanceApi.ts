// ═══════════════════════════════════════════════════════════════════════════════
// ChainBridge Governance API Client
// PAC-012: Governance Hardening — ORDER 3 (Sonny GID-05)
// ═══════════════════════════════════════════════════════════════════════════════

import type {
  AcknowledgmentDTO,
  AcknowledgmentListDTO,
  DependencyDTO,
  DependencyGraphDTO,
  CausalityLinkDTO,
  CausalityTraceDTO,
  NonCapabilityDTO,
  NonCapabilitiesListDTO,
  FailureSemanticsDTO,
  GovernanceSummaryDTO,
  GovernanceInvariantsDTO,
} from '../types/governance';

const API_BASE = '/api/oc/governance';

/**
 * Fetch helper with error handling.
 */
async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Governance API error: ${response.status} - ${error}`);
  }
  return response.json();
}

// ═══════════════════════════════════════════════════════════════════════════════
// ACKNOWLEDGMENT ENDPOINTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get all acknowledgments for a PAC.
 */
export async function getAcknowledgments(pacId: string): Promise<AcknowledgmentListDTO> {
  return fetchJson<AcknowledgmentListDTO>(`${API_BASE}/acknowledgments/${pacId}`);
}

/**
 * Get acknowledgments for a specific order.
 */
export async function getAcknowledgmentsByOrder(
  pacId: string,
  orderId: string
): Promise<AcknowledgmentDTO[]> {
  return fetchJson<AcknowledgmentDTO[]>(
    `${API_BASE}/acknowledgments/${pacId}/order/${orderId}`
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// DEPENDENCY ENDPOINTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get the dependency graph for a PAC.
 */
export async function getDependencyGraph(pacId: string): Promise<DependencyGraphDTO> {
  return fetchJson<DependencyGraphDTO>(`${API_BASE}/dependencies/${pacId}`);
}

/**
 * Get dependencies for a specific order.
 */
export async function getDependenciesForOrder(
  pacId: string,
  orderId: string
): Promise<DependencyDTO[]> {
  return fetchJson<DependencyDTO[]>(
    `${API_BASE}/dependencies/${pacId}/order/${orderId}`
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// CAUSALITY ENDPOINTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get causality links for artifacts produced by an order.
 */
export async function getCausalityForOrder(
  pacId: string,
  orderId: string
): Promise<CausalityLinkDTO[]> {
  return fetchJson<CausalityLinkDTO[]>(
    `${API_BASE}/causality/${pacId}/order/${orderId}`
  );
}

/**
 * Trace causality chain for an artifact.
 */
export async function traceCausality(artifactId: string): Promise<CausalityTraceDTO> {
  return fetchJson<CausalityTraceDTO>(`${API_BASE}/causality/trace/${artifactId}`);
}

// ═══════════════════════════════════════════════════════════════════════════════
// NON-CAPABILITIES ENDPOINTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get all non-capabilities.
 */
export async function getNonCapabilities(): Promise<NonCapabilitiesListDTO> {
  return fetchJson<NonCapabilitiesListDTO>(`${API_BASE}/non-capabilities`);
}

/**
 * Get non-capabilities by category.
 */
export async function getNonCapabilitiesByCategory(
  category: string
): Promise<NonCapabilityDTO[]> {
  return fetchJson<NonCapabilityDTO[]>(
    `${API_BASE}/non-capabilities/category/${category}`
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// FAILURE SEMANTICS ENDPOINTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get failure semantics reference.
 */
export async function getFailureSemantics(): Promise<FailureSemanticsDTO> {
  return fetchJson<FailureSemanticsDTO>(`${API_BASE}/failure-semantics`);
}

// ═══════════════════════════════════════════════════════════════════════════════
// SUMMARY ENDPOINTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get governance summary.
 */
export async function getGovernanceSummary(): Promise<GovernanceSummaryDTO> {
  return fetchJson<GovernanceSummaryDTO>(`${API_BASE}/summary`);
}

/**
 * Get governance invariants.
 */
export async function getGovernanceInvariants(): Promise<GovernanceInvariantsDTO> {
  return fetchJson<GovernanceInvariantsDTO>(`${API_BASE}/invariants`);
}
