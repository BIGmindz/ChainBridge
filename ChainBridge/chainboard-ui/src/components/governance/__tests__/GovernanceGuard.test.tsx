/**
 * GovernanceGuard Tests — PAC-SONNY-G1-PHASE-2-OPERATOR-VISIBILITY-AND-GOVERNANCE-UX-LOCK-01
 *
 * 🟡 SONNY | GID-02
 *
 * Tests verify FAIL-CLOSED governance enforcement:
 * - Actions disabled when BLOCKED
 * - Actions disabled when CORRECTION_REQUIRED (except RESUBMIT_PAC)
 * - Actions disabled when REJECTED (except ARCHIVE)
 * - Actions enabled when OPEN/UNBLOCKED
 * - Lock icon displayed when disabled by governance
 * - Button click prevented when governance blocks
 * - Full-screen overlay renders when system blocked
 *
 * @see PAC-SONNY-G1-PHASE-2-OPERATOR-VISIBILITY-AND-GOVERNANCE-UX-LOCK-01
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

import {
  GovernanceGuard,
  GovernanceButton,
  GovernanceBlockedOverlay,
  useGovernanceAction,
} from '../GovernanceGuard';
import * as governanceHook from '../../../hooks/useGovernanceState';
import type { UseGovernanceStateResult } from '../../../hooks/useGovernanceState';
import type { GovernanceContext, GovernanceUIState, EscalationLevel } from '../../../types/governanceState';

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
 * Create mock governance context with blocks.
 */
function createBlockedContext(): GovernanceContext {
  return {
    state: 'BLOCKED',
    active_blocks: [
      {
        rule_code: 'GOV-001',
        reason: 'Unauthorized trade execution attempt',
        triggered_by_gid: 'GID-07',
        correlation_id: 'corr-12345',
        blocked_at: new Date().toISOString(),
      },
    ],
    pending_escalations: [],
    current_pac: null,
    current_wrap: null,
    last_updated: new Date().toISOString(),
    system_health: 'DEGRADED',
  };
}

describe('GovernanceGuard', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('Fail-Closed Behavior', () => {
    it('disables children when state is BLOCKED', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'BLOCKED',
          isBlocked: true,
          actionsEnabled: false,
        })
      );

      render(
        <GovernanceGuard>
          <button data-testid="action-btn">Execute</button>
        </GovernanceGuard>
      );

      const wrapper = screen.getByTestId('action-btn').parentElement;
      expect(wrapper).toHaveClass('pointer-events-none');
      expect(wrapper).toHaveClass('opacity-50');
    });

    it('disables children when state is CORRECTION_REQUIRED', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'CORRECTION_REQUIRED',
          actionsEnabled: false,
          allowedAction: 'RESUBMIT_PAC',
        })
      );

      render(
        <GovernanceGuard>
          <button data-testid="action-btn">Execute</button>
        </GovernanceGuard>
      );

      const wrapper = screen.getByTestId('action-btn').parentElement;
      expect(wrapper).toHaveClass('pointer-events-none');
    });

    it('allows children when state is OPEN', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'OPEN',
          actionsEnabled: true,
        })
      );

      render(
        <GovernanceGuard>
          <button data-testid="action-btn">Execute</button>
        </GovernanceGuard>
      );

      const button = screen.getByTestId('action-btn');
      // When allowed, children render directly without wrapper div
      expect(button.parentElement).not.toHaveClass('pointer-events-none');
    });

    it('allows specific action when it matches allowedAction', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'CORRECTION_REQUIRED',
          actionsEnabled: false,
          allowedAction: 'RESUBMIT_PAC',
        })
      );

      render(
        <GovernanceGuard actionType="RESUBMIT_PAC">
          <button data-testid="resubmit-btn">Resubmit PAC</button>
        </GovernanceGuard>
      );

      const button = screen.getByTestId('resubmit-btn');
      // Allowed actions render without disabled wrapper
      expect(button.parentElement).not.toHaveClass('pointer-events-none');
    });

    it('shows disabled reason as title when blocked', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'BLOCKED',
          actionsEnabled: false,
        })
      );

      render(
        <GovernanceGuard showReason>
          <button data-testid="action-btn">Execute</button>
        </GovernanceGuard>
      );

      const wrapper = screen.getByTestId('action-btn').parentElement;
      expect(wrapper).toHaveAttribute('title', 'System is blocked by governance. All actions disabled.');
    });
  });

  describe('Lock Icon Display', () => {
    it('displays lock icon overlay when disabled by governance', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'BLOCKED',
          actionsEnabled: false,
        })
      );

      render(
        <GovernanceGuard>
          <button data-testid="action-btn">Execute</button>
        </GovernanceGuard>
      );

      // Lock icon should be present in the overlay
      const lockIcon = document.querySelector('svg');
      expect(lockIcon).toBeInTheDocument();
    });
  });
});

