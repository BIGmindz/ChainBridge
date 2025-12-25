/**
 * GovernanceStatePanel Tests — PAC-SONNY-G1-PHASE-2-OPERATOR-VISIBILITY-AND-GOVERNANCE-UX-LOCK-01
 *
 * 🟡 SONNY | GID-02
 *
 * Tests verify:
 * - All governance states render correctly
 * - State labels displayed accurately
 * - Visual indicators match state severity
 * - Loading state displays skeleton
 * - Error state displays prominently
 * - Block details shown when active
 * - Escalation counts displayed
 * - Refresh button triggers context reload
 *
 * @see PAC-SONNY-G1-PHASE-2-OPERATOR-VISIBILITY-AND-GOVERNANCE-UX-LOCK-01
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

import {
  GovernanceStatePanel,
  GovernanceStateIndicator,
} from '../GovernanceStatePanel';
import * as governanceHook from '../../../hooks/useGovernanceState';
import type { UseGovernanceStateResult } from '../../../hooks/useGovernanceState';
import type { GovernanceContext, GovernanceUIState, EscalationLevel, PACStatus } from '../../../types/governanceState';

/**
 * Create mock governance state result.
 */
function createMockGovernanceState(
  overrides: Partial<UseGovernanceStateResult> = {}
): UseGovernanceStateResult {
  const defaults: UseGovernanceStateResult = {
    context: null,
    isLoading: false,
    error: null,
    state: 'OPEN',
    escalationLevel: 'NONE',
    isBlocked: false,
    hasEscalation: false,
    actionsEnabled: true,
    bannerRequired: false,
    allowedAction: null,
    bannerSeverity: 'info',
    refresh: vi.fn(),
  };
  return { ...defaults, ...overrides };
}

/**
 * Create full governance context for a state.
 */
function createContext(state: GovernanceUIState): GovernanceContext {
  return {
    state,
    escalation_level: 'NONE',
    active_blocks: state === 'BLOCKED' ? [
      {
        rule_code: 'GOV-001',
        reason: 'Unauthorized action detected',
        triggered_by_gid: 'GID-07',
        correlation_id: 'corr-12345',
        blocked_at: new Date().toISOString(),
      },
    ] : [],
    pending_escalations: [],
    active_pacs: [{
      pac_id: 'PAC-SONNY-TEST-01',
      state: state === 'OPEN' ? 'OPEN' : state,
      owner_gid: 'GID-02',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }],
    recent_wraps: [],
    last_sync: new Date().toISOString(),
    system_healthy: state !== 'BLOCKED',
  };
}

