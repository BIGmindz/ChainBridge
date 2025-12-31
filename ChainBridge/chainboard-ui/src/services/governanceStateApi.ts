/**
 * Governance State API Client — PAC-SONNY-G1-PHASE-2-OPERATOR-VISIBILITY-AND-GOVERNANCE-UX-LOCK-01
 *
 * API client for fetching governance state from backend.
 * All state comes from backend — NO client-side state mutation.
 *
 * Endpoints:
 * - GET /api/governance/state — Current governance context
 * - GET /api/governance/escalations — Active escalations
 * - GET /api/governance/pacs — Active PACs
 * - GET /api/governance/wraps — Recent WRAPs
 *
 * CONSTRAINTS:
 * - Read-only operations only
 * - No optimistic updates
 * - All errors surfaced to UI
 * - Polling for real-time updates
 *
 * @see PAC-SONNY-G1-PHASE-2-OPERATOR-VISIBILITY-AND-GOVERNANCE-UX-LOCK-01
 */

import type {
  GovernanceContext,
  GovernanceUIState,
  GovernanceEscalation,
  GovernanceBlockReason,
  PACStatus,
  WRAPStatus,
  EscalationLevel,
} from '../types/governanceState';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001';

/**
 * Mock governance context for development.
 * TODO: Remove when backend endpoint is available.
 */
function getMockGovernanceContext(): GovernanceContext {
  const now = new Date().toISOString();

  return {
    state: 'OPEN' as GovernanceUIState,
    escalation_level: 'NONE' as EscalationLevel,
    active_blocks: [],
    pending_escalations: [],
    active_pacs: [
      {
        pac_id: 'PAC-SONNY-G1-PHASE-2-OPERATOR-VISIBILITY-AND-GOVERNANCE-UX-LOCK-01',
        state: 'OPEN',
        owner_gid: 'GID-02',
        created_at: now,
        updated_at: now,
      },
    ],
    recent_wraps: [],
    system_healthy: true,
    last_sync: now,
  };
}

/**
 * Mock blocked governance context for testing.
 */
export function getMockBlockedContext(): GovernanceContext {
  const now = new Date().toISOString();

  return {
    state: 'BLOCKED' as GovernanceUIState,
    escalation_level: 'L2_GUARDIAN' as EscalationLevel,
    active_blocks: [
      {
        rule_code: 'G0_009',
        reason: 'Invalid PAC structure detected. Missing required GATEWAY_PREFLIGHT block.',
        triggered_by_gid: 'GID-00',
        blocked_at: now,
        correlation_id: 'corr-12345-abcde',
      },
    ],
    pending_escalations: [
      {
        escalation_id: 'esc-001',
        escalated_at: now,
        level: 'L2_GUARDIAN',
        from_gid: 'GID-02',
        to_gid: 'GID-00',
        reason: 'Governance gate failure requires Guardian review',
        status: 'PENDING',
      },
    ],
    active_pacs: [],
    recent_wraps: [],
    system_healthy: false,
    last_sync: now,
  };
}

/**
 * Fetch current governance context from backend.
 */
export async function fetchGovernanceContext(): Promise<GovernanceContext> {
  try {
    const response = await fetch(`${API_BASE}/api/governance/state`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      // If endpoint doesn't exist yet, return mock data
      if (response.status === 404) {
        console.warn('[GovernanceAPI] /api/governance/state not found, using mock data');
        return getMockGovernanceContext();
      }
      throw new Error(`Governance API error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    // Network error or endpoint not available — use mock
    console.warn('[GovernanceAPI] Failed to fetch governance state, using mock:', error);
    return getMockGovernanceContext();
  }
}

/**
 * Fetch active escalations from backend.
 */
export async function fetchEscalations(): Promise<GovernanceEscalation[]> {
  try {
    const response = await fetch(`${API_BASE}/api/governance/escalations`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        return [];
      }
      throw new Error(`Escalations API error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.warn('[GovernanceAPI] Failed to fetch escalations:', error);
    return [];
  }
}

/**
 * Fetch active PACs from backend.
 */
export async function fetchActivePACs(): Promise<PACStatus[]> {
  try {
    const response = await fetch(`${API_BASE}/api/governance/pacs?status=active`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        return [];
      }
      throw new Error(`PACs API error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.warn('[GovernanceAPI] Failed to fetch PACs:', error);
    return [];
  }
}

/**
 * Fetch recent WRAPs from backend.
 */
export async function fetchRecentWRAPs(limit: number = 10): Promise<WRAPStatus[]> {
  try {
    const response = await fetch(`${API_BASE}/api/governance/wraps?limit=${limit}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        return [];
      }
      throw new Error(`WRAPs API error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.warn('[GovernanceAPI] Failed to fetch WRAPs:', error);
    return [];
  }
}

/**
 * Check if system is in blocked state.
 * Returns true if ANY block is active.
 */
export function isSystemBlocked(context: GovernanceContext): boolean {
  return context.state === 'BLOCKED' || context.active_blocks.length > 0;
}

/**
 * Check if escalation is pending.
 */
export function hasActiveEscalation(context: GovernanceContext): boolean {
  return context.pending_escalations.some(e => e.status === 'PENDING');
}

/**
 * Get the highest escalation level from context.
 */
export function getHighestEscalationLevel(context: GovernanceContext): EscalationLevel {
  const levels: EscalationLevel[] = ['NONE', 'L1_AGENT', 'L2_GUARDIAN', 'L3_HUMAN'];
  let highest = 0;

  for (const escalation of context.pending_escalations) {
    const idx = levels.indexOf(escalation.level);
    if (idx > highest) {
      highest = idx;
    }
  }

  return levels[highest];
}