describe('GovernanceButton', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('Fail-Closed Behavior', () => {
    it('renders disabled when state is BLOCKED', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'BLOCKED',
          isBlocked: true,
          actionsEnabled: false,
        })
      );

      render(<GovernanceButton>Execute Trade</GovernanceButton>);

      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });

    it('prevents click when governance blocks action', () => {
      const handleClick = vi.fn();
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'BLOCKED',
          isBlocked: true,
          actionsEnabled: false,
        })
      );

      render(<GovernanceButton onClick={handleClick}>Execute</GovernanceButton>);

      const button = screen.getByRole('button');
      fireEvent.click(button);

      expect(handleClick).not.toHaveBeenCalled();
    });

    it('allows click when governance is OPEN', () => {
      const handleClick = vi.fn();
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'OPEN',
          actionsEnabled: true,
        })
      );

      render(<GovernanceButton onClick={handleClick}>Execute</GovernanceButton>);

      const button = screen.getByRole('button');
      fireEvent.click(button);

      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('shows lock icon when disabled by governance', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'BLOCKED',
          isBlocked: true,
          actionsEnabled: false,
        })
      );

      render(<GovernanceButton showLockIcon>Execute</GovernanceButton>);

      // Lock icon should be rendered
      const lockIcon = document.querySelector('svg');
      expect(lockIcon).toBeInTheDocument();
    });

    it('shows disabled reason as title when governance blocks', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'REJECTED',
          actionsEnabled: false,
        })
      );

      render(<GovernanceButton>Execute</GovernanceButton>);

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('title', 'PAC rejected. Archive only.');
    });

    it('allows specific action matching allowedAction', () => {
      const handleClick = vi.fn();
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'REJECTED',
          actionsEnabled: false,
          allowedAction: 'ARCHIVE',
        })
      );

      render(
        <GovernanceButton actionType="ARCHIVE" onClick={handleClick}>
          Archive PAC
        </GovernanceButton>
      );

      const button = screen.getByRole('button');
      fireEvent.click(button);

      expect(handleClick).toHaveBeenCalledTimes(1);
    });
  });

  describe('Button Variants', () => {
    it('renders primary variant correctly', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({ state: 'OPEN', actionsEnabled: true })
      );

      render(<GovernanceButton variant="primary">Primary</GovernanceButton>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-sky-600');
    });

    it('renders danger variant correctly', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({ state: 'OPEN', actionsEnabled: true })
      );

      render(<GovernanceButton variant="danger">Danger</GovernanceButton>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-rose-600');
    });
  });

  describe('Size Variants', () => {
    it('renders small size correctly', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({ state: 'OPEN', actionsEnabled: true })
      );

      render(<GovernanceButton size="sm">Small</GovernanceButton>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('text-xs');
    });

    it('renders large size correctly', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({ state: 'OPEN', actionsEnabled: true })
      );

      render(<GovernanceButton size="lg">Large</GovernanceButton>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('text-base');
    });
  });
});