describe('GovernanceStatePanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('State Display', () => {
    it('renders OPEN state with correct label', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'OPEN',
          context: createContext('OPEN'),
        })
      );

      render(<GovernanceStatePanel />);

      expect(screen.getByText('SYSTEM OPEN')).toBeInTheDocument();
      expect(screen.getByText('Governance gates passed. Actions enabled.')).toBeInTheDocument();
    });

    it('renders BLOCKED state with correct label', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'BLOCKED',
          isBlocked: true,
          context: createContext('BLOCKED'),
        })
      );

      render(<GovernanceStatePanel />);

      expect(screen.getByText('SYSTEM BLOCKED')).toBeInTheDocument();
      expect(screen.getByText('Governance gate failure. All actions disabled.')).toBeInTheDocument();
    });

    it('renders CORRECTION_REQUIRED state with correct label', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'CORRECTION_REQUIRED',
          context: createContext('CORRECTION_REQUIRED'),
        })
      );

      render(<GovernanceStatePanel />);

      expect(screen.getByText('CORRECTION REQUIRED')).toBeInTheDocument();
      expect(screen.getByText('PAC correction needed. Resubmit to proceed.')).toBeInTheDocument();
    });

    it('renders RESUBMITTED state with correct label', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'RESUBMITTED',
          context: createContext('RESUBMITTED'),
        })
      );

      render(<GovernanceStatePanel />);

      expect(screen.getByText('RESUBMITTED')).toBeInTheDocument();
      expect(screen.getByText('PAC resubmitted. Awaiting re-evaluation.')).toBeInTheDocument();
    });

    it('renders RATIFIED state with correct label', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'RATIFIED',
          context: createContext('RATIFIED'),
        })
      );

      render(<GovernanceStatePanel />);

      expect(screen.getByText('RATIFIED')).toBeInTheDocument();
      expect(screen.getByText('Authority ratified. Unblock system to proceed.')).toBeInTheDocument();
    });

    it('renders UNBLOCKED state with correct label', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'UNBLOCKED',
          context: createContext('UNBLOCKED'),
        })
      );

      render(<GovernanceStatePanel />);

      expect(screen.getByText('UNBLOCKED')).toBeInTheDocument();
      expect(screen.getByText('System unblocked. Normal operation resumed.')).toBeInTheDocument();
    });

    it('renders REJECTED state with correct label', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'REJECTED',
          context: createContext('REJECTED'),
        })
      );

      render(<GovernanceStatePanel />);

      expect(screen.getByText('REJECTED')).toBeInTheDocument();
      expect(screen.getByText('PAC rejected. Archive only.')).toBeInTheDocument();
    });
  });

  describe('Loading State', () => {
    it('displays loading skeleton when loading', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          isLoading: true,
          context: null,
        })
      );

      render(<GovernanceStatePanel />);

      // Should show loading state
      expect(screen.getByText('Loading governance state...')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('displays error prominently', () => {
      const testError = new Error('Failed to fetch governance state');
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          error: testError,
          isLoading: false,
        })
      );

      render(<GovernanceStatePanel />);

      expect(screen.getByText('Governance State Error')).toBeInTheDocument();
      expect(screen.getByText('Failed to fetch governance state')).toBeInTheDocument();
    });
  });

  describe('Block Details', () => {
    it('displays active block details when BLOCKED', () => {
      const context = createContext('BLOCKED');
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'BLOCKED',
          isBlocked: true,
          context,
        })
      );

      render(<GovernanceStatePanel />);

      // Expand details
      const expandButton = screen.getByRole('button', { name: /show details/i });
      fireEvent.click(expandButton);

      expect(screen.getByText('GOV-001')).toBeInTheDocument();
      expect(screen.getByText('Unauthorized action detected')).toBeInTheDocument();
    });

    it('shows block count badge', () => {
      const context = createContext('BLOCKED');
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'BLOCKED',
          isBlocked: true,
          context,
        })
      );

      render(<GovernanceStatePanel />);

      expect(screen.getByText('1 Block')).toBeInTheDocument();
    });
  });

  describe('PAC Status', () => {
    it('displays current PAC information', () => {
      const context = createContext('OPEN');
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'OPEN',
          context,
        })
      );

      render(<GovernanceStatePanel />);

      // Expand details to see PAC
      const expandButton = screen.getByRole('button', { name: /show details/i });
      fireEvent.click(expandButton);

      expect(screen.getByText('PAC-SONNY-TEST-01')).toBeInTheDocument();
    });
  });

  describe('Refresh Functionality', () => {
    it('calls refresh when refresh button clicked', () => {
      const mockRefresh = vi.fn();
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'OPEN',
          context: createContext('OPEN'),
          refresh: mockRefresh,
        })
      );

      render(<GovernanceStatePanel />);

      const refreshButton = screen.getByRole('button', { name: /refresh/i });
      fireEvent.click(refreshButton);

      expect(mockRefresh).toHaveBeenCalledTimes(1);
    });
  });

  describe('Expandable Details', () => {
    it('expands and collapses details section', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'OPEN',
          context: createContext('OPEN'),
        })
      );

      render(<GovernanceStatePanel />);

      // Initially collapsed
      expect(screen.queryByText('Active Blocks')).not.toBeInTheDocument();

      // Expand
      const expandButton = screen.getByRole('button', { name: /show details/i });
      fireEvent.click(expandButton);

      // Now visible
      expect(screen.getByText('No active blocks')).toBeInTheDocument();

      // Collapse again
      fireEvent.click(expandButton);

      // Hidden again
      expect(screen.queryByText('No active blocks')).not.toBeInTheDocument();
    });
  });
});

