/**
 * Governance Ledger API — PAC-SONNY-G2-PHASE-2-GOVERNANCE-LEDGER-VISIBILITY-AND-OC-INTEGRATION-01
 *
 * API client for fetching governance ledger and PAC registry.
 * All operations are READ-ONLY — no client-side mutations.
 *
 * GUARANTEES:
 * - append_only: Ledger entries are never modified
 * - monotonic_sequence: Sequence numbers always increase
 * - closure_type_explicit: Every entry has explicit closure type
 *
 * @see PAC-SONNY-G2-PHASE-2-GOVERNANCE-LEDGER-VISIBILITY-AND-OC-INTEGRATION-01
 */

import type {
  GovernanceLedger,
  PACRegistry,
  PACRegistryEntry,
  GovernanceSummary,
  LedgerEntry,
  TimelineNode,
  CorrectionRecord,
  ViolationRecord,
} from '../types/governanceLedger';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001';

/**
 * Mock ledger entries for development.
 */
function getMockLedgerEntries(): LedgerEntry[] {
  const now = new Date();
  const entries: LedgerEntry[] = [];

  // PAC-SONNY-G1 lifecycle
  const pacId = 'PAC-SONNY-G1-PHASE-2-OPERATOR-VISIBILITY-AND-GOVERNANCE-UX-LOCK-01';
  const wrapId = 'WRAP-SONNY-G1-PHASE-2-GOVERNANCE-UX-LOCK-01';

  entries.push({
    entry_id: 'led-001',
    sequence: 1,
    type: 'PAC_CREATED',
    timestamp: new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    pac_id: pacId,
    agent_gid: 'GID-02',
    agent_name: 'SONNY',
    agent_color: 'YELLOW',
    description: 'PAC created for Governance UX implementation',
    correlation_id: 'corr-001',
  });

  entries.push({
    entry_id: 'led-002',
    sequence: 2,
    type: 'PAC_STARTED',
    timestamp: new Date(now.getTime() - 6 * 24 * 60 * 60 * 1000).toISOString(),
    pac_id: pacId,
    agent_gid: 'GID-02',
    agent_name: 'SONNY',
    agent_color: 'YELLOW',
    description: 'PAC execution started',
    correlation_id: 'corr-002',
  });

  entries.push({
    entry_id: 'led-003',
    sequence: 3,
    type: 'WRAP_SUBMITTED',
    timestamp: new Date(now.getTime() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    pac_id: pacId,
    wrap_id: wrapId,
    agent_gid: 'GID-02',
    agent_name: 'SONNY',
    agent_color: 'YELLOW',
    description: 'WRAP submitted for validation',
    correlation_id: 'corr-003',
  });

  entries.push({
    entry_id: 'led-004',
    sequence: 4,
    type: 'CORRECTION_ISSUED',
    timestamp: new Date(now.getTime() - 4 * 24 * 60 * 60 * 1000).toISOString(),
    pac_id: pacId,
    wrap_id: wrapId,
    agent_gid: 'GID-00',
    agent_name: 'BENSON',
    agent_color: 'RED',
    description: 'CORRECTION-01: Missing Gold Standard Checklist',
    metadata: {
      correction_version: 1,
      violations: ['G0_020', 'G0_021', 'G0_022'],
    },
    correlation_id: 'corr-004',
  });

  entries.push({
    entry_id: 'led-005',
    sequence: 5,
    type: 'CORRECTION_APPLIED',
    timestamp: new Date(now.getTime() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    pac_id: pacId,
    wrap_id: wrapId,
    agent_gid: 'GID-02',
    agent_name: 'SONNY',
    agent_color: 'YELLOW',
    description: 'CORRECTION-01 applied',
    correlation_id: 'corr-005',
  });

  entries.push({
    entry_id: 'led-006',
    sequence: 6,
    type: 'CORRECTION_ISSUED',
    timestamp: new Date(now.getTime() - 2.5 * 24 * 60 * 60 * 1000).toISOString(),
    pac_id: pacId,
    wrap_id: wrapId,
    agent_gid: 'GID-00',
    agent_name: 'BENSON',
    agent_color: 'RED',
    description: 'CORRECTION-02: Missing activation ACKs',
    metadata: {
      correction_version: 2,
      violations: ['G0_023'],
    },
    correlation_id: 'corr-006',
  });

  entries.push({
    entry_id: 'led-007',
    sequence: 7,
    type: 'CORRECTION_APPLIED',
    timestamp: new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    pac_id: pacId,
    wrap_id: wrapId,
    agent_gid: 'GID-02',
    agent_name: 'SONNY',
    agent_color: 'YELLOW',
    description: 'CORRECTION-02 applied',
    correlation_id: 'corr-007',
  });

  entries.push({
    entry_id: 'led-008',
    sequence: 8,
    type: 'CORRECTION_ISSUED',
    timestamp: new Date(now.getTime() - 1.5 * 24 * 60 * 60 * 1000).toISOString(),
    pac_id: pacId,
    wrap_id: wrapId,
    agent_gid: 'GID-00',
    agent_name: 'BENSON',
    agent_color: 'RED',
    description: 'CORRECTION-03: Missing closure authority',
    metadata: {
      correction_version: 3,
      violations: ['G0_024'],
    },
    correlation_id: 'corr-008',
  });

  entries.push({
    entry_id: 'led-009',
    sequence: 9,
    type: 'CORRECTION_APPLIED',
    timestamp: new Date(now.getTime() - 1 * 24 * 60 * 60 * 1000).toISOString(),
    pac_id: pacId,
    wrap_id: wrapId,
    agent_gid: 'GID-02',
    agent_name: 'SONNY',
    agent_color: 'YELLOW',
    description: 'CORRECTION-03 applied',
    correlation_id: 'corr-009',
  });

  entries.push({
    entry_id: 'led-010',
    sequence: 10,
    type: 'WRAP_VALIDATED',
    timestamp: new Date(now.getTime() - 12 * 60 * 60 * 1000).toISOString(),
    pac_id: pacId,
    wrap_id: wrapId,
    agent_gid: 'SYSTEM',
    agent_name: 'GATE_PACK',
    agent_color: 'GRAY',
    description: 'WRAP validated — Gold Standard compliance confirmed',
    correlation_id: 'corr-010',
  });

  entries.push({
    entry_id: 'led-011',
    sequence: 11,
    type: 'RATIFICATION_REQUESTED',
    timestamp: new Date(now.getTime() - 6 * 60 * 60 * 1000).toISOString(),
    pac_id: pacId,
    wrap_id: wrapId,
    agent_gid: 'GID-02',
    agent_name: 'SONNY',
    agent_color: 'YELLOW',
    description: 'Ratification requested from BENSON (GID-00)',
    correlation_id: 'corr-011',
  });

  entries.push({
    entry_id: 'led-012',
    sequence: 12,
    type: 'RATIFICATION_APPROVED',
    timestamp: new Date(now.getTime() - 3 * 60 * 60 * 1000).toISOString(),
    pac_id: pacId,
    wrap_id: wrapId,
    agent_gid: 'GID-00',
    agent_name: 'BENSON',
    agent_color: 'RED',
    description: 'Ratification approved',
    correlation_id: 'corr-012',
  });

  entries.push({
    entry_id: 'led-013',
    sequence: 13,
    type: 'POSITIVE_CLOSURE',
    timestamp: new Date(now.getTime() - 1 * 60 * 60 * 1000).toISOString(),
    pac_id: pacId,
    wrap_id: wrapId,
    agent_gid: 'GID-00',
    agent_name: 'BENSON',
    agent_color: 'RED',
    description: 'POSITIVE CLOSURE — Governance acknowledged',
    metadata: {
      closure_type: 'POSITIVE_CLOSURE',
      violations_resolved: 5,
      correction_cycles: 3,
    },
    correlation_id: 'corr-013',
  });

  return entries;
}

/**
 * Mock PAC registry entry.
 */
function getMockPACRegistryEntry(): PACRegistryEntry {
  const now = new Date();
  const pacId = 'PAC-SONNY-G1-PHASE-2-OPERATOR-VISIBILITY-AND-GOVERNANCE-UX-LOCK-01';
  const wrapId = 'WRAP-SONNY-G1-PHASE-2-GOVERNANCE-UX-LOCK-01';

  const corrections: CorrectionRecord[] = [
    {
      correction_pac_id: 'PAC-SONNY-G1-PHASE-2-GOVERNANCE-UX-CORRECTION-01',
      correction_version: 1,
      violations_addressed: [
        { violation_id: 'G0_020', description: 'Missing Gold Standard Checklist', resolved: true, resolution: 'Checklist added' },
        { violation_id: 'G0_021', description: 'No explicit correction class', resolved: true, resolution: 'CORRECTION_CLASS declared' },
        { violation_id: 'G0_022', description: 'Missing self-certification', resolved: true, resolution: 'Self-certification added' },
      ],
      status: 'APPLIED',
      applied_at: new Date(now.getTime() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    },
    {
      correction_pac_id: 'PAC-SONNY-G1-PHASE-2-GOVERNANCE-UX-CORRECTION-02',
      correction_version: 2,
      violations_addressed: [
        { violation_id: 'G0_023', description: 'Missing doctrine linkage', resolved: true, resolution: 'TRAINING_SIGNAL doctrine mutation declared' },
      ],
      status: 'APPLIED',
      applied_at: new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    },
    {
      correction_pac_id: 'PAC-SONNY-G1-PHASE-2-GOVERNANCE-UX-CORRECTION-03',
      correction_version: 3,
      violations_addressed: [
        { violation_id: 'G0_024', description: 'No closure authority', resolved: true, resolution: 'CORRECTION_CLOSURE declared' },
      ],
      status: 'APPLIED',
      applied_at: new Date(now.getTime() - 1 * 24 * 60 * 60 * 1000).toISOString(),
    },
  ];

  return {
    pac_id: pacId,
    title: 'Operator Visibility and Governance UX',
    state: 'POSITIVE_CLOSURE',
    closure_type: 'POSITIVE_CLOSURE',
    owner_gid: 'GID-02',
    owner_name: 'SONNY',
    owner_color: 'YELLOW',
    created_at: new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(now.getTime() - 1 * 60 * 60 * 1000).toISOString(),
    closed_at: new Date(now.getTime() - 1 * 60 * 60 * 1000).toISOString(),
    closure_authority_gid: 'GID-00',
    closure_authority_name: 'BENSON',
    wrap_ids: [wrapId],
    corrections,
    active_violations: [],
    ledger_entries: getMockLedgerEntries(),
  };
}

/**
 * Mock blocked PAC entry.
 */
function getMockBlockedPACEntry(): PACRegistryEntry {
  const now = new Date();
  const pacId = 'PAC-DAN-G1-PHASE-2-GOVERNANCE-FAILURE-DRILLS-01';

  const violations: ViolationRecord[] = [
    { violation_id: 'G0_030', description: 'Invalid closure semantics', resolved: false },
  ];

  return {
    pac_id: pacId,
    title: 'Governance Failure Drills',
    state: 'BLOCKED',
    closure_type: 'NONE',
    owner_gid: 'GID-07',
    owner_name: 'DAN',
    owner_color: 'GREEN',
    created_at: new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: now.toISOString(),
    wrap_ids: [],
    corrections: [],
    active_violations: violations,
    ledger_entries: [
      {
        entry_id: 'led-b01',
        sequence: 1,
        type: 'PAC_CREATED',
        timestamp: new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000).toISOString(),
        pac_id: pacId,
        agent_gid: 'GID-07',
        agent_name: 'DAN',
        agent_color: 'GREEN',
        description: 'PAC created for Governance Failure Drills',
        correlation_id: 'corr-b01',
      },
      {
        entry_id: 'led-b02',
        sequence: 2,
        type: 'PAC_BLOCKED',
        timestamp: now.toISOString(),
        pac_id: pacId,
        agent_gid: 'SYSTEM',
        agent_name: 'GATE_PACK',
        agent_color: 'GRAY',
        description: 'PAC blocked — Invalid closure semantics [G0_030]',
        metadata: { violations: ['G0_030'] },
        correlation_id: 'corr-b02',
      },
    ],
  };
}

/**
 * Fetch governance ledger from backend.
 */
export async function fetchGovernanceLedger(): Promise<GovernanceLedger> {
  const useMock = import.meta.env.VITE_USE_MOCK_DATA === 'true' || !import.meta.env.VITE_API_BASE_URL;

  if (useMock) {
    const entries = getMockLedgerEntries();
    return {
      entries,
      total_entries: entries.length,
      latest_sequence: entries[entries.length - 1]?.sequence || 0,
      last_sync: new Date().toISOString(),
    };
  }

  const response = await fetch(`${API_BASE}/api/governance/ledger`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch governance ledger: ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch PAC registry from backend.
 */
export async function fetchPACRegistry(): Promise<PACRegistry> {
  const useMock = import.meta.env.VITE_USE_MOCK_DATA === 'true' || !import.meta.env.VITE_API_BASE_URL;

  if (useMock) {
    const pacs = [getMockPACRegistryEntry(), getMockBlockedPACEntry()];
    return {
      pacs,
      total_pacs: pacs.length,
      active_pacs: pacs.filter(p => p.state !== 'POSITIVE_CLOSURE' && p.state !== 'ARCHIVED').length,
      blocked_pacs: pacs.filter(p => p.state === 'BLOCKED').length,
      positive_closures: pacs.filter(p => p.closure_type === 'POSITIVE_CLOSURE').length,
      last_sync: new Date().toISOString(),
    };
  }

  const response = await fetch(`${API_BASE}/api/governance/registry`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch PAC registry: ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch single PAC by ID.
 */
export async function fetchPACById(pacId: string): Promise<PACRegistryEntry | null> {
  const useMock = import.meta.env.VITE_USE_MOCK_DATA === 'true' || !import.meta.env.VITE_API_BASE_URL;

  if (useMock) {
    const mockPac = getMockPACRegistryEntry();
    if (mockPac.pac_id === pacId) return mockPac;
    const blockedPac = getMockBlockedPACEntry();
    if (blockedPac.pac_id === pacId) return blockedPac;
    return null;
  }

  const response = await fetch(`${API_BASE}/api/governance/pacs/${encodeURIComponent(pacId)}`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (response.status === 404) return null;
  if (!response.ok) {
    throw new Error(`Failed to fetch PAC: ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch governance summary.
 */
export async function fetchGovernanceSummary(): Promise<GovernanceSummary> {
  const useMock = import.meta.env.VITE_USE_MOCK_DATA === 'true' || !import.meta.env.VITE_API_BASE_URL;

  if (useMock) {
    const entries = getMockLedgerEntries();
    return {
      total_pacs: 2,
      active_pacs: 1,
      blocked_pacs: 1,
      correction_cycles: 0,
      positive_closures: 1,
      pending_ratifications: 0,
      system_healthy: true,
      last_activity: entries[entries.length - 1]?.timestamp || new Date().toISOString(),
    };
  }

  const response = await fetch(`${API_BASE}/api/governance/summary`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch governance summary: ${response.status}`);
  }

  return response.json();
}

/**
 * Convert ledger entries to timeline nodes.
 */
export function ledgerToTimeline(entries: LedgerEntry[]): TimelineNode[] {
  return entries.map((entry): TimelineNode => {
    let status: TimelineNode['status'] = 'info';
    let isCorrection = false;
    let isClosure = false;
    let closureType: TimelineNode['closure_type'];

    switch (entry.type) {
      case 'POSITIVE_CLOSURE':
        status = 'success';
        isClosure = true;
        closureType = 'POSITIVE_CLOSURE';
        break;
      case 'NEGATIVE_CLOSURE':
        status = 'error';
        isClosure = true;
        closureType = 'NEGATIVE_CLOSURE';
        break;
      case 'CORRECTION_ISSUED':
      case 'CORRECTION_APPLIED':
        status = 'warning';
        isCorrection = true;
        break;
      case 'PAC_BLOCKED':
      case 'WRAP_REJECTED':
      case 'RATIFICATION_DENIED':
        status = 'blocked';
        break;
      case 'RATIFICATION_APPROVED':
      case 'WRAP_VALIDATED':
        status = 'success';
        break;
      case 'ESCALATION_RAISED':
        status = 'warning';
        break;
      default:
        status = 'info';
    }

    return {
      id: entry.entry_id,
      type: entry.type,
      label: entry.description,
      timestamp: entry.timestamp,
      agent: {
        gid: entry.agent_gid,
        name: entry.agent_name,
        color: entry.agent_color,
      },
      is_correction: isCorrection,
      is_closure: isClosure,
      closure_type: closureType,
      status,
    };
  });
}
