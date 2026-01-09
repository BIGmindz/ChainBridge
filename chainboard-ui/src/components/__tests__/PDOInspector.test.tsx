/**
 * PDOInspector Component Tests
 * 
 * Tests for PDO Inspector and PDO Detail Page components.
 * Per PAC-BENSON-EXEC-GOVERNANCE-MULTI-AGENT-PDO-STRESS-023.
 * 
 * Agent: GID-02 (Sonny) — Frontend Engineer
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { PDOInspector, PDOArtifact } from '../PDOInspector';
import { PDODetailPage } from '../../pages/PDODetailPage';

// ═══════════════════════════════════════════════════════════════════════════════
// TEST DATA
// ═══════════════════════════════════════════════════════════════════════════════

const mockPDO: PDOArtifact = {
  pdo_id: 'PDO-TEST-001',
  pac_id: 'PAC-TEST-001',
  wrap_id: 'WRAP-TEST-001',
  ber_id: 'BER-TEST-001',
  issuer: 'GID-00',
  proof_hash: 'a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef12345678',
  decision_hash: 'b2c3d4e5f67890123456789012345678901234567890abcdef1234567890abcd',
  outcome_hash: 'c3d4e5f678901234567890123456789012345678901234567890abcdef123456',
  pdo_hash: 'd4e5f6789012345678901234567890123456789012345678901234567890abcdef',
  outcome_status: 'ACCEPTED',
  emitted_at: '2025-12-26T12:00:00.000Z',
  created_at: '2025-12-26T11:59:00.000Z',
};

const mockCorrective: PDOArtifact = {
  ...mockPDO,
  pdo_id: 'PDO-TEST-002',
  outcome_status: 'CORRECTIVE',
};

const mockRejected: PDOArtifact = {
  ...mockPDO,
  pdo_id: 'PDO-TEST-003',
  outcome_status: 'REJECTED',
};

// ═══════════════════════════════════════════════════════════════════════════════
// PDO INSPECTOR TESTS
// ═══════════════════════════════════════════════════════════════════════════════

describe('PDOInspector', () => {
  describe('Empty State', () => {
    it('should render empty state when no PDO provided', () => {
      render(<PDOInspector pdo={null} />);
      
      expect(screen.getByText('No PDO selected')).toBeInTheDocument();
      expect(screen.getByText(/Select a PDO from the list/)).toBeInTheDocument();
    });
  });

  describe('Loading State', () => {
    it('should render loading skeleton when loading', () => {
      render(<PDOInspector pdo={null} loading={true} />);
      
      expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Loading PDO data');
    });
  });

  describe('Error State', () => {
    it('should render error message when error provided', () => {
      render(<PDOInspector pdo={null} error="Failed to load PDO" />);
      
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText('Failed to load PDO')).toBeInTheDocument();
    });

    it('should show retry button when onRefresh provided', () => {
      const onRefresh = jest.fn();
      render(<PDOInspector pdo={null} error="Failed" onRefresh={onRefresh} />);
      
      const retryButton = screen.getByText('Retry');
      fireEvent.click(retryButton);
      
      expect(onRefresh).toHaveBeenCalled();
    });
  });

  describe('PDO Display', () => {
    it('should render PDO details', () => {
      render(<PDOInspector pdo={mockPDO} />);
      
      expect(screen.getByText('🧿 PDO Inspector')).toBeInTheDocument();
      expect(screen.getByText('PDO-TEST-001')).toBeInTheDocument();
      expect(screen.getByText('PAC-TEST-001')).toBeInTheDocument();
      expect(screen.getByText('BER-TEST-001')).toBeInTheDocument();
      expect(screen.getByText('GID-00')).toBeInTheDocument();
    });

    it('should render ACCEPTED status badge', () => {
      render(<PDOInspector pdo={mockPDO} />);
      
      const badge = screen.getByRole('status');
      expect(badge).toHaveTextContent('ACCEPTED');
      expect(badge).toHaveAttribute('aria-label', 'Outcome status: ACCEPTED');
    });

    it('should render CORRECTIVE status badge', () => {
      render(<PDOInspector pdo={mockCorrective} />);
      
      const badge = screen.getByRole('status');
      expect(badge).toHaveTextContent('CORRECTIVE');
    });

    it('should render REJECTED status badge', () => {
      render(<PDOInspector pdo={mockRejected} />);
      
      const badge = screen.getByRole('status');
      expect(badge).toHaveTextContent('REJECTED');
    });
  });

  describe('Hash Chain Display', () => {
    it('should display hash chain', () => {
      render(<PDOInspector pdo={mockPDO} />);
      
      expect(screen.getByText('Hash Chain')).toBeInTheDocument();
      expect(screen.getByText('1. Proof Hash')).toBeInTheDocument();
      expect(screen.getByText('2. Decision Hash')).toBeInTheDocument();
      expect(screen.getByText('3. Outcome Hash')).toBeInTheDocument();
      expect(screen.getByText('4. PDO Hash (Final)')).toBeInTheDocument();
    });

    it('should show valid hash chain indicator', () => {
      render(<PDOInspector pdo={mockPDO} />);
      
      expect(screen.getByText('✓ Valid')).toBeInTheDocument();
    });

    it('should truncate long hashes', () => {
      render(<PDOInspector pdo={mockPDO} />);
      
      // Hash should be truncated with ellipsis
      const hashElements = screen.getAllByRole('code');
      expect(hashElements[0].textContent).toContain('...');
    });
  });

  describe('Refresh Button', () => {
    it('should show refresh button when onRefresh provided', () => {
      const onRefresh = jest.fn();
      render(<PDOInspector pdo={mockPDO} onRefresh={onRefresh} />);
      
      const refreshButton = screen.getByText('🔄 Refresh');
      expect(refreshButton).toBeInTheDocument();
    });

    it('should call onRefresh when clicked', () => {
      const onRefresh = jest.fn();
      render(<PDOInspector pdo={mockPDO} onRefresh={onRefresh} />);
      
      fireEvent.click(screen.getByText('🔄 Refresh'));
      
      expect(onRefresh).toHaveBeenCalled();
    });

    it('should not show refresh button when onRefresh not provided', () => {
      render(<PDOInspector pdo={mockPDO} />);
      
      expect(screen.queryByText('🔄 Refresh')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      render(<PDOInspector pdo={mockPDO} />);
      
      const statusBadge = screen.getByRole('status');
      expect(statusBadge).toHaveAttribute('aria-label');
    });
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// PDO DETAIL PAGE TESTS
// ═══════════════════════════════════════════════════════════════════════════════

describe('PDODetailPage', () => {
  describe('Rendering', () => {
    it('should render page header', () => {
      render(<PDODetailPage />);
      
      expect(screen.getByText('🧿 PDO Artifacts')).toBeInTheDocument();
      expect(screen.getByText('Proof → Decision → Outcome Chain')).toBeInTheDocument();
    });

    it('should render PDO list sidebar', async () => {
      render(<PDODetailPage />);
      
      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument();
      });
    });

    it('should show back button when onNavigateBack provided', () => {
      const onNavigateBack = jest.fn();
      render(<PDODetailPage onNavigateBack={onNavigateBack} />);
      
      expect(screen.getByText('← Back')).toBeInTheDocument();
    });
  });

  describe('Navigation', () => {
    it('should call onNavigateBack when back button clicked', () => {
      const onNavigateBack = jest.fn();
      render(<PDODetailPage onNavigateBack={onNavigateBack} />);
      
      fireEvent.click(screen.getByText('← Back'));
      
      expect(onNavigateBack).toHaveBeenCalled();
    });

    it('should call onNavigateToPDO when PDO selected', async () => {
      const onNavigateToPDO = jest.fn();
      render(<PDODetailPage onNavigateToPDO={onNavigateToPDO} />);
      
      await waitFor(() => {
        expect(screen.getByText('PDO-PAC-023-001')).toBeInTheDocument();
      });
      
      fireEvent.click(screen.getByText('PDO-PAC-023-001'));
      
      await waitFor(() => {
        expect(onNavigateToPDO).toHaveBeenCalledWith('PDO-PAC-023-001');
      });
    });
  });

  describe('List Interaction', () => {
    it('should highlight selected PDO', async () => {
      render(<PDODetailPage />);
      
      await waitFor(() => {
        expect(screen.getByText('PDO-PAC-023-001')).toBeInTheDocument();
      });
      
      const firstItem = screen.getByText('PDO-PAC-023-001').closest('button');
      fireEvent.click(firstItem!);
      
      expect(firstItem).toHaveAttribute('aria-selected', 'true');
    });
  });

  describe('Refresh', () => {
    it('should have refresh list button', () => {
      render(<PDODetailPage />);
      
      expect(screen.getByText('🔄 Refresh List')).toBeInTheDocument();
    });
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// SNAPSHOT TESTS
// ═══════════════════════════════════════════════════════════════════════════════

describe('Snapshots', () => {
  it('should match snapshot for empty state', () => {
    const { container } = render(<PDOInspector pdo={null} />);
    expect(container).toMatchSnapshot();
  });

  it('should match snapshot for loaded PDO', () => {
    const { container } = render(<PDOInspector pdo={mockPDO} />);
    expect(container).toMatchSnapshot();
  });

  it('should match snapshot for error state', () => {
    const { container } = render(<PDOInspector pdo={null} error="Error message" />);
    expect(container).toMatchSnapshot();
  });
});
