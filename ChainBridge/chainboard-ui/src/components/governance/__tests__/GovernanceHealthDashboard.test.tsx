/**
 * Governance Health Dashboard Tests — PAC-SONNY-P01-GOVERNANCE-HEALTH-DASHBOARD-01
 *
 * Tests for the Governance Health Dashboard components.
 * Verifies read-only rendering and data binding.
 *
 * @see PAC-SONNY-P01-GOVERNANCE-HEALTH-DASHBOARD-01
 */

import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

import { GovernanceHealthDashboard } from '../GovernanceHealthDashboard';
import { GovernanceHealthMetricsPanel } from '../GovernanceHealthMetrics';
import { SettlementFlowDiagram, CanonicalSettlementFlow } from '../SettlementFlowDiagram';
import { ArtifactStatusTimeline } from '../ArtifactStatusTimeline';
import { EnterpriseComplianceSummaryPanel } from '../EnterpriseComplianceSummary';
import type {
  GovernanceHealthMetrics,
  SettlementChain,
  EnterpriseComplianceSummary,
} from '../../../types/governanceHealth';

// Mock data
const mockMetrics: GovernanceHealthMetrics = {
  totalPacs: 50,
  activePacs: 10,
  blockedPacs: 2,
  positiveClosures: 35,
  totalBers: 40,
  pendingBers: 3,
  approvedBers: 37,
  totalPdos: 37,
  finalizedPdos: 35,
  totalWraps: 35,
  acceptedWraps: 33,
  settlementRate: 92.5,
  avgSettlementTimeMs: 180000,
  pendingSettlements: 5,
  ledgerIntegrity: 'HEALTHY',
  lastLedgerSync: new Date().toISOString(),
  sequenceGaps: 0,
};

const mockChain: SettlementChain = {
  chainId: 'test-chain-001',
  pacId: 'PAC-TEST-P01-GOVERNANCE-TEST-01',
  berId: 'BER-TEST-P01-20251226',
  currentStage: 'HUMAN_REVIEW',
  status: 'IN_PROGRESS',
  startedAt: new Date().toISOString(),
  nodes: [
    { stage: 'PAC_DISPATCH', status: 'FINALIZED', artifactId: 'PAC-TEST-P01' },
    { stage: 'AGENT_EXECUTION', status: 'FINALIZED' },
    { stage: 'BER_GENERATION', status: 'FINALIZED', artifactId: 'BER-TEST-P01' },
    { stage: 'HUMAN_REVIEW', status: 'AWAITING_REVIEW' },
    { stage: 'PDO_FINALIZATION', status: 'PENDING' },
    { stage: 'WRAP_GENERATION', status: 'PENDING' },
    { stage: 'WRAP_ACCEPTED', status: 'PENDING' },
    { stage: 'LEDGER_COMMIT', status: 'PENDING' },
  ],
};

const mockComplianceSummary: EnterpriseComplianceSummary = {
  mappings: [
    { framework: 'SOX', control: '§302', description: 'Scope Definition', artifact: 'PAC' },
    { framework: 'SOC2', control: 'CC6.1', description: 'Change Control', artifact: 'PAC' },
  ],
  lastAuditDate: '2025-12-20',
  complianceScore: 96,
  frameworkCoverage: {
    sox: 100,
    soc2: 100,
    nist: 100,
    iso27001: 100,
  },
};

describe('GovernanceHealthDashboard', () => {
  it('renders without crashing', async () => {
    render(<GovernanceHealthDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Governance Health Dashboard')).toBeInTheDocument();
    });
  });

  it('displays Doctrine V1.1 reference', async () => {
    render(<GovernanceHealthDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/Doctrine V1.1/)).toBeInTheDocument();
    });
  });

  it('shows BENSON authority in footer', async () => {
    render(<GovernanceHealthDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/BENSON.*GID-00.*Authority/)).toBeInTheDocument();
    });
  });
});

describe('GovernanceHealthMetricsPanel', () => {
  it('renders all metric cards', () => {
    render(<GovernanceHealthMetricsPanel metrics={mockMetrics} />);

    expect(screen.getByText('Total PACs')).toBeInTheDocument();
    expect(screen.getByText('Settlement Rate')).toBeInTheDocument();
    expect(screen.getByText('Avg Settlement')).toBeInTheDocument();
    expect(screen.getByText('Ledger Integrity')).toBeInTheDocument();
  });

  it('displays correct metric values', () => {
    render(<GovernanceHealthMetricsPanel metrics={mockMetrics} />);

    expect(screen.getByText('50')).toBeInTheDocument(); // totalPacs
    expect(screen.getByText('92.5%')).toBeInTheDocument(); // settlementRate
    expect(screen.getByText('HEALTHY')).toBeInTheDocument(); // ledgerIntegrity
  });

  it('shows blocked PACs warning when present', () => {
    render(<GovernanceHealthMetricsPanel metrics={mockMetrics} />);

    expect(screen.getByText(/2 blocked/)).toBeInTheDocument();
  });

  it('displays secondary metrics', () => {
    render(<GovernanceHealthMetricsPanel metrics={mockMetrics} />);

    expect(screen.getByText('BERs Generated')).toBeInTheDocument();
    expect(screen.getByText('PDOs Finalized')).toBeInTheDocument();
    expect(screen.getByText('WRAPs Accepted')).toBeInTheDocument();
    expect(screen.getByText('Positive Closures')).toBeInTheDocument();
  });
});

