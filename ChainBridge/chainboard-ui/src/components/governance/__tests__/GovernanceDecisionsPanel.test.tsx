/**
 * Governance Decisions Panel Tests
 *
 * Component-level tests for the governance decisions panel including
 * filtering, search, and detail drawer functionality.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { GovernanceDecisionsPanel } from '../GovernanceDecisionsPanel';
import { governanceDecisionsMock } from '../../../services/governanceDecisionsMock';

// Mock the governance decisions service
vi.mock('../../../services/governanceDecisionsMock', () => ({
  governanceDecisionsMock: {
    fetchGovernanceDecisions: vi.fn(),
  },
}));

const mockGovernanceDecisions = vi.mocked(governanceDecisionsMock);

describe('GovernanceDecisionsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Mock successful API response
    mockGovernanceDecisions.fetchGovernanceDecisions.mockResolvedValue({
      decisions: [
        {
          id: 'gd-0001',
          createdAt: '2025-12-01T08:00:00Z',
          decisionType: 'settlement_precheck',
          status: 'APPROVE',
          shipmentId: 'SHP-2025-0001',
          payerId: 'PAYER-001',
          payeeId: 'PAYEE-001',
          amount: 25000,
          currency: 'USD',
          corridor: 'US-MX',
          riskScore: 5.2,
          reasonCodes: ['ROUTINE_CHECK', 'COMPLIANCE_PASSED'],
          policiesApplied: ['GID-HGP-L1: Code = Cash'],
          economicJustification: 'Settlement approved within risk parameters.',
          agentId: 'GID-Kernel',
          gid: 'GID-01',
          gidVersion: '1.0',
        },
        {
          id: 'gd-0002',
          createdAt: '2025-12-01T07:30:00Z',
          decisionType: 'settlement_precheck',
          status: 'FREEZE',
          shipmentId: 'SHP-2025-0002',
          payerId: 'PAYER-002',
          payeeId: 'PAYEE-002',
          amount: 75000,
          currency: 'USD',
          corridor: 'CN-US',
          riskScore: 8.7,
          reasonCodes: ['HIGH_RISK_CORRIDOR', 'L3_SECURITY_THRESHOLD_EXCEEDED'],
          policiesApplied: ['GID-HGP-L3: Security > Speed', 'Risk Score >= 7.5 Threshold'],
          economicJustification: 'Risk score 8.7 exceeds L3 threshold. Manual Guardian review required.',
          agentId: 'GID-Kernel',
          gid: 'GID-01',
          gidVersion: '1.0',
        },
      ],
      total: 2,
      page: 1,
      limit: 50,
    });
  });

  it('renders governance decisions panel with header', async () => {
    render(<GovernanceDecisionsPanel />);

    expect(screen.getByText('Governance Decisions')).toBeInTheDocument();
    expect(screen.getByText(/GID-HGP v1.0/)).toBeInTheDocument();
    expect(screen.getByText(/FREEZE indicates ChainIQ Risk Score/)).toBeInTheDocument();
  });

  it('displays governance decisions in table format', async () => {
    render(<GovernanceDecisionsPanel />);

    await waitFor(() => {
      expect(screen.getByText('gd-0001')).toBeInTheDocument();
      expect(screen.getByText('gd-0002')).toBeInTheDocument();
    });

    expect(screen.getByText('SHP-2025-0001')).toBeInTheDocument();
    expect(screen.getByText('SHP-2025-0002')).toBeInTheDocument();
    expect(screen.getByText('$25,000')).toBeInTheDocument();
    expect(screen.getByText('$75,000')).toBeInTheDocument();
  });

  it('filters decisions by status', async () => {
    render(<GovernanceDecisionsPanel />);

    await waitFor(() => {
      expect(screen.getByText('gd-0001')).toBeInTheDocument();
    });

    // Click FREEZE filter
    fireEvent.click(screen.getByRole('button', { name: /FREEZE/ }));

    await waitFor(() => {
      expect(mockGovernanceDecisions.fetchGovernanceDecisions).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'FREEZE' }),
        1,
        50
      );
    });
  });

  it('handles search input', async () => {
    render(<GovernanceDecisionsPanel />);

    await waitFor(() => {
      expect(screen.getByText('gd-0001')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Search by shipment ID/);
    fireEvent.change(searchInput, { target: { value: 'SHP-2025-0001' } });

    await waitFor(() => {
      expect(mockGovernanceDecisions.fetchGovernanceDecisions).toHaveBeenCalledWith(
        expect.objectContaining({ searchQuery: 'SHP-2025-0001' }),
        1,
        50
      );
    });
  });

  it('opens detail drawer when decision is clicked', async () => {
    render(<GovernanceDecisionsPanel />);

    await waitFor(() => {
      expect(screen.getByText('gd-0001')).toBeInTheDocument();
    });

    // Click on the first decision
    fireEvent.click(screen.getByText('gd-0001').closest('div')!);

    // Check if drawer opens with decision details
    expect(screen.getByText('Economic Context')).toBeInTheDocument();
    expect(screen.getByText('Risk Assessment')).toBeInTheDocument();
    expect(screen.getByText('Reason Codes')).toBeInTheDocument();
  });

  it('displays status counts in filter buttons', async () => {
    render(<GovernanceDecisionsPanel />);

    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument(); // All Decisions count
    });

    // Should show individual status counts
    const approveButton = screen.getByRole('button', { name: /APPROVE/ });
    const freezeButton = screen.getByRole('button', { name: /FREEZE/ });

    expect(approveButton).toContainHTML('1'); // 1 APPROVE decision
    expect(freezeButton).toContainHTML('1'); // 1 FREEZE decision
  });

  it('handles API errors gracefully', async () => {
    mockGovernanceDecisions.fetchGovernanceDecisions.mockRejectedValue(
      new Error('API unavailable')
    );

    render(<GovernanceDecisionsPanel />);

    await waitFor(() => {
      expect(screen.getByText('Governance feed unavailable')).toBeInTheDocument();
      expect(screen.getByText('API unavailable')).toBeInTheDocument();
    });
  });
});