describe('GovernanceStateIndicator', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('Compact Display', () => {
    it('renders compact indicator for OPEN state', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'OPEN',
          context: createContext('OPEN'),
        })
      );

      render(<GovernanceStateIndicator />);

      expect(screen.getByText('OPEN')).toBeInTheDocument();
    });

    it('renders compact indicator for BLOCKED state', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'BLOCKED',
          isBlocked: true,
          context: createContext('BLOCKED'),
        })
      );

      render(<GovernanceStateIndicator />);

      expect(screen.getByText('BLOCKED')).toBeInTheDocument();
    });

    it('shows pulse animation when BLOCKED', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'BLOCKED',
          isBlocked: true,
          context: createContext('BLOCKED'),
        })
      );

      const { container } = render(<GovernanceStateIndicator />);

      // Should have pulse animation class
      const indicator = container.querySelector('[class*="animate-pulse"]');
      expect(indicator).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has appropriate aria labels', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'BLOCKED',
          isBlocked: true,
        })
      );

      render(<GovernanceStateIndicator />);

      const indicator = screen.getByRole('status');
      expect(indicator).toHaveAttribute('aria-label', expect.stringContaining('Governance'));
    });
  });
});

describe('Visual Severity Mapping', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('Color Coding', () => {
    it('uses emerald/green for OPEN state', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'OPEN',
          context: createContext('OPEN'),
        })
      );

      const { container } = render(<GovernanceStatePanel />);

      // Check for emerald color classes
      const greenElements = container.querySelectorAll('[class*="emerald"]');
      expect(greenElements.length).toBeGreaterThan(0);
    });

    it('uses rose/red for BLOCKED state', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'BLOCKED',
          isBlocked: true,
          context: createContext('BLOCKED'),
        })
      );

      const { container } = render(<GovernanceStatePanel />);

      // Check for rose color classes
      const redElements = container.querySelectorAll('[class*="rose"]');
      expect(redElements.length).toBeGreaterThan(0);
    });

    it('uses amber/yellow for CORRECTION_REQUIRED state', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'CORRECTION_REQUIRED',
          context: createContext('CORRECTION_REQUIRED'),
        })
      );

      const { container } = render(<GovernanceStatePanel />);

      // Check for amber color classes
      const amberElements = container.querySelectorAll('[class*="amber"]');
      expect(amberElements.length).toBeGreaterThan(0);
    });

    it('uses sky/blue for RATIFIED state', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'RATIFIED',
          context: createContext('RATIFIED'),
        })
      );

      const { container } = render(<GovernanceStatePanel />);

      // Check for sky color classes
      const blueElements = container.querySelectorAll('[class*="sky"]');
      expect(blueElements.length).toBeGreaterThan(0);
    });
  });
});

describe('Governance State Transitions Coverage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const states: GovernanceUIState[] = [
    'OPEN',
    'BLOCKED',
    'CORRECTION_REQUIRED',
    'RESUBMITTED',
    'RATIFIED',
    'UNBLOCKED',
    'REJECTED',
  ];

  describe.each(states)('State: %s', (state) => {
    it(`renders GovernanceStatePanel correctly for ${state}`, () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state,
          isBlocked: state === 'BLOCKED',
          context: createContext(state),
        })
      );

      render(<GovernanceStatePanel />);

      // All states should render without crashing
      expect(document.body).toBeInTheDocument();
    });

    it(`renders GovernanceStateIndicator correctly for ${state}`, () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state,
          isBlocked: state === 'BLOCKED',
          context: createContext(state),
        })
      );

      render(<GovernanceStateIndicator />);

      // All states should render without crashing
      expect(document.body).toBeInTheDocument();
    });
  });
});