describe('SettlementFlowDiagram', () => {
  it('renders chain with correct status', () => {
    render(<SettlementFlowDiagram chain={mockChain} />);

    expect(screen.getByText('IN_PROGRESS')).toBeInTheDocument();
  });

  it('displays PAC ID', () => {
    render(<SettlementFlowDiagram chain={mockChain} />);

    expect(screen.getByText(mockChain.pacId)).toBeInTheDocument();
  });

  it('shows artifact badges', () => {
    render(<SettlementFlowDiagram chain={mockChain} />);

    expect(screen.getByText(/BER:/)).toBeInTheDocument();
  });

  it('renders compact mode', () => {
    render(<SettlementFlowDiagram chain={mockChain} compact />);

    // In compact mode, we should see progress percentage
    expect(screen.getByText(/\d+%/)).toBeInTheDocument();
  });
});

describe('CanonicalSettlementFlow', () => {
  it('renders canonical flow diagram', () => {
    render(<CanonicalSettlementFlow />);

    expect(screen.getByText(/Canonical Settlement Flow/)).toBeInTheDocument();
  });

  it('displays all settlement stages', () => {
    render(<CanonicalSettlementFlow />);

    expect(screen.getByText('PAC')).toBeInTheDocument();
    expect(screen.getByText('Agent')).toBeInTheDocument();
    expect(screen.getByText('BER')).toBeInTheDocument();
    expect(screen.getByText('Human')).toBeInTheDocument();
    expect(screen.getByText('PDO')).toBeInTheDocument();
    expect(screen.getByText('WRAP')).toBeInTheDocument();
    expect(screen.getByText('Accepted')).toBeInTheDocument();
  });

  it('shows authority statement', () => {
    render(<CanonicalSettlementFlow />);

    expect(screen.getByText(/BENSON.*GID-00/)).toBeInTheDocument();
    expect(screen.getByText(/No WRAP without PDO/)).toBeInTheDocument();
  });
});

describe('ArtifactStatusTimeline', () => {
  it('renders empty state when no chains', () => {
    render(<ArtifactStatusTimeline chains={[]} />);

    expect(screen.getByText('No settlement chains in progress')).toBeInTheDocument();
  });

  it('renders timeline entries', () => {
    render(<ArtifactStatusTimeline chains={[mockChain]} />);

    expect(screen.getByText('Settlement Timeline')).toBeInTheDocument();
    expect(screen.getByText('1 chains')).toBeInTheDocument();
  });

  it('displays chain status', () => {
    render(<ArtifactStatusTimeline chains={[mockChain]} />);

    expect(screen.getByText('IN_PROGRESS')).toBeInTheDocument();
  });
});

describe('EnterpriseComplianceSummaryPanel', () => {
  it('renders compliance score', () => {
    render(<EnterpriseComplianceSummaryPanel summary={mockComplianceSummary} />);

    expect(screen.getByText('96%')).toBeInTheDocument();
  });

  it('displays framework cards', () => {
    render(<EnterpriseComplianceSummaryPanel summary={mockComplianceSummary} />);

    expect(screen.getByText('SOX')).toBeInTheDocument();
    expect(screen.getByText('SOC 2')).toBeInTheDocument();
    expect(screen.getByText('NIST CSF')).toBeInTheDocument();
    expect(screen.getByText('ISO 27001')).toBeInTheDocument();
  });

  it('shows artifact mapping table', () => {
    render(<EnterpriseComplianceSummaryPanel summary={mockComplianceSummary} />);

    expect(screen.getByText('Artifact → Framework Mapping (Doctrine V1.1)')).toBeInTheDocument();
  });

  it('displays last audit date', () => {
    render(<EnterpriseComplianceSummaryPanel summary={mockComplianceSummary} />);

    expect(screen.getByText(/Last audit: 2025-12-20/)).toBeInTheDocument();
  });
});

describe('Read-Only Invariants', () => {
  it('GovernanceHealthDashboard has no write operations', () => {
    const { container } = render(<GovernanceHealthDashboard />);

    // Should not have any form inputs
    const inputs = container.querySelectorAll('input[type="text"], textarea');
    expect(inputs.length).toBe(0);

    // Should not have any submit buttons
    const submitButtons = container.querySelectorAll('button[type="submit"]');
    expect(submitButtons.length).toBe(0);
  });

  it('Metrics panel is display-only', () => {
    const { container } = render(<GovernanceHealthMetricsPanel metrics={mockMetrics} />);

    // No interactive elements that could trigger writes
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBe(0);
  });
});
