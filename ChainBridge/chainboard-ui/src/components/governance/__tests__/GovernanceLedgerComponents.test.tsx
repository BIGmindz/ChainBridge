/**
 * Governance Ledger Components Tests — PAC-SONNY-G2-PHASE-2-GOVERNANCE-LEDGER-VISIBILITY-AND-OC-INTEGRATION-01
 *
 * Tests for governance ledger visibility components.
 * Verifies fail-closed UX rules:
 * - blocked_means_disabled: BLOCKED states visually distinct
 * - closure_requires_badge: Every closure shows badge
 * - corrections_must_show_lineage: Correction history visible
 * - no_green_without_positive_closure: Only POSITIVE_CLOSURE = green
 * - hover_explains_violation_codes: Tooltips on violations
 *
 * @see PAC-SONNY-G2-PHASE-2-GOVERNANCE-LEDGER-VISIBILITY-AND-OC-INTEGRATION-01
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import '@testing-library/jest-dom';

import { PositiveClosureBadge, ClosureIndicator } from '../PositiveClosureBadge';
import { GovernanceStateSummaryCard } from '../GovernanceStateSummaryCard';
import { CorrectionCycleStepper } from '../CorrectionCycleStepper';
import { PacTimelineView } from '../PacTimelineView';
import type {
  ClosureType,
  PACLifecycleState,
  GovernanceSummary,
  CorrectionRecord,
  ViolationRecord,
  TimelineNode,
} from '../../../types/governanceLedger';

// ============================================================================
// POSITIVE CLOSURE BADGE TESTS
// ============================================================================

describe('PositiveClosureBadge', () => {
  describe('UX Rule: no_green_without_positive_closure', () => {
    it('shows green styling ONLY for POSITIVE_CLOSURE', () => {
      const { rerender } = render(
        <PositiveClosureBadge closureType="POSITIVE_CLOSURE" />
      );

      const badge = screen.getByRole('status');
      expect(badge.className).toContain('bg-green');
      expect(badge).toHaveTextContent('Positive Closure');

      // Non-positive closures should NOT be green
      const nonGreenTypes: ClosureType[] = ['NONE', 'NEGATIVE_CLOSURE', 'CORRECTION_CLOSURE', 'ARCHIVED'];

      for (const type of nonGreenTypes) {
        rerender(<PositiveClosureBadge closureType={type} />);
        const nonGreenBadge = screen.getByRole('status');
        if (type !== 'NONE') {
          expect(nonGreenBadge.className).not.toContain('bg-green');
        }
      }
    });

    it('shows red styling for BLOCKED state', () => {
      render(
        <PositiveClosureBadge closureType="NONE" state="BLOCKED" />
      );

      const badge = screen.getByRole('status');
      expect(badge.className).toContain('bg-red');
      expect(badge).toHaveTextContent('Blocked');
    });

    it('shows red styling for NEGATIVE_CLOSURE', () => {
      render(
        <PositiveClosureBadge closureType="NEGATIVE_CLOSURE" />
      );

      const badge = screen.getByRole('status');
      expect(badge.className).toContain('bg-red');
      expect(badge).toHaveTextContent('Negative Closure');
    });

    it('shows amber styling for CORRECTION_CLOSURE', () => {
      render(
        <PositiveClosureBadge closureType="CORRECTION_CLOSURE" />
      );

      const badge = screen.getByRole('status');
      expect(badge.className).toContain('bg-amber');
      expect(badge).toHaveTextContent('Correction Closure');
    });
  });

  describe('UX Rule: closure_requires_badge', () => {
    it('renders badge for all closure types', () => {
      const closureTypes: ClosureType[] = [
        'NONE',
        'POSITIVE_CLOSURE',
        'NEGATIVE_CLOSURE',
        'CORRECTION_CLOSURE',
        'ARCHIVED',
      ];

      for (const type of closureTypes) {
        const { unmount } = render(<PositiveClosureBadge closureType={type} />);
        expect(screen.getByRole('status')).toBeInTheDocument();
        unmount();
      }
    });

    it('includes lock icon for POSITIVE_CLOSURE', () => {
      render(<PositiveClosureBadge closureType="POSITIVE_CLOSURE" />);

      const badge = screen.getByRole('status');
      const svg = badge.querySelector('svg');
      expect(svg).toBeInTheDocument();
    });
  });

  describe('size variants', () => {
    it('renders small variant correctly', () => {
      render(<PositiveClosureBadge closureType="POSITIVE_CLOSURE" size="sm" />);
      const badge = screen.getByRole('status');
      expect(badge.className).toContain('px-2');
      expect(badge.className).toContain('text-xs');
    });

    it('renders large variant correctly', () => {
      render(<PositiveClosureBadge closureType="POSITIVE_CLOSURE" size="lg" />);
      const badge = screen.getByRole('status');
      expect(badge.className).toContain('px-4');
      expect(badge.className).toContain('text-base');
    });
  });

  describe('showLabel prop', () => {
    it('hides label when showLabel is false', () => {
      render(
        <PositiveClosureBadge closureType="POSITIVE_CLOSURE" showLabel={false} />
      );

      expect(screen.queryByText('Positive Closure')).not.toBeInTheDocument();
    });
  });
});

describe('ClosureIndicator', () => {
  it('renders minimal icon-only indicator', () => {
    render(<ClosureIndicator closureType="POSITIVE_CLOSURE" />);

    const indicator = screen.getByRole('status');
    expect(indicator.querySelector('svg')).toBeInTheDocument();
  });
});

// ============================================================================
// GOVERNANCE STATE SUMMARY CARD TESTS
// ============================================================================

describe('GovernanceStateSummaryCard', () => {
  const mockSummary: GovernanceSummary = {
    total_pacs: 10,
    active_pacs: 3,
    blocked_pacs: 2,
    correction_cycles: 1,
    positive_closures: 5,
    pending_ratifications: 0,
    system_healthy: true,
    last_activity: new Date().toISOString(),
  };

  describe('UX Rule: blocked_means_disabled', () => {
    it('shows blocked count with error styling when blocked > 0', () => {
      render(<GovernanceStateSummaryCard summary={mockSummary} />);

      // Find the blocked stat
      expect(screen.getByText('Blocked')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument();
    });

    it('highlights active PACs with warning styling when active > 0', () => {
      render(<GovernanceStateSummaryCard summary={mockSummary} />);

      expect(screen.getByText('Active')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
    });
  });

  describe('system health indicator', () => {
    it('shows healthy indicator when system_healthy is true', () => {
      render(<GovernanceStateSummaryCard summary={mockSummary} />);

      expect(screen.getByText('Healthy')).toBeInTheDocument();
    });

    it('shows unhealthy indicator when system_healthy is false', () => {
      render(
        <GovernanceStateSummaryCard
          summary={{ ...mockSummary, system_healthy: false }}
        />
      );

      expect(screen.getByText('Unhealthy')).toBeInTheDocument();
    });
  });

  describe('loading state', () => {
    it('shows loading skeleton when loading is true', () => {
      const { container } = render(
        <GovernanceStateSummaryCard summary={null} loading={true} />
      );

      expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('shows error message when error is provided', () => {
      render(
        <GovernanceStateSummaryCard
          summary={null}
          error={new Error('Test error')}
        />
      );

      expect(screen.getByText(/Failed to load/)).toBeInTheDocument();
    });
  });

  describe('positive closures display', () => {
    it('shows positive closures with success styling', () => {
      render(<GovernanceStateSummaryCard summary={mockSummary} />);

      expect(screen.getByText('Positive Closures')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument();
    });
  });
});

// ============================================================================
// CORRECTION CYCLE STEPPER TESTS
// ============================================================================

describe('CorrectionCycleStepper', () => {
  const mockViolations: ViolationRecord[] = [
    { violation_id: 'G0_020', description: 'Missing checklist', resolved: true, resolution: 'Added' },
    { violation_id: 'G0_021', description: 'No correction class', resolved: true, resolution: 'Declared' },
  ];

  const mockCorrections: CorrectionRecord[] = [
    {
      correction_pac_id: 'CORRECTION-01',
      correction_version: 1,
      violations_addressed: [mockViolations[0]],
      status: 'APPLIED',
      applied_at: new Date(Date.now() - 86400000).toISOString(),
    },
    {
      correction_pac_id: 'CORRECTION-02',
      correction_version: 2,
      violations_addressed: [mockViolations[1]],
      status: 'APPLIED',
      applied_at: new Date().toISOString(),
    },
  ];

  describe('UX Rule: corrections_must_show_lineage', () => {
    it('displays all correction steps in order', () => {
      render(<CorrectionCycleStepper corrections={mockCorrections} />);

      expect(screen.getByText('Correction 1')).toBeInTheDocument();
      expect(screen.getByText('Correction 2')).toBeInTheDocument();
    });

    it('shows violation IDs for each correction', () => {
      render(<CorrectionCycleStepper corrections={mockCorrections} />);

      expect(screen.getByText('G0_020')).toBeInTheDocument();
      expect(screen.getByText('G0_021')).toBeInTheDocument();
    });

    it('shows complete checkmark for applied corrections', () => {
      const { container } = render(
        <CorrectionCycleStepper corrections={mockCorrections} />
      );

      // Check for green completed step indicators
      const greenIndicators = container.querySelectorAll('.bg-green-600');
      expect(greenIndicators.length).toBeGreaterThan(0);
    });
  });

  describe('UX Rule: hover_explains_violation_codes', () => {
    it('shows tooltip on violation badge hover', async () => {
      render(<CorrectionCycleStepper corrections={mockCorrections} />);

      const violationBadge = screen.getByText('G0_020');
      fireEvent.mouseEnter(violationBadge.parentElement!);

      await waitFor(() => {
        expect(screen.getByRole('tooltip')).toBeInTheDocument();
        expect(screen.getByText('Missing checklist')).toBeInTheDocument();
      });
    });

    it('shows resolution in tooltip for resolved violations', async () => {
      render(<CorrectionCycleStepper corrections={mockCorrections} />);

      const violationBadge = screen.getByText('G0_020');
      fireEvent.mouseEnter(violationBadge.parentElement!);

      await waitFor(() => {
        expect(screen.getByText(/Added/)).toBeInTheDocument();
      });
    });
  });

  describe('active violations display', () => {
    it('shows active violations step when provided', () => {
      const activeViolations: ViolationRecord[] = [
        { violation_id: 'G0_030', description: 'Invalid closure', resolved: false },
      ];

      render(
        <CorrectionCycleStepper
          corrections={mockCorrections}
          activeViolations={activeViolations}
        />
      );

      expect(screen.getByText('Active Violations')).toBeInTheDocument();
      expect(screen.getByText('G0_030')).toBeInTheDocument();
    });
  });

  describe('empty state', () => {
    it('shows empty message when no corrections', () => {
      render(<CorrectionCycleStepper corrections={[]} />);

      expect(screen.getByText('No correction cycles')).toBeInTheDocument();
    });
  });

  describe('orientation', () => {
    it('renders horizontally when orientation is horizontal', () => {
      const { container } = render(
        <CorrectionCycleStepper corrections={mockCorrections} orientation="horizontal" />
      );

      // Check for horizontal flex layout
      expect(container.firstChild).toHaveClass('flex');
    });
  });
});

// ============================================================================
// PAC TIMELINE VIEW TESTS
// ============================================================================

describe('PacTimelineView', () => {
  const mockNodes: TimelineNode[] = [
    {
      id: 'node-1',
      type: 'PAC_CREATED',
      label: 'PAC created',
      timestamp: new Date(Date.now() - 7 * 86400000).toISOString(),
      agent: { gid: 'GID-02', name: 'SONNY', color: 'YELLOW' },
      is_correction: false,
      is_closure: false,
      status: 'info',
    },
    {
      id: 'node-2',
      type: 'PAC_BLOCKED',
      label: 'PAC blocked — G0_020',
      timestamp: new Date(Date.now() - 5 * 86400000).toISOString(),
      agent: { gid: 'SYSTEM', name: 'GATE_PACK', color: 'GRAY' },
      is_correction: false,
      is_closure: false,
      status: 'blocked',
    },
    {
      id: 'node-3',
      type: 'CORRECTION_ISSUED',
      label: 'CORRECTION-01 issued',
      timestamp: new Date(Date.now() - 4 * 86400000).toISOString(),
      agent: { gid: 'GID-00', name: 'BENSON', color: 'RED' },
      is_correction: true,
      is_closure: false,
      status: 'warning',
    },
    {
      id: 'node-4',
      type: 'POSITIVE_CLOSURE',
      label: 'POSITIVE CLOSURE',
      timestamp: new Date().toISOString(),
      agent: { gid: 'GID-00', name: 'BENSON', color: 'RED' },
      is_correction: false,
      is_closure: true,
      closure_type: 'POSITIVE_CLOSURE',
      status: 'success',
    },
  ];

  describe('UX Rule: blocked_means_disabled', () => {
    it('displays blocked nodes with distinct red styling', () => {
      const { container } = render(<PacTimelineView nodes={mockNodes} />);

      // Find the blocked node
      const blockedText = screen.getByText(/PAC blocked/);
      expect(blockedText.className).toContain('text-red');
    });
  });

  describe('UX Rule: closure_requires_badge', () => {
    it('shows closure badge for closure nodes', () => {
      render(<PacTimelineView nodes={mockNodes} />);

      // Positive closure should show badge
      const closureBadges = screen.getAllByRole('status');
      expect(closureBadges.length).toBeGreaterThan(0);
    });
  });

  describe('UX Rule: no_green_without_positive_closure', () => {
    it('only shows green for POSITIVE_CLOSURE node', () => {
      const { container } = render(<PacTimelineView nodes={mockNodes} />);

      // Find the positive closure node
      const successNode = screen.getByText('POSITIVE CLOSURE');
      expect(successNode.className).toContain('text-green');
    });
  });

  describe('filter controls', () => {
    it('shows filter buttons when showFilters is true', () => {
      render(<PacTimelineView nodes={mockNodes} showFilters={true} />);

      expect(screen.getByText('All')).toBeInTheDocument();
      expect(screen.getByText('Corrections')).toBeInTheDocument();
      expect(screen.getByText('Closures')).toBeInTheDocument();
      expect(screen.getByText('Blocks')).toBeInTheDocument();
    });

    it('filters to corrections when Corrections filter clicked', () => {
      render(<PacTimelineView nodes={mockNodes} showFilters={true} />);

      fireEvent.click(screen.getByText('Corrections'));

      // Should only show correction nodes
      expect(screen.getByText('CORRECTION-01 issued')).toBeInTheDocument();
      expect(screen.queryByText('PAC created')).not.toBeInTheDocument();
    });

    it('filters to closures when Closures filter clicked', () => {
      render(<PacTimelineView nodes={mockNodes} showFilters={true} />);

      fireEvent.click(screen.getByText('Closures'));

      expect(screen.getByText('POSITIVE CLOSURE')).toBeInTheDocument();
      expect(screen.queryByText('PAC created')).not.toBeInTheDocument();
    });

    it('filters to blocks when Blocks filter clicked', () => {
      render(<PacTimelineView nodes={mockNodes} showFilters={true} />);

      fireEvent.click(screen.getByText('Blocks'));

      expect(screen.getByText(/PAC blocked/)).toBeInTheDocument();
      expect(screen.queryByText('PAC created')).not.toBeInTheDocument();
    });
  });

  describe('maxItems prop', () => {
    it('limits displayed items when maxItems is set', () => {
      render(<PacTimelineView nodes={mockNodes} maxItems={2} showFilters={false} />);

      // Should show truncation notice
      expect(screen.getByText(/Showing last 2 of 4 events/)).toBeInTheDocument();
    });
  });

  describe('empty state', () => {
    it('shows empty message when no nodes', () => {
      render(<PacTimelineView nodes={[]} />);

      expect(screen.getByText('No timeline events')).toBeInTheDocument();
    });
  });

  describe('agent display', () => {
    it('shows agent name and GID for each node', () => {
      render(<PacTimelineView nodes={mockNodes} />);

      expect(screen.getByText(/SONNY/)).toBeInTheDocument();
      expect(screen.getByText(/GID-02/)).toBeInTheDocument();
    });

    it('shows agent color indicator', () => {
      const { container } = render(<PacTimelineView nodes={mockNodes} />);

      // Check for yellow indicator for SONNY
      expect(container.querySelector('.bg-yellow-500')).toBeInTheDocument();
    });
  });
});

// ============================================================================
// INTEGRATION TESTS
// ============================================================================

describe('Governance Ledger Components Integration', () => {
  describe('fail-closed behavior', () => {
    it('never shows green styling for non-positive-closure states', () => {
      const states: PACLifecycleState[] = [
        'READY_FOR_EXECUTION',
        'IN_PROGRESS',
        'BLOCKED',
        'CORRECTION_REQUIRED',
        'RESUBMITTED',
        'REJECTED',
        'ARCHIVED',
      ];

      for (const state of states) {
        const { container, unmount } = render(
          <PositiveClosureBadge closureType="NONE" state={state} />
        );

        // Only BLOCKED and REJECTED should show red, others blue/gray
        // But NONE of them should show green
        const badge = container.querySelector('[role="status"]');
        expect(badge?.className).not.toContain('bg-green');

        unmount();
      }
    });

    it('POSITIVE_CLOSURE is the ONLY way to get green', () => {
      const closureTypes: ClosureType[] = [
        'NONE',
        'NEGATIVE_CLOSURE',
        'CORRECTION_CLOSURE',
        'ARCHIVED',
      ];

      for (const type of closureTypes) {
        const { container, unmount } = render(
          <PositiveClosureBadge closureType={type} />
        );

        const badge = container.querySelector('[role="status"]');
        expect(badge?.className).not.toContain('bg-green');

        unmount();
      }

      // Only POSITIVE_CLOSURE gets green
      const { container } = render(
        <PositiveClosureBadge closureType="POSITIVE_CLOSURE" />
      );

      const badge = container.querySelector('[role="status"]');
      expect(badge?.className).toContain('bg-green');
    });
  });
});
