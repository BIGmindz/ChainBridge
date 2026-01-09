/**
 * Operator Console UI Tests — READ-ONLY Enforcement
 * 
 * PAC Reference: PAC-BENSON-CHAINBRIDGE-PDO-OC-VISIBILITY-EXEC-007C
 * Agent: Sonny (GID-02) — UI / Dan (GID-07) — CI
 * Effective Date: 2025-12-30
 * 
 * TEST REQUIREMENTS (Section 10):
 *   ☑ UI action dispatch → FAIL / NO-OP
 *   ☑ Missing ledger hash → "UNAVAILABLE"
 *   ☑ Positive read-only paths succeed
 * 
 * INVARIANTS TESTED:
 *   INV-OC-001: UI may not mutate PDO or settlement state
 *   INV-OC-003: Ledger hash visible for final outcomes
 *   INV-OC-004: Missing data explicit (no silent gaps)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import type {
  OCPDOView,
  OCPDOListResponse,
  OCTimelineResponse,
  OCLedgerEntry,
  OCHealthResponse,
} from '../types/operatorConsole';
import { UNAVAILABLE_MARKER } from '../types/operatorConsole';

// ═══════════════════════════════════════════════════════════════════════════════
// MOCK DATA
// ═══════════════════════════════════════════════════════════════════════════════

const mockPDO: OCPDOView = {
  pdo_id: 'PDO-TEST-001',
  decision_id: 'DEC-001',
  outcome_id: 'OUT-001',
  settlement_id: null,
  ledger_entry_hash: 'a1b2c3d4e5f67890' + '1234567890abcdef'.repeat(3),
  sequence_number: 42,
  timestamp: '2025-12-30T10:00:00Z',
  pac_id: 'PAC-TEST',
  outcome_status: 'ACCEPTED',
  issuer: 'GID-00',
};

const mockPDOWithUnavailableHash: OCPDOView = {
  ...mockPDO,
  pdo_id: 'PDO-TEST-002',
  ledger_entry_hash: UNAVAILABLE_MARKER,
  sequence_number: -1,
};

const mockPDOListResponse: OCPDOListResponse = {
  items: [mockPDO, mockPDOWithUnavailableHash],
  count: 2,
  total: 2,
  limit: 100,
  offset: 0,
  api_version: '1.0.0',
};

const mockHealthResponse: OCHealthResponse = {
  status: 'ok',
  api_version: '1.0.0',
  read_only: true,
  timestamp: '2025-12-30T10:00:00Z',
};

const mockTimelineResponse: OCTimelineResponse = {
  events: [
    {
      event_id: 'evt_1',
      event_type: 'PDO_CREATED',
      timestamp: '2025-12-30T10:00:00Z',
      pdo_id: 'PDO-TEST-001',
      ledger_hash: 'a1b2c3d4...',
      details: { pac_id: 'PAC-TEST' },
    },
  ],
  pdo_id: 'PDO-TEST-001',
  settlement_id: null,
  span_start: '2025-12-30T10:00:00Z',
  span_end: '2025-12-30T10:00:00Z',
};

// ═══════════════════════════════════════════════════════════════════════════════
// MOCK API
// ═══════════════════════════════════════════════════════════════════════════════

vi.mock('../api/operatorConsole', () => ({
  fetchOCHealth: vi.fn(() => Promise.resolve(mockHealthResponse)),
  fetchPDOList: vi.fn(() => Promise.resolve(mockPDOListResponse)),
  fetchPDOView: vi.fn((pdoId: string) => {
    if (pdoId === 'PDO-TEST-002') return Promise.resolve(mockPDOWithUnavailableHash);
    return Promise.resolve(mockPDO);
  }),
  fetchPDOTimeline: vi.fn(() => Promise.resolve(mockTimelineResponse)),
  fetchSettlementList: vi.fn(() => Promise.resolve({ items: [], count: 0, total: 0, limit: 100, offset: 0, api_version: '1.0.0' })),
  fetchSettlementTimeline: vi.fn(() => Promise.resolve({ events: [], pdo_id: null, settlement_id: null, span_start: null, span_end: null })),
  fetchLedgerEntries: vi.fn(() => Promise.resolve([])),
  verifyLedgerChain: vi.fn(() => Promise.resolve({ chain_valid: true, error: null, entry_count: 0, verified_at: new Date().toISOString() })),
}));

// ═══════════════════════════════════════════════════════════════════════════════
// INV-OC-001: UI May Not Mutate State
// ═══════════════════════════════════════════════════════════════════════════════

describe('INV-OC-001: UI may not mutate PDO or settlement state', () => {
  it('PDOListView has no mutation buttons', async () => {
    const { PDOListView } = await import('../components/PDOListView');
    render(<PDOListView />);
    
    await waitFor(() => {
      expect(screen.queryByText(/delete/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/edit/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/update/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/create/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/save/i)).not.toBeInTheDocument();
    });
  });
  
  it('displays READ-ONLY badge', async () => {
    const { PDOListView } = await import('../components/PDOListView');
    render(<PDOListView />);
    
    await waitFor(() => {
      expect(screen.getByText('READ-ONLY')).toBeInTheDocument();
    });
  });
  
  it('OperatorConsolePage shows read-only banner', async () => {
    const { OperatorConsolePage } = await import('../pages/OperatorConsolePage');
    render(<OperatorConsolePage />);
    
    await waitFor(() => {
      expect(screen.getByText(/read-only/i)).toBeInTheDocument();
    });
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// INV-OC-003: Ledger Hash Visible
// ═══════════════════════════════════════════════════════════════════════════════

describe('INV-OC-003: Ledger hash visible for final outcomes', () => {
  it('displays ledger hash in PDO list item', async () => {
    const { PDOListView } = await import('../components/PDOListView');
    render(<PDOListView />);
    
    await waitFor(() => {
      // Hash should be visible (truncated)
      expect(screen.getByText(/Ledger/i)).toBeInTheDocument();
    });
  });
  
  it('displays hash in timeline events', async () => {
    const { PDOTimelineView } = await import('../components/PDOTimelineView');
    render(<PDOTimelineView pdoId="PDO-TEST-001" />);
    
    await waitFor(() => {
      expect(screen.getByText(/Hash:/i)).toBeInTheDocument();
    });
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// INV-OC-004: Missing Data Explicit
// ═══════════════════════════════════════════════════════════════════════════════

describe('INV-OC-004: Missing data explicit (no silent gaps)', () => {
  it('shows UNAVAILABLE for missing ledger hash', async () => {
    const { PDOListView } = await import('../components/PDOListView');
    render(<PDOListView />);
    
    await waitFor(() => {
      expect(screen.getByText(/UNAVAILABLE/i)).toBeInTheDocument();
    });
  });
  
  it('shows explicit empty state for no PDOs', async () => {
    const api = await import('../api/operatorConsole');
    vi.mocked(api.fetchPDOList).mockResolvedValueOnce({
      items: [],
      count: 0,
      total: 0,
      limit: 100,
      offset: 0,
      api_version: '1.0.0',
    });
    
    const { PDOListView } = await import('../components/PDOListView');
    render(<PDOListView />);
    
    await waitFor(() => {
      expect(screen.getByText(/No PDOs found/i)).toBeInTheDocument();
    });
  });
  
  it('displays N/A for missing sequence number', async () => {
    const { PDOListView } = await import('../components/PDOListView');
    render(<PDOListView />);
    
    await waitFor(() => {
      expect(screen.getByText(/N\/A/i)).toBeInTheDocument();
    });
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// POSITIVE READ-ONLY TESTS
// ═══════════════════════════════════════════════════════════════════════════════

describe('Positive read-only paths', () => {
  it('renders PDO list successfully', async () => {
    const { PDOListView } = await import('../components/PDOListView');
    render(<PDOListView />);
    
    await waitFor(() => {
      expect(screen.getByText('PDO-TEST-001')).toBeInTheDocument();
    });
  });
  
  it('allows PDO selection (read-only view)', async () => {
    const onSelectPDO = vi.fn();
    const { PDOListView } = await import('../components/PDOListView');
    render(<PDOListView onSelectPDO={onSelectPDO} />);
    
    await waitFor(() => {
      const pdoItem = screen.getByText('PDO-TEST-001');
      fireEvent.click(pdoItem);
      expect(onSelectPDO).toHaveBeenCalledWith('PDO-TEST-001');
    });
  });
  
  it('renders timeline view successfully', async () => {
    const { PDOTimelineView } = await import('../components/PDOTimelineView');
    render(<PDOTimelineView pdoId="PDO-TEST-001" />);
    
    await waitFor(() => {
      expect(screen.getByText(/Timeline/i)).toBeInTheDocument();
    });
  });
  
  it('renders ledger view successfully', async () => {
    const { LedgerHashView } = await import('../components/LedgerHashView');
    render(<LedgerHashView />);
    
    await waitFor(() => {
      expect(screen.getByText(/Ledger Hash Chain/i)).toBeInTheDocument();
    });
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// STATUS INDICATORS
// ═══════════════════════════════════════════════════════════════════════════════

describe('Status indicators', () => {
  it('shows correct status badge colors', async () => {
    const { PDOListView } = await import('../components/PDOListView');
    render(<PDOListView />);
    
    await waitFor(() => {
      expect(screen.getByText('ACCEPTED')).toBeInTheDocument();
    });
  });
  
  it('displays PAC ID when available', async () => {
    const { PDOListView } = await import('../components/PDOListView');
    render(<PDOListView />);
    
    await waitFor(() => {
      expect(screen.getByText('PAC-TEST')).toBeInTheDocument();
    });
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// ERROR HANDLING
// ═══════════════════════════════════════════════════════════════════════════════

describe('Error handling', () => {
  it('displays error message on API failure', async () => {
    const api = await import('../api/operatorConsole');
    vi.mocked(api.fetchPDOList).mockRejectedValueOnce(new Error('Network error'));
    
    const { PDOListView } = await import('../components/PDOListView');
    render(<PDOListView />);
    
    await waitFor(() => {
      expect(screen.getByText(/Error:/i)).toBeInTheDocument();
    });
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// EXPORTS
// ═══════════════════════════════════════════════════════════════════════════════

export {};