describe('GovernanceBlockedOverlay', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('Visibility', () => {
    it('renders when system is BLOCKED', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'BLOCKED',
          isBlocked: true,
          context: createBlockedContext(),
        })
      );

      render(<GovernanceBlockedOverlay />);

      expect(screen.getByText('System Blocked')).toBeInTheDocument();
      expect(
        screen.getByText('Governance has blocked system operations. All actions are disabled.')
      ).toBeInTheDocument();
    });

    it('does not render when system is OPEN', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'OPEN',
          isBlocked: false,
        })
      );

      render(<GovernanceBlockedOverlay />);

      expect(screen.queryByText('System Blocked')).not.toBeInTheDocument();
    });

    it('does not render when system is CORRECTION_REQUIRED', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'CORRECTION_REQUIRED',
          isBlocked: false,
        })
      );

      render(<GovernanceBlockedOverlay />);

      expect(screen.queryByText('System Blocked')).not.toBeInTheDocument();
    });
  });

  describe('Block Details Display', () => {
    it('displays block rule code', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'BLOCKED',
          isBlocked: true,
          context: createBlockedContext(),
        })
      );

      render(<GovernanceBlockedOverlay />);

      expect(screen.getByText('GOV-001')).toBeInTheDocument();
    });

    it('displays block reason', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'BLOCKED',
          isBlocked: true,
          context: createBlockedContext(),
        })
      );

      render(<GovernanceBlockedOverlay />);

      expect(screen.getByText('Unauthorized trade execution attempt')).toBeInTheDocument();
    });

    it('displays triggered by GID', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'BLOCKED',
          isBlocked: true,
          context: createBlockedContext(),
        })
      );

      render(<GovernanceBlockedOverlay />);

      expect(screen.getByText('by GID-07')).toBeInTheDocument();
    });

    it('displays correlation ID', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'BLOCKED',
          isBlocked: true,
          context: createBlockedContext(),
        })
      );

      render(<GovernanceBlockedOverlay />);

      expect(screen.getByText('Correlation: corr-12345')).toBeInTheDocument();
    });
  });

  describe('User Guidance', () => {
    it('displays escalation guidance message', () => {
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state: 'BLOCKED',
          isBlocked: true,
          context: createBlockedContext(),
        })
      );

      render(<GovernanceBlockedOverlay />);

      expect(
        screen.getByText('Contact your Guardian or Administrator to resolve this block.')
      ).toBeInTheDocument();
    });
  });
});

describe('useGovernanceAction Hook', () => {
  // Note: Testing hooks directly requires renderHook from @testing-library/react
  // These tests verify the hook behavior through component integration

  it('blocks handler execution when governance is blocked', () => {
    const handleAction = vi.fn();
    vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
      createMockGovernanceState({
        state: 'BLOCKED',
        actionsEnabled: false,
      })
    );

    // Test through GovernanceButton which uses similar logic
    render(<GovernanceButton onClick={handleAction}>Execute</GovernanceButton>);

    const button = screen.getByRole('button');
    fireEvent.click(button);

    expect(handleAction).not.toHaveBeenCalled();
  });

  it('allows handler execution when governance is open', () => {
    const handleAction = vi.fn();
    vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
      createMockGovernanceState({
        state: 'OPEN',
        actionsEnabled: true,
      })
    );

    render(<GovernanceButton onClick={handleAction}>Execute</GovernanceButton>);

    const button = screen.getByRole('button');
    fireEvent.click(button);

    expect(handleAction).toHaveBeenCalledTimes(1);
  });
});

describe('Governance State Transitions', () => {
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
    it(`renders button correctly for ${state}`, () => {
      const isActionState = state === 'OPEN' || state === 'UNBLOCKED';
      vi.spyOn(governanceHook, 'useGovernanceState').mockReturnValue(
        createMockGovernanceState({
          state,
          actionsEnabled: isActionState,
          isBlocked: state === 'BLOCKED',
        })
      );

      render(<GovernanceButton>Action</GovernanceButton>);

      const button = screen.getByRole('button');
      if (isActionState) {
        expect(button).not.toBeDisabled();
      } else {
        expect(button).toBeDisabled();
      }
    });
  });
});
